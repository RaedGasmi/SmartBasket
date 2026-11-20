"""Unit tests for the serving tables exported for the API."""
import pandas as pd

from ml.src.export_serving import (
    bought_together_frame,
    habits_frames,
    popular_frame,
    products_frame,
    user_recommendations_frame,
)
from ml.src.models.cooccurrence import CooccurrenceRecommender
from ml.src.models.popularity import PopularityRecommender

NAN = float("nan")
# User 10 has orders o1 and o2 (10 days apart); users 11 and 12 have a single order each.
PRIOR = pd.DataFrame(
    {
        "order_id": [1, 1, 2, 2, 3, 3, 4],
        "user_id": [10, 10, 10, 10, 11, 11, 12],
        "product_id": [1, 2, 1, 3, 1, 3, 4],
        "days_since_prior_order": [NAN, NAN, 10.0, 10.0, NAN, NAN, NAN],
    }
)
PRODUCTS = pd.DataFrame(
    {
        "product_id": [1, 2, 3, 4],
        "product_name": ["a", "b", "c", "d"],
        "aisle": ["x", "x", "y", "y"],
        "department": ["p", "p", "q", "q"],
    }
)


def test_products_frame_has_the_columns_the_api_needs() -> None:
    assert list(products_frame(PRODUCTS).columns) == ["product_id", "name", "aisle", "department"]


def test_popular_frame_is_ranked_from_one() -> None:
    frame = popular_frame(PopularityRecommender().fit(PRIOR), 3)
    assert frame["rank"].tolist() == [1, 2, 3]
    assert frame["product_id"].tolist() == [1, 3, 2]


def test_bought_together_rows_are_ranked_by_similarity() -> None:
    popularity = PopularityRecommender().fit(PRIOR)
    model = CooccurrenceRecommender(popularity, n_neighbors=2, min_support=1, block_size=2).fit(PRIOR)
    frame = bought_together_frame(model, [1], k=2)
    assert frame["rank"].tolist() == [1, 2]
    assert frame["similar_product_id"].tolist() == [3, 2]
    assert frame["score"].is_monotonic_decreasing


def test_user_recommendations_have_both_strategies_and_discovery_skips_history() -> None:
    model = PopularityRecommender().fit(PRIOR)  # stands in for both models
    frame = user_recommendations_frame(model, model, {10: {1, 2}}, k=2)
    reorder = frame[frame["strategy"] == "reorder"]
    discovery = frame[frame["strategy"] == "discovery"]
    assert reorder["product_id"].tolist() == [1, 3]
    assert discovery["product_id"].tolist() == [3, 4]
    assert discovery["rank"].tolist() == [1, 2]


def test_habits_interval_and_top_categories() -> None:
    habits, top = habits_frames(PRIOR, PRODUCTS, n_categories=2)
    by_user = habits.set_index("user_id")
    assert by_user.loc[10, "n_orders"] == 2
    assert by_user.loc[10, "avg_reorder_interval_days"] == 10.0
    assert pd.isna(by_user.loc[11, "avg_reorder_interval_days"])  # single order: no interval
    user_10 = top[top["user_id"] == 10]
    assert list(zip(user_10["category"], user_10["purchases"], user_10["rank"])) == [("x", 3, 1), ("y", 1, 2)]