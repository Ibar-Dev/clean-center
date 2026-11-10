from fastapi import APIRouter
from sqlalchemy import text
from sqlmodel import Session

from app.core.database import engine

router = APIRouter(tags=["health"])


@router.get("/health")
def healthcheck() -> dict[str, str]:
    with Session(engine) as session:
        session.execute(text("SELECT 1"))
    return {"status": "ok"}
