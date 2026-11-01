"""Demo data: python -m shop.seed"""
from shop import database
from shop.models import Category, Product


def seed() -> None:
    database.init_db()
    with database.SessionLocal() as session:
        if session.query(Category).count():
            print("Database already contains data")
            return
        electronics, stationery = Category(name="electronics"), Category(name="stationery")
        session.add_all([electronics, stationery])
        session.flush()
        session.add_all([
            Product(name="Laptop", category_id=electronics.id, price=25000.0, quantity=3),
            Product(name="Mouse", category_id=electronics.id, price=500.0, quantity=20),
            Product(name="Notebook", category_id=stationery.id, price=40.5, quantity=100),
        ])
        session.commit()
        print("Seeded 2 categories and 3 products")


if __name__ == "__main__":
    seed()
