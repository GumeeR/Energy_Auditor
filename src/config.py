import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# raiz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# datasets & contextos
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DATASETS_DIR = DATA_DIR / "datasets"
CONTEXT_DIR = DATA_DIR / "context"

# LLM
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")

# logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# version del prompt
PROMPT_VERSION = "v1.0"