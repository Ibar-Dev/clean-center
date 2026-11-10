from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def _pickup(hours: int = 3) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).isoformat()


def _payload(product_id: int, *, quantity: int = 1, pickup: str | None = None) -> dict:
    return {
        "customer_name": "Ana",
        "customer_last_name": "García",
        "customer_email": "ana@example.com",
        "customer_phone": "+54 11 5555-1234",
        "pickup_date": pickup or _pickup(),
        "items": [{"product_id": product_id, "quantity": quantity}],
        "terms_accepted": True,
        "privacy_consent": True,
    }


def test_create_reservation_decrements_stock(
    client: TestClient,
    product: dict,
) -> None:
    response = client.post("/api/reservations", json=_payload(product["id"], quantity=3))

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["code"].startswith("CC-")
    assert len(data["code"]) == 9
    assert data["status"] == "PENDIENTE"
    assert data["total_amount"] == "4501.50"
    assert data["items"][0]["product_name"] == product["name"]
    assert data["items"][0]["unit_price"] == "1500.50"
    assert data["whatsapp_url"].startswith("https://wa.me/5491123456789?text=")

    stock = client.get(f"/api/products/{product['id']}").json()["stock"]
    assert stock == 7


def test_create_reservation_rejects_insufficient_stock(
    client: TestClient,
    product: dict,
) -> None:
    response = client.post("/api/reservations", json=_payload(product["id"], quantity=11))

    assert response.status_code == 409
    assert "stock" in response.json()["detail"].lower()

    stock = client.get(f"/api/products/{product['id']}").json()["stock"]
    assert stock == 10


def test_create_reservation_requires_consents(
    client: TestClient,
    product: dict,
) -> None:
    payload = _payload(product["id"])
    payload["terms_accepted"] = False

    response = client.post("/api/reservations", json=payload)

    assert response.status_code == 422


def test_create_reservation_rejects_pickup_outside_window(
    client: TestClient,
    product: dict,
) -> None:
    too_soon = client.post(
        "/api/reservations",
        json=_payload(product["id"], pickup=(datetime.now(UTC) + timedelta(minutes=5)).isoformat()),
    )
    too_late = client.post(
        "/api/reservations",
        json=_payload(product["id"], pickup=_pickup(hours=72)),
    )

    assert too_soon.status_code == 422
    assert too_late.status_code == 422


def test_create_reservation_rejects_duplicate_products(
    client: TestClient,
    product: dict,
) -> None:
    payload = _payload(product["id"])
    payload["items"].append({"product_id": product["id"], "quantity": 1})

    response = client.post("/api/reservations", json=payload)

    assert response.status_code == 422


def test_lookup_requires_matching_email(
    client: TestClient,
    product: dict,
) -> None:
    created = client.post("/api/reservations", json=_payload(product["id"])).json()

    assert (
        client.post(
            "/api/reservations/lookup",
            json={"code": created["code"], "email": "ana@example.com"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/reservations/lookup",
            json={"code": created["code"], "email": "otra@example.com"},
        ).status_code
        == 404
    )


def test_cancel_reservation_restores_stock(
    client: TestClient,
    product: dict,
) -> None:
    created = client.post("/api/reservations", json=_payload(product["id"], quantity=4)).json()
    assert client.get(f"/api/products/{product['id']}").json()["stock"] == 6

    response = client.post(
        f"/api/reservations/{created['code']}/cancel",
        json={"email": "ana@example.com", "reason": "No puedo retirar"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "CANCELADO"
    assert response.json()["cancellation_reason"] == "No puedo retirar"
    assert client.get(f"/api/products/{product['id']}").json()["stock"] == 10

    # Cancelar dos veces no vuelve a reponer stock.
    again = client.post(
        f"/api/reservations/{created['code']}/cancel",
        json={"email": "ana@example.com"},
    )
    assert again.status_code == 200
    assert client.get(f"/api/products/{product['id']}").json()["stock"] == 10


def test_admin_status_flow(
    client: TestClient,
    admin_headers: dict[str, str],
    product: dict,
) -> None:
    created = client.post("/api/reservations", json=_payload(product["id"])).json()

    listing = client.get("/api/admin/reservations", headers=admin_headers).json()
    reservation_id = next(
        item["id"] for item in listing["items"] if item["code"] == created["code"]
    )

    assert (
        client.patch(
            f"/api/admin/reservations/{reservation_id}/status",
            headers=admin_headers,
            json={"status": "RETIRADO"},
        ).status_code
        == 409
    )

    confirm = client.patch(
        f"/api/admin/reservations/{reservation_id}/status",
        headers=admin_headers,
        json={"status": "CONFIRMADO"},
    )
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "CONFIRMADO"

    picked_up = client.patch(
        f"/api/admin/reservations/{reservation_id}/status",
        headers=admin_headers,
        json={"status": "RETIRADO"},
    )
    assert picked_up.status_code == 200
    assert picked_up.json()["status"] == "RETIRADO"

    # Un retiro completado ya no repone stock al intentar cancelar.
    assert (
        client.patch(
            f"/api/admin/reservations/{reservation_id}/status",
            headers=admin_headers,
            json={"status": "CANCELADO"},
        ).status_code
        == 409
    )


def test_reservation_snapshots_survive_price_change(
    client: TestClient,
    admin_headers: dict[str, str],
    product: dict,
) -> None:
    created = client.post("/api/reservations", json=_payload(product["id"])).json()

    update = client.patch(
        f"/api/admin/products/{product['id']}",
        headers=admin_headers,
        json={"price": "9999.00", "name": "Producto renombrado"},
    )
    assert update.status_code == 200

    lookup = client.post(
        "/api/reservations/lookup",
        json={"code": created["code"], "email": "ana@example.com"},
    )

    assert lookup.status_code == 200
    item = lookup.json()["items"][0]
    assert item["product_name"] == product["name"]
    assert item["unit_price"] == "1500.50"
    assert lookup.json()["total_amount"] == created["total_amount"]
