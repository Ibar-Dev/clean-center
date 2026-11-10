from pydantic import BaseModel, ConfigDict

from app.schemas.common import Money


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    price: Money
    unit: str
    stock: int
    category_id: int
    category: CategoryRead | None = None
    is_active: bool


class ProductPage(BaseModel):
    items: list[ProductRead]
    total: int
    page: int
    page_size: int
    pages: int
