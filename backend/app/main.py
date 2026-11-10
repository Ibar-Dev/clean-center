import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import OperationalError
from sqlmodel import Session

from app.core.config import settings
from app.core.database import engine, init_db, is_database_locked
from app.core.logging import setup_logging
from app.core.rate_limit import limiter, rate_limit_handler
from app.routers import (
    admin_products,
    admin_reservations,
    auth,
    catalog,
    config,
    health,
    reservations,
)
from app.services.seed import seed_database

setup_logging()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.bind(event="app.startup", environment=settings.environment).info(
        "Iniciando Clean Center API"
    )
    init_db()
    with Session(engine) as session:
        seed_database(session)
    logger.bind(
        event="app.ready",
        docs=f"{settings.api_prefix}/docs",
        rate_limit_enabled=settings.rate_limit_enabled,
    ).info("Aplicación lista")
    yield
    logger.bind(event="app.shutdown").info("Deteniendo Clean Center API")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=None,
    openapi_url=f"{settings.api_prefix}/openapi.json",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)


@app.exception_handler(OperationalError)
async def database_error_handler(request: Request, exc: OperationalError) -> JSONResponse:
    if is_database_locked(exc):
        return JSONResponse(
            status_code=503,
            content={
                "detail": "La base de datos está ocupada. Intentá nuevamente en unos segundos."
            },
        )
    logger.bind(event="database.unhandled_error", path=request.url.path).exception(
        "Error de base de datos no controlado"
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Ocurrió un error interno al acceder a los datos."},
    )


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    request_id = request_id[:64]
    started = time.perf_counter()
    client_ip = _client_ip(request)

    with logger.contextualize(request_id=request_id):
        logger.bind(
            event="http.request",
            method=request.method,
            path=request.url.path,
            ip=client_ip,
        ).info("Petición iniciada")

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.bind(
                event="http.exception",
                method=request.method,
                path=request.url.path,
                ip=client_ip,
                duration_ms=elapsed_ms,
            ).exception("Excepción no controlada")
            raise

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        log = logger.bind(
            event="http.response",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=elapsed_ms,
            ip=client_ip,
        )
        if response.status_code >= 500:
            log.error("Petición finalizada con error")
        elif response.status_code >= 400:
            log.warning("Petición finalizada con advertencia")
        else:
            log.info("Petición finalizada")

        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Retry-After"],
)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(config.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(catalog.router, prefix=settings.api_prefix)
app.include_router(reservations.router, prefix=settings.api_prefix)
app.include_router(admin_reservations.router, prefix=settings.api_prefix)
app.include_router(admin_products.router, prefix=settings.api_prefix)


@app.get(f"{settings.api_prefix}", include_in_schema=False)
def api_root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "docs": f"{settings.api_prefix}/docs",
    }
