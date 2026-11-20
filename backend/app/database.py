"""Engine creation. Set DATABASE_URL to switch from SQLite to PostgreSQL."""
import os
from pathlib import Path

from sqlalchemy import Engine, create_engine

ROOT: Path = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL: str = f"sqlite:///{(ROOT / 'data' / 'smartbasket.db').as_posix()}"


def get_database_url() -> str:
    """Return DATABASE_URL from the environment, or the local SQLite file."""
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def make_engine(url: str | None = None) -> Engine:
    """Create an engine; SQLite needs check_same_thread=False to work with FastAPI's threads."""
    url = url or get_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)