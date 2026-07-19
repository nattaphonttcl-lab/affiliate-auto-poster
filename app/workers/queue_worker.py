from __future__ import annotations

from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.repositories.ai_content_repository import AIContentRepository
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.image_engine_repository import ImageEngineRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.publishing_repository import PublishingRepository
from app.services.publishing_service import PublishingService
from app.services.publishing_workers import QueueWorker
from app.services.social_providers import ProviderFactory, ProviderRegistry
from app.workers.runtime import get_runtime_settings, run_forever


def _run_once() -> None:
    settings = get_runtime_settings()
    with SessionLocal() as db:
        service = PublishingService(
            product_repository=ProductRepository(db),
            ai_repository=AIContentRepository(db),
            image_repository=ImageEngineRepository(db),
            repository=PublishingRepository(db),
            provider_registry=ProviderRegistry(factory=ProviderFactory()),
            settings=settings,
            analytics_repository=AnalyticsRepository(db),
        )
        worker = QueueWorker(service)
        worker.run_once(worker_id="queue-worker")


def main() -> None:
    settings = get_runtime_settings()
    configure_logging(settings.log_level, json_logs=settings.log_json)
    run_forever("queue-worker", _run_once, settings)


if __name__ == "__main__":
    main()
