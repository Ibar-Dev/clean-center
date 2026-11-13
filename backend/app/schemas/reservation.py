import re
from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.models.enums import ReservationStatus
from app.schemas.common import Money, UtcDateTime

PHONE_RE = re.compile(r"^[+()\d\s.-]{8,30}$")


class ReservationItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=99)


class ReservationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_name: str = Field(min_length=2, max_length=80)
    customer_last_name: str = Field(min_length=2, max_length=80)
    customer_email: EmailStr
    customer_phone: str = Field(min_length=8, max_length=30)
    pickup_date: datetime
    items: list[ReservationItemCreate] = Field(min_length=1, max_length=30)
    terms_accepted: bool
    privacy_consent: bool
    idempotency_key: UUID | None = None

    @field_validator("customer_name", "customer_last_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")
        return cleaned

    @field_validator("customer_phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        cleaned = value.strip()
        if not PHONE_RE.fullmatch(cleaned):
            raise ValueError("El teléfono no tiene un formato válido")
        digits = re.sub(r"\D", "", cleaned)
        if len(digits) < 8:
            raise ValueError("El teléfono debe tener al menos 8 dígitos")
        return cleaned

    @field_validator("pickup_date")
    @classmethod
    def validate_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("La fecha de retiro debe incluir zona horaria")
        return value

    @model_validator(mode="after")
    def validate_consents_and_items(self) -> Self:
        if not self.terms_accepted:
            raise ValueError("Debe aceptar los Términos y Condiciones")
        if not self.privacy_consent:
            raise ValueError("Debe aceptar la Política de Privacidad")
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("No se puede repetir un producto en la reserva")
        return self


class ReservationLookupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=6, max_length=12)
    email: EmailStr

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class ReservationCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    reason: str | None = Field(default=None, max_length=500)


class ReservationItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    product_unit: str
    quantity: int
    unit_price: Money
    line_total: Money


class ReservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    customer_name: str
    customer_last_name: str
    customer_email: EmailStr
    customer_phone: str
    pickup_date: UtcDateTime
    status: ReservationStatus
    total_amount: Money
    created_at: UtcDateTime
    expires_at: UtcDateTime
    price_guaranteed_until: UtcDateTime
    terms_version: str
    privacy_version: str
    cancelled_at: UtcDateTime | None = None
    cancellation_reason: str | None = None
    items: list[ReservationItemRead] = Field(default_factory=list)
    whatsapp_url: str | None = None


class ReservationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    customer_name: str
    customer_last_name: str
    customer_email: EmailStr
    customer_phone: str
    pickup_date: UtcDateTime
    status: ReservationStatus
    total_amount: Money
    created_at: UtcDateTime
    expires_at: UtcDateTime
    item_count: int = 0


class ReservationPage(BaseModel):
    items: list[ReservationSummary]
    total: int
    page: int
    page_size: int
    pages: int


class ReservationStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ReservationStatus
    reason: str | None = Field(default=None, max_length=500)
