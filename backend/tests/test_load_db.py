"""Tests for loading the serving CSV files into the database."""
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.orm import Session

from backend.app.models import BoughtTogether, UserHabit, UserRecommendation
from backend.scripts.load_db import build_database, optional_float

SERVING_FILES = {
    "products.csv": "product_id,name,aisle,department\n1,Banana,fresh fruits,produce\n2,Soda,soft drinks,beverages\n3,Chips,chips pretzels,snacks\n",
    "popular_products.csv": "rank,product_id\n1,1\n2,2\n",
    "bought_together.csv": "product_id,rank,similar_product_id,score\n1,1,3,0.8\n1,2,2,0.5\n2,1,1,0.4\n",
    "user_recommendations.csv": "user_id,strategy,rank,product_id\n10,reorder,1,1\n10,discovery,1,3\n",
    "user_habits.csv": "user_id,n_orders,avg_reorder_interval_days\n10,2,10.0\n11,1,\n",
    "user_top_categories.csv": "user_id,rank,category,purchases\n10,1,fresh fruits,3\n",
}
EXPECTED_COUNTS = {
    "products": 3,
    "popular_products": 2,
    "bought_together": 3,
    "user_recommendations": 2,
    "user_habits": 2,
    "user_top_categories": 1,
}


@pytest.fixture
def serving_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "serving"
    directory.mkdir()
    for filename, content in SERVING_FILES.items():
        (directory / filename).write_text(content, encoding="utf-8")
    return directory


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    return create_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")


def test_build_database_loads_every_table(engine: Engine, serving_dir: Path) -> None:
    assert build_database(engine, serving_dir) == EXPECTED_COUNTS
    with Session(engine) as session:
        neighbours = session.scalars(
            select(BoughtTogether.similar_product_id)
            .where(BoughtTogether.product_id == 1)
            .order_by(BoughtTogether.rank)
        ).all()
        strategies = session.scalars(select(UserRecommendation.strategy).order_by(UserRecommendation.strategy)).all()
    assert neighbours == [3, 2]
    assert strategies == ["discovery", "reorder"]


def test_empty_interval_is_stored_as_null(engine: Engine, serving_dir: Path) -> None:
    build_database(engine, serving_dir)
    with Session(engine) as session:
        intervals = dict(session.execute(select(UserHabit.user_id, UserHabit.avg_reorder_interval_days)).all())
    assert intervals == {10: 10.0, 11: None}


def test_rebuilding_does_not_duplicate_rows(engine: Engine, serving_dir: Path) -> None:
    build_database(engine, serving_dir)
    assert build_database(engine, serving_dir) == EXPECTED_COUNTS
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(BoughtTogether)) == 3


def test_missing_csv_gives_a_helpful_error(engine: Engine, tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="export_serving"):
        build_database(engine, tmp_path)


def test_optional_float_treats_empty_as_missing() -> None:
    assert optional_float("") is None
    assert optional_float("2.5") == 2.5