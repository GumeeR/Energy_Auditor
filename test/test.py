import pytest
from src.services import calculos
from src import config

def test_kwh_por_unidad_normal():
      row = {"energy_kwh": 20480, "production_units": 4300, "target_kwh_per_unit": 3.9}
      resultado = calculos.calcular_kwh_por_unidad(row)
      assert resultado is not None

def test_kwh_por_unidad_falta_data():
    row = {"energy_kwh": None, "production_units": 3920, "target_kwh_per_unit": 5.2}
    resultado = calculos.calcular_kwh_por_unidad(row)
    assert resultado is None

def test_variance_calculo():
    v = calculos.calcular_variance(4.7627906976, 3.9)
    assert abs(v - 22.1228) < 0.1

def test_variance_con_none():
    v = calculos.calcular_variance(None, 3.9)
    assert v is None

def test_clasificar_severidad():
    assert calculos.clasificar_severidad(3.0) == "baja"
    assert calculos.clasificar_severidad(8.0) == "media"
    assert calculos.clasificar_severidad(15.0) == "alta"
    assert calculos.clasificar_severidad(-2.0) is None
    assert calculos.clasificar_severidad(None) is None

def test_emisiones():
    e = calculos.calcular_emisiones(20000, 0.182)
    assert abs(e - 3640.0) < 0.01

def test_procesar_todo_con_dataset_real():
    csv_path = config.DATASETS_DIR / "dataset_consumo_energetico.csv"
    if not csv_path.exists():
        pytest.skip("csv no disponible")
    resultado = calculos.procesar_todo(str(csv_path), period="2025-03")
    assert resultado["metricas_agregadas"]["records_count"] == 4
    assert len(resultado["hallazgos"]) >= 1

def test_job_result_se_puede_serializar():
      from src.schema import JobResult, Summary, Metric, Trace, StatusEnum
      jr = JobResult(
          job_id="test-123", status=StatusEnum.success,
          summary=Summary(period="2025-03", dataset_ref="dataset.csv"),
          metrics=[Metric(name="total", value=100, unit="kWh")],
          findings=[], recommendations_draft=[], warnings=[],
          trace=Trace(prompt_version="v1", documents_used=["a.md"], rules_applied=["r1"]),
      )
      data = jr.model_dump()
      assert data["job_id"] == "test-123"

def test_ruta_segura_bloquea_traversal():
    from src.main import ruta_segura_dataset
    with pytest.raises(ValueError):
        ruta_segura_dataset("../../../etc/passwd")
    with pytest.raises(ValueError):
        ruta_segura_dataset("/etc/passwd")

def test_endpoint_root():
    from fastapi.testclient import TestClient
    from src.main import app
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "up"

def test_endpoint_job_not_found():
    from fastapi.testclient import TestClient
    from src.main import app
    client = TestClient(app)
    r = client.get("/jobs/id-que-no-existe")
    assert r.status_code == 404