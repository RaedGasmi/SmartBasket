"""Tests for the HTTP API, run against a small database built from CSV files."""
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.database import make_engine
from backend.app.main import app, get_session
from backend.scripts.load_db import build_database

SERVING_FILES = {
    "products.csv": (
        "product_id,name,aisle,department\n"
        "1,Banana,fresh fruits,produce\n"
        "2,Bag of Organic Bananas,fresh fruits,produce\n"
        "3,Soda,soft drinks,beverages\n"
        "4,Chips,chips pretzels,snacks\n"
        "5,100% Juice,juice nectars,beverages\n"
    ),
    "popular_products.csv": "rank,product_id\n1,1\n2,2\n3,3\n",
    "bought_together.csv": "product_id,rank,similar_product_id,score\n1,1,2,0.8\n1,2,3,0.5\n2,1,1,0.4\n",
    "user_recommendations.csv": (
        "user_id,strategy,rank,product_id\n"
        "10,reorder,1,3\n10,reorder,2,1\n"
        "10,discovery,1,4\n10,discovery,2,2\n"
    ),
    "user_habits.csv": "user_id,n_orders,avg_reorder_interval_days\n10,2,10.0\n11,1,\n",
    "user_top_categories.csv": "user_id,rank,category,purchases\n10,1,soft drinks,3\n10,2,fresh fruits,1\n",
}
UNKNOWN_ID = 999


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """A test client whose API reads from a throwaway database holding SERVING_FILES."""
    serving_dir = tmp_path / "serving"
    serving_dir.mkdir()
    for filename, content in SERVING_FILES.items():
        (serving_dir / filename).write_text(content, encoding="utf-8")
    engine = make_engine(f"sqlite:///{(tmp_path / 'api.db').as_posix()}")
    build_database(engine, serving_dir)

    def get_test_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    yield TestClient(app)
    app.dependency_overrides.clear()
    engine.dispose()


def names(items: list[dict]) -> list[str]:
    return [item["name"] for item in items]


def product_ids(items: list[dict]) -> list[int]:
    return [item["product_id"] for item in items]


def test_search_is_case_insensitive_and_alphabetical(client: TestClient) -> None:
    response = client.get("/products", params={"q": "BANANA"})
    assert response.status_code == 200
    assert names(response.json()) == ["Bag of Organic Bananas", "Banana"]


def test_search_without_query_lists_everything_and_paginates(client: TestClient) -> None:
    assert len(client.get("/products").json()) == 5
    page = client.get("/products", params={"limit": 2, "offset": 1}).json()
    assert names(page) == ["Bag of Organic Bananas", "Banana"]


def test_search_treats_percent_as_plain_text(client: TestClient) -> None:
    assert names(client.get("/products", params={"q": "%"}).json()) == ["100% Juice"]


def test_read_product(client: TestClient) -> None:
    response = client.get("/products/1")
    assert response.status_code == 200
    assert response.json() == {"product_id": 1, "name": "Banana", "aisle": "fresh fruits", "department": "produce"}


@pytest.mark.parametrize("url", [f"/products/{UNKNOWN_ID}", f"/products/{UNKNOWN_ID}/bought-together"])
def test_unknown_product_is_404(client: TestClient, url: str) -> None:
    response = client.get(url)
    assert response.status_code == 404
    assert str(UNKNOWN_ID) in response.json()["detail"]


def test_bought_together_is_ranked_and_carries_scores(client: TestClient) -> None:
    items = client.get("/products/1/bought-together").json()
    assert names(items) == ["Bag of Organic Bananas", "Soda"]
    assert [item["score"] for item in items] == [0.8, 0.5]


def test_bought_together_respects_limit(client: TestClient) -> None:
    assert product_ids(client.get("/products/1/bought-together", params={"limit": 1}).json()) == [2]


def test_product_without_neighbours_gets_an_empty_list(client: TestClient) -> None:
    response = client.get("/products/4/bought-together")
    assert response.status_code == 200
    assert response.json() == []


def test_recommendations_default_to_reorder(client: TestClient) -> None:
    body = client.get("/users/10/recommendations").json()
    assert body["user_id"] == 10
    assert body["strategy"] == "reorder"
    assert product_ids(body["items"]) == [3, 1]


def test_discovery_strategy_uses_its_own_list(client: TestClient) -> None:
    body = client.get("/users/10/recommendations", params={"strategy": "discovery"}).json()
    assert body["strategy"] == "discovery"
    assert product_ids(body["items"]) == [4, 2]


def test_recommendations_respect_limit(client: TestClient) -> None:
    body = client.get("/users/10/recommendations", params={"limit": 1}).json()
    assert product_ids(body["items"]) == [3]


@pytest.mark.parametrize("strategy", ["reorder", "discovery"])
def test_unknown_user_gets_the_popularity_fallback(client: TestClient, strategy: str) -> None:
    response = client.get(f"/users/{UNKNOWN_ID}/recommendations", params={"strategy": strategy})
    assert response.status_code == 200
    body = response.json()
    assert body["strategy"] == "popularity_fallback"
    assert product_ids(body["items"]) == [1, 2, 3]


def test_popularity_fallback_respects_limit(client: TestClient) -> None:
    body = client.get(f"/users/{UNKNOWN_ID}/recommendations", params={"limit": 2}).json()
    assert product_ids(body["items"]) == [1, 2]


@pytest.mark.parametrize(
    "url",
    ["/users/10/recommendations?strategy=foo", "/products/1/bought-together?limit=0", "/products?limit=101"],
)
def test_invalid_parameters_are_rejected(client: TestClient, url: str) -> None:
    assert client.get(url).status_code == 422


def test_habits(client: TestClient) -> None:
    response = client.get("/habits/10")
    assert response.status_code == 200
    assert response.json() == {
        "user_id": 10,
        "n_orders": 2,
        "avg_reorder_interval_days": 10.0,
        "top_categories": [
            {"category": "soft drinks", "purchases": 3},
            {"category": "fresh fruits", "purchases": 1},
        ],
    }


def test_single_order_user_has_a_null_interval(client: TestClient) -> None:
    body = client.get("/habits/11").json()
    assert body["n_orders"] == 1
    assert body["avg_reorder_interval_days"] is None
    assert body["top_categories"] == []


def test_unknown_user_has_no_habits(client: TestClient) -> None:
    assert client.get(f"/habits/{UNKNOWN_ID}").status_code == 404