"""Service layer: business rules and transactions."""
from __future__ import annotations

from sqlalchemy.orm import Session

from shop.exceptions import (
    CategoryNotFoundError,
    DuplicateCategoryError,
    EmptyUpdateError,
    InsufficientStockError,
    InvalidPriceRangeError,
    ProductNotFoundError,
)
from shop.models import Category, Order, Product
from shop.repositories import CategoryRepository, OrderRepository, ProductRepository
from shop.schemas import (
    CategoryCreate,
    ProductCreate,
    ProductUpdate,
    PurchaseResponse,
    StockSummary,
)


class ShopService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.categories = CategoryRepository(session)
        self.products = ProductRepository(session)
        self.orders = OrderRepository(session)

    # ---- categories -------------------------------------------------------
    def create_category(self, data: CategoryCreate) -> Category:
        if self.categories.get_by_name(data.name):
            raise DuplicateCategoryError(f"Category '{data.name}' already exists")
        category = self.categories.add(Category(name=data.name))
        self.session.commit()
        return category

    def list_categories(self) -> list[Category]:
        return self.categories.get_all()

    def _require_category(self, category_id: int) -> Category:
        category = self.categories.get(category_id)
        if category is None:
            raise CategoryNotFoundError(f"Category {category_id} not found")
        return category

    # ---- products ---------------------------------------------------------
    def create_product(self, data: ProductCreate) -> Product:
        self._require_category(data.category_id)
        product = self.products.add(Product(**data.model_dump()))
        self.session.commit()
        return product

    def get_product(self, product_id: int) -> Product:
        product = self.products.get(product_id)
        if product is None:
            raise ProductNotFoundError(f"Product {product_id} not found")
        return product

    def list_products(self, **filters) -> list[Product]:
        low, high = filters.get("min_price"), filters.get("max_price")
        if low is not None and high is not None and low > high:
            raise InvalidPriceRangeError("min_price cannot be greater than max_price")
        return self.products.search(**filters)

    def products_in_category(self, category_id: int) -> list[Product]:
        self._require_category(category_id)
        return self.products.by_category(category_id)

    def update_product(self, product_id: int, data: ProductUpdate) -> Product:
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            raise EmptyUpdateError("No fields to update")
        product = self.get_product(product_id)
        for field, value in changes.items():
            setattr(product, field, value)
        self.session.commit()
        return product

    def delete_product(self, product_id: int) -> None:
        product = self.get_product(product_id)
        self.products.delete(product)
        self.session.commit()

    def summary(self) -> StockSummary:
        count, total = self.products.stock_stats()
        return StockSummary(
            products_count=count,
            total_stock_value=round(total, 2),
            most_expensive=self.products.most_expensive(),
        )

    # ---- transaction ------------------------------------------------------
    def purchase(self, product_id: int, quantity: int) -> PurchaseResponse:
        """Atomically decrease stock and create an order (all or nothing)."""
        try:
            product = self.get_product(product_id)
            if product.quantity < quantity:
                raise InsufficientStockError(
                    f"Only {product.quantity} item(s) left, requested {quantity}"
                )
            product.quantity -= quantity
            order = self.orders.add(
                Order(
                    product_id=product.id,
                    quantity=quantity,
                    total_price=round(product.price * quantity, 2),
                )
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return PurchaseResponse(
            order_id=order.id,
            product_id=product.id,
            quantity=quantity,
            total_price=order.total_price,
            remaining_quantity=product.quantity,
        )
