from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """Devuelve la fecha actual con zona horaria UTC."""
    return datetime.now(UTC)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=80)
    hashed_password: str
    role: str = Field(default="ADMIN", max_length=20)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow)
