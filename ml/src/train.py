"""Single entry point: fit every recommender, evaluate it and save the metrics.

Run from the repo root:  python -m ml.src.train
"""
import json
import pickle
from collections.abc import Sequence
from pathlib import Path

import pandas as pd
from threadpoolctl import threadpool_limits

from ml.src.config import MODELS_DIR, N_USERS, PROCESSED_DIR, RESULTS_DIR, SEED, TOP_K
from ml.src.evaluation import PROTOCOLS, Recommender, evaluate
from ml.src.models.als import ALSRecommender
from ml.src.models.cooccurrence import CooccurrenceRecommender
from ml.src.models.popularity import PopularityRecommender
from ml.src.report import plot_comparison, results_to_frame, save_table


def to_user_sets(interactions: pd.DataFrame) -> dict[int, set[int]]:
    """Map each user id to the set of product ids they bought."""
    return {
        int(user_id): {int(p) for p in products}
        for user_id, products in interactions.groupby("user_id")["product_id"]
    }


def print_table(results: dict[str, dict[str, dict[str, float]]]) -> None:
    """Print one metrics table per evaluation protocol."""
    for protocol, by_model in results.items():
        print(f"\nProtocol: {protocol}")
        print(pd.DataFrame(by_model).T.round(4).to_string())


def print_bought_together_samples(
    model: CooccurrenceRecommender, prior: pd.DataFrame, products: pd.DataFrame, n_products: int = 3
) -> None:
    """Print the "bought together" list of the most popular products, as a sanity check."""
    names = products.set_index("product_id")["product_name"]
    for product_id in prior["product_id"].value_counts().head(n_products).index:
        print(f"\nBought together with '{names[product_id]}':")
        for other_id, similarity in model.similar_items(int(product_id), k=5):
            print(f"  {similarity:.3f}  {names[other_id]}")


def print_recommendation_samples(model: Recommender, products: pd.DataFrame, known_user_id: int, k: int = 5) -> None:
    """Print top-k lists for a user with history and for an unknown user (cold start)."""
    names = products.set_index("product_id")["product_name"]
    for label, user_id in ((f"user {known_user_id} (has history)", known_user_id), ("unknown user (cold start)", -1)):
        print(f"\nRecommended by '{model.name}' for {label}:")
        for product_id in model.recommend(user_id, k, set()):
            print(f"  {names[product_id]}")


def save_models(models: Sequence[Recommender], directory: Path) -> None:
    """Pickle every fitted model to <directory>/<model name>.pkl."""
    directory.mkdir(parents=True, exist_ok=True)
    for model in models:
        with (directory / f"{model.name}.pkl").open("wb") as file:
            pickle.dump(model, file)


def main() -> None:
    """Fit all models on the history, evaluate them and save models, metrics, table and chart."""
    prior = pd.read_parquet(PROCESSED_DIR / "prior.parquet")
    test = pd.read_parquet(PROCESSED_DIR / "test.parquet")
    products = pd.read_parquet(PROCESSED_DIR / "products.parquet")
    history, holdout = to_user_sets(prior), to_user_sets(test)

    # A single BLAS thread avoids a slow-down in implicit's ALS and keeps runs repeatable.
    with threadpool_limits(limits=1, user_api="blas"):
        popularity = PopularityRecommender().fit(prior)
        cooccurrence = CooccurrenceRecommender(fallback=popularity).fit(prior)
        als = ALSRecommender(fallback=popularity).fit(prior)
        models: list[Recommender] = [popularity, cooccurrence, als]
        results = {
            protocol: {model.name: evaluate(model, history, holdout, TOP_K, protocol) for model in models}
            for protocol in PROTOCOLS
        }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"seed": SEED, "n_users_sampled": N_USERS, "k": TOP_K, "results": results}
    (RESULTS_DIR / "metrics.json").write_text(json.dumps(payload, indent=2))
    frame = results_to_frame(results)
    save_table(frame, TOP_K, RESULTS_DIR)
    plot_comparison(frame, TOP_K, RESULTS_DIR / "model_comparison.png")
    save_models(models, MODELS_DIR)

    print_table(results)
    print_bought_together_samples(cooccurrence, prior, products)
    print_recommendation_samples(als, products, known_user_id=min(history))


if __name__ == "__main__":
    main()