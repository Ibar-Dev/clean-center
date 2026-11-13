from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Column, Numeric
from sqlmodel import Field, Relationship, SQLModel

from app.models.category import Category
from app.models.user import utcnow


class Product(SQLModel, table=True):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price > 0", name="ck_products_price_positive"),
        CheckConstraint("stock >= 0", name="ck_products_stock_non_negative"),
    )

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=160)
    slug: str | None = Field(default=None, index=True, unique=True, max_length=160)
    description: str = Field(default="", max_length=2000)
    price: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    unit: str = Field(max_length=60)
    stock: int = Field(default=0, ge=0)
    category_id: int = Field(foreign_key="categories.id", index=True)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    category: Category | None = Relationship(back_populates="products")
