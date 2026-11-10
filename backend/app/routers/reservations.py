from fastapi import APIRouter, Request, status

from app.core.config import settings
from app.core.deps import SessionDep
from app.core.rate_limit import limiter
from app.schemas.reservation import (
    ReservationCancelRequest,
    ReservationCreate,
    ReservationLookupRequest,
    ReservationRead,
)
from app.services.reservations import cancel_reservation, create_reservation, lookup_reservation

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.post("", response_model=ReservationRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.reservation_rate_limit)
def create(
    request: Request,
    payload: ReservationCreate,
    session: SessionDep,
) -> ReservationRead:
    return create_reservation(session, payload)


@router.post("/lookup", response_model=ReservationRead)
@limiter.limit(settings.lookup_rate_limit)
def lookup(
    request: Request,
    payload: ReservationLookupRequest,
    session: SessionDep,
) -> ReservationRead:
    return lookup_reservation(session, payload)


@router.post("/{code}/cancel", response_model=ReservationRead)
@limiter.limit(settings.lookup_rate_limit)
def cancel(
    request: Request,
    code: str,
    payload: ReservationCancelRequest,
    session: SessionDep,
) -> ReservationRead:
    return cancel_reservation(session, code, payload)
