from decimal import Decimal

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.models import Category, Product, utcnow
from app.schemas.admin_product import (
    AdminProductCreate,
    AdminProductStatusUpdate,
    AdminProductUpdate,
)
from app.schemas.catalog import ProductRead


def _get_admin_product(session: Session, product_id: int) -> Product:
    product = session.exec(
        select(Product).options(selectinload(Product.category)).where(Product.id == product_id)
    ).first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )
    return product


def _require_category(session: Session, category_id: int) -> Category:
    category = session.get(Category, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La categoría indicada no existe",
        )
    return category


def create_product(
    session: Session,
    payload: AdminProductCreate,
    *,
    admin_username: str,
) -> ProductRead:
    _require_category(session, payload.category_id)
    product = Product(**payload.model_dump())
    session.add(product)
    session.commit()
    session.refresh(product)
    logger.bind(
        event="admin.product_created",
        admin=admin_username,
        product_id=product.id,
        name=product.name,
        price=str(product.price),
        stock=product.stock,
    ).info("Producto creado")
    return ProductRead.model_validate(_get_admin_product(session, product.id or 0))


def update_product(
    session: Session,
    product_id: int,
    payload: AdminProductUpdate,
    *,
    admin_username: str,
) -> ProductRead:
    product = _get_admin_product(session, product_id)
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)

    if not updates:
        return ProductRead.model_validate(product)

    if "category_id" in updates:
        _require_category(session, int(updates["category_id"]))

    previous_price: Decimal = product.price
    previous_stock: int = product.stock

    for field, value in updates.items():
        setattr(product, field, value)
    product.updated_at = utcnow()

    session.add(product)
    session.commit()
    session.refresh(product)

    logger.bind(
        event="admin.product_updated",
        admin=admin_username,
        product_id=product.id,
        fields=sorted(updates.keys()),
        previous_price=str(previous_price),
        new_price=str(product.price),
        previous_stock=previous_stock,
        new_stock=product.stock,
    ).info("Producto actualizado")

    return ProductRead.model_validate(_get_admin_product(session, product_id))


def set_product_status(
    session: Session,
    product_id: int,
    payload: AdminProductStatusUpdate,
    *,
    admin_username: str,
) -> ProductRead:
    product = _get_admin_product(session, product_id)
    previous = product.is_active
    product.is_active = payload.is_active
    product.updated_at = utcnow()
    session.add(product)
    session.commit()
    session.refresh(product)
    logger.bind(
        event="admin.product_status_changed",
        admin=admin_username,
        product_id=product.id,
        previous=previous,
        current=product.is_active,
    ).info("Estado de producto modificado")
    return ProductRead.model_validate(_get_admin_product(session, product_id))
