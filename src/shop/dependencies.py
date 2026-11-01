"""FastAPI dependencies."""
from __future__ import annotations

from collections.abc import Generator

import httpx
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from shop import database
from shop.config import Settings
from shop.services import ShopService


def get_session() -> Generator[Session, None, None]:
    session = database.SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_service(session: Session = Depends(get_session)) -> ShopService:
    return ShopService(session)


def get_settings() -> Settings:
    return Settings.from_env()


def get_http_client(request: Request) -> httpx.AsyncClient:
    """Shared AsyncClient created in the application lifespan."""
    return request.app.state.http_client
