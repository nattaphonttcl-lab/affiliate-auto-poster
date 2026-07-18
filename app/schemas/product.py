from datetime import datetime
from decimal import Decimal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict

from app.schemas.common import ORMModel


class ProductPayload(BaseModel):
    title: str
    price: Decimal
    original_price: Decimal | None = None
    discount: str | None = None
    rating: float | None = None
    sold_count: int | None = None
    images: list[str]
    shop_name: str | None = None
    category: str | None = None
    affiliate_url: str


class ShopeeProductRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    url: AnyHttpUrl


class ProductRead(ORMModel):
    id: int
    title: str
    price: Decimal
    original_price: Decimal | None
    discount: str | None
    rating: float | None
    sold_count: int | None
    images: list[str]
    shop_name: str | None
    category: str | None
    affiliate_url: str
    created_at: datetime
    updated_at: datetime
