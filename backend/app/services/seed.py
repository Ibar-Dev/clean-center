import json
from decimal import Decimal
from pathlib import Path

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import hash_password
from app.models import Category, Product, User, UserRole


class SeedProduct(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=160)
    slug: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=2000)
    unit: str = Field(min_length=1, max_length=60)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    stock: int = Field(default=0, ge=0, le=1_000_000)
    is_active: bool = True


class SeedCategory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=120)
    sort_order: int = Field(default=0, ge=0)
    products: list[SeedProduct] = Field(min_length=1)


class SeedCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = "1.0.0"
    currency: str = "ARS"
    categories: list[SeedCategory] = Field(min_length=1)

    @field_validator("categories")
    @classmethod
    def validate_unique_slugs(cls, categories: list[SeedCategory]) -> list[SeedCategory]:
        category_slugs = [category.slug for category in categories]
        if len(category_slugs) != len(set(category_slugs)):
            raise ValueError("Hay categorías con slug duplicado en el catálogo inicial")
        product_slugs = [product.slug for category in categories for product in category.products]
        if len(product_slugs) != len(set(product_slugs)):
            raise ValueError("Hay productos con slug duplicado en el catálogo inicial")
        return categories


def load_seed_catalog(path: Path | None = None) -> SeedCatalog:
    seed_path = path or settings.catalog_seed_path
    try:
        raw = seed_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"No se pudo leer el catálogo inicial en {seed_path}") from exc

    try:
        return SeedCatalog.model_validate(json.loads(raw))
    except ValueError as exc:
        raise RuntimeError(f"El catálogo inicial {seed_path} no es válido: {exc}") from exc


def seed_database(session: Session) -> None:
    catalog = load_seed_catalog()

    categories_by_slug: dict[str, Category] = {}
    for category_data in catalog.categories:
        category = session.exec(select(Category).where(Category.slug == category_data.slug)).first()
        if category is None:
            category = Category(
                name=category_data.name,
                slug=category_data.slug,
                sort_order=category_data.sort_order,
            )
            session.add(category)
            session.flush()
            logger.bind(event="seed.category_created", slug=category.slug).info(
                "Categoría creada por seed"
            )
        categories_by_slug[category.slug] = category

    for category_data in catalog.categories:
        category = categories_by_slug[category_data.slug]
        for product_data in category_data.products:
            existing = session.exec(
                select(Product).where(Product.slug == product_data.slug)
            ).first()
            if existing is not None:
                # Nunca se pisan precios, stock ni estado definidos desde /admin.
                continue
            product = Product(
                name=product_data.name,
                slug=product_data.slug,
                description=product_data.description,
                price=product_data.price,
                unit=product_data.unit,
                stock=product_data.stock,
                category_id=category.id or 0,
                is_active=product_data.is_active,
            )
            session.add(product)
            logger.bind(event="seed.product_created", slug=product.slug).info(
                "Producto creado por seed"
            )

    username = settings.admin_username.strip().lower()
    admin = session.exec(select(User).where(User.username == username)).first()
    if admin is None:
        admin = User(
            username=username,
            hashed_password=hash_password(settings.admin_password),
            role=UserRole.ADMIN.value,
            is_active=True,
        )
        session.add(admin)
        logger.bind(event="seed.admin_created", username=username).info("Usuario admin creado")
    else:
        logger.bind(event="seed.admin_exists", username=username).debug("Usuario admin existente")

    session.commit()
