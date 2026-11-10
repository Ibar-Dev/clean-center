from fastapi.testclient import TestClient


def _new_product(category_id: int) -> dict:
    return {
        "name": "Nuevo producto",
        "description": "Descripción de prueba",
        "price": "2500.00",
        "unit": "1 Litro",
        "stock": 12,
        "category_id": category_id,
        "is_active": True,
    }


def test_admin_can_create_product(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    category_id = client.get("/api/admin/categories", headers=admin_headers).json()[0]["id"]

    response = client.post(
        "/api/admin/products",
        headers=admin_headers,
        json=_new_product(category_id),
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == "Nuevo producto"
    assert data["price"] == "2500.00"
    assert data["stock"] == 12
    assert data["is_active"] is True


def test_admin_product_rejects_unknown_category(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/admin/products",
        headers=admin_headers,
        json=_new_product(999999),
    )

    assert response.status_code == 422


def test_admin_product_rejects_invalid_price(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    category_id = client.get("/api/admin/categories", headers=admin_headers).json()[0]["id"]
    payload = _new_product(category_id)
    payload["price"] = "0"

    response = client.post("/api/admin/products", headers=admin_headers, json=payload)

    assert response.status_code == 422


def test_admin_can_update_product(
    client: TestClient,
    admin_headers: dict[str, str],
    product: dict,
) -> None:
    response = client.patch(
        f"/api/admin/products/{product['id']}",
        headers=admin_headers,
        json={"price": "1800.00", "stock": 3, "description": "Actualizado"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["price"] == "1800.00"
    assert data["stock"] == 3
    assert data["description"] == "Actualizado"


def test_admin_can_toggle_is_active_through_update(
    client: TestClient,
    admin_headers: dict[str, str],
    product: dict,
) -> None:
    response = client.patch(
        f"/api/admin/products/{product['id']}",
        headers=admin_headers,
        json={"name": "Producto editado", "is_active": False},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "Producto editado"
    assert data["is_active"] is False


def test_admin_can_archive_product(
    client: TestClient,
    admin_headers: dict[str, str],
    product: dict,
) -> None:
    response = client.patch(
        f"/api/admin/products/{product['id']}/status",
        headers=admin_headers,
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    public = client.get("/api/products?search=Producto de prueba")
    assert all(item["id"] != product["id"] for item in public.json()["items"])

    admin = client.get(
        "/api/admin/products?search=Producto de prueba",
        headers=admin_headers,
    )
    assert any(item["id"] == product["id"] for item in admin.json()["items"])
