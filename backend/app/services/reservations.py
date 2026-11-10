import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from math import ceil

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import func, or_, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import is_database_locked
from app.models import (
    Product,
    Reservation,
    ReservationItem,
    ReservationStatus,
    utcnow,
)
from app.schemas.reservation import (
    ReservationCancelRequest,
    ReservationCreate,
    ReservationItemRead,
    ReservationLookupRequest,
    ReservationPage,
    ReservationRead,
    ReservationStatusUpdate,
    ReservationSummary,
)
from app.services.whatsapp import build_whatsapp_url

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
ALLOWED_TRANSITIONS: dict[ReservationStatus, set[ReservationStatus]] = {
    ReservationStatus.PENDIENTE: {
        ReservationStatus.CONFIRMADO,
        ReservationStatus.CANCELADO,
    },
    ReservationStatus.CONFIRMADO: {
        ReservationStatus.RETIRADO,
        ReservationStatus.CANCELADO,
    },
    ReservationStatus.RETIRADO: set(),
    ReservationStatus.CANCELADO: set(),
}


class StockError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _generate_code() -> str:
    suffix = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
    return f"CC-{suffix}"


def _load_reservation(
    session: Session,
    *,
    code: str | None = None,
    reservation_id: int | None = None,
):
    statement = select(Reservation).options(selectinload(Reservation.items))
    if code is not None:
        statement = statement.where(Reservation.code == code)
    elif reservation_id is not None:
        statement = statement.where(Reservation.id == reservation_id)
    else:
        raise ValueError("Se requiere code o reservation_id")
    return session.exec(statement).first()


def _read_reservation(reservation: Reservation) -> ReservationRead:
    items = sorted(reservation.items, key=lambda item: item.id or 0)
    return ReservationRead(
        id=reservation.id or 0,
        code=reservation.code,
        customer_name=reservation.customer_name,
        customer_last_name=reservation.customer_last_name,
        customer_email=reservation.customer_email,
        customer_phone=reservation.customer_phone,
        pickup_date=reservation.pickup_date,
        status=reservation.status,
        total_amount=reservation.total_amount,
        created_at=reservation.created_at,
        expires_at=reservation.expires_at,
        price_guaranteed_until=reservation.expires_at,
        terms_version=reservation.terms_version,
        privacy_version=reservation.privacy_version,
        cancelled_at=reservation.cancelled_at,
        cancellation_reason=reservation.cancellation_reason,
        items=[ReservationItemRead.model_validate(item) for item in items],
        whatsapp_url=build_whatsapp_url(reservation, items, settings),
    )


def _reserve_items(
    session: Session,
    payload: ReservationCreate,
) -> tuple[list[ReservationItem], Decimal]:
    items: list[ReservationItem] = []
    total = Decimal("0.00")

    for item_payload in payload.items:
        statement = (
            update(Product)
            .where(
                Product.id == item_payload.product_id,
                Product.is_active.is_(True),
                Product.stock >= item_payload.quantity,
            )
            .values(stock=Product.stock - item_payload.quantity)
            .returning(Product.name, Product.unit, Product.price)
        )
        row = session.execute(statement).first()
        if row is None:
            product = session.get(Product, item_payload.product_id)
            if product is None or not product.is_active:
                raise StockError("Uno de los productos ya no está disponible")
            raise StockError(f"No hay stock suficiente de {product.name}")

        product_name, product_unit, unit_price = row
        price = Decimal(unit_price).quantize(Decimal("0.01"))
        total += price * item_payload.quantity
        items.append(
            ReservationItem(
                product_id=item_payload.product_id,
                product_name=product_name,
                product_unit=product_unit,
                quantity=item_payload.quantity,
                unit_price=price,
            )
        )

    return items, total.quantize(Decimal("0.01"))


def create_reservation(session: Session, payload: ReservationCreate) -> ReservationRead:
    now = datetime.now(UTC)
    pickup_utc = payload.pickup_date.astimezone(UTC)
    min_pickup = now + timedelta(seconds=settings.min_pickup_lead_seconds)
    max_pickup = now + timedelta(seconds=settings.reservation_expiration_seconds)

    if pickup_utc < min_pickup:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "La fecha de retiro debe ser al menos "
                f"{settings.min_pickup_lead_minutes} minutos posterior a la reserva"
            ),
        )
    if pickup_utc > max_pickup:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "La fecha de retiro no puede superar la ventana de "
                f"{settings.reservation_expiration_hours} horas"
            ),
        )

    expires_at = now + timedelta(seconds=settings.reservation_expiration_seconds)

    last_error: Exception | None = None
    for _attempt in range(5):
        code = _generate_code()
        try:
            items, total = _reserve_items(session, payload)
            reservation = Reservation(
                code=code,
                customer_name=payload.customer_name,
                customer_last_name=payload.customer_last_name,
                customer_email=str(payload.customer_email).lower(),
                customer_phone=payload.customer_phone,
                pickup_date=pickup_utc,
                status=ReservationStatus.PENDIENTE,
                total_amount=total,
                created_at=now,
                expires_at=expires_at,
                terms_accepted_at=now,
                privacy_consent_at=now,
                terms_version=settings.terms_version,
                privacy_version=settings.privacy_version,
            )
            session.add(reservation)
            session.flush()
            for item in items:
                item.reservation_id = reservation.id or 0
                session.add(item)
            session.commit()
            session.refresh(reservation)

            logger.bind(
                event="reservation.created",
                reservation_code=reservation.code,
                reservation_id=reservation.id,
                item_count=len(items),
                total=str(total),
            ).info("Reserva creada")

            loaded = _load_reservation(session, reservation_id=reservation.id)
            if loaded is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No se pudo recuperar la reserva creada",
                )
            return _read_reservation(loaded)
        except StockError as exc:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=exc.message,
            ) from exc
        except IntegrityError as exc:
            session.rollback()
            last_error = exc
            logger.bind(event="reservation.code_collision", code=code).warning(
                "Colisión de código de reserva, reintentando"
            )
            continue
        except OperationalError as exc:
            session.rollback()
            if is_database_locked(exc):
                logger.bind(event="reservation.database_locked").warning(
                    "Base de datos ocupada durante la creación de reserva"
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="La base de datos está ocupada. Intentá nuevamente.",
                ) from exc
            raise

    logger.bind(event="reservation.code_collision_exhausted").error(
        "No se pudo generar un código único"
    )
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="No se pudo generar la reserva. Intentá nuevamente.",
    ) from last_error


