"""FastAPI application: REST endpoints of the online shop."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Literal

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from shop import database
from shop.config import Settings
from shop.dependencies import get_http_client, get_service, get_settings
from shop.exceptions import ShopError
from shop.external_api import fetch_many
from shop.schemas import (
    BatchRequest,
    CategoryCreate,
    CategoryResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    PurchaseRequest,
    PurchaseResponse,
    StockSummary,
)
from shop.services import ShopService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables and one shared AsyncClient for the whole application."""
    database.init_db()
    settings = Settings.from_env()
    app.state.http_client = httpx.AsyncClient(
        base_url=settings.api_base_url,
        timeout=httpx.Timeout(5.0, connect=2.0),
    )
    try:
        yield
    finally:
        await app.state.http_client.aclose()


app = FastAPI(
    title="Shop API",
    version="0.8.0",
    description="Асинхронний REST API інтернет-магазину (лабораторна робота №8).",
    lifespan=lifespan,
)


@app.exception_handler(ShopError)
async def shop_error_handler(request: Request, exc: ShopError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc), "code": exc.code},
    )


@app.get("/", tags=["service"])
async def root() -> dict[str, str]:
    return {"service": "Shop API", "version": app.version, "docs": "/docs"}


# ---------------------------------------------------------------- categories
@app.get("/categories", response_model=list[CategoryResponse], tags=["categories"])
async def list_categories(service: ShopService = Depends(get_service)):
    return service.list_categories()


@app.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["categories"],
)
async def create_category(data: CategoryCreate, service: ShopService = Depends(get_service)):
    return service.create_category(data)


@app.get(
    "/categories/{category_id}/products",
    response_model=list[ProductResponse],
    tags=["categories"],
)
async def category_products(category_id: int, service: ShopService = Depends(get_service)):
    return service.products_in_category(category_id)


# ------------------------------------------------------------------ products
@app.get("/products", response_model=list[ProductResponse], tags=["products"])
async def list_products(
    q: str | None = Query(default=None, min_length=1, description="Пошук за назвою"),
    category_id: int | None = Query(default=None, gt=0),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    sort_by: Literal["name", "price", "quantity"] = "name",
    descending: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: ShopService = Depends(get_service),
):
    return service.list_products(
        q=q, category_id=category_id, min_price=min_price, max_price=max_price,
        sort_by=sort_by, descending=descending, limit=limit, offset=offset,
    )


@app.get("/products/summary", response_model=StockSummary, tags=["products"])
async def stock_summary(service: ShopService = Depends(get_service)):
    """Total stock value and the most expensive product."""
    return service.summary()


@app.post("/products/batch", response_model=list[ProductResponse], tags=["async"])
async def batch_products(
    body: BatchRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    settings: Settings = Depends(get_settings),
):
    """Fetch several products in parallel through HTTPX (Task, gather, Semaphore, timeout, retry)."""
    try:
        return await asyncio.wait_for(
            fetch_many(
                client,
                body.product_ids,
                max_concurrency=settings.max_concurrency,
                attempts=settings.retry_attempts,
                backoff_base=settings.backoff_base,
            ),
            timeout=settings.batch_timeout,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status.HTTP_504_GATEWAY_TIMEOUT, "Batch operation timed out")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "One of the products was not found")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Upstream request failed")
    except httpx.RequestError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Upstream is unavailable")


@app.get("/products/{product_id}", response_model=ProductResponse, tags=["products"])
async def get_product(product_id: int, service: ShopService = Depends(get_service)):
    return service.get_product(product_id)


@app.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["products"],
)
async def create_product(data: ProductCreate, service: ShopService = Depends(get_service)):
    return service.create_product(data)


@app.patch("/products/{product_id}", response_model=ProductResponse, tags=["products"])
async def update_product(
    product_id: int, data: ProductUpdate, service: ShopService = Depends(get_service)
):
    return service.update_product(product_id, data)


@app.delete(
    "/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["products"]
)
async def delete_product(product_id: int, service: ShopService = Depends(get_service)) -> None:
    service.delete_product(product_id)


@app.post(
    "/products/{product_id}/purchase", response_model=PurchaseResponse, tags=["products"]
)
async def purchase_product(
    product_id: int, body: PurchaseRequest, service: ShopService = Depends(get_service)
):
    """Transactional purchase: stock decrease + order creation."""
    return service.purchase(product_id, body.quantity)
