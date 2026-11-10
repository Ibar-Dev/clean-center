from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer


def _serialize_money(value: Decimal) -> str:
    return f"{value:.2f}"


def _serialize_utc_datetime(value: datetime) -> str:
    value = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return value.isoformat().replace("+00:00", "Z")


Money = Annotated[
    Decimal,
    PlainSerializer(_serialize_money, return_type=str, when_used="json"),
]

UtcDateTime = Annotated[
    datetime,
    PlainSerializer(_serialize_utc_datetime, return_type=str, when_used="json"),
]
