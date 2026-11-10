from fastapi.testclient import TestClient

from app.core.config import settings


def test_login_success(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": settings.admin_username, "password": settings.admin_password},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["user"]["username"] == settings.admin_username
    assert data["user"]["role"] == "ADMIN"


def test_login_with_bad_password(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": settings.admin_username, "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_login_with_unknown_user(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "nobody", "password": "whatever"},
    )

    assert response.status_code == 401


def test_me_requires_token(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_token(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.get("/api/auth/me", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"


def test_invalid_token_rejected(client: TestClient) -> None:
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 401


def test_admin_endpoints_require_auth(client: TestClient) -> None:
    assert client.get("/api/admin/reservations").status_code == 401
    assert client.get("/api/admin/products").status_code == 401
