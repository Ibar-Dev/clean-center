import smtplib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, ClassVar

import pytest

from app.core.config import settings
from app.schemas.reservation import ReservationItemRead, ReservationRead
from app.services.email import (
    build_admin_email,
    build_customer_email,
    send_email,
    send_reservation_emails,
)


class FakeSMTP:
    instances: ClassVar[list["FakeSMTP"]] = []

    def __init__(self, host: str, port: int, timeout: int | None = None) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.login_credentials: tuple[str, str] | None = None
        self.messages: list[Any] = []
        FakeSMTP.instances.append(self)

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False

    def starttls(self) -> None:
        self.started_tls = True

    def login(self, user: str, password: str) -> None:
        self.login_credentials = (user, password)

    def send_message(self, message: Any) -> None:
        self.messages.append(message)


class FailingSMTP(FakeSMTP):
    def send_message(self, message: Any) -> None:
        raise smtplib.SMTPException("falla simulada")


@pytest.fixture(autouse=True)
def _reset_fake_smtp() -> None:
    FakeSMTP.instances.clear()


def _settings(**overrides: Any):
    base = {
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "smtp_user": "remitente@example.com",
        "smtp_password": "secreto",
        "smtp_from": "remitente@example.com",
        "smtp_tls": True,
        "admin_email": "karen@example.com",
    }
    base.update(overrides)
    return settings.model_copy(update=base)


def _reservation() -> ReservationRead:
    now = datetime.now(UTC)
    item = ReservationItemRead(
        id=1,
        product_id=1,
        product_name="Detergente Lavanda",
        product_unit="500 ml",
        quantity=2,
        unit_price=Decimal("2250.75"),
        line_total=Decimal("4501.50"),
    )
    return ReservationRead(
        id=10,
        code="CC-ABC234",
        customer_name="Ana",
        customer_last_name="García",
        customer_email="ana@example.com",
        customer_phone="+54 11 5555-1234",
        pickup_date=now + timedelta(hours=3),
        status="PENDIENTE",
        total_amount=Decimal("4501.50"),
        created_at=now,
        expires_at=now + timedelta(hours=48),
        price_guaranteed_until=now + timedelta(hours=48),
        terms_version="2026-11",
        privacy_version="2026-11",
        items=[item],
    )


def test_send_email_uses_smtp_with_starttls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.email.smtplib.SMTP", FakeSMTP)

    result = send_email(
        to="ana@example.com",
        subject="Hola",
        body="Texto plano",
        current_settings=_settings(),
    )

    assert result is True
    smtp = FakeSMTP.instances[0]
    assert (smtp.host, smtp.port) == ("smtp.example.com", 587)
    assert smtp.started_tls is True
    assert smtp.login_credentials == ("remitente@example.com", "secreto")
    message = smtp.messages[0]
    assert message["To"] == "ana@example.com"
    assert message["From"] == "remitente@example.com"
    assert message["Subject"] == "Hola"
    assert message.get_content().strip() == "Texto plano"


def test_send_email_is_noop_without_smtp_host(monkeypatch: pytest.MonkeyPatch) -> None:
    def _unexpected(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("No debería abrirse una conexión SMTP")

    monkeypatch.setattr("app.services.email.smtplib.SMTP", _unexpected)

    assert (
        send_email(
            to="ana@example.com",
            subject="Hola",
            body="Texto",
            current_settings=_settings(smtp_host=""),
        )
        is False
    )
    assert FakeSMTP.instances == []


def test_send_email_does_not_raise_on_smtp_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.email.smtplib.SMTP", FailingSMTP)

    assert (
        send_email(
            to="ana@example.com",
            subject="Hola",
            body="Texto",
            current_settings=_settings(),
        )
        is False
    )


def test_send_reservation_emails_notifies_customer_and_admin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.email.smtplib.SMTP", FakeSMTP)

    send_reservation_emails(_reservation(), _settings())

    recipients = [message["To"] for smtp in FakeSMTP.instances for message in smtp.messages]
    assert recipients == ["ana@example.com", "karen@example.com"]
    subjects = [str(message["Subject"]) for smtp in FakeSMTP.instances for message in smtp.messages]
    assert "CC-ABC234" in subjects[0]
    assert "Nuevo pedido" in subjects[1]


def test_send_reservation_emails_falls_back_to_store_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.email.smtplib.SMTP", FakeSMTP)
    config = _settings(admin_email="")

    send_reservation_emails(_reservation(), config)

    recipients = [message["To"] for smtp in FakeSMTP.instances for message in smtp.messages]
    assert recipients == ["ana@example.com", str(config.store_email)]


def test_customer_email_includes_code_items_and_store_data() -> None:
    config = _settings()

    _subject, body = build_customer_email(_reservation(), config)

    assert "CC-ABC234" in body
    assert "2 x Detergente Lavanda (500 ml)" in body
    assert "$ 4.501,50" in body
    assert config.store_address in body
    assert config.store_hours in body


def test_admin_email_includes_customer_contact_and_items() -> None:
    config = _settings()

    _subject, body = build_admin_email(_reservation(), config)

    assert "CC-ABC234" in body
    assert "ana@example.com" in body
    assert "+54 11 5555-1234" in body
    assert "Productos a preparar:" in body
    assert "Detergente Lavanda" in body
