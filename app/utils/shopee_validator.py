from urllib.parse import urlparse

from app.core.exceptions import AppException
from app.schemas.product import ProductPayload


class ShopeeProductValidator:
    def validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise AppException(status_code=422, detail="Shopee URL must use http or https")

        host = parsed.netloc.lower()
        if "shopee." not in host:
            raise AppException(status_code=422, detail="URL must be a Shopee product URL")

    def validate_payload(self, payload: ProductPayload) -> None:
        if not payload.title.strip():
            raise AppException(status_code=422, detail="Product title is required")

        if payload.price <= 0:
            raise AppException(status_code=422, detail="Product price must be greater than 0")

        if not payload.affiliate_url.startswith(("http://", "https://")):
            raise AppException(status_code=422, detail="Affiliate URL must be a valid absolute URL")
