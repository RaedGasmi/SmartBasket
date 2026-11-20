"""SQLAlchemy models for the precomputed data served by the API."""
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    """Declarative base class shared by all tables."""


class Product(Base):
    """A product of the catalogue."""

    __tablename__ = "products"

    product_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(255))
    aisle: Mapped[str] = mapped_column(String(100))
    department: Mapped[str] = mapped_column(String(100))


class PopularProduct(Base):
    """Global popularity ranking, served to users without history (cold start)."""

    __tablename__ = "popular_products"

    rank: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"))


class BoughtTogether(Base):
    """Products frequently bought in the same basket as `product_id`, best first."""

    __tablename__ = "bought_together"

    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"), primary_key=True)
    rank: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    similar_product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"))
    score: Mapped[float]


class UserRecommendation(Base):
    """A recommended product for a user; `strategy` is "reorder" or "discovery"."""

    __tablename__ = "user_recommendations"

    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    strategy: Mapped[str] = mapped_column(String(20), primary_key=True)
    rank: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"))


class UserHabit(Base):
    """Shopping rhythm of a user; the interval is NULL for a single order."""

    __tablename__ = "user_habits"

    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    n_orders: Mapped[int]
    avg_reorder_interval_days: Mapped[float | None]


class UserTopCategory(Base):
    """One of a user's most purchased categories (aisles), most purchased first."""

    __tablename__ = "user_top_categories"

    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    rank: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    category: Mapped[str] = mapped_column(String(100))
    purchases: Mapped[int]