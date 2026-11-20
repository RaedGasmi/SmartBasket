"""Precompute everything the API serves and write it as CSV files in data/serving/.

The CSV files are the only interface between the ML pipeline and the backend: the
backend never imports this package. Run from the repo root, after train.py:

    python -m ml.src.export_serving

Strategies written to user_recommendations.csv:
  - "reorder":   co-occurrence model, may include products the user already bought
  - "discovery": ALS model, only products the user never bought
"""
import pickle
from collections.abc import Iterable, Mapping

import pandas as pd
from threadpoolctl import threadpool_limits

from ml.src.config import MODELS_DIR, N_POPULAR, N_TOP_CATEGORIES, PROCESSED_DIR, SERVING_DIR, TOP_K
from ml.src.evaluation import Recommender
from ml.src.models.cooccurrence import CooccurrenceRecommender
from ml.src.models.popularity import PopularityRecommender
from ml.src.train import to_user_sets


def products_frame(products: pd.DataFrame) -> pd.DataFrame:
    """Select the product columns the API needs."""
    return products.rename(columns={"product_name": "name"})[["product_id", "name", "aisle", "department"]]


def popular_frame(popularity: PopularityRecommender, n: int) -> pd.DataFrame:
    """The n most popular products, ranked from 1: the cold-start list."""
    product_ids = popularity.recommend(0, n)
    return pd.DataFrame({"rank": range(1, len(product_ids) + 1), "product_id": product_ids})


def bought_together_frame(model: CooccurrenceRecommender, product_ids: Iterable[int], k: int) -> pd.DataFrame:
    """Top-k "bought together" neighbours of every product, with their similarity score."""
    rows = [
        {"product_id": product_id, "rank": rank, "similar_product_id": other_id, "score": score}
        for product_id in product_ids
        for rank, (other_id, score) in enumerate(model.similar_items(product_id, k), start=1)
    ]
    return pd.DataFrame(rows, columns=["product_id", "rank", "similar_product_id", "score"])


def user_recommendations_frame(
    reorder_model: Recommender,
    discovery_model: Recommender,
    history: Mapping[int, set[int]],
    k: int,
) -> pd.DataFrame:
    """Top-k lists per user for both strategies; discovery never repeats a past purchase."""
    rows = []
    for user_id in sorted(history):
        lists = {
            "reorder": reorder_model.recommend(user_id, k, set()),
            "discovery": discovery_model.recommend(user_id, k, history[user_id]),
        }
        for strategy, product_ids in lists.items():
            rows.extend(
                {"user_id": user_id, "strategy": strategy, "rank": rank, "product_id": product_id}
                for rank, product_id in enumerate(product_ids, start=1)
            )
    return pd.DataFrame(rows, columns=["user_id", "strategy", "rank", "product_id"])


def habits_frames(
    prior: pd.DataFrame, products: pd.DataFrame, n_categories: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-user order count, average days between orders, and top aisles by purchases.

    The average interval is empty for a user with a single order, because the first
    order has no previous order to measure from.
    """
    orders = prior[["user_id", "order_id", "days_since_prior_order"]].drop_duplicates("order_id")
    habits = (
        orders.groupby("user_id")
        .agg(n_orders=("order_id", "size"), avg_reorder_interval_days=("days_since_prior_order", "mean"))
        .reset_index()
    )
    habits["avg_reorder_interval_days"] = habits["avg_reorder_interval_days"].round(1)

    aisles = products.set_index("product_id")["aisle"]
    purchases = (
        prior.assign(category=prior["product_id"].map(aisles))
        .groupby(["user_id", "category"])
        .size()
        .rename("purchases")
        .reset_index()
        .sort_values(["user_id", "purchases", "category"], ascending=[True, False, True])
    )
    top = purchases.groupby("user_id").head(n_categories).copy()
    top["rank"] = top.groupby("user_id").cumcount() + 1
    return habits, top[["user_id", "rank", "category", "purchases"]]


def load_model(name: str) -> Recommender:
    """Load a model pickled by train.py."""
    with (MODELS_DIR / f"{name}.pkl").open("rb") as file:
        return pickle.load(file)


def main() -> None:
    """Build every serving table from the saved models and write the CSV files."""
    prior = pd.read_parquet(PROCESSED_DIR / "prior.parquet")
    products = pd.read_parquet(PROCESSED_DIR / "products.parquet")
    popularity, cooccurrence, als = (load_model(name) for name in ("popularity", "cooccurrence", "als"))
    history = to_user_sets(prior)
    seen_products = sorted(int(product_id) for product_id in prior["product_id"].unique())

    with threadpool_limits(limits=1, user_api="blas"):
        habits, top_categories = habits_frames(prior, products, N_TOP_CATEGORIES)
        frames = {
            "products": products_frame(products),
            "popular_products": popular_frame(popularity, N_POPULAR),
            "bought_together": bought_together_frame(cooccurrence, seen_products, TOP_K),
            "user_recommendations": user_recommendations_frame(cooccurrence, als, history, TOP_K),
            "user_habits": habits,
            "user_top_categories": top_categories,
        }

    SERVING_DIR.mkdir(parents=True, exist_ok=True)
    for name, frame in frames.items():
        frame.to_csv(SERVING_DIR / f"{name}.csv", index=False)
        print(f"{name}.csv: {len(frame)} rows")


if __name__ == "__main__":
    main()