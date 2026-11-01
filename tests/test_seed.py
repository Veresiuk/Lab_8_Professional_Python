from sqlalchemy.orm import sessionmaker

from shop import database, seed
from shop.models import Product


def test_seed_is_idempotent(monkeypatch, tmp_path, capsys):
    engine = database.make_engine(f"sqlite:///{tmp_path}/seed.db")
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=engine, expire_on_commit=False))
    seed.seed()
    seed.seed()
    with database.SessionLocal() as session:
        assert session.query(Product).count() == 3
    assert "already contains data" in capsys.readouterr().out
