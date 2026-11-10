from fastapi import APIRouter, Response

from app.core.config import settings
from app.schemas.config import PublicConfigRead
from app.services.whatsapp import normalize_whatsapp_phone

router = APIRouter(tags=["config"])


@router.get("/config", response_model=PublicConfigRead)
def public_config(response: Response) -> PublicConfigRead:
    response.headers["Cache-Control"] = "public, max-age=60"
    return PublicConfigRead(
        store_name=settings.store_name,
        store_legal_name=settings.store_legal_name,
        store_cuit=settings.store_cuit,
        store_address=settings.store_address,
        store_phone=settings.store_phone,
        store_email=settings.store_email,
        store_hours=settings.store_hours,
        reservation_expiration_hours=settings.reservation_expiration_hours,
        min_pickup_lead_minutes=settings.min_pickup_lead_minutes,
        aaip_url=str(settings.aaip_url),
        terms_version=settings.terms_version,
        privacy_version=settings.privacy_version,
        whatsapp_available=normalize_whatsapp_phone(settings.whatsapp_phone) is not None,
    )
