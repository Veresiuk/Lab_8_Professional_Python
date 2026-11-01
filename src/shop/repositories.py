"""Repository layer. Repositories never commit: transactions belong to services."""
from __future__ import annotations

from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shop.models import Category, Order, Product

SortField = Literal["name", "price", "quantity"]


class CategoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, category_id: int) -> Category | None:
        return self.session.get(Category, category_id)

    def get_by_name(self, name: str) -> Category | None:
        return self.session.scalars(select(Category).where(Category.name == name)).first()

    def get_all(self) -> list[Category]:
        return list(self.session.scalars(select(Category).order_by(Category.name)))

    def add(self, category: Category) -> Category:
        self.session.add(category)
        self.session.flush()
        return category


class ProductRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, product_id: int) -> Product | None:
        return self.session.get(Product, product_id)

    def search(
        self,
        *,
        q: str | None = None,
        category_id: int | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        sort_by: SortField = "name",
        descending: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Product]:
        stmt = select(Product)
        if q:
            stmt = stmt.where(func.lower(Product.name).contains(q.lower()))
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        if min_price is not None:
            stmt = stmt.where(Product.price >= min_price)
        if max_price is not None:
            stmt = stmt.where(Product.price <= max_price)
        column = getattr(Product, sort_by)
        stmt = stmt.order_by(column.desc() if descending else column.asc(), Product.id)
        return list(self.session.scalars(stmt.limit(limit).offset(offset)))

    def by_category(self, category_id: int) -> list[Product]:
        return self.search(category_id=category_id, limit=1000)

    def add(self, product: Product) -> Product:
        self.session.add(product)
        self.session.flush()
        return product

    def delete(self, product: Product) -> None:
        self.session.delete(product)
        self.session.flush()

    def most_expensive(self) -> Product | None:
        return self.session.scalars(
            select(Product).order_by(Product.price.desc(), Product.id).limit(1)
        ).first()

    def stock_stats(self) -> tuple[int, float]:
        count, total = self.session.execute(
            select(func.count(Product.id), func.coalesce(func.sum(Product.price * Product.quantity), 0.0))
        ).one()
        return int(count), float(total)


class OrderRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, order: Order) -> Order:
        self.session.add(order)
        self.session.flush()
        return order

    def count(self) -> int:
        return int(self.session.scalar(select(func.count(Order.id))) or 0)
