"""Pydantic schemas: the JSON shapes returned by the API."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Strategy = Literal["reorder", "discovery"]
StrategyUsed = Literal["reorder", "discovery", "popularity_fallback"]


class ProductOut(BaseModel):
    """A product of the catalogue."""

    model_config = ConfigDict(from_attributes=True)

    product_id: int
    name: str
    aisle: str
    department: str


class RelatedProductOut(ProductOut):
    """A product bought together with another one; a higher score means a stronger link."""

    score: float


class RecommendationsOut(BaseModel):
    """Recommendations for a user, with the strategy that actually produced them."""

    user_id: int
    strategy: StrategyUsed = Field(description="'popularity_fallback' when the user has no history.")
    items: list[ProductOut]


class CategoryOut(BaseModel):
    """A category (aisle) a user buys often, with the number of purchases."""

    model_config = ConfigDict(from_attributes=True)

    category: str
    purchases: int


class HabitsOut(BaseModel):
    """Shopping rhythm and favourite categories of a user."""

    user_id: int
    n_orders: int
    avg_reorder_interval_days: float | None = Field(description="Null when the user has a single order.")
    top_categories: list[CategoryOut]