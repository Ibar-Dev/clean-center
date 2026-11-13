import sqlite3
from collections.abc import Generator
from pathlib import Path

from loguru import logger
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings


def _ensure_database_directory(database_url: str) -> None:
    url = make_url(database_url)
    if url.drivername.startswith("sqlite") and url.database not in (None, "", ":memory:"):
        Path(url.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


_ensure_database_directory(settings.database_url)

connect_args = {"check_same_thread": False, "timeout": 30}
if not settings.database_url.startswith("sqlite"):
    connect_args = {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def _configure_sqlite(dbapi_connection, _connection_record) -> None:
    if not isinstance(dbapi_connection, sqlite3.Connection):
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA busy_timeout=5000;")
    finally:
        cursor.close()


@event.listens_for(engine, "handle_error")
def _log_database_error(exception_context) -> None:
    original = exception_context.original_exception
    if not isinstance(original, sqlite3.OperationalError):
        return
    sqlite_code = getattr(original, "sqlite_errorcode", None)
    sqlite_name = getattr(original, "sqlite_errorname", None)
    level = "ERROR"
    message = str(original).lower()
    if sqlite_code in {5, 6} or "locked" in message or "busy" in message:
        level = "WARNING"
    logger.bind(
        event="sqlite.error",
        sqlite_code=sqlite_code,
        sqlite_name=sqlite_name,
        statement=(exception_context.statement or "")[:300],
    ).log(level, "Error de SQLite/WAL: {}", original)


def _table_columns(connection, table: str) -> set[str]:
    rows = connection.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def _ensure_column(connection, table: str, column: str, ddl: str) -> None:
    if column in _table_columns(connection, table):
        return
    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
    logger.bind(event="database.column_added", table=table, column=column).info(
        "Columna agregada por migración ligera"
    )


def _apply_lightweight_migrations(connection) -> None:
    """Agrega columnas e índices nuevos sin perder datos existentes.

    SQLModel.create_all() solo crea tablas nuevas; para bases ya desplegadas hay que
    aplicar los cambios de esquema de forma idempotente.
    """
    _ensure_column(connection, "products", "slug", "slug VARCHAR(160)")
    _ensure_column(
        connection,
        "categories",
        "sort_order",
        "sort_order INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        "reservations",
        "idempotency_key",
        "idempotency_key VARCHAR(64)",
    )
    connection.execute(
        text("CREATE UNIQUE INDEX IF NOT EXISTS ix_products_slug ON products (slug)")
    )
    connection.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_reservations_idempotency_key "
            "ON reservations (idempotency_key)"
        )
    )


def init_db() -> None:
    # Importa los modelos para registrar las tablas en SQLModel.metadata.
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    with engine.begin() as connection:
        _apply_lightweight_migrations(connection)
    with engine.connect() as connection:
        journal_mode = connection.execute(text("PRAGMA journal_mode;")).scalar_one()
        synchronous = connection.execute(text("PRAGMA synchronous;")).scalar_one()
        foreign_keys = connection.execute(text("PRAGMA foreign_keys;")).scalar_one()
    logger.bind(
        event="database.ready",
        journal_mode=journal_mode,
        synchronous=synchronous,
        foreign_keys=foreign_keys,
    ).info("Base de datos inicializada")


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def is_database_locked(exc: Exception) -> bool:
    if isinstance(exc, sqlite3.OperationalError):
        return "locked" in str(exc).lower() or "busy" in str(exc).lower()
    return False
