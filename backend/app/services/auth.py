from loguru import logger
from sqlmodel import Session, select

from app.core.security import hash_password, verify_password
from app.models import User

# Hash de referencia para mantener un costo similar cuando el usuario no existe.
_DUMMY_HASH = hash_password("not-a-real-password")


def authenticate_user(
    session: Session,
    username: str,
    password: str,
    client_ip: str,
) -> User | None:
    normalized_username = username.strip().lower()
    user = session.exec(select(User).where(User.username == normalized_username)).first()

    if user is None:
        verify_password(password, _DUMMY_HASH)
        logger.bind(
            event="auth.login_failed",
            username=normalized_username,
            reason="user_not_found",
            ip=client_ip,
        ).warning("Login fallido")
        return None

    if not user.is_active or not verify_password(password, user.hashed_password):
        logger.bind(
            event="auth.login_failed",
            username=normalized_username,
            reason="invalid_credentials",
            ip=client_ip,
        ).warning("Login fallido")
        return None

    logger.bind(
        event="auth.login_success",
        user_id=user.id,
        username=user.username,
        role=user.role,
        ip=client_ip,
    ).info("Login exitoso")
    return user
