import csv
from typing import Any, Dict, List, Optional

CAMPOS_NUMERICOS = [
    "energy_kwh",
    "production_units",
    "co2_factor_kg_per_kwh",
    "operating_hours",
    "target_kwh_per_unit",
    "baseline_energy_kwh",
]

def parse_float(valor: Optional[str]) -> Optional[float]:
    if valor is None:
        return None
    s = str(valor).strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None

def cargar_dataset(path: str) -> List[Dict[str, Any]]:
    filas: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for campo in CAMPOS_NUMERICOS:
                if campo in row:
                    row[campo] = parse_float(row[campo])
            filas.append(row)
    return filas

def filtrar_datos(
    filas: List[Dict],
    period: Optional[str] = None,
    facility: Optional[str] = None,
) -> List[Dict]:
    resultado = filas[:]
    if period is not None:
        resultado = [r for r in resultado if r.get("period") == period]
    if facility is not None:
        resultado = [r for r in resultado if r.get("facility_id") == facility]
    return resultado

def calcular_kwh_por_unidad(row: Dict) -> Optional[float]:
    energy = row.get("energy_kwh")
    prod = row.get("production_units")
    if energy is None or prod is None or prod == 0:
        return None
    return energy / prod

def calcular_variance(kwh_per_unit: Optional[float], target: Optional[float]) -> Optional[float]:
    if kwh_per_unit is None or target is None or target == 0:
        return None
    return ((kwh_per_unit - target) / target) * 100

def calcular_emisiones(energy_kwh: Optional[float], co2_factor: Optional[float]) -> Optional[float]:
    if energy_kwh is None or co2_factor is None:
        return None
    return energy_kwh * co2_factor

def procesar_fila(row: Dict) -> Dict[str, Any]:
    kwh_unit = calcular_kwh_por_unidad(row)
    variance = calcular_variance(kwh_unit, row.get("target_kwh_per_unit"))
    emisiones = calcular_emisiones(row.get("energy_kwh"), row.get("co2_factor_kg_per_kwh"))
    return {
        "facility_id": row["facility_id"],
        "process_name": row["process_name"],
        "equipment_id": row["equipment_id"],
        "period": row["period"],
        "energy_kwh": row.get("energy_kwh"),
        "production_units": row.get("production_units"),
        "kwh_per_unit": kwh_unit,
        "target_kwh_per_unit": row.get("target_kwh_per_unit"),
        "variance_vs_target_pct": variance,
        "estimated_emissions_kg": emisiones,
    }

def clasificar_severidad(variance_pct: Optional[float]) -> Optional[str]:
    if variance_pct is None or variance_pct <= 0:
        return None
    if variance_pct <= 5:
        return "baja"
    if variance_pct <= 12:
        return "media"
    return "alta"

def detectar_hallazgos(resultados: List[Dict]) -> List[Dict]:
    hallazgos: List[Dict] = []
    contador = 1
    for r in resultados:
        severidad = clasificar_severidad(r["variance_vs_target_pct"])
        if severidad is not None:
            hallazgos.append({
                "id": f"F-{contador:03d}",
                "type": "sobreconsumo_energetico",
                "severity": severidad,
                "facility_id": r["facility_id"],
                "process_name": r["process_name"],
                "equipment_id": r["equipment_id"],
                "period": r["period"],
                "kwh_per_unit": r["kwh_per_unit"],
                "target_kwh_per_unit": r["target_kwh_per_unit"],
                "variance_pct": r["variance_vs_target_pct"],
            })
            contador += 1
    return hallazgos

def detectar_warnings(filas: List[Dict]) -> List[Dict]:
    warnings_list: List[Dict] = []
    for r in filas:
        if r.get("energy_kwh") is None:
            warnings_list.append({
                "code": "MISSING_ENERGY_DATA",
                "message": (
                    f"energy_kwh faltante en {r.get('facility_id','?')} / "
                    f"{r.get('equipment_id','?')} periodo {r.get('period','?')}. "
                    "No se calcula kwh/unit ni emisiones."
                ),
            })
    raras = [r for r in filas if (r.get("production_units") is None or r.get("production_units") <= 0)]
    if len(raras) > 0:
        warnings_list.append({
            "code": "INVALID_PRODUCTION",
            "message": f"Hay {len(raras)} registros con production_units invalido (0 o negativo)",
        })
    return warnings_list

def _sumar_no_none(valores: List[Optional[float]]) -> Optional[float]:
    validos = [v for v in valores if v is not None]
    if len(validos) == 0:
        return None
    return sum(validos)

def _promedio_no_none(valores: List[Optional[float]]) -> Optional[float]:
    validos = [v for v in valores if v is not None]
    if len(validos) == 0:
        return None
    return sum(validos) / len(validos)

def procesar_todo(
    path_csv: str,
    period: Optional[str] = None,
    facility: Optional[str] = None,
) -> Dict[str, Any]:
    filas = cargar_dataset(path_csv)
    filas_filtradas = filtrar_datos(filas, period=period, facility=facility)

    resultados_por_fila = [procesar_fila(r) for r in filas_filtradas]
    hallazgos = detectar_hallazgos(resultados_por_fila)
    warnings_data = detectar_warnings(filas_filtradas)

    metricas_agregadas = {
        "total_energy_kwh": _sumar_no_none([r.get("energy_kwh") for r in filas_filtradas]),
        "total_production_units": _sumar_no_none([r.get("production_units") for r in filas_filtradas]),
        "total_estimated_emissions_kg": _sumar_no_none([r["estimated_emissions_kg"] for r in resultados_por_fila]),
        "avg_kwh_per_unit": _promedio_no_none([r["kwh_per_unit"] for r in resultados_por_fila]),
        "avg_variance_vs_target_pct": _promedio_no_none([r["variance_vs_target_pct"] for r in resultados_por_fila]),
        "records_count": len(filas_filtradas),
    }

    return {
        "metricas_por_fila": resultados_por_fila,
        "metricas_agregadas": metricas_agregadas,
        "hallazgos": hallazgos,
        "warnings": warnings_data,
    }