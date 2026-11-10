from fastapi import APIRouter, Query, status

from app.core.deps import CurrentAdmin, SessionDep
from app.schemas.admin_product import (
    AdminProductCreate,
    AdminProductPage,
    AdminProductStatusUpdate,
    AdminProductUpdate,
)
from app.schemas.catalog import CategoryRead, ProductRead
from app.services.admin_products import create_product, set_product_status, update_product
from app.services.catalog import list_admin_products, list_categories

router = APIRouter(prefix="/admin", tags=["admin-products"])


@router.get("/categories", response_model=list[CategoryRead])
def admin_categories(admin: CurrentAdmin, session: SessionDep) -> list[CategoryRead]:
    return list_categories(session)


@router.get("/products", response_model=AdminProductPage)
def products(
    admin: CurrentAdmin,
    session: SessionDep,
    search: str = Query(default="", max_length=120),
    category_id: int | None = Query(default=None, ge=1),
    include_inactive: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AdminProductPage:
    result = list_admin_products(
        session,
        search=search,
        category_id=category_id,
        include_inactive=include_inactive,
        page=page,
        page_size=page_size,
    )
    return AdminProductPage(**result.model_dump())


@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def new_product(
    payload: AdminProductCreate,
    admin: CurrentAdmin,
    session: SessionDep,
) -> ProductRead:
    return create_product(session, payload, admin_username=admin.username)


@router.patch("/products/{product_id}", response_model=ProductRead)
def edit_product(
    product_id: int,
    payload: AdminProductUpdate,
    admin: CurrentAdmin,
    session: SessionDep,
) -> ProductRead:
    return update_product(
        session,
        product_id,
        payload,
        admin_username=admin.username,
    )


@router.patch("/products/{product_id}/status", response_model=ProductRead)
def change_product_status(
    product_id: int,
    payload: AdminProductStatusUpdate,
    admin: CurrentAdmin,
    session: SessionDep,
) -> ProductRead:
    return set_product_status(
        session,
        product_id,
        payload,
        admin_username=admin.username,
    )
