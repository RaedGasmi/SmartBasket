"""Unit tests for saving the fitted models."""
import pickle
from pathlib import Path

import pandas as pd

from ml.src.models.als import ALSRecommender
from ml.src.models.cooccurrence import CooccurrenceRecommender
from ml.src.models.popularity import PopularityRecommender
from ml.src.train import save_models

PRIOR = pd.DataFrame(
    {
        "order_id": [1, 1, 2, 2, 3, 3, 4, 4, 5],
        "user_id": [10, 10, 10, 10, 11, 11, 12, 12, 12],
        "product_id": [1, 2, 1, 2, 1, 2, 3, 4, 3],
    }
)


def test_saved_models_reload_and_recommend_the_same(tmp_path: Path) -> None:
    popularity = PopularityRecommender().fit(PRIOR)
    cooccurrence = CooccurrenceRecommender(popularity, n_neighbors=2, min_support=1, block_size=2).fit(PRIOR)
    als = ALSRecommender(popularity, factors=3, iterations=5, seed=0).fit(PRIOR)
    models = [popularity, cooccurrence, als]

    save_models(models, tmp_path)

    for model in models:
        with (tmp_path / f"{model.name}.pkl").open("rb") as file:
            reloaded = pickle.load(file)
        assert reloaded.recommend(10, k=3) == model.recommend(10, k=3)