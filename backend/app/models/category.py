from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from app.models.user import utcnow

if TYPE_CHECKING:
    from app.models.product import Product


class Category(SQLModel, table=True):
    __tablename__ = "categories"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=100)
    slug: str = Field(index=True, unique=True, max_length=120)
    created_at: datetime = Field(default_factory=utcnow)

    products: list["Product"] = Relationship(back_populates="category")
