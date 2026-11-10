from pydantic import BaseModel, EmailStr


class PublicConfigRead(BaseModel):
    store_name: str
    store_legal_name: str
    store_cuit: str
    store_address: str
    store_phone: str
    store_email: EmailStr
    store_hours: str
    reservation_expiration_hours: int
    min_pickup_lead_minutes: int
    aaip_url: str
    terms_version: str
    privacy_version: str
    whatsapp_available: bool
