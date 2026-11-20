"""Unit tests for the ALS recommender on a tiny hand-made dataset."""
import pandas as pd
import pytest

from ml.src.models.als import ALSRecommender
from ml.src.models.popularity import PopularityRecommender

# Users 10 and 11 share items 1-2, user 12 buys items 3-4.
PRIOR = pd.DataFrame(
    {
        "order_id": [1, 1, 2, 2, 3, 3, 4, 4, 5],
        "user_id": [10, 10, 10, 10, 11, 11, 12, 12, 12],
        "product_id": [1, 2, 1, 2, 1, 2, 3, 4, 3],
    }
)


def build_model() -> ALSRecommender:
    fallback = PopularityRecommender().fit(PRIOR)
    return ALSRecommender(fallback, factors=3, iterations=5, seed=0).fit(PRIOR)


@pytest.fixture
def model() -> ALSRecommender:
    return build_model()


def test_recommendations_are_unique_known_products(model: ALSRecommender) -> None:
    recommended = model.recommend(10, k=3)
    assert len(recommended) == 3
    assert len(set(recommended)) == 3
    assert set(recommended) <= {1, 2, 3, 4}


def test_exclude_is_respected(model: ALSRecommender) -> None:
    assert set(model.recommend(10, k=2, exclude={1, 2})) == {3, 4}


def test_unknown_user_gets_popularity_fallback(model: ALSRecommender) -> None:
    assert model.recommend(999, k=2) == PopularityRecommender().fit(PRIOR).recommend(999, k=2)


def test_excluding_everything_returns_nothing(model: ALSRecommender) -> None:
    assert model.recommend(10, k=3, exclude={1, 2, 3, 4}) == []


def test_exclude_ignores_unknown_product_ids(model: ALSRecommender) -> None:
    assert len(model.recommend(10, k=2, exclude={777})) == 2


def test_same_seed_gives_same_recommendations() -> None:
    first, second = build_model(), build_model()
    for user_id in (10, 11, 12):
        assert first.recommend(user_id, k=4) == second.recommend(user_id, k=4)