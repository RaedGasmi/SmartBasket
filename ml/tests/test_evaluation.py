"""Unit tests for the ranking metrics and the evaluation protocols."""
import pandas as pd
import pytest

from ml.src.evaluation import evaluate, hit_rate_at_k, precision_at_k, recall_at_k
from ml.src.models.popularity import PopularityRecommender


def test_metrics_on_known_example() -> None:
    recommended = [1, 2, 3, 4]
    relevant = {2, 4, 9}
    assert precision_at_k(recommended, relevant, 4) == pytest.approx(0.5)
    assert recall_at_k(recommended, relevant, 4) == pytest.approx(2 / 3)
    assert hit_rate_at_k(recommended, relevant, 4) == 1.0
    assert hit_rate_at_k(recommended, {9}, 4) == 0.0


def test_metrics_only_look_at_top_k() -> None:
    assert precision_at_k([1, 2, 3], {3}, 2) == 0.0


def test_popularity_ranks_by_count_and_respects_exclude() -> None:
    prior = pd.DataFrame({"product_id": [5, 5, 5, 7, 7, 3]})
    model = PopularityRecommender().fit(prior)
    assert model.recommend(user_id=1, k=2) == [5, 7]
    assert model.recommend(user_id=1, k=2, exclude={5}) == [7, 3]


def test_evaluate_full_and_discovery_protocols() -> None:
    prior = pd.DataFrame({"product_id": [5, 5, 5, 7, 7, 3]})
    model = PopularityRecommender().fit(prior)
    history = {1: {5}, 2: {5, 7, 3}}
    holdout = {1: {5, 3}, 2: {7}}

    full = evaluate(model, history, holdout, k=2, protocol="full")
    assert full["n_users_evaluated"] == 2
    assert full["precision@2"] == pytest.approx((1 / 2 + 1 / 2) / 2)

    discovery = evaluate(model, history, holdout, k=2, protocol="discovery")
    assert discovery["n_users_evaluated"] == 1  # user 2 has nothing new in the holdout
    assert discovery["recall@2"] == 1.0  # user 1: new item 3 is recommended after excluding 5


def test_evaluate_rejects_unknown_protocol() -> None:
    with pytest.raises(ValueError):
        evaluate(PopularityRecommender(), {}, {}, k=10, protocol="nope")