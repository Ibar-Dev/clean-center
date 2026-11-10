from decimal import Decimal

from loguru import logger
from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import hash_password
from app.models import Category, Product, User, UserRole

CATEGORIES = [
    {"name": "Hogar", "slug": "hogar"},
    {"name": "Desinfectantes", "slug": "desinfectantes"},
    {"name": "Industrial", "slug": "industrial"},
    {"name": "Accesorios", "slug": "accesorios"},
]

PRODUCTS = [
    {
        "name": "Detergente Lavanda",
        "description": "Detergente concentrado para vajilla, aroma lavanda.",
        "price": Decimal("2890.00"),
        "unit": "500 ml",
        "stock": 40,
        "category": "hogar",
    },
    {
        "name": "Detergente Limón",
        "description": "Fórmula desengrasante con aroma a limón.",
        "price": Decimal("2890.00"),
        "unit": "500 ml",
        "stock": 35,
        "category": "hogar",
    },
    {
        "name": "Lavandina Concentrada",
        "description": "Lavandina de alto rendimiento para superficies y ropa.",
        "price": Decimal("1990.00"),
        "unit": "1 Litro",
        "stock": 60,
        "category": "desinfectantes",
    },
    {
        "name": "Alcohol Etílico 70%",
        "description": "Alcohol etílico al 70% para desinfección.",
        "price": Decimal("2450.00"),
        "unit": "500 ml",
        "stock": 50,
        "category": "desinfectantes",
    },
    {
        "name": "Desinfectante de Superficies",
        "description": "Desinfectante multisuperficie de acción prolongada.",
        "price": Decimal("3490.00"),
        "unit": "1 Litro",
        "stock": 30,
        "category": "desinfectantes",
    },
    {
        "name": "Limpiador de Pisos",
        "description": "Limpiador perfumado para pisos de cerámica y madera.",
        "price": Decimal("3150.00"),
        "unit": "2 Litros",
        "stock": 25,
        "category": "hogar",
    },
    {
        "name": "Jabón Líquido para Manos",
        "description": "Jabón líquido con glicerina, aroma neutro.",
        "price": Decimal("2290.00"),
        "unit": "500 ml",
        "stock": 45,
        "category": "hogar",
    },
    {
        "name": "Limpiador Desengrasante Industrial",
        "description": "Desengrasante de alta potencia para cocinas y talleres.",
        "price": Decimal("6890.00"),
        "unit": "5 Litros",
        "stock": 18,
        "category": "industrial",
    },
    {
        "name": "Detergente Industrial",
        "description": "Detergente de alto rendimiento para uso profesional.",
        "price": Decimal("7490.00"),
        "unit": "5 Litros",
        "stock": 20,
        "category": "industrial",
    },
    {
        "name": "Alcohol Industrial",
        "description": "Alcohol de uso industrial para limpieza general.",
        "price": Decimal("5990.00"),
        "unit": "5 Litros",
        "stock": 15,
        "category": "industrial",
    },
    {
        "name": "Paño de Microfibra",
        "description": "Paño reutilizable de alta absorción.",
        "price": Decimal("1490.00"),
        "unit": "Unidad",
        "stock": 80,
        "category": "accesorios",
    },
    {
        "name": "Guantes de Limpieza",
        "description": "Guantes resistentes para tareas de limpieza.",
        "price": Decimal("1890.00"),
        "unit": "Par",
        "stock": 70,
        "category": "accesorios",
    },
]


def seed_database(session: Session) -> None:
    categories_by_slug: dict[str, Category] = {}
    for category_data in CATEGORIES:
        category = session.exec(
            select(Category).where(Category.slug == category_data["slug"])
        ).first()
        if category is None:
            category = Category(**category_data)
            session.add(category)
            session.flush()
            logger.bind(event="seed.category_created", slug=category.slug).info(
                "Categoría creada por seed"
            )
        categories_by_slug[category.slug] = category

    for product_data in PRODUCTS:
        existing = session.exec(select(Product).where(Product.name == product_data["name"])).first()
        if existing is not None:
            continue
        category = categories_by_slug[product_data["category"]]
        product = Product(
            name=product_data["name"],
            description=product_data["description"],
            price=product_data["price"],
            unit=product_data["unit"],
            stock=product_data["stock"],
            category_id=category.id or 0,
            is_active=True,
        )
        session.add(product)
        logger.bind(event="seed.product_created", name=product.name).info(
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
