import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.error import URLError

import pytest

from app.core.config import settings
from app.schemas.reservation import ReservationItemRead, ReservationRead
from app.services.telegram import (
    build_reservation_message,
    notify_new_reservation,
    send_telegram_message,
)


class FakeResponse:
    status = 200

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False

    def read(self) -> bytes:
        return b'{"ok": true}'


def _settings(**overrides: Any):
    base = {
        "telegram_bot_token": "123456:ABC-DEF",
        "telegram_chat_id": "987654321",
    }
    base.update(overrides)
    return settings.model_copy(update=base)


def _reservation() -> ReservationRead:
    now = datetime.now(UTC)
    item = ReservationItemRead(
        id=1,
        product_id=1,
        product_name="Papel Delfín (30x100m)",
        product_unit="Pack x5 u.",
        quantity=3,
        unit_price=Decimal("4000.00"),
        line_total=Decimal("12000.00"),
    )
    return ReservationRead(
        id=11,
        code="CC-XYZ789",
        customer_name="Ana",
        customer_last_name="García",
        customer_email="ana@example.com",
        customer_phone="+54 11 5555-1234",
        pickup_date=now + timedelta(hours=3),
        status="PENDIENTE",
        total_amount=Decimal("12000.00"),
        created_at=now,
        expires_at=now + timedelta(hours=48),
        price_guaranteed_until=now + timedelta(hours=48),
        terms_version="2026-11",
        privacy_version="2026-11",
        items=[item],
    )


def test_send_telegram_message_posts_to_bot_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Any, int | None]] = []

    def fake_urlopen(request: Any, timeout: int | None = None) -> FakeResponse:
        calls.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr("app.services.telegram.urlopen", fake_urlopen)

    assert send_telegram_message("Hola Karen", _settings()) is True

    request, timeout = calls[0]
    assert request.full_url == "https://api.telegram.org/bot123456:ABC-DEF/sendMessage"
    assert timeout == 10
    assert request.get_method() == "POST"
    payload = json.loads(request.data.decode("utf-8"))
    assert payload["chat_id"] == "987654321"
    assert payload["text"] == "Hola Karen"


def test_send_telegram_message_is_noop_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _unexpected(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("No debería llamarse a la API de Telegram")

    monkeypatch.setattr("app.services.telegram.urlopen", _unexpected)

    assert send_telegram_message("Hola", _settings(telegram_bot_token="")) is False
    assert send_telegram_message("Hola", _settings(telegram_chat_id="")) is False


def test_send_telegram_message_does_not_raise_on_network_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_urlopen(*_args: object, **_kwargs: object) -> FakeResponse:
        raise URLError("sin conexión")

    monkeypatch.setattr("app.services.telegram.urlopen", failing_urlopen)

    assert send_telegram_message("Hola", _settings()) is False


def test_notify_new_reservation_includes_order_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.telegram.urlopen", lambda *_a, **_k: FakeResponse())

    reservation = _reservation()
    message = build_reservation_message(reservation, _settings())

    assert "CC-XYZ789" in message
    assert "Ana García" in message
    assert "+54 11 5555-1234" in message
    assert "ana@example.com" in message
    assert "3 x Papel Delfín" in message
    assert "$ 12.000,00" in message

    notify_new_reservation(reservation, _settings())


def test_notify_new_reservation_swallows_unexpected_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_urlopen(*_args: object, **_kwargs: object) -> FakeResponse:
        raise RuntimeError("falla inesperada")

    monkeypatch.setattr("app.services.telegram.urlopen", failing_urlopen)

    notify_new_reservation(_reservation(), _settings())
