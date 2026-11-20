"""SmartBasket API: product search, "bought together", recommendations and shopping habits."""
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app import queries
from backend.app.database import make_engine
from backend.app.models import Product
from backend.app.schemas import (
    CategoryOut,
    HabitsOut,
    ProductOut,
    RecommendationsOut,
    RelatedProductOut,
    Strategy,
)

app = FastAPI(
    title="SmartBasket API",
    version="0.1.0",
    description=(
        "Product search, 'bought together', personalised recommendations and shopping habits. "
        "MVP proof of concept: the models are trained on the public Instacart dataset, not on Tunisian data."
    ),
)
engine = make_engine()


def get_session() -> Iterator[Session]:
    """Open a database session for one request and close it afterwards."""
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
Limit = Annotated[int, Query(ge=1, le=50, description="Maximum number of items to return.")]


def product_or_404(session: Session, product_id: int) -> Product:
    """Return the product, or answer 404 if it does not exist."""
    product = queries.get_product(session, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return product


@app.get("/products", tags=["products"], summary="Search products by name")
def list_products(
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=100, description="Part of the name, case-insensitive.")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ProductOut]:
    """Products whose name contains `q`, alphabetically and paginated; every product if `q` is omitted."""
    return [ProductOut.model_validate(row) for row in queries.search_products(session, q, limit, offset)]


@app.get("/products/{product_id}", tags=["products"], summary="Get one product")
def read_product(product_id: int, session: SessionDep) -> ProductOut:
    """Details of one product."""
    return ProductOut.model_validate(product_or_404(session, product_id))


@app.get("/products/{product_id}/bought-together", tags=["products"], summary="Frequently bought together")
def read_bought_together(product_id: int, session: SessionDep, limit: Limit = 10) -> list[RelatedProductOut]:
    """Products most often bought in the same basket. Empty for products that were rarely ordered."""
    product_or_404(session, product_id)
    return [RelatedProductOut.model_validate(row) for row in queries.bought_together(session, product_id, limit)]


@app.get("/users/{user_id}/recommendations", tags=["users"], summary="Recommended for you")
def read_recommendations(
    user_id: int,
    session: SessionDep,
    strategy: Annotated[
        Strategy, Query(description="'reorder': what the user is likely to buy again. 'discovery': new products.")
    ] = "reorder",
    limit: Limit = 10,
) -> RecommendationsOut:
    """Top products for a user. An unknown user gets the popularity list, flagged as `popularity_fallback`."""
    rows = queries.user_recommendations(session, user_id, strategy, limit)
    used = strategy
    if not rows:
        rows = queries.popular_products(session, limit)
        used = "popularity_fallback"
    return RecommendationsOut(user_id=user_id, strategy=used, items=[ProductOut.model_validate(row) for row in rows])


@app.get("/habits/{user_id}", tags=["users"], summary="Shopping habits")
def read_habits(user_id: int, session: SessionDep) -> HabitsOut:
    """Number of orders, average days between orders and favourite categories of a user."""
    habit = queries.get_habit(session, user_id)
    if habit is None:
        raise HTTPException(status_code=404, detail=f"No shopping history for user {user_id}")
    categories = [CategoryOut.model_validate(row) for row in queries.top_categories(session, user_id)]
    return HabitsOut(
        user_id=habit.user_id,
        n_orders=habit.n_orders,
        avg_reorder_interval_days=habit.avg_reorder_interval_days,
        top_categories=categories,
    )