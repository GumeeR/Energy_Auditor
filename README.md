# SG Tech — Energy Audit Service

Prueba tecnica de LLM Engineer. Es un microservicio FastAPI que recibe un dataset de consumo energetico mas documentos de contexto y devuelve hallazgos + recomendaciones preliminares en JSON estructurado.

Pensado para correr en Linux. El Dockerfile usa imagen base `python:3.11-slim`.

## Requisitos

- Linux
- Python 3.11+
- Opcional: Docker si preferis correrlo contenedorizado

## Estructura

El codigo fuente esta en `app/` (API, schemas pydantic, config, store de jobs y los servicios de dominio bajo `app/services/`). Los datos viven en `data/`: el dataset CSV en `data/datasets/`, los markdown de contexto en `data/context/`, y los schemas, metadata y casos de prueba en la raiz de `data/`. Los tests estan en `tests/test_basico.py`. En `docs/` quedo la documentacion extra, un output de ejemplo y el README original del brief.

## Decisiones clave

Todo calculo (kwh_per_unit, variance, emisiones, severidad) vive en `app/services/calculos.py`. El LLM solo recibe los numeros ya listos y los redacta — no hace matematica.

El "async" esta simulado con `BackgroundTasks` de FastAPI: se devuelve `job_id` al instante y el procesamiento corre en segundo plano.

Para los archivos, `ruta_segura_dataset()` rechaza `..` y rutas absolutas (anti path traversal) y fuerza que todo se lea desde `data/datasets/`. Nada de secretos hardcodeados — `.env.example` documenta las variables y, si no hay API key, el sistema cae al LLM fake en vez de romperse.

Si falta `energy_kwh` en una fila se emite warning y esa fila se saltea; el status final del job queda en `"warning"`. Las excepciones del procesamiento se envuelven a nivel de job, asi que nunca sale un stack trace al cliente.

## Instalacion

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Editar `.env` solo si queres usar OpenAI real — sin key funciona con el fake.

### Con Docker

```bash
docker build -t energy-auditor .
docker run --rm -p 8000:8000 --env-file .env energy-auditor
```

## Ejecucion

```bash
uvicorn src.main:app --reload
# o:
python -m src.main
```

Queda en `http://localhost:8000`. Los docs automaticos estan en `/docs`.

Ejemplo:

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_ref": "dataset_consumo_energetico.csv",
    "period": "2025-03",
    "business_prompt": "Review March 2025 energy consumption"
  }'
```

Respuesta:

```json
{"job_id": "xxxx-xxxx-...", "status": "pending"}
```

Despues:

```bash
curl http://localhost:8000/jobs/xxxx-xxxx-...
```

Devuelve el JSON completo conforme a `data/output_schema.json`.

## Tests

```bash
pytest test/test.py -v

```

## Limites conocidos y supuestos

La cola de jobs vive en memoria (un dict). Si se reinicia el servicio se pierden los jobs en vuelo — en produccion iria a Redis o similar. El RAG es keyword matching, no vector DB, pero alcanza para el tamano de documentos del brief. El LLM fake siempre responde lo mismo; util para demos sin API key. No hay auth en los endpoints (no era requisito). `DATA_DIR` se puede cambiar por env var, por defecto apunta a `./data`.

## Casos de prueba cubiertos

- CASE-01: `GET` de jobs con `period=2025-03` detecta al menos un hallazgo de severidad alta (Bombeo PUMP-07 en marzo esta ~26% sobre target) y emite warning por `energy_kwh` faltante en Refrigeracion CH-11 febrero (solo si el filtro incluye feb o si no se filtra).
- CASE-02: `POST` con `facility_filter="PLT-01"` devuelve solo hallazgos de esa planta.