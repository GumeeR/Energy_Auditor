import logging
from typing import List, Dict
from src import config
from src.services.prompts import construir_prompt_hallazgo, construir_prompt_recomendacion

log = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_DISPONIBLE = True
except ImportError:
    OPENAI_DISPONIBLE = False

def _llm_fake(prompt: str) -> str:
    if "recomendacion" in prompt.lower():
        return (
            "Se sugiere verificar la calibracion y rutina de mantenimiento preventivo del equipo, "
            "asi como contrastar la produccion efectiva vs el consumo registrado en el periodo."
        )
    return (
        "Se observa un sobreconsumo energetico en el equipo respecto al target definido. "
        "Se recomienda verificacion humana y contrastar con condiciones operativas del periodo."
    )
def _llamar_llm(prompt: str) -> str:
    if config.OPENAI_API_KEY and OPENAI_DISPONIBLE:
        try:
            client = OpenAI(api_key=config.OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=200,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            # No loguear prompt completo (puede tener datos sensibles)
            log.warning(f"LLM real fallo ({type(e).__name__}), usando fake")
            return _llm_fake(prompt)
    return _llm_fake(prompt)


def redactar_hallazgo(hallazgo: Dict, contexto_refs: List[str]) -> str:
    prompt = construir_prompt_hallazgo(hallazgo, contexto_refs)
    return _llamar_llm(prompt)


def redactar_recomendacion(hallazgos_ids: List[str], severidad_max: str) -> str:
    prompt = construir_prompt_recomendacion(hallazgos_ids, severidad_max)
    return _llamar_llm(prompt)
