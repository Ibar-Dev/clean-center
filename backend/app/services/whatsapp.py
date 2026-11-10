from datetime import UTC, datetime
from decimal import Decimal
from urllib.parse import quote
from zoneinfo import ZoneInfo

from loguru import logger

from app.core.config import Settings
from app.models import Reservation, ReservationItem

ARGENTINA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def format_ars(value: Decimal) -> str:
    formatted = f"{value:,.2f}"
    return "$ " + formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def format_datetime_ar(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(ARGENTINA_TZ).strftime("%d/%m/%Y %H:%M")


def normalize_whatsapp_phone(phone: str) -> str | None:
    digits = "".join(character for character in phone if character.isdigit())
    if len(digits) < 8 or len(digits) > 15:
        return None
    return digits


def build_reservation_whatsapp_message(
    reservation: Reservation,
    items: list[ReservationItem],
    current_settings: Settings,
) -> str:
    item_lines = [
        f"• {item.quantity} x {item.product_name} ({item.product_unit}) - "
        f"{format_ars(item.line_total)}"
        for item in items
    ]
    lines = [
        f"Hola {current_settings.store_name}, quiero enviar mi pedido:",
        "",
        f"Comercio: {current_settings.store_name}",
        f"Dirección de retiro: {current_settings.store_address}",
        f"Código: {reservation.code}",
        f"Cliente: {reservation.customer_name} {reservation.customer_last_name}",
        f"Retiro estimado: {format_datetime_ar(reservation.pickup_date)}",
        "",
        "Productos:",
        *item_lines,
        "",
        f"Total a pagar en el local: {format_ars(reservation.total_amount)}",
        "",
        f"Horario de atención: {current_settings.store_hours}",
    ]
    return "\n".join(lines)


def build_whatsapp_url(
    reservation: Reservation,
    items: list[ReservationItem],
    current_settings: Settings,
) -> str | None:
    phone = normalize_whatsapp_phone(current_settings.whatsapp_phone)
    if phone is None:
        return None
    message = build_reservation_whatsapp_message(reservation, items, current_settings)
    logger.bind(event="whatsapp.link_created", reservation_code=reservation.code).info(
        "Enlace de WhatsApp generado"
    )
    return f"https://wa.me/{phone}?text={quote(message, safe='')}"
