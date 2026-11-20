"""Ranking metrics and the evaluation harness shared by all recommenders."""
from collections.abc import Collection, Mapping, Sequence
from typing import Protocol

PROTOCOLS = ("full", "discovery")


class Recommender(Protocol):
    """Interface every recommender must implement."""

    name: str

    def recommend(self, user_id: int, k: int, exclude: Collection[int]) -> list[int]:
        """Return up to k product ids for a user, never returning ids in `exclude`."""


def precision_at_k(recommended: Sequence[int], relevant: Collection[int], k: int) -> float:
    """Fraction of the top-k recommendations that are relevant."""
    return len(set(recommended[:k]) & set(relevant)) / k


def recall_at_k(recommended: Sequence[int], relevant: Collection[int], k: int) -> float:
    """Fraction of the relevant items found in the top-k recommendations."""
    return len(set(recommended[:k]) & set(relevant)) / len(relevant)


def hit_rate_at_k(recommended: Sequence[int], relevant: Collection[int], k: int) -> float:
    """1.0 if at least one relevant item is in the top-k, else 0.0."""
    return float(len(set(recommended[:k]) & set(relevant)) > 0)


def evaluate(
    model: Recommender,
    history: Mapping[int, set[int]],
    holdout: Mapping[int, set[int]],
    k: int,
    protocol: str,
) -> dict[str, float]:
    """Average precision@k, recall@k and hit-rate@k over the users of the holdout.

    Protocols:
      - "full": recommendations may include items the user already bought and every
        holdout item counts. Grocery shopping is repeat-driven, so this is the realistic
        "what will I buy next" setting.
      - "discovery": recommendations exclude the user's history and only items the user
        never bought before count. Users without any new item in the holdout are skipped.
    """
    if protocol not in PROTOCOLS:
        raise ValueError(f"protocol must be one of {PROTOCOLS}, got {protocol!r}")

    totals = {"precision": 0.0, "recall": 0.0, "hit_rate": 0.0}
    n_users = 0
    for user_id, target in holdout.items():
        seen = history.get(user_id, set())
        if protocol == "full":
            relevant, exclude = target, set()
        else:
            relevant, exclude = target - seen, seen
        if not relevant:
            continue
        recommended = model.recommend(user_id, k, exclude)
        totals["precision"] += precision_at_k(recommended, relevant, k)
        totals["recall"] += recall_at_k(recommended, relevant, k)
        totals["hit_rate"] += hit_rate_at_k(recommended, relevant, k)
        n_users += 1

    return {
        f"precision@{k}": totals["precision"] / n_users,
        f"recall@{k}": totals["recall"] / n_users,
        f"hit_rate@{k}": totals["hit_rate"] / n_users,
        "n_users_evaluated": n_users,
    }