from shop.config import Settings


def test_defaults(monkeypatch):
    for name in ("DATABASE_URL", "SHOP_API_BASE_URL", "SHOP_BATCH_TIMEOUT", "SHOP_MAX_CONCURRENCY", "SHOP_RETRY_ATTEMPTS"):
        monkeypatch.delenv(name, raising=False)
    s = Settings.from_env()
    assert (s.max_concurrency, s.retry_attempts, s.batch_timeout) == (5, 3, 10.0)


def test_settings_from_environment(monkeypatch):
    monkeypatch.setenv("SHOP_MAX_CONCURRENCY", "2")
    monkeypatch.setenv("SHOP_RETRY_ATTEMPTS", "4")
    monkeypatch.setenv("SHOP_BATCH_TIMEOUT", "1.5")
    s = Settings.from_env()
    assert (s.max_concurrency, s.retry_attempts, s.batch_timeout) == (2, 4, 1.5)
