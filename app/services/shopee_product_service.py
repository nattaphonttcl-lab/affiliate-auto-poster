from app.core.cache import InMemoryTTLCache
from app.core.config import Settings
from app.models.product import Product
from app.repositories.analytics_repository import AnalyticsRepositoryProtocol
from app.repositories.product_repository import ProductRepositoryProtocol
from app.services.provider_factory import build_provider_registry
from app.services.product_service import ProductService
from app.services.refresh_queue import InMemoryProductRefreshQueue
from app.utils.shopee_parser import ShopeeProductParser
from app.utils.shopee_validator import ShopeeProductValidator


class ShopeeProductService:
    def __init__(
        self,
        repository: ProductRepositoryProtocol | None = None,
        parser: ShopeeProductParser | None = None,
        validator: ShopeeProductValidator | None = None,
        settings: Settings | None = None,
        analytics_repository: AnalyticsRepositoryProtocol | None = None,
        *,
        product_service: ProductService | None = None,
    ) -> None:
        if product_service is not None:
            self._product_service = product_service
            return

        if (
            repository is None
            or parser is None
            or validator is None
            or settings is None
        ):
            raise ValueError(
                "Provide either product_service or repository/parser/validator/settings"
            )

        self._product_service = ProductService(
            repository,
            build_provider_registry(
                shopee_parser=parser,
                shopee_validator=validator,
            ),
            InMemoryTTLCache(),
            InMemoryProductRefreshQueue(),
            cache_ttl_minutes=settings.shopee_cache_ttl_minutes,
            analytics_repository=analytics_repository,
        )

    def get_product(self, source_url: str) -> Product:
        return self._product_service.import_product(source_url=source_url)
