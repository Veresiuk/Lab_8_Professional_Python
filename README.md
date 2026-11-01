# Shop API

Лабораторна робота №8 «Мережеве та асинхронне програмування. REST API», варіант №3 — «Інтернет-магазин».

Архітектура: `HTTP client → FastAPI → Pydantic → Service layer → Repository layer → SQLAlchemy / SQLite`.

## Installation
    python -m venv .venv
    .venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
    python -m pip install -e ".[test]"

## Run API
    python -m shop.seed             # (необов'язково) демонстраційні дані
    uvicorn shop.api:app --reload

Swagger UI: http://127.0.0.1:8000/docs

## Environment variables
| Variable | Default | Description |
|---|---|---|
| DATABASE_URL | sqlite:///shop.db | SQLAlchemy URL |
| SHOP_API_BASE_URL | http://127.0.0.1:8000 | base URL для batch-запитів HTTPX |
| SHOP_BATCH_TIMEOUT | 10 | timeout batch-операції, с |
| SHOP_MAX_CONCURRENCY | 5 | розмір Semaphore |
| SHOP_RETRY_ATTEMPTS | 3 | кількість спроб retry |

## Tests
    python -m pytest -v
