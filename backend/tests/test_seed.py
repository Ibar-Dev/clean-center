from decimal import Decimal

from sqlmodel import Session, select

from app.core.database import engine
from app.models import Category, Product
from app.services.seed import load_seed_catalog, seed_database


def test_seed_catalog_defines_six_categories_and_68_products() -> None:
    catalog = load_seed_catalog()

    total_products = sum(len(category.products) for category in catalog.categories)

    assert len(catalog.categories) == 6
    assert total_products == 68
    assert [category.sort_order for category in catalog.categories] == [1, 2, 3, 4, 5, 6]


def test_seed_creates_all_products_with_default_stock() -> None:
    catalog = load_seed_catalog()
    seed_slugs = {product.slug for category in catalog.categories for product in category.products}

    with Session(engine) as session:
        stored = {
            product.slug: product
            for product in session.exec(select(Product)).all()
            if product.slug is not None
        }

    assert seed_slugs <= stored.keys()
    assert all(stored[slug].stock == 50 for slug in seed_slugs)
    assert all(stored[slug].is_active for slug in seed_slugs)


def test_seed_is_idempotent() -> None:
    with Session(engine) as session:
        seed_database(session)

    with Session(engine) as session:
        first_products = len(session.exec(select(Product)).all())
        first_categories = len(session.exec(select(Category)).all())
        seed_database(session)

    with Session(engine) as session:
        second_products = len(session.exec(select(Product)).all())
        second_categories = len(session.exec(select(Category)).all())

    assert second_products == first_products
    assert second_categories == first_categories


def test_seed_does_not_overwrite_admin_changes() -> None:
    catalog = load_seed_catalog()
    slug = catalog.categories[-1].products[0].slug

    with Session(engine) as session:
        product = session.exec(select(Product).where(Product.slug == slug)).one()
        product.price = Decimal("99999.00")
        product.stock = 7
        product.name = "Editado desde admin"
        product.is_active = False
        session.add(product)
        session.commit()

    with Session(engine) as session:
        seed_database(session)

    with Session(engine) as session:
        product = session.exec(select(Product).where(Product.slug == slug)).one()
        assert product.price == Decimal("99999.00")
        assert product.stock == 7
        assert product.name == "Editado desde admin"
        assert product.is_active is False
