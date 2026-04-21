# Doc tecnico

**Proyecto:** Energy Auditor — servicio FastAPI para auditoria energetica
**Entrega:** prueba tecnica LLM Engineer (SG Tech)
**Version:** v1.0.0

---

## 1. Arquitectura

Microservicio en Python con FastAPI, separado por capas. La API vive en `src/main.py`, los contratos de entrada/salida en `src/schema.py` (pydantic), la config en `src/config.py` y el store de jobs en memoria en `src/jobs_store.py`. La logica de dominio esta en `src/services/`: `calculos.py` para los numeros, `rag.py` para la recuperacion de contexto y `llm_client.py` para el cliente de OpenAI con fallback offline.

Cuando entra una peticion, `POST /jobs` valida el payload y responde al toque con un `job_id`. El procesamiento real se dispara en background via `BackgroundTasks`. Ahi adentro el orden es: validar la ruta del dataset, correr los calculos deterministas, cargar y chunkear los documentos de contexto, detectar hallazgos y warnings, y recien al final invocar al LLM — pero solo para redactar texto sobre numeros que ya estan calculados. El resultado se arma como `JobResult` y se valida contra el schema antes de guardarse. El `GET /jobs/{id}` despues devuelve el estado o el resultado.

La regla que quise mantener firme: el LLM no calcula nada. `calculos.py` es puro y determinista, se testea aislado, y los valores que llegan al prompt ya estan redondeados.

## 2. Decisiones de seguridad

Para path traversal arme `ruta_segura_dataset()` que rechaza rutas absolutas, `..` y caracteres de escape. Toda lectura se resuelve y se verifica contra `DATASETS_DIR`. Lo probe con tests automaticos y a mano con curl.

Ninguna API key hardcodeada. `.env.example` documenta que variables se necesitan, el `.env` real esta en `.gitignore`, y el programa arranca igual aunque no haya key — cae al LLM fake. 

En `procesar_job` toda excepcion se captura y se responde con mensaje generico y codigo `INTERNAL_ERROR`; el stack trace nunca sale al cliente, queda solo en el log del servidor. El nivel de log es configurable por env y trate de no loguear payloads completos ni variables sensibles.

En el Dockerfile el contenedor corre con usuario no-root (`appuser`, UID 1000).

## 3. Patrones aplicados

Basicamente Service Layer y un Repository simplificado. Los modulos en `src/services/*` encapsulan la logica de dominio (calculos, retrieval, generacion) y la capa de API solo orquesta. `jobs_store.py` abstrae el almacenamiento, asi que reemplazarlo por Redis o Postgres mas adelante no deberia tocar `main.py`.

El cliente LLM funciona como adapter: esconde el SDK de OpenAI detras de `redactar_hallazgo` y `redactar_recomendacion`, y el fallback a `llm_fake` es transparente — los callers no se enteran. Los modelos pydantic hacen doble trabajo: validan lo que entra y serializan lo que sale, y `JobResult` es la unica forma de respuesta. La config vive solo en `config.py` para no tener lecturas de env dispersas por todo el codigo.

## 4. Limitaciones conocidas

Lo mas obvio: `jobs_store` esta en memoria, asi que si reinicias el servicio se pierden los jobs en vuelo. En produccion esto deberia ir a Redis o Postgres.

El RAG es keyword matching, no vector DB. Me alcanzo para los 3 documentos cortos del brief pero no escala a un corpus grande. Tampoco hay autenticacion y la cola "async" es simplemente `BackgroundTasks` — para carga real conviene migrar a Celery o Arq.

El `llm_fake` siempre devuelve el mismo texto canned. Sirve para demos y para que los tests corran sin key, no para produccion. Los tests cubren calculos, seguridad y contrato de API; no hay integracion real con OpenAI, eso queda mockeado implicitamente via el fallback.

## 5. Riesgos y mitigaciones

Datos faltantes el sistema no cancela, genera un warning por cada campo nulo y el job termina con status warning en lugar de success.

El LLM no calcula nada todos los números llegan pre-calculados al prompt. El modelo solo redacta el texto. Temperatura en 0.2 para reducir variaciones.

API key no se loguean variables de entorno ni payloads. El .env está en gitignore.

Path traversal la función ruta_segura_dataset bloquea rutas absolutas y con ... Hay tests que cubren esto.

Cambio de schema schema.py es la única fuente de verdad. Pydantic valida en runtime, cualquier campo roto rompe el job antes de llegar al LLM.

## 6. Cumplimiento del brief

Chequeando contra los requisitos pedidos:

- API con `POST /jobs` y `GET /jobs/{id}` ✔
- 3+ calculos deterministas (kwh/unit, variance, emisiones, agregados) ✔
- Recuperacion de contexto documental ✔
- LLM limitado a redaccion ✔
- Salida conforme a `output_schema.json` ✔
- Trazabilidad via `trace` (prompt_version, documents_used, rules_applied) ✔
- Manejo seguro de errores y datos faltantes ✔
- Validacion de inputs/outputs con pydantic ✔
- `.env.example` sin secretos ✔
- Logging basico sin datos sensibles ✔
- Validacion de rutas contra path traversal ✔
- Tests unitarios y de integracion ✔
- Dockerfile ejecutable en Linux ✔
- README con instalacion, ejecucion y arquitectura ✔
