"""Read-only database queries behind the API endpoints."""
from collections.abc import Sequence
from typing import Any

from sqlalchemy import Row, func, select
from sqlalchemy.orm import Session

from backend.app.models import (
    BoughtTogether,
    PopularProduct,
    Product,
    UserHabit,
    UserRecommendation,
    UserTopCategory,
)

PRODUCT_COLUMNS = (Product.product_id, Product.name, Product.aisle, Product.department)

Rows = Sequence[Row[Any]]


def search_products(session: Session, text: str | None, limit: int, offset: int) -> Rows:
    """Products whose name contains `text` (case-insensitive), alphabetically; all products if `text` is empty."""
    statement = select(*PRODUCT_COLUMNS).order_by(Product.name, Product.product_id).limit(limit).offset(offset)
    if text:
        statement = statement.where(func.lower(Product.name).contains(text.lower(), autoescape=True))
    return session.execute(statement).all()


def get_product(session: Session, product_id: int) -> Product | None:
    """The product with this id, or None."""
    return session.get(Product, product_id)


def bought_together(session: Session, product_id: int, limit: int) -> Rows:
    """Products bought with `product_id`, best first, each with its similarity score."""
    statement = (
        select(*PRODUCT_COLUMNS, BoughtTogether.score)
        .select_from(BoughtTogether)
        .join(Product, Product.product_id == BoughtTogether.similar_product_id)
        .where(BoughtTogether.product_id == product_id)
        .order_by(BoughtTogether.rank)
        .limit(limit)
    )
    return session.execute(statement).all()


def user_recommendations(session: Session, user_id: int, strategy: str, limit: int) -> Rows:
    """The precomputed list of a user for one strategy; empty for an unknown user."""
    statement = (
        select(*PRODUCT_COLUMNS)
        .select_from(UserRecommendation)
        .join(Product, Product.product_id == UserRecommendation.product_id)
        .where(UserRecommendation.user_id == user_id, UserRecommendation.strategy == strategy)
        .order_by(UserRecommendation.rank)
        .limit(limit)
    )
    return session.execute(statement).all()


def popular_products(session: Session, limit: int) -> Rows:
    """The globally most popular products, used when a user has no history."""
    statement = (
        select(*PRODUCT_COLUMNS)
        .select_from(PopularProduct)
        .join(Product, Product.product_id == PopularProduct.product_id)
        .order_by(PopularProduct.rank)
        .limit(limit)
    )
    return session.execute(statement).all()


def get_habit(session: Session, user_id: int) -> UserHabit | None:
    """The shopping rhythm of a user, or None for an unknown user."""
    return session.get(UserHabit, user_id)


def top_categories(session: Session, user_id: int) -> Rows:
    """A user's most purchased categories, most purchased first."""
    statement = (
        select(UserTopCategory.category, UserTopCategory.purchases)
        .where(UserTopCategory.user_id == user_id)
        .order_by(UserTopCategory.rank)
    )
    return session.execute(statement).all()