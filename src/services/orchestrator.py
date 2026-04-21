import logging
from pathlib import Path
from typing import List
from src import config
from src.schema import (
    ConfidenceEnum, Evidence, Finding, JobRequest, JobResult, Metric,
    Recommendation, StatusEnum, Summary, Trace, WarningItem,
)
from src.security import ruta_segura
from src.services import calculos, llm_client, rag
from src.validators import validar_output
from src.jobs_store import store

log = logging.getLogger(__name__)

def _severidad_a_confidence(sev: str) -> ConfidenceEnum:
    if sev == "alta":
        return ConfidenceEnum.high
    if sev == "media":
        return ConfidenceEnum.medium
    return ConfidenceEnum.low

def _metricas_agregadas_a_lista(agg: dict) -> List[Metric]:
    posibles = [
        ("total_energy_kwh", agg.get("total_energy_kwh"), "kWh", None),
        ("total_production_units", agg.get("total_production_units"), "unit", None),
        ("total_estimated_emissions_kg", agg.get("total_estimated_emissions_kg"), "kgCO2e", 2),
        ("avg_kwh_per_unit", agg.get("avg_kwh_per_unit"), "kWh/unit", 4),
        ("avg_variance_vs_target_pct", agg.get("avg_variance_vs_target_pct"), "%", 2),
        ("records_count", agg.get("records_count"), "count", None),
    ]
    metrics: List[Metric] = []
    for nombre, valor, unidad, decimales in posibles:
        if valor is None:
            continue
        if decimales is not None and isinstance(valor, float):
            valor = round(valor, decimales)
        metrics.append(Metric(name=nombre, value=valor, unit=unidad))
    return metrics

def procesar_job(job_id: str, request: JobRequest) -> None:
    try:
        log.info(f"iniciando job {job_id}")
        store.update_status(job_id, "running")

        csv_path = ruta_segura(request.dataset_ref, config.DATASETS_DIR)
        if not csv_path.exists():
            raise FileNotFoundError(f"Dataset no existe: {request.dataset_ref}")

        resultado = calculos.procesar_todo(
            str(csv_path),
            period=request.period,
            facility=request.facility_filter,
        )

        docs = rag.cargar_docs(config.CONTEXT_DIR)
        all_chunks = []
        for nombre, texto in docs.items():
            all_chunks.extend(rag.chunkear(texto, nombre))
        documentos_disponibles = list(docs.keys())

        metrics_list = _metricas_agregadas_a_lista(resultado["metricas_agregadas"])

        findings_list: List[Finding] = []
        for h in resultado["hallazgos"]:
            refs = rag.recuperar_contexto_para_hallazgo(all_chunks, h)
            statement = llm_client.redactar_hallazgo(h, refs)
            findings_list.append(Finding(
                id=h["id"],
                type=f"sobreconsumo_{h['severity']}",
                statement=statement,
                evidence=Evidence(
                    dataset_fields=[
                        "energy_kwh", "production_units", "target_kwh_per_unit",
                        "facility_id", "equipment_id", "period",
                    ],
                    document_refs=refs if refs else ["criterios_hallazgos#p0"],
                ),
                confidence=_severidad_a_confidence(h["severity"]),
            ))

        recs_list: List[Recommendation] = []
        for i, h in enumerate(resultado["hallazgos"], start=1):
            texto = llm_client.redactar_recomendacion([h["id"]], h["severity"])
            recs_list.append(Recommendation(
                id=f"R-{i:03d}",
                text=texto,
                based_on_findings=[h["id"]],
            ))

        warn_list = [WarningItem(code=w["code"], message=w["message"]) for w in resultado["warnings"]]

        if resultado["metricas_agregadas"]["records_count"] == 0:
            warn_list.append(WarningItem(
                code="NO_DATA_FOR_FILTER",
                message="Filtros aplicados no arrojaron registros. Revise period/facility_filter.",
            ))

        if len(findings_list) == 0 and resultado["metricas_agregadas"]["records_count"] > 0:
            warn_list.append(WarningItem(
                code="NO_FINDINGS",
                message="No se detectaron desviaciones por sobre el target en el periodo evaluado.",
            ))

        if len(warn_list) > 0 and len(findings_list) == 0 and resultado["metricas_agregadas"]["records_count"] == 0:
            status_final = StatusEnum.error
        elif len(warn_list) > 0:
            status_final = StatusEnum.warning
        else:
            status_final = StatusEnum.success

        trace = Trace(
            prompt_version=config.PROMPT_VERSION,
            documents_used=[request.dataset_ref] + [f"{d}.md" for d in documentos_disponibles],
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

        payload = final.model_dump(mode="json")

        schema_path = config.DATA_DIR / "output_schema.json"
        if schema_path.exists():
            errores = validar_output(payload, schema_path)
            if errores:
                log.error(f"job {job_id} fallo validacion contra output_schema: {errores}")
                payload["warnings"].append({
                    "code": "SCHEMA_VALIDATION_FAILED",
                    "message": "Output no cumple output_schema.json. Ver logs del servicio.",
                })
                payload["status"] = StatusEnum.warning.value

        store.set_result(job_id, payload, status="done")
        log.info(f"job {job_id} terminado status={payload.get('status')}")

    except ValueError as e:
        log.warning(f"job {job_id} rechazado por validacion: {e}")
        store.set_result(job_id, _error_payload(job_id, request, "INVALID_INPUT", str(e)), status="error")
    except FileNotFoundError as e:
        log.warning(f"job {job_id} dataset no encontrado")
        store.set_result(job_id, _error_payload(job_id, request, "DATASET_NOT_FOUND", str(e)), status="error")
    except Exception as e:
        # No exponemos el error real al cliente, solo codigo generico.
        log.exception(f"error interno job {job_id}: {type(e).__name__}")
        store.set_result(
            job_id,
            _error_payload(job_id, request, "INTERNAL_ERROR", "Error procesando el job. Revisar logs del servicio."),
            status="error",
        )

def _error_payload(job_id: str, request: JobRequest, code: str, message: str) -> dict:
    return {
        "job_id": job_id,
        "status": "error",
        "summary": {"period": request.period or "ALL", "dataset_ref": request.dataset_ref},
        "metrics": [],
        "findings": [],
        "recommendations_draft": [],
        "warnings": [{"code": code, "message": message}],
        "trace": {
            "prompt_version": config.PROMPT_VERSION,
            "documents_used": [request.dataset_ref],
            "rules_applied": [],
        },
    }
