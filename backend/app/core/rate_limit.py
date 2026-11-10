from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.rate_limit_enabled,
    # No inyectamos cabeceras X-RateLimit-* para no exigir un parámetro Response
    # en cada endpoint decorado (SlowAPI lo requiere si esta opción está activa).
    headers_enabled=False,
)


def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    client_ip = get_remote_address(request)
    logger.bind(event="rate_limit.exceeded", ip=client_ip, path=request.url.path).warning(
        "Rate limit excedido"
    )
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Demasiadas solicitudes. Esperá unos minutos antes de volver a intentar."
        },
        headers={"Retry-After": "60"},
    )
