import os
import uuid
import logging
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks, HTTPException
from src import config
from src.schemas import (
    JobRequest, JobResult, StatusEnum, Summary, Metric,
    Finding, Evidence, Recommendation, Warning_, Trace, ConfidenceEnum
)
from src.services import calculos, rag, llm_client
from src.jobs_store import store


# config y logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
log = logging.getLogger("sgtech-service")

app = FastAPI(title="SG Tech Energy Audit Service", version="0.1.0")

# helpers
def ruta_segura_dataset(filename: str) -> Path:
    # rechazo absolutos y cualquier cosa con ".."
    if os.path.isabs(filename) or ".." in filename.split("/") or "\\" in filename:
        raise ValueError(f"Ruta insegura: {filename}")
    full = (config.DATASETS_DIR / filename).resolve()
    # mirar que en efecto este dentro del DATASETS_DIR
    if not str(full).startswith(str(config.DATASETS_DIR.resolve())):
        raise ValueError(f"Ruta fuera de DATASETS_DIR: {filename}")
    return full

def mapear_severidad_a_confidence(sev: str) -> ConfidenceEnum:
    if sev == "alta":
        return ConfidenceEnum.high
    elif sev == "media":
        return ConfidenceEnum.medium
    else:
        return ConfidenceEnum.low

def procesar_job(job_id: str, request: JobRequest):
    try:
        log.info(f"iniciando job {job_id}")
        store.update_status(job_id, "running")

        csv_path = ruta_segura_dataset(request.dataset_ref)
        if not csv_path.exists():
            raise FileNotFoundError(f"Dataset no existe: {request.dataset_ref}")

        resultado = calculos.procesar_todo(
            str(csv_path),
            period=request.period,
            facility=request.facility_filter,
        )

        docs = rag.cargar_docs(config.CONTEXT_DIR)
        all_chunks = []
        for doc_name, texto in docs.items():
            all_chunks.extend(rag.chunkear(texto, doc_name))

        agg = resultado["metricas_agregadas"]
        metrics_list = [
            Metric(name="total_energy_kwh", value=agg["total_energy_kwh"] if agg["total_energy_kwh"] is not None else "N/A", unit="kWh"),
            Metric(name="total_production_units", value=agg["total_production_units"] if agg["total_production_units"] is not None else "N/A", unit="unit"),
            Metric(name="total_estimated_emissions_kg", value=round(agg["total_estimated_emissions_kg"], 2) if agg["total_estimated_emissions_kg"] else "N/A", unit="kgCO2e"),
            Metric(name="avg_kwh_per_unit", value=round(agg["avg_kwh_per_unit"], 4) if agg["avg_kwh_per_unit"] else "N/A", unit="kWh/unit"),
            Metric(name="avg_variance_vs_target_pct", value=round(agg["avg_variance_vs_target_pct"], 2) if agg["avg_variance_vs_target_pct"] is not None else "N/A", unit="%"),
            Metric(name="records_count", value=agg["records_count"], unit="count"),
        ]

        findings_list = []
        for h in resultado["hallazgos"]:
            refs = rag.recuperar_contexto_para_hallazgo(all_chunks, h)
            statement = llm_client.redactar_hallazgo(h, refs)
            f = Finding(
                id=h["id"],
                type=f"sobreconsumo_{h['severity']}",
                statement=statement,
                evidence=Evidence(
                    dataset_fields=["energy_kwh", "production_units", "target_kwh_per_unit", "facility_id", "equipment_id", "period"],
                    document_refs=refs if len(refs) > 0 else ["criterios#p0"],
                ),
                confidence=mapear_severidad_a_confidence(h["severity"]),
            )
            findings_list.append(f)

        recs_list = []
        for i, h in enumerate(resultado["hallazgos"], start=1):
            texto = llm_client.redactar_recomendacion([h["id"]], h["severity"])
            rec = Recommendation(
                id=f"R-{i:03d}",
                text=texto,
                based_on_findings=[h["id"]],
                disclaimer="Draft subject to human review",
            )
            recs_list.append(rec)

        warn_list = [Warning_(code=w["code"], message=w["message"]) for w in resultado["warnings"]]

        status_final = StatusEnum.warning if len(warn_list) > 0 else StatusEnum.success

        trace = Trace(
            prompt_version=config.PROMPT_VERSION,
            documents_used=[request.dataset_ref, "contexto_criterios_hallazgos.md",
                            "contexto_recomendaciones.md", "contexto_salida_estructurada.md"],
            rules_applied=[
                "kwh_per_unit = energy_kwh / production_units",
                "variance_vs_target_pct = ((kwh_per_unit - target) / target) * 100",
                "estimated_emissions_kg = energy_kwh * co2_factor_kg_per_kwh",
                "severidad: baja 0-5%, media 5-12%, alta >12%",
                "LLM solo redacta, no calcula",
            ],
        )

        final = JobResult(
            job_id=job_id,
            status=status_final,
            summary=Summary(
                period=request.period or "ALL",
                dataset_ref=request.dataset_ref,
            ),
            metrics=metrics_list,
            findings=findings_list,
            recommendations_draft=recs_list,
            warnings=warn_list,
            trace=trace,
        )

        store.set_result(job_id, final.model_dump(mode="json"), status="done")
        log.info(f"job {job_id} terminado ok")

    except Exception as e:
        # OJO: no expongo el traceback completo al usuario, solo un mensaje generico
        log.exception(f"error en job {job_id}: {e}")
        error_result = {
            "job_id": job_id,
            "status": "error",
            "summary": {"period": request.period or "ALL", "dataset_ref": request.dataset_ref},
            "metrics": [],
            "findings": [],
            "recommendations_draft": [],
            "warnings": [{"code": "INTERNAL_ERROR", "message": "Error procesando el job. Revisar logs del servicio."}],
            "trace": {
                "prompt_version": config.PROMPT_VERSION,
                "documents_used": [request.dataset_ref],
                "rules_applied": [],
            },
        }
        store.set_result(job_id, error_result, status="error")

# endpoints
@app.get("/")
def root():
    return {"service": "sgtech-energy-audit", "status": "up"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/jobs")
def crear_job(req: JobRequest, bg: BackgroundTasks):
    job_id = str(uuid.uuid4())
    store.create(job_id, req.model_dump())
    bg.add_task(procesar_job, job_id, req)
    log.info(f"job creado {job_id} dataset={req.dataset_ref}")
    return {"job_id": job_id, "status": "pending"}

@app.get("/jobs/{job_id}")
def obtener_job(job_id: str):
    j = store.get(job_id)
    if j is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    if j["status"] in ("pending", "running"):
        return {"job_id": job_id, "status": j["status"]}
    return j["result"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)