"""Collaborative filtering recommender: implicit-feedback ALS."""
from collections.abc import Collection

import numpy as np
import pandas as pd
from implicit.als import AlternatingLeastSquares
from scipy import sparse

from ml.src.config import ALS_ALPHA, ALS_FACTORS, ALS_ITERATIONS, ALS_REGULARIZATION, SEED
from ml.src.models.popularity import PopularityRecommender


class ALSRecommender:
    """Matrix factorisation of the user-product purchase matrix (implicit ALS).

    The matrix holds log(1 + n) where n is the number of the user's orders that
    contained the product, so heavy repeat purchases count more without dominating.
    A user's score for a product is the dot product of their factors with the
    product's factors. Users unknown at fit time (cold start) get the popularity
    fallback, which also fills the list when exclusions leave fewer than k items.
    """

    name = "als"

    def __init__(
        self,
        fallback: PopularityRecommender,
        factors: int = ALS_FACTORS,
        regularization: float = ALS_REGULARIZATION,
        iterations: int = ALS_ITERATIONS,
        alpha: float = ALS_ALPHA,
        seed: int = SEED,
    ) -> None:
        self._fallback = fallback
        self._params = {
            "factors": factors,
            "regularization": regularization,
            "alpha": alpha,
            "iterations": iterations,
            "random_state": seed,
        }
        self._item_ids = np.empty(0, dtype=np.int64)
        self._user_rows: dict[int, int] = {}
        self._user_factors = np.empty((0, 0), dtype=np.float32)
        self._item_factors = np.empty((0, 0), dtype=np.float32)

    def fit(self, prior: pd.DataFrame) -> "ALSRecommender":
        """Factorise the user-product matrix built from the purchase history."""
        user_ids = np.sort(prior["user_id"].unique()).astype(np.int64)
        self._item_ids = np.sort(prior["product_id"].unique()).astype(np.int64)
        self._user_rows = {int(user_id): row for row, user_id in enumerate(user_ids)}

        counts = prior.groupby(["user_id", "product_id"]).size().rename("n").reset_index()
        rows = np.searchsorted(user_ids, counts["user_id"].to_numpy())
        cols = np.searchsorted(self._item_ids, counts["product_id"].to_numpy())
        values = np.log1p(counts["n"].to_numpy()).astype(np.float32)
        matrix = sparse.csr_matrix((values, (rows, cols)), shape=(len(user_ids), len(self._item_ids)))

        model = AlternatingLeastSquares(**self._params, use_gpu=False)
        model.fit(matrix, show_progress=False)
        self._user_factors = np.asarray(model.user_factors, dtype=np.float32)
        self._item_factors = np.asarray(model.item_factors, dtype=np.float32)
        return self

    def recommend(self, user_id: int, k: int, exclude: Collection[int] = ()) -> list[int]:
        """Return k products for the user, or the popularity list for an unknown user."""
        row = self._user_rows.get(user_id)
        if row is None:
            return self._fallback.recommend(user_id, k, exclude)

        scores = self._item_factors @ self._user_factors[row]
        scores[self._indices_of(exclude)] = -np.inf
        n_top = min(k, len(scores))
        top = np.argpartition(-scores, n_top - 1)[:n_top]
        top = top[np.lexsort((top, -scores[top]))]
        chosen = [int(self._item_ids[i]) for i in top if np.isfinite(scores[i])]
        if len(chosen) < k:
            chosen += self._fallback.recommend(user_id, k - len(chosen), set(exclude) | set(chosen))
        return chosen

    def _indices_of(self, product_ids: Collection[int]) -> np.ndarray:
        """Map product ids to matrix columns, ignoring ids unknown to the model."""
        ids = np.fromiter(product_ids, dtype=np.int64, count=len(product_ids))
        cols = np.searchsorted(self._item_ids, ids)
        in_range = cols < len(self._item_ids)
        known = in_range & (self._item_ids[np.where(in_range, cols, 0)] == ids)
        return cols[known]