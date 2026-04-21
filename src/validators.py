import json
from pathlib import Path
from typing import Any, Dict

try:
    from jsonschema import Draft202012Validator
    JSONSCHEMA_DISPONIBLE = True
except ImportError:
    JSONSCHEMA_DISPONIBLE = False

_cache: Dict[str, Any] = {}

def cargar_schema(schema_path: Path) -> Dict:
    key = str(schema_path)
    if key not in _cache:
        with open(schema_path, "r", encoding="utf-8") as f:
            _cache[key] = json.load(f)
    return _cache[key]

def validar_output(data: Dict, schema_path: Path) -> list:
    if not JSONSCHEMA_DISPONIBLE:
        return []
    schema = cargar_schema(schema_path)
    validator = Draft202012Validator(schema)
    errores = []
    for err in validator.iter_errors(data):
        ruta = ".".join(str(p) for p in err.absolute_path) or "<root>"
        errores.append(f"{ruta}: {err.message}")
    return errores