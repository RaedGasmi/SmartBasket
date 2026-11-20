"""Loading and sampling helpers for the raw Instacart files."""
from pathlib import Path

import numpy as np
import pandas as pd

from ml.src.config import RAW_DIR

CHUNK_SIZE = 5_000_000


def load_orders() -> pd.DataFrame:
    """Load orders.csv with compact dtypes."""
    return pd.read_csv(
        RAW_DIR / "orders.csv",
        dtype={
            "order_id": "int32",
            "user_id": "int32",
            "eval_set": "category",
            "order_number": "int16",
            "order_dow": "int8",
            "order_hour_of_day": "int8",
            "days_since_prior_order": "float32",
        },
    )


def load_products() -> pd.DataFrame:
    """Load products joined with their aisle and department names."""
    products = pd.read_csv(RAW_DIR / "products.csv")
    aisles = pd.read_csv(RAW_DIR / "aisles.csv")
    departments = pd.read_csv(RAW_DIR / "departments.csv")
    return products.merge(aisles, on="aisle_id").merge(departments, on="department_id")


def sample_users(orders: pd.DataFrame, n_users: int, seed: int) -> np.ndarray:
    """Sample users that have a labelled last order (eval_set == 'train').

    Only these users can be evaluated, because the 'test' orders have no labels.
    """
    eligible = orders.loc[orders["eval_set"] == "train", "user_id"].unique()
    rng = np.random.default_rng(seed)
    return np.sort(rng.choice(eligible, size=n_users, replace=False))


def read_order_products(path: Path, order_ids: pd.Series) -> pd.DataFrame:
    """Read an order_products file in chunks, keeping only the given orders."""
    wanted = set(order_ids.tolist())
    parts = []
    for chunk in pd.read_csv(
        path,
        usecols=["order_id", "product_id", "reordered"],
        dtype={"order_id": "int32", "product_id": "int32", "reordered": "int8"},
        chunksize=CHUNK_SIZE,
    ):
        parts.append(chunk[chunk["order_id"].isin(wanted)])
    return pd.concat(parts, ignore_index=True)