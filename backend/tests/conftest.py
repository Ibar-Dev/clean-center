import os
from collections.abc import Generator
from pathlib import Path

import pytest

TEST_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "test_clean_center.db"

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-characters"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "test-admin-password"
os.environ["WHATSAPP_PHONE"] = "5491123456789"
os.environ["STORE_NAME"] = "Clean Center Test"
os.environ["STORE_ADDRESS"] = "Av. Test 123"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _clean_database() -> Generator[None, None, None]:
    for suffix in ("", "-wal", "-shm"):
        path = Path(f"{TEST_DB_PATH}{suffix}")
        path.unlink(missing_ok=True)
    yield
    engine.dispose()
    for suffix in ("", "-wal", "-shm"):
        path = Path(f"{TEST_DB_PATH}{suffix}")
        path.unlink(missing_ok=True)


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": settings.admin_username, "password": settings.admin_password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def product(client: TestClient, admin_headers: dict[str, str]) -> dict:
    categories = client.get("/api/admin/categories", headers=admin_headers).json()
    response = client.post(
        "/api/admin/products",
        headers=admin_headers,
        json={
            "name": "Producto de prueba",
            "description": "Producto para tests",
            "price": "1500.50",
            "unit": "Unidad",
            "stock": 10,
            "category_id": categories[0]["id"],
            "is_active": True,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
