"""Load the CSV files written by the ML pipeline into the database.

Run from the repo root, after `python -m ml.src.export_serving`:

    python -m backend.scripts.load_db

Honours DATABASE_URL (default: SQLite at data/smartbasket.db). The tables are dropped
and rebuilt each time, so the command is safe to repeat.
"""
import csv
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, Engine, insert

from backend.app.database import ROOT, make_engine
from backend.app.models import (
    Base,
    BoughtTogether,
    PopularProduct,
    Product,
    UserHabit,
    UserRecommendation,
    UserTopCategory,
)

SERVING_DIR: Path = ROOT / "data" / "serving"
BATCH_SIZE = 50_000

Casts = dict[str, Callable[[str], Any]]


def optional_float(value: str) -> float | None:
    """Parse a float, treating an empty CSV field as missing."""
    return float(value) if value else None


# (model, CSV file, column -> parser), in an order that respects the foreign keys.
TABLES: tuple[tuple[type[Base], str, Casts], ...] = (
    (Product, "products.csv", {"product_id": int, "name": str, "aisle": str, "department": str}),
    (PopularProduct, "popular_products.csv", {"rank": int, "product_id": int}),
    (
        BoughtTogether,
        "bought_together.csv",
        {"product_id": int, "rank": int, "similar_product_id": int, "score": float},
    ),
    (
        UserRecommendation,
        "user_recommendations.csv",
        {"user_id": int, "strategy": str, "rank": int, "product_id": int},
    ),
    (
        UserHabit,
        "user_habits.csv",
        {"user_id": int, "n_orders": int, "avg_reorder_interval_days": optional_float},
    ),
    (
        UserTopCategory,
        "user_top_categories.csv",
        {"user_id": int, "rank": int, "category": str, "purchases": int},
    ),
)


def read_rows(path: Path, casts: Casts) -> Iterator[dict[str, Any]]:
    """Yield the rows of a CSV file as dicts, parsing each column with its cast."""
    with path.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            yield {column: cast(row[column]) for column, cast in casts.items()}


def load_table(connection: Connection, model: type[Base], path: Path, casts: Casts) -> int:
    """Insert the rows of one CSV file in batches and return how many were inserted."""
    table = model.__table__
    total = 0
    batch: list[dict[str, Any]] = []
    for row in read_rows(path, casts):
        batch.append(row)
        if len(batch) == BATCH_SIZE:
            connection.execute(insert(table), batch)
            total += len(batch)
            batch = []
    if batch:
        connection.execute(insert(table), batch)
        total += len(batch)
    return total


def build_database(engine: Engine, serving_dir: Path = SERVING_DIR) -> dict[str, int]:
    """Recreate all tables and fill them from the CSV files; return rows loaded per table."""
    missing = [filename for _, filename, _ in TABLES if not (serving_dir / filename).exists()]
    if missing:
        raise FileNotFoundError(f"Missing {missing} in {serving_dir}. Run `python -m ml.src.export_serving` first.")

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    counts: dict[str, int] = {}
    with engine.begin() as connection:
        for model, filename, casts in TABLES:
            counts[model.__tablename__] = load_table(connection, model, serving_dir / filename, casts)
    return counts


def main() -> None:
    """Load data/serving/*.csv into the configured database and print the row counts."""
    engine = make_engine()
    print(f"Loading {SERVING_DIR} into {engine.url.render_as_string(hide_password=True)}")
    for table, n_rows in build_database(engine).items():
        print(f"  {table}: {n_rows} rows")


if __name__ == "__main__":
    main()