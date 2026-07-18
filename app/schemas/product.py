from datetime import datetime
from decimal import Decimal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from app.schemas.common import ORMModel


class ProductPayload(BaseModel):
    marketplace: str = "shopee"
    external_product_id: str | None = None
    normalized_url: str
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


class ProductImportRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    url: AnyHttpUrl


class ProductUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=512)
    price: Decimal | None = Field(default=None, gt=0)
    original_price: Decimal | None = Field(default=None, gt=0)
    discount: str | None = Field(default=None, max_length=64)
    rating: float | None = Field(default=None, ge=0, le=5)
    sold_count: int | None = Field(default=None, ge=0)
    images: list[AnyHttpUrl] | None = None
    shop_name: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=255)
    affiliate_url: AnyHttpUrl | None = None


class ProductRead(ORMModel):
    id: int
    source_url: str
    normalized_url: str
    marketplace: str
    external_product_id: str | None
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
    expires_at: datetime
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ProductRead]
