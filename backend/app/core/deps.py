from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from loguru import logger
from sqlmodel import Session

from app.core.config import settings
from app.core.database import get_session
from app.core.security import decode_access_token
from app.models import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login")

SessionDep = Annotated[Session, Depends(get_session)]
TokenDep = Annotated[str, Depends(oauth2_scheme)]


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_current_user(request: Request, session: SessionDep, token: TokenDep) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub", "0"))
    except (ValueError, TypeError):
        logger.bind(event="auth.token_invalid", ip=_client_ip(request)).warning(
            "Intento de acceso con token inválido"
        )
        raise credentials_error from None

    user = session.get(User, user_id)
    if user is None or not user.is_active:
        logger.bind(
            event="auth.user_unavailable",
            user_id=user_id,
            ip=_client_ip(request),
        ).warning("Token válido para un usuario inexistente o inactivo")
        raise credentials_error

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_admin(current_user: CurrentUser) -> User:
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador",
        )
    return current_user


CurrentAdmin = Annotated[User, Depends(get_current_admin)]
