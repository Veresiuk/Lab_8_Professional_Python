"""REST API tests: status codes, validation, filters, transactions."""
import pytest

from shop.models import Order, Product
from shop.repositories import OrderRepository


async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "Shop API"


# ---------------------------------------------------------------- categories
async def test_create_category_returns_201(client):
    response = await client.post("/categories", json={"name": "books"})
    assert response.status_code == 201
    assert response.json() == {"id": 1, "name": "books"}


async def test_duplicate_category_returns_409(client, category):
    response = await client.post("/categories", json={"name": "electronics"})
    assert response.status_code == 409
    assert response.json()["code"] == "duplicate_category"


async def test_list_categories(client, catalog):
    names = [c["name"] for c in (await client.get("/categories")).json()]
    assert names == ["electronics", "stationery"]


async def test_category_products(client, catalog):
    category_id = catalog["electronics"]["id"]
    response = await client.get(f"/categories/{category_id}/products")
    assert response.status_code == 200
    assert {p["name"] for p in response.json()} == {"Laptop", "Mouse"}


async def test_category_products_unknown_category_returns_404(client):
    response = await client.get("/categories/999/products")
    assert response.status_code == 404
    assert response.json()["code"] == "category_not_found"


# ------------------------------------------------------------------ products
async def test_create_product_returns_201_and_json(client, category):
    payload = {"name": "Laptop", "category_id": category["id"], "price": 25000, "quantity": 3}
    response = await client.post("/products", json=payload)
    assert response.status_code == 201
    assert response.json() == {"id": 1, "name": "Laptop", "category_id": 1, "price": 25000.0, "quantity": 3}


@pytest.mark.parametrize(
    "patch",
    [
        {"price": 0},
        {"price": -5},
        {"quantity": -1},
        {"name": "A"},
        {"name": ""},
        {"category_id": 0},
        {"price": "abc"},
    ],
    ids=["zero-price", "negative-price", "negative-quantity", "short-name", "empty-name", "bad-category", "price-not-number"],
)
async def test_create_product_validation_errors_return_422(client, category, patch):
    payload = {"name": "Laptop", "category_id": category["id"], "price": 10, "quantity": 1, **patch}
    response = await client.post("/products", json=payload)
    assert response.status_code == 422


async def test_create_product_missing_field_returns_422(client):
    response = await client.post("/products", json={"name": "Laptop"})
    assert response.status_code == 422


async def test_create_product_unknown_category_returns_404(client):
    payload = {"name": "Laptop", "category_id": 42, "price": 10, "quantity": 1}
    response = await client.post("/products", json=payload)
    assert response.status_code == 404


async def test_get_product(client, laptop):
    response = await client.get(f"/products/{laptop['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Laptop"


async def test_get_missing_product_returns_404(client):
    response = await client.get("/products/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Product 999 not found", "code": "product_not_found"}


async def test_get_product_with_non_integer_id_returns_422(client):
    assert (await client.get("/products/abc")).status_code == 422


async def test_list_products_sorted_by_name_by_default(client, catalog):
    names = [p["name"] for p in (await client.get("/products")).json()]
    assert names == ["Laptop", "Mouse", "Notebook"]


async def test_filter_by_category(client, catalog):
    response = await client.get("/products", params={"category_id": catalog["stationery"]["id"]})
    assert [p["name"] for p in response.json()] == ["Notebook"]


async def test_search_by_name_is_case_insensitive(client, catalog):
    response = await client.get("/products", params={"q": "LAP"})
    assert [p["name"] for p in response.json()] == ["Laptop"]


async def test_filter_by_price_range(client, catalog):
    response = await client.get("/products", params={"min_price": 100, "max_price": 1000})
    assert [p["name"] for p in response.json()] == ["Mouse"]


async def test_invalid_price_range_returns_400(client, catalog):
    response = await client.get("/products", params={"min_price": 500, "max_price": 100})
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_price_range"


async def test_sort_by_price_descending(client, catalog):
    response = await client.get("/products", params={"sort_by": "price", "descending": "true"})
    assert [p["name"] for p in response.json()] == ["Laptop", "Mouse", "Notebook"]


async def test_pagination(client, catalog):
    response = await client.get("/products", params={"limit": 1, "offset": 1})
    assert [p["name"] for p in response.json()] == ["Mouse"]


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"sort_by": "color"}])
async def test_invalid_query_parameters_return_422(client, params):
    assert (await client.get("/products", params=params)).status_code == 422


