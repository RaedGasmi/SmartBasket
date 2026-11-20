"""Popularity baseline: recommend the most purchased products to everyone."""
from collections.abc import Collection

import pandas as pd


class PopularityRecommender:
    """Global popularity ranking, also used as the cold-start fallback."""

    name = "popularity"

    def __init__(self) -> None:
        self._ranking: list[int] = []

    def fit(self, prior: pd.DataFrame) -> "PopularityRecommender":
        """Rank products by number of purchases (ties broken by product id)."""
        counts = prior["product_id"].value_counts().rename_axis("product_id").reset_index(name="n")
        counts = counts.sort_values(["n", "product_id"], ascending=[False, True])
        self._ranking = counts["product_id"].astype(int).tolist()
        return self

    def recommend(self, user_id: int, k: int, exclude: Collection[int] = ()) -> list[int]:
        """Return the k most popular products that are not in `exclude`."""
        recommended: list[int] = []
        for product_id in self._ranking:
            if product_id not in exclude:
                recommended.append(product_id)
                if len(recommended) == k:
                    break
        return recommended