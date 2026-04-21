import logging
import uuid
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from src import config
from src.jobs_store import store
from src.schema import JobRequest
from src.services.orchestrator import procesar_job

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("sgtech-service")

MAX_BODY_BYTES = 64 * 1024

app = FastAPI(title="SG Tech Energy Audit Service", version="1.0.0")

@app.middleware("http")
async def limitar_body_size(request: Request, call_next):
    cl = request.headers.get("content-length")
    if cl is not None:
        try:
            if int(cl) > MAX_BODY_BYTES:
                return JSONResponse(status_code=413, content={"detail": "Request body too large"})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})
    return await call_next(request)
@app.get("/")
def root():
    return {"service": "sgtech-energy-audit", "status": "up", "version": app.version}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/jobs", status_code=202)
def crear_job(req: JobRequest, bg: BackgroundTasks):
    job_id = str(uuid.uuid4())
    store.create(job_id, req.model_dump())
    bg.add_task(procesar_job, job_id, req)
    # Log sin datos sensibles
    log.info(f"job creado id={job_id} dataset={req.dataset_ref} period={req.period or 'ALL'}")
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
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
