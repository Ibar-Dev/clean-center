from fastapi import APIRouter, Query

from app.core.deps import SessionDep
from app.schemas.catalog import CategoryRead, ProductPage, ProductRead
from app.services.catalog import get_public_product, list_categories, list_public_products

router = APIRouter(tags=["catalog"])


@router.get("/categories", response_model=list[CategoryRead])
def categories(session: SessionDep) -> list[CategoryRead]:
    return list_categories(session)


@router.get("/products", response_model=ProductPage)
def products(
    session: SessionDep,
    search: str = Query(default="", max_length=120),
    category: str = Query(default="", max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
) -> ProductPage:
    return list_public_products(
        session,
        search=search,
        category=category,
        page=page,
        page_size=page_size,
    )


@router.get("/products/{product_id}", response_model=ProductRead)
def product_detail(product_id: int, session: SessionDep) -> ProductRead:
    return get_public_product(session, product_id)
