"""Domain exceptions mapped to HTTP status codes in api.py."""


class ShopError(Exception):
    code = "shop_error"
    status_code = 400


class ProductNotFoundError(ShopError):
    code = "product_not_found"
    status_code = 404


class CategoryNotFoundError(ShopError):
    code = "category_not_found"
    status_code = 404


class DuplicateCategoryError(ShopError):
    code = "duplicate_category"
    status_code = 409


class InsufficientStockError(ShopError):
    code = "insufficient_stock"
    status_code = 409


class EmptyUpdateError(ShopError):
    code = "empty_update"
    status_code = 400


class InvalidPriceRangeError(ShopError):
    code = "invalid_price_range"
    status_code = 400
