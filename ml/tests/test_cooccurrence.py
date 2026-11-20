"""Unit tests for the co-occurrence recommender on a tiny hand-made dataset."""
import pandas as pd
import pytest

from ml.src.models.cooccurrence import CooccurrenceRecommender
from ml.src.models.popularity import PopularityRecommender

# Orders: o1={1,2} o2={1,2} o3={1,3} o4={4} (user 10 bought o1, o2; user 11 bought o3; user 12 bought o4)
PRIOR = pd.DataFrame(
    {
        "order_id": [1, 1, 2, 2, 3, 3, 4],
        "user_id": [10, 10, 10, 10, 11, 11, 12],
        "product_id": [1, 2, 1, 2, 1, 3, 4],
    }
)


@pytest.fixture
def model() -> CooccurrenceRecommender:
    fallback = PopularityRecommender().fit(PRIOR)
    return CooccurrenceRecommender(fallback, n_neighbors=2, min_support=1, block_size=2).fit(PRIOR)


def test_similarity_is_cosine_of_basket_membership(model: CooccurrenceRecommender) -> None:
    neighbors = dict(model.similar_items(1, k=2))
    assert neighbors[2] == pytest.approx(2 / (3**0.5 * 2**0.5))  # cooc=2, n_1=3, n_2=2
    assert neighbors[3] == pytest.approx(1 / (3**0.5 * 1**0.5))
    assert neighbors[2] > neighbors[3]


def test_unknown_product_has_no_neighbors(model: CooccurrenceRecommender) -> None:
    assert model.similar_items(999) == []


def test_user_recommendations_exclude_history_when_asked(model: CooccurrenceRecommender) -> None:
    assert model.recommend(11, k=2, exclude={1, 3}) == [2, 4]  # neighbour 2, then popularity fills with 4


def test_unknown_user_falls_back_to_popularity(model: CooccurrenceRecommender) -> None:
    assert model.recommend(999, k=2) == [1, 2]