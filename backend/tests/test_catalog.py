from fastapi.testclient import TestClient


def test_list_categories(client: TestClient) -> None:
    response = client.get("/api/categories")

    assert response.status_code == 200
    slugs = {category["slug"] for category in response.json()}
    assert {"hogar", "desinfectantes", "industrial", "accesorios"} <= slugs


def test_list_products_paginated(client: TestClient) -> None:
    response = client.get("/api/products?page=1&page_size=5")

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 5
    assert data["total"] >= 12
    assert len(data["items"]) == 5


def test_search_products(client: TestClient) -> None:
    response = client.get("/api/products?search=detergente")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert all("detergente" in item["name"].lower() for item in data["items"])


def test_filter_products_by_category(client: TestClient) -> None:
    response = client.get("/api/products?category=industrial")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert all(item["category"]["slug"] == "industrial" for item in data["items"])


def test_product_detail(client: TestClient) -> None:
    listing = client.get("/api/products?page_size=1").json()

    response = client.get(f"/api/products/{listing['items'][0]['id']}")

    assert response.status_code == 200
    assert response.json()["price"].count(".") == 1


def test_missing_product_returns_404(client: TestClient) -> None:
    assert client.get("/api/products/999999").status_code == 404


def test_price_serialized_with_two_decimals(client: TestClient) -> None:
    item = client.get("/api/products?page_size=1").json()["items"][0]

    whole, decimals = item["price"].split(".")
    assert len(decimals) == 2
    assert whole.isdigit()
