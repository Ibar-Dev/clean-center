from fastapi.testclient import TestClient

from app.core.config import settings


def test_public_config_exposes_commercial_data(client: TestClient) -> None:
    response = client.get("/api/config")

    assert response.status_code == 200
    data = response.json()
    assert data["store_name"] == settings.store_name
    assert data["store_address"] == settings.store_address
    assert data["reservation_expiration_hours"] == settings.reservation_expiration_hours
    assert data["min_pickup_lead_minutes"] == settings.min_pickup_lead_minutes
    assert data["whatsapp_available"] is True
    assert response.headers["cache-control"] == "public, max-age=60"


def test_public_config_never_leaks_secrets(client: TestClient) -> None:
    payload = client.get("/api/config").text.lower()

    for secret in (
        "jwt_secret",
        "admin_password",
        "database_url",
        "secret-key-with",
        "test-admin-password",
    ):
        assert secret not in payload


def test_healthcheck(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
