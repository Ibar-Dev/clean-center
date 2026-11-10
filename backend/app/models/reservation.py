from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import CheckConstraint, Column, Numeric
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import ReservationStatus
from app.models.user import utcnow


class ReservationItem(SQLModel, table=True):
    __tablename__ = "reservation_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_reservation_items_quantity_positive"),
    )

    id: int | None = Field(default=None, primary_key=True)
    reservation_id: int = Field(foreign_key="reservations.id", index=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    product_name: str = Field(max_length=160)
    product_unit: str = Field(max_length=60)
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))

    reservation: Optional["Reservation"] = Relationship(back_populates="items")

    @property
    def line_total(self) -> Decimal:
        return (self.unit_price * self.quantity).quantize(Decimal("0.01"))


class Reservation(SQLModel, table=True):
    __tablename__ = "reservations"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True, max_length=12)
    customer_name: str = Field(max_length=80)
    customer_last_name: str = Field(max_length=80)
    customer_email: str = Field(index=True, max_length=254)
    customer_phone: str = Field(max_length=30)
    pickup_date: datetime = Field(index=True)
    status: ReservationStatus = Field(
        default=ReservationStatus.PENDIENTE,
        sa_column=Column(
            SAEnum(
                ReservationStatus,
                native_enum=False,
                values_callable=lambda enum: [item.value for item in enum],
            ),
            nullable=False,
            index=True,
        ),
    )
    total_amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    created_at: datetime = Field(default_factory=utcnow, index=True)
    expires_at: datetime = Field()
    terms_accepted_at: datetime = Field(default_factory=utcnow)
    privacy_consent_at: datetime = Field(default_factory=utcnow)
    terms_version: str = Field(max_length=30)
    privacy_version: str = Field(max_length=30)
    cancelled_at: datetime | None = Field(default=None)
    cancellation_reason: str | None = Field(default=None, max_length=500)

    items: list["ReservationItem"] = Relationship(
        back_populates="reservation",
        cascade_delete=True,
    )
