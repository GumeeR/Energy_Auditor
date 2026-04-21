import os
import json
from typing import List, Dict
from src import config

try:
    from openai import OpenAI
    OPENAI_DISPONIBLE = True
except ImportError:
    OPENAI_DISPONIBLE = False

def construir_prompt_hallazgo(hallazgo: Dict, contexto_refs: List[str]) -> str:

    kwh_unit = round(hallazgo["kwh_per_unit"], 3) if hallazgo["kwh_per_unit"] else "N/A"
    target = hallazgo["target_kwh_per_unit"]
    variance = round(hallazgo["variance_pct"], 2) if hallazgo["variance_pct"] else "N/A"

    prompt = f"""Eres un asistente tecnico que SOLO redacta hallazgos. NO calcules nada.
Usa los datos ya calculados abajo.

Equipo: {hallazgo['equipment_id']} en {hallazgo['facility_id']}, proceso {hallazgo['process_name']}
Periodo: {hallazgo['period']}
kWh/unidad observado: {kwh_unit}
Target kWh/unidad: {target}
Desviacion vs target: {variance}%
Severidad clasificada: {hallazgo['severity']}

Redacta un statement breve (max 2 frases) que describa el sobreconsumo observado.
No inventes causas. No menciones normas. Tono tecnico y preliminar.

Devuelve solo el statement, sin comillas ni JSON.
"""
    return prompt

def construir_prompt_recomendacion(hallazgos_ids: List[str], severidad_max: str) -> str:
    prompt = f"""Eres un asistente que redacta recomendaciones preliminares.
Hallazgos relacionados: {', '.join(hallazgos_ids)}
Severidad mas alta detectada: {severidad_max}

Segun la guia: verificar calibracion y mantenimiento preventivo del equipo,
revisar horarios de operacion y cargas parciales, contrastar produccion vs consumo,
validar si hubo cambios operativos o paradas.

Redacta una recomendacion operativa en 1-2 frases. Tono preliminar.
No cites normas. No afirmes incumplimientos. No inventes causas raiz.

Devuelve solo el texto, sin comillas ni JSON.
"""
    return prompt

def llamar_llm(prompt: str) -> str:

    if config.OPENAI_API_KEY and OPENAI_DISPONIBLE:
        try:
            client = OpenAI(api_key=config.OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,   # bajito para que no alucine tanto
                max_tokens=200,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            # si falla el LLM degrado al fake (no explota la app)
            return llm_fake(prompt)
    else:
        return llm_fake(prompt)


def llm_fake(prompt: str) -> str:
    if "recomendacion" in prompt.lower() or "recomendaciones" in prompt.lower():
        return ("Se sugiere verificar la calibracion y rutina de mantenimiento preventivo del equipo,"
                "asi como contrastar la produccion efectiva vs el consumo registrado en el periodo.")
    else:
        return ("Se observa un sobreconsumo energetico en el equipo respecto al target definido."
                "Se recomienda verificacion humana y contrastar con condiciones operativas del periodo.")

def redactar_hallazgo(hallazgo: Dict, contexto_refs: List[str]) -> str:
    prompt = construir_prompt_hallazgo(hallazgo, contexto_refs)
    return llamar_llm(prompt)

def redactar_recomendacion(hallazgos_ids: List[str], severidad_max: str) -> str:
    prompt = construir_prompt_recomendacion(hallazgos_ids, severidad_max)
    return llamar_llm(prompt)