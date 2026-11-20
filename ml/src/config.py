"""Central configuration: paths and reproducibility settings."""
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[2]
RAW_DIR: Path = ROOT / "data" / "raw"
PROCESSED_DIR: Path = ROOT / "data" / "processed"
RESULTS_DIR: Path = ROOT / "ml" / "results"
MODELS_DIR: Path = ROOT / "ml" / "models"
SERVING_DIR: Path = ROOT / "data" / "serving"

SEED: int = 42
N_USERS: int = 20_000
TOP_K: int = 10
N_POPULAR: int = 50
ALS_FACTORS: int = 64
ALS_REGULARIZATION: float = 0.01
ALS_ITERATIONS: int = 15
ALS_ALPHA: float = 10.0
N_TOP_CATEGORIES: int = 5