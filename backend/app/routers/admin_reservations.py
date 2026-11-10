from fastapi import APIRouter, Query

from app.core.deps import CurrentAdmin, SessionDep
from app.models import ReservationStatus
from app.schemas.reservation import (
    ReservationPage,
    ReservationRead,
    ReservationStatusUpdate,
)
from app.services.reservations import (
    get_admin_reservation,
    list_admin_reservations,
    update_admin_status,
)

router = APIRouter(prefix="/admin/reservations", tags=["admin-reservations"])


@router.get("", response_model=ReservationPage)
def list_reservations(
    admin: CurrentAdmin,
    session: SessionDep,
    status_filter: ReservationStatus | None = Query(default=None, alias="status"),
    search: str = Query(default="", max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ReservationPage:
    return list_admin_reservations(
        session,
        status_filter=status_filter,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/{reservation_id}", response_model=ReservationRead)
def reservation_detail(
    reservation_id: int,
    admin: CurrentAdmin,
    session: SessionDep,
) -> ReservationRead:
    return get_admin_reservation(session, reservation_id)


@router.patch("/{reservation_id}/status", response_model=ReservationRead)
def change_status(
    reservation_id: int,
    payload: ReservationStatusUpdate,
    admin: CurrentAdmin,
    session: SessionDep,
) -> ReservationRead:
    return update_admin_status(
        session,
        reservation_id,
        payload,
        admin_username=admin.username,
    )
