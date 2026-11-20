"""Build the sampled, processed dataset used by every recommender.

Run from the repo root:  python -m ml.src.prepare_data
"""
from ml.src.config import N_USERS, PROCESSED_DIR, RAW_DIR, SEED
from ml.src.data import load_orders, load_products, read_order_products, sample_users


def main() -> None:
    """Sample users, split history/holdout and save parquet files."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    orders = load_orders()
    users = sample_users(orders, N_USERS, SEED)
    user_orders = orders[orders["user_id"].isin(users)]
    prior_orders = user_orders[user_orders["eval_set"] == "prior"]
    train_orders = user_orders[user_orders["eval_set"] == "train"]
    print(f"Users with a labelled last order: {orders[orders['eval_set'] == 'train']['user_id'].nunique()}")
    print(f"Sampled users: {len(users)} (seed={SEED})")

    prior = read_order_products(RAW_DIR / "order_products__prior.csv", prior_orders["order_id"])
    prior = prior.merge(
        prior_orders[["order_id", "user_id", "order_number", "days_since_prior_order"]],
        on="order_id",
    ).sort_values(["user_id", "order_number"])

    test = read_order_products(RAW_DIR / "order_products__train.csv", train_orders["order_id"])
    test = test.merge(train_orders[["order_id", "user_id"]], on="order_id")[["user_id", "product_id"]]

    prior.to_parquet(PROCESSED_DIR / "prior.parquet", index=False)
    test.to_parquet(PROCESSED_DIR / "test.parquet", index=False)
    load_products().to_parquet(PROCESSED_DIR / "products.parquet", index=False)

    print(f"prior rows: {len(prior)} | test rows: {len(test)}")
    print(f"Saved to {PROCESSED_DIR}")


if __name__ == "__main__":
    main()