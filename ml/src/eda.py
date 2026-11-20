"""Exploratory statistics and charts for the processed dataset.

Run from the repo root:  python -m ml.src.eda
"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from ml.src.config import PROCESSED_DIR, RESULTS_DIR


def compute_stats(prior: pd.DataFrame, test: pd.DataFrame) -> dict[str, float]:
    """Return dataset statistics relevant to recommender design."""
    basket = prior.groupby("order_id").size()
    orders_per_user = prior.groupby("user_id")["order_id"].nunique()
    pairs = prior[["user_id", "product_id"]].drop_duplicates()
    n_users = prior["user_id"].nunique()
    n_items = prior["product_id"].nunique()

    seen = test.merge(pairs.assign(seen=True), on=["user_id", "product_id"], how="left")
    return {
        "n_users": int(n_users),
        "n_orders_prior": int(prior["order_id"].nunique()),
        "n_products_seen": int(n_items),
        "n_interactions_prior": int(len(prior)),
        "n_user_product_pairs": int(len(pairs)),
        "matrix_density": float(len(pairs) / (n_users * n_items)),
        "basket_size_mean": float(basket.mean()),
        "basket_size_median": float(basket.median()),
        "orders_per_user_mean": float(orders_per_user.mean()),
        "test_items_per_user_mean": float(test.groupby("user_id").size().mean()),
        "test_items_already_in_user_history": float(seen["seen"].notna().mean()),
        "test_items_never_seen_in_prior": float((~test["product_id"].isin(prior["product_id"].unique())).mean()),
    }


def plot_eda(prior: pd.DataFrame, products: pd.DataFrame) -> None:
    """Save a 2x2 overview chart to ml/results/eda.png."""
    names = products.set_index("product_id")["product_name"]
    departments = products.set_index("product_id")["department"]
    basket = prior.groupby("order_id").size()
    orders_per_user = prior.groupby("user_id")["order_id"].nunique()
    top_products = prior["product_id"].value_counts().head(15)[::-1]
    top_departments = prior["product_id"].map(departments).value_counts().head(10)[::-1]

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    axes[0, 0].hist(basket.clip(upper=60), bins=60)
    axes[0, 0].set(title="Basket size (clipped at 60)", xlabel="items per order", ylabel="orders")
    axes[0, 1].hist(orders_per_user, bins=40)
    axes[0, 1].set(title="Prior orders per user", xlabel="orders", ylabel="users")
    axes[1, 0].barh(top_products.index.map(names), top_products.values)
    axes[1, 0].set(title="Top 15 products", xlabel="purchases")
    axes[1, 1].barh(top_departments.index, top_departments.values)
    axes[1, 1].set(title="Top departments", xlabel="purchases")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "eda.png", dpi=120)


def main() -> None:
    """Compute stats, save them as JSON and draw the overview chart."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    prior = pd.read_parquet(PROCESSED_DIR / "prior.parquet")
    test = pd.read_parquet(PROCESSED_DIR / "test.parquet")
    products = pd.read_parquet(PROCESSED_DIR / "products.parquet")

    stats = compute_stats(prior, test)
    (RESULTS_DIR / "eda_stats.json").write_text(json.dumps(stats, indent=2))
    plot_eda(prior, products)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()