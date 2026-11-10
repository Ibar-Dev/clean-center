from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.core.config import settings
from app.models import Reservation, ReservationItem, ReservationStatus
from app.services.whatsapp import (
    build_reservation_whatsapp_message,
    build_whatsapp_url,
    format_ars,
    normalize_whatsapp_phone,
)


def _reservation_and_items() -> tuple[Reservation, list[ReservationItem]]:
    now = datetime.now(UTC)
    reservation = Reservation(
        code="CC-ABC234",
        customer_name="Ana",
        customer_last_name="García",
        customer_email="ana@example.com",
        customer_phone="+54 11 5555-1234",
        pickup_date=now + timedelta(hours=3),
        status=ReservationStatus.PENDIENTE,
        total_amount=Decimal("4501.50"),
        created_at=now,
        expires_at=now + timedelta(hours=48),
        terms_version="2026-11",
        privacy_version="2026-11",
    )
    item = ReservationItem(
        reservation_id=0,
        product_id=1,
        product_name="Detergente Lavanda",
        product_unit="500 ml",
        quantity=3,
        unit_price=Decimal("1500.50"),
    )
    return reservation, [item]


def test_format_ars() -> None:
    assert format_ars(Decimal("1500.5")) == "$ 1.500,50"
    assert format_ars(Decimal("1234567.89")) == "$ 1.234.567,89"


def test_normalize_whatsapp_phone() -> None:
    assert normalize_whatsapp_phone("+54 9 11 2345-6789") == "5491123456789"
    assert normalize_whatsapp_phone("123") is None
    assert normalize_whatsapp_phone("1234567890123456") is None


def test_message_includes_store_name_and_address() -> None:
    reservation, items = _reservation_and_items()

    message = build_reservation_whatsapp_message(reservation, items, settings)

    assert settings.store_name in message
    assert settings.store_address in message
    assert reservation.code in message
    assert "Detergente Lavanda" in message
    assert "$ 4.501,50" in message


def test_whatsapp_url_is_generated() -> None:
    reservation, items = _reservation_and_items()

    url = build_whatsapp_url(reservation, items, settings)

    assert url is not None
    assert url.startswith("https://wa.me/5491123456789?text=")
    assert "%20" in url or "+" in url


def test_whatsapp_url_is_none_without_phone() -> None:
    reservation, items = _reservation_and_items()
    current = settings.model_copy(update={"whatsapp_phone": ""})

    assert build_whatsapp_url(reservation, items, current) is None
