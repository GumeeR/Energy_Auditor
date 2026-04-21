from typing import List, Dict

def construir_prompt_hallazgo(hallazgo: Dict, contexto_refs: List[str]) -> str:
    kwh_unit = round(hallazgo["kwh_per_unit"], 3) if hallazgo.get("kwh_per_unit") is not None else "N/A"
    target = hallazgo.get("target_kwh_per_unit", "N/A")
    variance = round(hallazgo["variance_pct"], 2) if hallazgo.get("variance_pct") is not None else "N/A"
    refs_txt = ", ".join(contexto_refs) if contexto_refs else "ninguno"

    return (
        "Eres un asistente tecnico que SOLO redacta hallazgos. NO calcules nada.\n"
        "Usa los datos ya calculados abajo.\n\n"
        f"Equipo: {hallazgo['equipment_id']} en {hallazgo['facility_id']}, "
        f"proceso {hallazgo['process_name']}\n"
        f"Periodo: {hallazgo['period']}\n"
        f"kWh/unidad observado: {kwh_unit}\n"
        f"Target kWh/unidad: {target}\n"
        f"Desviacion vs target: {variance}%\n"
        f"Severidad clasificada: {hallazgo['severity']}\n"
        f"Referencias de contexto recuperadas: {refs_txt}\n\n"
        "Redacta un statement breve (max 2 frases) que describa el sobreconsumo observado. "
        "No inventes causas. No menciones normas. Tono tecnico y preliminar.\n\n"
        "Devuelve solo el statement, sin comillas ni JSON."
    )

def construir_prompt_recomendacion(hallazgos_ids: List[str], severidad_max: str) -> str:
    return (
        "Eres un asistente que redacta recomendaciones preliminares.\n"
        f"Hallazgos relacionados: {', '.join(hallazgos_ids)}\n"
        f"Severidad mas alta detectada: {severidad_max}\n\n"
        "Segun la guia: verificar calibracion y mantenimiento preventivo del equipo,\n"
        "revisar horarios de operacion y cargas parciales, contrastar produccion vs consumo,\n"
        "validar si hubo cambios operativos o paradas.\n\n"
        "Redacta una recomendacion operativa en 1-2 frases. Tono preliminar. "
        "No cites normas. No afirmes incumplimientos. No inventes causas raiz.\n\n"
        "Devuelve solo el texto, sin comillas ni JSON."
    )