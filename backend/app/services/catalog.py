from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select
from sqlmodel.sql.expression import SelectOfScalar

from app.models import Category, Product
from app.schemas.catalog import CategoryRead, ProductPage, ProductRead


def list_categories(session: Session) -> list[CategoryRead]:
    categories = session.exec(select(Category).order_by(Category.sort_order, Category.name)).all()
    return [CategoryRead.model_validate(category) for category in categories]


def _paginate_products(
    session: Session,
    statement: SelectOfScalar[Product],
    count_statement: SelectOfScalar[int],
    page: int,
    page_size: int,
) -> ProductPage:
    total = session.exec(count_statement).one()
    pages = max(1, ceil(total / page_size)) if total else 0
    products = session.exec(statement.offset((page - 1) * page_size).limit(page_size)).all()
    return ProductPage(
        items=[ProductRead.model_validate(product) for product in products],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


def list_public_products(
    session: Session,
    *,
    search: str = "",
    category: str = "",
    page: int = 1,
    page_size: int = 12,
) -> ProductPage:
    from sqlalchemy.orm import selectinload

    filters = [Product.is_active.is_(True)]
    if search.strip():
        pattern = f"%{search.strip()}%"
        filters.append((Product.name.ilike(pattern)) | (Product.description.ilike(pattern)))
    statement = (
        select(Product)
        .options(selectinload(Product.category))
        .where(*filters)
        .order_by(Product.name)
    )
    count_statement = select(func.count()).select_from(Product).where(*filters)

    if category.strip():
        statement = statement.join(Category).where(Category.slug == category.strip())
        count_statement = count_statement.join(Category).where(Category.slug == category.strip())

    return _paginate_products(session, statement, count_statement, page, page_size)


def list_admin_products(
    session: Session,
    *,
    search: str = "",
    category_id: int | None = None,
    include_inactive: bool = True,
    page: int = 1,
    page_size: int = 20,
) -> ProductPage:
    from sqlalchemy.orm import selectinload

    filters = []
    if not include_inactive:
        filters.append(Product.is_active.is_(True))
    if search.strip():
        pattern = f"%{search.strip()}%"
        filters.append(Product.name.ilike(pattern))
    if category_id is not None:
        filters.append(Product.category_id == category_id)

    statement = (
        select(Product)
        .options(selectinload(Product.category))
        .where(*filters)
        .order_by(Product.name)
    )
    count_statement = select(func.count()).select_from(Product).where(*filters)
    return _paginate_products(session, statement, count_statement, page, page_size)


def get_public_product(session: Session, product_id: int) -> ProductRead:
    from sqlalchemy.orm import selectinload

    product = session.exec(
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.id == product_id, Product.is_active.is_(True))
    ).first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )
    return ProductRead.model_validate(product)
