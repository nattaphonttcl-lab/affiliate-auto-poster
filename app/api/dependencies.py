from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.cache import InMemoryTTLCache
from app.core.config import Settings, get_settings
from app.core.exceptions import AppException
from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.ai_content_repository import AIContentRepository
from app.repositories.caption_repository import CaptionRepository
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.image_repository import ImageRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.scheduler_repository import SchedulerRepository
from app.repositories.user_repository import UserRepository
from app.services.ai_content_service import AIContentService
from app.services.ai_providers import ProviderFactory
from app.services.analytics_service import AnalyticsService
from app.services.auth_service import AuthService
from app.services.caption_service import CaptionService
from app.services.dashboard_service import DashboardService
from app.services.image_service import ImageService
from app.services.marketplace_provider import MarketplaceProviderRegistry
from app.services.product_service import ProductService
from app.services.provider_factory import build_provider_registry
from app.services.refresh_queue import InMemoryProductRefreshQueue, ProductRefreshQueue
from app.services.scheduler_service import SchedulerService
from app.services.shopee_product_service import ShopeeProductService
from app.services.user_service import UserService
from app.utils.ai_caption_engine import AICaptionEngine
from app.utils.image_generator_engine import ImageGeneratorEngine
from app.utils.post_publisher import (
    AuditPostPublisher,
    PostPublisherProtocol,
    WebhookPostPublisher,
)
from app.utils.shopee_parser import ShopeeProductParser
from app.utils.shopee_validator import ShopeeProductValidator

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
_product_cache = InMemoryTTLCache()
_refresh_queue = InMemoryProductRefreshQueue()
_ai_template_cache = InMemoryTTLCache()
_ai_provider_factory = ProviderFactory()


def get_settings_dependency() -> Settings:
    return get_settings()


def get_user_service(db: Session = Depends(get_db_session)) -> UserService:
    return UserService(UserRepository(db))


def get_analytics_repository(
    db: Session = Depends(get_db_session),
) -> AnalyticsRepository:
    return AnalyticsRepository(db)


def get_auth_service(
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dependency),
) -> AuthService:
    return AuthService(UserRepository(db), settings)


def get_marketplace_provider_registry(
    settings: Settings = Depends(get_settings_dependency),
) -> MarketplaceProviderRegistry:
    parser = ShopeeProductParser(
        timeout_seconds=settings.shopee_request_timeout_seconds
    )
    validator = ShopeeProductValidator()
    return build_provider_registry(
        shopee_parser=parser,
        shopee_validator=validator,
    )


def get_product_refresh_queue() -> ProductRefreshQueue:
    return _refresh_queue


def get_product_service(
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dependency),
    provider_registry: MarketplaceProviderRegistry = Depends(
        get_marketplace_provider_registry
    ),
    refresh_queue: ProductRefreshQueue = Depends(get_product_refresh_queue),
    analytics_repository: AnalyticsRepository = Depends(get_analytics_repository),
) -> ProductService:
    repository = ProductRepository(db)
    return ProductService(
        repository,
        provider_registry,
        _product_cache,
        refresh_queue,
        cache_ttl_minutes=settings.shopee_cache_ttl_minutes,
        analytics_repository=analytics_repository,
    )


def get_shopee_product_service(
    product_service: ProductService = Depends(get_product_service),
) -> ShopeeProductService:
    return ShopeeProductService(product_service=product_service)


def get_caption_service(
    db: Session = Depends(get_db_session),
    analytics_repository: AnalyticsRepository = Depends(get_analytics_repository),
) -> CaptionService:
    product_repository = ProductRepository(db)
    caption_repository = CaptionRepository(db)
    engine = AICaptionEngine()
    return CaptionService(
        product_repository, caption_repository, engine, analytics_repository
    )


def get_ai_content_service(
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dependency),
    analytics_repository: AnalyticsRepository = Depends(get_analytics_repository),
) -> AIContentService:
    product_repository = ProductRepository(db)
    ai_repository = AIContentRepository(db)
    return AIContentService(
        product_repository,
        ai_repository,
        _ai_provider_factory,
        settings,
        _ai_template_cache,
        analytics_repository,
    )


def get_image_service(
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dependency),
    analytics_repository: AnalyticsRepository = Depends(get_analytics_repository),
) -> ImageService:
    product_repository = ProductRepository(db)
    image_repository = ImageRepository(db)
    generator = ImageGeneratorEngine(
        output_dir=settings.image_output_dir,
        timeout_seconds=settings.image_request_timeout_seconds,
    )
    return ImageService(
        product_repository, image_repository, generator, analytics_repository
    )


def get_scheduler_service(
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dependency),
    analytics_repository: AnalyticsRepository = Depends(get_analytics_repository),
) -> SchedulerService:
    scheduler_repository = SchedulerRepository(db)

    publisher: PostPublisherProtocol
    if settings.scheduler_publisher_mode.lower() == "webhook":
        if not settings.scheduler_webhook_url:
            raise AppException(
                status_code=500,
                detail="Scheduler webhook URL is required when publisher mode is webhook",
            )
        publisher = WebhookPostPublisher(
            webhook_url=settings.scheduler_webhook_url,
            timeout_seconds=settings.scheduler_webhook_timeout_seconds,
        )
    else:
        publisher = AuditPostPublisher()

    return SchedulerService(scheduler_repository, publisher, analytics_repository)


def get_dashboard_service(db: Session = Depends(get_db_session)) -> DashboardService:
    repository = DashboardRepository(db)
    return DashboardService(repository)


def get_analytics_service(
    analytics_repository: AnalyticsRepository = Depends(get_analytics_repository),
) -> AnalyticsService:
    return AnalyticsService(analytics_repository)


def get_current_user_id(
    token: str = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings_dependency),
) -> int:
    subject = decode_access_token(token=token, settings=settings)
    if not subject:
        raise AppException(status_code=401, detail="Invalid or expired token")

    try:
        return int(subject)
    except ValueError as exc:
        raise AppException(status_code=401, detail="Invalid token subject") from exc
