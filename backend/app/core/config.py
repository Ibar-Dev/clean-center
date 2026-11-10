from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import EmailStr, Field, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
ENV_FILE = REPO_DIR / ".env"

DEFAULT_JWT_SECRET = "dev-only-secret-change-me-0123456789abcdef"
DEFAULT_ADMIN_PASSWORD = "change-me-now"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["development", "production", "test"] = "development"
    app_name: str = "Clean Center API"
    api_prefix: str = "/api"

    database_url: str = f"sqlite:///{DATA_DIR / 'clean_center.db'}"
    jwt_secret_key: str = Field(default=DEFAULT_JWT_SECRET, min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=120, ge=5, le=1440)

    admin_username: str = "admin"
    admin_password: str = DEFAULT_ADMIN_PASSWORD

    cors_origins: str = "http://localhost:4200"
    rate_limit_enabled: bool = True
    reservation_rate_limit: str = "5/minute"
    lookup_rate_limit: str = "10/minute"
    login_rate_limit: str = "5/minute"

    # Datos comerciales públicos
    store_name: str = Field(default="Clean Center", min_length=2, max_length=100)
    store_legal_name: str = Field(default="Clean Center S.R.L.", min_length=2, max_length=150)
    store_cuit: str = Field(default="30-00000000-0", min_length=8, max_length=20)
    store_address: str = Field(default="Dirección a configurar", min_length=3, max_length=250)
    store_phone: str = Field(default="+54 11 0000-0000", min_length=6, max_length=40)
    store_email: EmailStr = "contacto@cleancenter.com.ar"
    store_hours: str = Field(
        default="Lun a Vie de 09:00 a 18:00, Sáb de 09:00 a 13:00",
        min_length=3,
        max_length=250,
    )
    reservation_expiration_hours: int = Field(default=48, ge=1, le=720)
    min_pickup_lead_minutes: int = Field(default=60, ge=0, le=10080)

    # Parámetros legales
    aaip_url: HttpUrl = "https://www.argentina.gob.ar/aaip"
    terms_version: str = "2026-11"
    privacy_version: str = "2026-11"

    # WhatsApp (solo enlace wa.me, sin envío automático)
    whatsapp_phone: str = ""

    # Logging
    log_level: str = "INFO"
    log_json: bool = False
    log_file: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def min_pickup_lead_seconds(self) -> int:
        return self.min_pickup_lead_minutes * 60

    @property
    def reservation_expiration_seconds(self) -> int:
        return self.reservation_expiration_hours * 3600

    @model_validator(mode="after")
    def validate_pickup_window(self) -> "Settings":
        if self.min_pickup_lead_minutes * 60 >= self.reservation_expiration_hours * 3600:
            raise ValueError(
                "MIN_PICKUP_LEAD_MINUTES debe ser menor que RESERVATION_EXPIRATION_HOURS."
            )
        if self.environment == "production":
            if self.jwt_secret_key == DEFAULT_JWT_SECRET:
                raise ValueError("JWT_SECRET_KEY debe configurarse en producción.")
            if self.admin_password == DEFAULT_ADMIN_PASSWORD:
                raise ValueError("ADMIN_PASSWORD debe configurarse en producción.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
