from __future__ import annotations

from datetime import UTC, datetime

from app.services.publishing_service import PublishingService


class QueueWorker:
    def __init__(self, service: PublishingService) -> None:
        self._service = service

    def run_once(self, *, worker_id: str, limit: int = 20) -> tuple[int, int, int]:
        return self._service.process_queue(worker_id=worker_id, limit=limit)


class RetryWorker:
    def __init__(self, service: PublishingService) -> None:
        self._service = service

    def run_once(self, *, worker_id: str, limit: int = 20) -> tuple[int, int, int]:
        return self._service.process_retry(worker_id=worker_id, limit=limit)


class AnalyticsSyncWorker:
    def __init__(self, service: PublishingService) -> None:
        self._service = service

    def run_once(self, *, owner_user_id: int, limit: int = 100) -> int:
        return self._service.sync_analytics(owner_user_id=owner_user_id, limit=limit)


class DeadLetterQueueWorker:
    def __init__(self, service: PublishingService) -> None:
        self._service = service

    def run_once(self, *, limit: int = 100) -> int:
        return self._service.process_dead_letter(limit=limit)


class CleanupWorker:
    def __init__(self, service: PublishingService) -> None:
        self._service = service

    def run_once(self, *, now: datetime | None = None) -> int:
        return self._service.cleanup_expired(now=now or datetime.now(UTC))
