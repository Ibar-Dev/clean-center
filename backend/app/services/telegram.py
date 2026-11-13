import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from loguru import logger

from app.core.config import Settings, settings
from app.schemas.reservation import ReservationItemRead, ReservationRead
from app.services.whatsapp import format_ars, format_datetime_ar

TELEGRAM_TIMEOUT_SECONDS = 10
TELEGRAM_MAX_LENGTH = 4000


def _items_block(items: list[ReservationItemRead]) -> str:
    return "\n".join(
        f"• {item.quantity} x {item.product_name} ({item.product_unit}) - "
        f"{format_ars(item.line_total)}"
        for item in items
    )


def build_reservation_message(
    reservation: ReservationRead,
    current_settings: Settings | None = None,
) -> str:
    config = current_settings or settings
    text = "\n".join(
        [
            f"🛒 Nuevo pedido {reservation.code}",
            "",
            f"Cliente: {reservation.customer_name} {reservation.customer_last_name}",
            f"Teléfono: {reservation.customer_phone}",
            f"Email: {reservation.customer_email}",
            f"Retiro: {format_datetime_ar(reservation.pickup_date)}",
            f"Vence: {format_datetime_ar(reservation.expires_at)}",
            "",
            "Preparar:",
            _items_block(reservation.items),
            "",
            f"Total a cobrar en el local: {format_ars(reservation.total_amount)}",
            f"Local: {config.store_name} · {config.store_address}",
        ]
    )
    return text[:TELEGRAM_MAX_LENGTH]


def send_telegram_message(
    text: str,
    current_settings: Settings | None = None,
) -> bool:
    config = current_settings or settings
    if not config.telegram_bot_token or not config.telegram_chat_id:
        logger.bind(event="telegram.disabled").debug(
            "Notificación de Telegram omitida: token o chat sin configurar"
        )
        return False

    payload = json.dumps(
        {
            "chat_id": config.telegram_chat_id,
            "text": text[:TELEGRAM_MAX_LENGTH],
            "disable_web_page_preview": True,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(
        f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=TELEGRAM_TIMEOUT_SECONDS) as response:
            status = getattr(response, "status", 200)
            response.read()
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        logger.bind(event="telegram.send_failed").warning(
            "No se pudo enviar la notificación de Telegram: {}", exc
        )
        return False

    if status >= 400:
        logger.bind(event="telegram.send_failed", status=status).warning(
            "Telegram respondió con un estado inesperado"
        )
        return False

    logger.bind(event="telegram.sent").info("Notificación de Telegram enviada")
    return True


def notify_new_reservation(
    reservation: ReservationRead,
    current_settings: Settings | None = None,
) -> None:
    try:
        send_telegram_message(
            build_reservation_message(reservation, current_settings),
            current_settings,
        )
    except Exception:
        logger.bind(event="telegram.notify_failed", code=reservation.code).exception(
            "Error inesperado al notificar la reserva por Telegram"
        )