def lookup_reservation(session: Session, payload: ReservationLookupRequest) -> ReservationRead:
    reservation = _load_reservation(session, code=payload.code)
    if reservation is None or reservation.customer_email != str(payload.email).lower():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No encontramos una reserva con esos datos",
        )
    return _read_reservation(reservation)


def _restore_stock(session: Session, reservation: Reservation) -> None:
    for item in reservation.items:
        session.execute(
            update(Product)
            .where(Product.id == item.product_id)
            .values(stock=Product.stock + item.quantity)
        )


def _cancel_reservation(
    session: Session,
    reservation: Reservation,
    *,
    reason: str,
    actor: str,
) -> ReservationRead:
    if reservation.status == ReservationStatus.CANCELADO:
        return _read_reservation(reservation)
    if reservation.status == ReservationStatus.RETIRADO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Una reserva ya retirada no puede cancelarse",
        )

    _restore_stock(session, reservation)
    reservation.status = ReservationStatus.CANCELADO
    reservation.cancelled_at = utcnow()
    reservation.cancellation_reason = reason
    session.add(reservation)
    session.commit()
    session.refresh(reservation)

    logger.bind(
        event="reservation.cancelled",
        reservation_code=reservation.code,
        actor=actor,
        reason=reason,
    ).info("Reserva cancelada")

    loaded = _load_reservation(session, reservation_id=reservation.id)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo recuperar la reserva cancelada",
        )
    return _read_reservation(loaded)


def cancel_reservation(
    session: Session,
    code: str,
    payload: ReservationCancelRequest,
) -> ReservationRead:
    reservation = _load_reservation(session, code=code.strip().upper())
    if reservation is None or reservation.customer_email != str(payload.email).lower():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No encontramos una reserva con esos datos",
        )
    reason = payload.reason or "Cancelación solicitada por el cliente"
    return _cancel_reservation(session, reservation, reason=reason, actor="customer")


def get_admin_reservation(session: Session, reservation_id: int) -> ReservationRead:
    reservation = _load_reservation(session, reservation_id=reservation_id)
    if reservation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reserva no encontrada",
        )
    return _read_reservation(reservation)


def list_admin_reservations(
    session: Session,
    *,
    status_filter: ReservationStatus | None = None,
    search: str = "",
    page: int = 1,
    page_size: int = 20,
) -> ReservationPage:
    filters = []
    if status_filter is not None:
        filters.append(Reservation.status == status_filter)
    if search.strip():
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Reservation.code.ilike(pattern),
                Reservation.customer_email.ilike(pattern),
                Reservation.customer_name.ilike(pattern),
                Reservation.customer_last_name.ilike(pattern),
            )
        )

    total = session.exec(select(func.count()).select_from(Reservation).where(*filters)).one()
    pages = max(1, ceil(total / page_size)) if total else 0
    reservations = session.exec(
        select(Reservation)
        .options(selectinload(Reservation.items))
        .where(*filters)
        .order_by(Reservation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    summaries = []
    for reservation in reservations:
        summary = ReservationSummary.model_validate(reservation)
        summary.item_count = len(reservation.items)
        summaries.append(summary)

    return ReservationPage(
        items=summaries,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


def update_admin_status(
    session: Session,
    reservation_id: int,
    payload: ReservationStatusUpdate,
    *,
    admin_username: str,
) -> ReservationRead:
    reservation = _load_reservation(session, reservation_id=reservation_id)
    if reservation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reserva no encontrada",
        )

    previous_status = reservation.status
    if previous_status == payload.status:
        return _read_reservation(reservation)

    allowed = ALLOWED_TRANSITIONS.get(previous_status, set())
    if payload.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede cambiar de {previous_status.value} a {payload.status.value}",
        )

    if payload.status == ReservationStatus.CANCELADO:
        _restore_stock(session, reservation)
        reservation.cancelled_at = utcnow()
        reservation.cancellation_reason = payload.reason or f"Cancelada por {admin_username}"

    reservation.status = payload.status
    session.add(reservation)
    session.commit()
    session.refresh(reservation)

    logger.bind(
        event="admin.reservation_status_changed",
        admin=admin_username,
        reservation_code=reservation.code,
        previous=previous_status.value,
        current=payload.status.value,
    ).info("Estado de reserva modificado")

    loaded = _load_reservation(session, reservation_id=reservation.id)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo recuperar la reserva actualizada",
        )
    return _read_reservation(loaded)