async def test_patch_price_and_quantity(client, laptop):
    response = await client.patch(f"/products/{laptop['id']}", json={"price": 23999.99, "quantity": 7})
    assert response.status_code == 200
    body = response.json()
    assert (body["price"], body["quantity"], body["name"]) == (23999.99, 7, "Laptop")


async def test_patch_with_empty_body_returns_400(client, laptop):
    response = await client.patch(f"/products/{laptop['id']}", json={})
    assert response.status_code == 400
    assert response.json()["code"] == "empty_update"


async def test_patch_invalid_value_returns_422(client, laptop):
    assert (await client.patch(f"/products/{laptop['id']}", json={"quantity": -3})).status_code == 422


async def test_patch_missing_product_returns_404(client):
    assert (await client.patch("/products/999", json={"price": 5})).status_code == 404


async def test_delete_product_returns_204_then_404(client, laptop):
    response = await client.delete(f"/products/{laptop['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert (await client.get(f"/products/{laptop['id']}")).status_code == 404


async def test_delete_missing_product_returns_404(client):
    assert (await client.delete("/products/999")).status_code == 404


# ------------------------------------------------------------------- summary
async def test_summary_total_value_and_most_expensive(client, catalog):
    body = (await client.get("/products/summary")).json()
    assert body["products_count"] == 3
    assert body["total_stock_value"] == pytest.approx(25000 * 3 + 500 * 20 + 40.5 * 100)
    assert body["most_expensive"]["name"] == "Laptop"


async def test_summary_of_empty_shop(client):
    body = (await client.get("/products/summary")).json()
    assert body == {"products_count": 0, "total_stock_value": 0.0, "most_expensive": None}


# ------------------------------------------------------- transactional logic
async def test_purchase_decreases_stock_and_creates_order(client, laptop, db_session):
    response = await client.post(f"/products/{laptop['id']}/purchase", json={"quantity": 2})
    assert response.status_code == 200
    assert response.json() == {
        "order_id": 1, "product_id": laptop["id"], "quantity": 2,
        "total_price": 50000.0, "remaining_quantity": 1,
    }
    assert (await client.get(f"/products/{laptop['id']}")).json()["quantity"] == 1
    assert OrderRepository(db_session).count() == 1


async def test_purchase_all_remaining_stock_is_allowed(client, laptop):
    response = await client.post(f"/products/{laptop['id']}/purchase", json={"quantity": 3})
    assert response.status_code == 200
    assert response.json()["remaining_quantity"] == 0


async def test_purchase_more_than_stock_returns_409_and_keeps_stock(client, laptop, db_session):
    response = await client.post(f"/products/{laptop['id']}/purchase", json={"quantity": 4})
    assert response.status_code == 409
    assert response.json()["code"] == "insufficient_stock"
    assert (await client.get(f"/products/{laptop['id']}")).json()["quantity"] == 3
    assert OrderRepository(db_session).count() == 0


@pytest.mark.parametrize("quantity", [0, -1, 1001, "x"])
async def test_purchase_invalid_quantity_returns_422(client, laptop, quantity):
    response = await client.post(f"/products/{laptop['id']}/purchase", json={"quantity": quantity})
    assert response.status_code == 422


async def test_purchase_unknown_product_returns_404(client):
    assert (await client.post("/products/999/purchase", json={"quantity": 1})).status_code == 404


async def test_purchase_is_rolled_back_when_order_cannot_be_saved(client, laptop, monkeypatch, db_session):
    """Transaction: if creating the order fails, stock must not change."""
    def broken_add(self, order):
        raise RuntimeError("database failure")

    monkeypatch.setattr(OrderRepository, "add", broken_add)
    response = await client.post(f"/products/{laptop['id']}/purchase", json={"quantity": 1})
    assert response.status_code == 500
    monkeypatch.undo()
    assert (await client.get(f"/products/{laptop['id']}")).json()["quantity"] == 3
    assert OrderRepository(db_session).count() == 0
