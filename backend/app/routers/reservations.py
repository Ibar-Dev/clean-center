from fastapi import APIRouter, BackgroundTasks, Request, Response, status

from app.core.config import settings
from app.core.deps import SessionDep
from app.core.rate_limit import limiter
from app.schemas.reservation import (
    ReservationCancelRequest,
    ReservationCreate,
    ReservationLookupRequest,
    ReservationRead,
)
from app.services.email import send_reservation_emails
from app.services.reservations import cancel_reservation, create_reservation, lookup_reservation
from app.services.telegram import notify_new_reservation

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.post("", response_model=ReservationRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.reservation_rate_limit)
def create(
    request: Request,
    response: Response,
    payload: ReservationCreate,
    session: SessionDep,
    background_tasks: BackgroundTasks,
) -> ReservationRead:
    reservation, created = create_reservation(session, payload)
    if not created:
        # Reintento idempotente: se devuelve la reserva existente sin reenviar avisos.
        response.status_code = status.HTTP_200_OK
        return reservation
    # Las notificaciones corren después de la respuesta y nunca revierten la reserva.
    background_tasks.add_task(send_reservation_emails, reservation)
    background_tasks.add_task(notify_new_reservation, reservation)
    return reservation


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
