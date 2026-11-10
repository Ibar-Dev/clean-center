from enum import StrEnum


class ReservationStatus(StrEnum):
    PENDIENTE = "PENDIENTE"
    CONFIRMADO = "CONFIRMADO"
    RETIRADO = "RETIRADO"
    CANCELADO = "CANCELADO"


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"
