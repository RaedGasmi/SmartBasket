"""Central configuration: paths and reproducibility settings."""
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[2]
RAW_DIR: Path = ROOT / "data" / "raw"
PROCESSED_DIR: Path = ROOT / "data" / "processed"
RESULTS_DIR: Path = ROOT / "ml" / "results"

SEED: int = 42
N_USERS: int = 20_000