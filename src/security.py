import os
import re
from pathlib import Path
from typing import Optional

# Limites
MAX_BUSINESS_PROMPT_LEN = 2000
MAX_PERIOD_LEN = 20
MAX_FACILITY_LEN = 50
MAX_DATASET_REF_LEN = 200

_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

def sanitize_prompt(texto: Optional[str], max_len: int = MAX_BUSINESS_PROMPT_LEN) -> str:
    if texto is None:
        return ""
    s = str(texto)
    s = _CTRL_RE.sub(" ", s)
    s = s.strip()
    if len(s) > max_len:
        s = s[:max_len]
    lower = s.lower()
    for marcador in ("ignore previous", "ignore all previous", "system:", "assistant:"):
        if marcador in lower:
            idx = lower.find(marcador)
            s = s[:idx] + "[FILTERED]" + s[idx + len(marcador):]
            lower = s.lower()
    return s

def validar_ref_simple(valor: Optional[str], max_len: int, campo: str) -> Optional[str]:
    if valor is None:
        return None
    s = str(valor).strip()
    if len(s) == 0:
        return None
    if len(s) > max_len:
        raise ValueError(f"{campo} excede longitud maxima {max_len}")
    if not re.match(r"^[A-Za-z0-9_\-:/]+$", s):
        raise ValueError(f"{campo} contiene caracteres no permitidos")
    return s

def ruta_segura(filename: str, base_dir: Path) -> Path:
    if not filename or len(filename) > MAX_DATASET_REF_LEN:
        raise ValueError("dataset_ref invalido o muy largo")
    if os.path.isabs(filename):
        raise ValueError(f"Ruta absoluta no permitida: {filename}")
    if ".." in filename.replace("\\", "/").split("/"):
        raise ValueError(f"Path traversal detectado: {filename}")
    if "\x00" in filename:
        raise ValueError("Null byte en filename")
    base_resuelto = base_dir.resolve()
    full = (base_dir / filename).resolve()
    try:
        full.relative_to(base_resuelto)
    except ValueError:
        raise ValueError(f"Ruta fuera de base permitida: {filename}")
    return full