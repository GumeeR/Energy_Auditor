Paquete sintético para prueba técnica de LLM Engineer.

Contenido:
- dataset_consumo_energetico.csv: datos estructurados ficticios
- metadata.json: unidades, definiciones y notas de calidad
- output_schema.json: contrato mínimo de salida
- contexto_*.md: documentos de apoyo para grounding / RAG
- test_cases.json: escenarios sugeridos

Notas:
- Dataset 100% sintético y reutilizable.
- Diseñado para medir cálculo determinista + recuperación de contexto + salida estructurada.
- Incluye una inconsistencia intencional para probar degradación segura.
