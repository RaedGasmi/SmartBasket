"""Item-to-item co-occurrence recommender (cosine similarity on shared baskets)."""
from collections.abc import Collection

import numpy as np
import pandas as pd
from scipy import sparse

from ml.src.models.popularity import PopularityRecommender


class CooccurrenceRecommender:
    """Recommend items that are frequently bought in the same basket as a given item.

    Similarity between items i and j is cosine similarity of their basket-membership
    vectors: cooc(i, j) / sqrt(n_i * n_j). Dividing by the popularity of both items
    stops best-sellers from being the "neighbour" of everything.

    For a user, every item in their history votes for its neighbours (and for itself),
    weighted by the share of the user's orders that contained it. When fewer than k
    items get a score, e.g. a new user, the popularity fallback fills the list.
    """

    name = "cooccurrence"

    def __init__(
        self,
        fallback: PopularityRecommender,
        n_neighbors: int = 50,
        min_support: int = 5,
        block_size: int = 500,
    ) -> None:
        self._fallback = fallback
        self._n_neighbors = n_neighbors
        self._min_support = min_support
        self._block_size = block_size
        self._item_ids = np.empty(0, dtype=np.int64)
        self._neighbor_idx = np.empty((0, 0), dtype=np.int32)
        self._neighbor_sim = np.empty((0, 0), dtype=np.float32)
        self._profiles: dict[int, tuple[np.ndarray, np.ndarray]] = {}

    def fit(self, prior: pd.DataFrame) -> "CooccurrenceRecommender":
        """Build the neighbour table from baskets and the user profiles from history.

        Items bought in fewer than `min_support` orders are never suggested as
        neighbours, because their similarity estimates are too noisy.
        """
        self._item_ids = np.sort(prior["product_id"].unique()).astype(np.int64)
        item_col = np.searchsorted(self._item_ids, prior["product_id"].to_numpy())
        order_row, _ = pd.factorize(prior["order_id"])
        basket = sparse.csr_matrix(
            (np.ones(len(prior), dtype=np.float32), (order_row, item_col)),
            shape=(order_row.max() + 1, len(self._item_ids)),
        )
        self._build_neighbors(basket)
        self._build_profiles(prior, item_col)
        return self

    def _build_neighbors(self, basket: sparse.csr_matrix) -> None:
        """Keep the top `n_neighbors` cosine neighbours of every item, block by block."""
        n_items = basket.shape[1]
        n_neighbors = min(self._n_neighbors, n_items)
        n_orders_per_item = np.asarray(basket.sum(axis=0)).ravel()
        norm = np.sqrt(n_orders_per_item).astype(np.float32)
        supported = n_orders_per_item >= self._min_support
        basket_t = basket.T.tocsr()

        self._neighbor_idx = np.zeros((n_items, n_neighbors), dtype=np.int32)
        self._neighbor_sim = np.zeros((n_items, n_neighbors), dtype=np.float32)
        for start in range(0, n_items, self._block_size):
            stop = min(start + self._block_size, n_items)
            rows = np.arange(start, stop)
            sim = (basket_t[start:stop] @ basket).toarray()
            sim /= norm[start:stop, None] * norm[None, :]
            sim[:, ~supported] = 0.0
            sim[~supported[start:stop], :] = 0.0
            sim[rows - start, rows] = 0.0
            top = np.argpartition(sim, -n_neighbors, axis=1)[:, -n_neighbors:]
            top_sim = np.take_along_axis(sim, top, axis=1)
            order = np.argsort(-top_sim, axis=1, kind="stable")
            self._neighbor_idx[start:stop] = np.take_along_axis(top, order, axis=1)
            self._neighbor_sim[start:stop] = np.take_along_axis(top_sim, order, axis=1)

    def _build_profiles(self, prior: pd.DataFrame, item_col: np.ndarray) -> None:
        """Store, per user, their items and the share of their orders containing each."""
        pairs = pd.DataFrame(
            {"user_id": prior["user_id"].to_numpy(), "item": item_col, "order_id": prior["order_id"].to_numpy()}
        )
        n_orders = pairs.groupby("user_id")["order_id"].nunique()
        counts = pairs.groupby(["user_id", "item"]).size().rename("n").reset_index()
        counts["weight"] = counts["n"] / counts["user_id"].map(n_orders)
        self._profiles = {
            int(user_id): (group["item"].to_numpy(), group["weight"].to_numpy())
            for user_id, group in counts.groupby("user_id")
        }

    def similar_items(self, product_id: int, k: int = 10) -> list[tuple[int, float]]:
        """Return up to k (product_id, similarity) pairs: the "bought together" list."""
        index = int(np.searchsorted(self._item_ids, product_id))
        if index >= len(self._item_ids) or self._item_ids[index] != product_id:
            return []
        sims = self._neighbor_sim[index, :k]
        keep = sims > 0
        return [
            (int(self._item_ids[i]), float(s))
            for i, s in zip(self._neighbor_idx[index, :k][keep], sims[keep])
        ]

    def recommend(self, user_id: int, k: int, exclude: Collection[int] = ()) -> list[int]:
        """Return k products for the user, filling with popular items when scores run out."""
        chosen: list[int] = []
        profile = self._profiles.get(user_id)
        if profile is not None:
            chosen = self._score_user(*profile, k, exclude)
        if len(chosen) < k:
            chosen += self._fallback.recommend(user_id, k - len(chosen), set(exclude) | set(chosen))
        return chosen

    def _score_user(self, items: np.ndarray, weights: np.ndarray, k: int, exclude: Collection[int]) -> list[int]:
        """Rank items by the weighted similarity votes of the user's history."""
        votes = self._neighbor_sim[items] * weights[:, None]
        scores = np.bincount(
            self._neighbor_idx[items].ravel(), weights=votes.ravel(), minlength=len(self._item_ids)
        )
        scores[items] += weights
        for product_id in exclude:
            index = int(np.searchsorted(self._item_ids, product_id))
            if index < len(self._item_ids) and self._item_ids[index] == product_id:
                scores[index] = 0.0
        candidates = np.flatnonzero(scores > 0)
        if len(candidates) > k:
            candidates = candidates[np.argpartition(-scores[candidates], k - 1)[:k]]
        ranked = candidates[np.lexsort((candidates, -scores[candidates]))]
        return [int(self._item_ids[i]) for i in ranked]