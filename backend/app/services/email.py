import smtplib
from email.message import EmailMessage

from loguru import logger
from pydantic import EmailStr, TypeAdapter, ValidationError

from app.core.config import Settings, settings
from app.schemas.reservation import ReservationItemRead, ReservationRead
from app.services.whatsapp import format_ars, format_datetime_ar

SMTP_TIMEOUT_SECONDS = 10
EMAIL_ADAPTER = TypeAdapter(EmailStr)


def _valid_email(value: str) -> str | None:
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    try:
        return str(EMAIL_ADAPTER.validate_python(cleaned))
    except ValidationError:
        logger.bind(event="email.invalid_address").warning(
            "Dirección de correo inválida configurada para el envío"
        )
        return None


def _admin_recipient(current_settings: Settings) -> str | None:
    return _valid_email(current_settings.admin_email) or _valid_email(
        str(current_settings.store_email)
    )


def _items_block(items: list[ReservationItemRead]) -> str:
    return "\n".join(
        f"• {item.quantity} x {item.product_name} ({item.product_unit}) - "
        f"{format_ars(item.line_total)}"
        for item in items
    )


def build_customer_email(
    reservation: ReservationRead,
    current_settings: Settings | None = None,
) -> tuple[str, str]:
    config = current_settings or settings
    subject = f"Reserva {reservation.code} confirmada - {config.store_name}"
    body = "\n".join(
        [
            f"Hola {reservation.customer_name},",
            "",
            f"Tu reserva en {config.store_name} quedó registrada correctamente.",
            "",
            f"Código de reserva: {reservation.code}",
            f"Retiro estimado: {format_datetime_ar(reservation.pickup_date)}",
            f"Vence: {format_datetime_ar(reservation.expires_at)}",
            "",
            "Productos reservados:",
            _items_block(reservation.items),
            "",
            f"Total a pagar en el local: {format_ars(reservation.total_amount)}",
            "",
            f"Dirección de retiro: {config.store_address}",
            f"Horario de atención: {config.store_hours}",
            f"Teléfono: {config.store_phone}",
            f"Correo: {config.store_email}",
            "",
            "Presentá este código y tu documento de identidad al retirar. El pago se realiza",
            "exclusivamente en el local.",
            "",
            config.store_name,
        ]
    )
    return subject, body


def build_admin_email(
    reservation: ReservationRead,
    current_settings: Settings | None = None,
) -> tuple[str, str]:
    config = current_settings or settings
    subject = f"Nuevo pedido {reservation.code} - {config.store_name}"
    body = "\n".join(
        [
            f"Nuevo pedido recibido: {reservation.code}",
            "",
            f"Cliente: {reservation.customer_name} {reservation.customer_last_name}",
            f"Teléfono: {reservation.customer_phone}",
            f"Email: {reservation.customer_email}",
            f"Retiro estimado: {format_datetime_ar(reservation.pickup_date)}",
            f"Vence: {format_datetime_ar(reservation.expires_at)}",
            "",
            "Productos a preparar:",
            _items_block(reservation.items),
            "",
            f"Total a cobrar en el local: {format_ars(reservation.total_amount)}",
            "",
            "Podés gestionar la reserva desde el panel de administración.",
        ]
    )
    return subject, body


def send_email(
    *,
    to: str,
    subject: str,
    body: str,
    current_settings: Settings | None = None,
) -> bool:
    config = current_settings or settings
    recipient = _valid_email(to)
    sender = _valid_email(config.smtp_from)

    if not config.smtp_host or sender is None or recipient is None:
        logger.bind(event="email.disabled").debug(
            "Envío de email omitido: SMTP sin configurar o destinatario inválido"
        )
        return False

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(
            config.smtp_host,
            config.smtp_port,
            timeout=SMTP_TIMEOUT_SECONDS,
        ) as smtp:
            if config.smtp_tls:
                smtp.starttls()
            if config.smtp_user:
                smtp.login(config.smtp_user, config.smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        logger.bind(event="email.send_failed", to=recipient).warning(
            "No se pudo enviar el email: {}", exc
        )
        return False

    logger.bind(event="email.sent", to=recipient).info("Email enviado")
    return True


def send_reservation_emails(
    reservation: ReservationRead,
    current_settings: Settings | None = None,
) -> None:
    config = current_settings or settings

    try:
        subject, body = build_customer_email(reservation, config)
        send_email(
            to=str(reservation.customer_email),
            subject=subject,
            body=body,
            current_settings=config,
        )
    except Exception:
        logger.bind(event="email.customer_failed", code=reservation.code).exception(
            "Error inesperado al preparar el email al cliente"
        )

    admin_recipient = _admin_recipient(config)
    if admin_recipient is None:
        logger.bind(event="email.admin_missing", code=reservation.code).warning(
            "No hay destinatario configurado para el aviso de nuevos pedidos"
        )
        return

    try:
        subject, body = build_admin_email(reservation, config)
        send_email(
            to=admin_recipient,
            subject=subject,
            body=body,
            current_settings=config,
        )
    except Exception:
        logger.bind(event="email.admin_failed", code=reservation.code).exception(
            "Error inesperado al preparar el email al administrador"
        )
