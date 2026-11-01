"""Shared fixtures: isolated in-memory database and ASGI test client."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from shop.api import app
from shop.config import Settings
from shop.database import Base
from shop.dependencies import get_http_client, get_session, get_settings
from shop import models  # noqa: F401


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def db_session(session_factory):
    with session_factory() as session:
        yield session


@pytest.fixture
async def client(session_factory):
    """AsyncClient talking to the app through ASGI (no real network)."""

    def override_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        app.dependency_overrides[get_session] = override_session
        app.dependency_overrides[get_http_client] = lambda: http
        app.dependency_overrides[get_settings] = lambda: Settings(
            batch_timeout=2.0, max_concurrency=3, retry_attempts=2, backoff_base=0.0
        )
        yield http
    app.dependency_overrides.clear()


@pytest.fixture
async def category(client):
    response = await client.post("/categories", json={"name": "electronics"})
    return response.json()


@pytest.fixture
async def laptop(client, category):
    response = await client.post(
        "/products",
        json={"name": "Laptop", "category_id": category["id"], "price": 25000, "quantity": 3},
    )
    return response.json()


@pytest.fixture
async def catalog(client, category):
    """Three products in two categories."""
    stationery = (await client.post("/categories", json={"name": "stationery"})).json()
    items = [
        {"name": "Laptop", "category_id": category["id"], "price": 25000, "quantity": 3},
        {"name": "Mouse", "category_id": category["id"], "price": 500, "quantity": 20},
        {"name": "Notebook", "category_id": stationery["id"], "price": 40.5, "quantity": 100},
    ]
    for item in items:
        await client.post("/products", json=item)
    return {"electronics": category, "stationery": stationery}
