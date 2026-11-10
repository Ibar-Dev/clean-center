from fastapi import APIRouter, HTTPException, Request, status
from loguru import logger

from app.core.config import settings
from app.core.deps import CurrentUser, SessionDep
from app.core.rate_limit import limiter
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, TokenResponse, UserRead
from app.services.auth import authenticate_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.login_rate_limit)
def login(request: Request, payload: LoginRequest, session: SessionDep) -> TokenResponse:
    user = authenticate_user(session, payload.username, payload.password, _client_ip(request))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token, _expires_in = create_access_token(
        user_id=user.id or 0,
        username=user.username,
        role=user.role,
    )
    return TokenResponse(
        access_token=token,
        user=UserRead.model_validate(user),
    )


@router.get("/me", response_model=UserRead)
def me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.post("/logout")
def logout(current_user: CurrentUser) -> dict[str, str]:
    logger.bind(
        event="auth.logout",
        user_id=current_user.id,
        username=current_user.username,
    ).info("Logout solicitado")
    return {"status": "ok"}
