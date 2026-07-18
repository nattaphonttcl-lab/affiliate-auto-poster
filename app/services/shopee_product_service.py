from app.core.config import Settings
from app.models.product import Product
from app.repositories.product_repository import ProductRepositoryProtocol, utc_now
from app.utils.shopee_parser import ShopeeProductParser
from app.utils.shopee_validator import ShopeeProductValidator


class ShopeeProductService:
    def __init__(
        self,
        repository: ProductRepositoryProtocol,
        parser: ShopeeProductParser,
        validator: ShopeeProductValidator,
        settings: Settings,
    ) -> None:
        self._repository = repository
        self._parser = parser
        self._validator = validator
        self._settings = settings

    def get_product(self, source_url: str) -> Product:
        self._validator.validate_url(source_url)

        now = utc_now()
        cached = self._repository.get_valid_by_source_url(source_url, now)
        if cached is not None:
            return cached

        payload = self._parser.parse(source_url)
        self._validator.validate_payload(payload)

        return self._repository.upsert_cached(
            source_url=source_url,
            payload=payload,
            now=now,
            ttl_minutes=self._settings.shopee_cache_ttl_minutes,
        )
