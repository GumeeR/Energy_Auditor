import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DATASETS_DIR = DATA_DIR / "datasets"
CONTEXT_DIR = DATA_DIR / "context"