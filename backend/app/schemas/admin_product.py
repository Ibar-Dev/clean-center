from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.catalog import ProductRead


class AdminProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=2000)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    unit: str = Field(min_length=1, max_length=60)
    stock: int = Field(default=0, ge=0, le=1_000_000)
    category_id: int = Field(gt=0)
    is_active: bool = True

    @field_validator("name", "description", "unit")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("price")
    @classmethod
    def validate_price(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("El precio debe ser mayor a cero")
        return value.quantize(Decimal("0.01"))


class AdminProductUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    unit: str | None = Field(default=None, min_length=1, max_length=60)
    stock: int | None = Field(default=None, ge=0, le=1_000_000)
    category_id: int | None = Field(default=None, gt=0)
    is_active: bool | None = None

    @field_validator("name", "description", "unit")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("price")
    @classmethod
    def validate_optional_price(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("El precio debe ser mayor a cero")
        return value.quantize(Decimal("0.01"))


class AdminProductStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool


class AdminProductPage(BaseModel):
    items: list[ProductRead]
    total: int
    page: int
    page_size: int
    pages: int
