from datetime import UTC, datetime

from app.core.exceptions import AppException
from app.models.scheduled_post import ScheduledPost
from app.repositories.analytics_repository import AnalyticsRepositoryProtocol
from app.repositories.scheduler_repository import SchedulerRepositoryProtocol
from app.schemas.scheduler import ScheduledPostStatus
from app.utils.post_publisher import PostPublisherProtocol


class SchedulerService:
    def __init__(
        self,
        scheduler_repository: SchedulerRepositoryProtocol,
        publisher: PostPublisherProtocol,
        analytics_repository: AnalyticsRepositoryProtocol | None = None,
    ) -> None:
        self._scheduler_repository = scheduler_repository
        self._publisher = publisher
        self._analytics_repository = analytics_repository

    def schedule_post(
        self,
        *,
        product_id: int,
        caption_batch_id: int | None,
        promotional_image_id: int | None,
        platform: str,
        target: str,
        scheduled_for: datetime,
    ) -> ScheduledPost:
        now = datetime.now(UTC)
        if scheduled_for < now:
            raise AppException(status_code=422, detail="Scheduled time must be in the future")

        created = self._scheduler_repository.create(
            product_id=product_id,
            caption_batch_id=caption_batch_id,
            promotional_image_id=promotional_image_id,
            platform=platform,
            target=target,
            scheduled_for=scheduled_for,
        )

        if self._analytics_repository is not None:
            self._analytics_repository.record_event(
                event_type="scheduled_post_created",
                entity_type="scheduled_post",
                entity_id=created.id,
                metadata={"product_id": product_id, "platform": platform, "target": target},
            )

        return created

    def run_due(self) -> tuple[int, int, int]:
        now = datetime.now(UTC)
        due_posts = self._scheduler_repository.list_due_pending(now)

        published = 0
        failed = 0

        for scheduled_post in due_posts:
            self._scheduler_repository.update_status(
                scheduled_post=scheduled_post,
                status=ScheduledPostStatus.PROCESSING.value,
            )

            try:
                message = self._publisher.publish(scheduled_post)
                self._scheduler_repository.update_status(
                    scheduled_post=scheduled_post,
                    status=ScheduledPostStatus.PUBLISHED.value,
                    published_at=datetime.now(UTC),
                    error_message=None,
                )
                self._scheduler_repository.create_execution(
                    scheduled_post_id=scheduled_post.id,
                    status=ScheduledPostStatus.PUBLISHED.value,
                    message=message,
                )
                if self._analytics_repository is not None:
                    self._analytics_repository.record_event(
                        event_type="scheduled_post_published",
                        entity_type="scheduled_post",
                        entity_id=scheduled_post.id,
                        metadata={"target": scheduled_post.target},
                    )
                published += 1
            except Exception as exc:
                self._scheduler_repository.update_status(
                    scheduled_post=scheduled_post,
                    status=ScheduledPostStatus.FAILED.value,
                    error_message=str(exc),
                )
                self._scheduler_repository.create_execution(
                    scheduled_post_id=scheduled_post.id,
                    status=ScheduledPostStatus.FAILED.value,
                    message=str(exc),
                )
                if self._analytics_repository is not None:
                    self._analytics_repository.record_event(
                        event_type="scheduled_post_failed",
                        entity_type="scheduled_post",
                        entity_id=scheduled_post.id,
                        metadata={"error": str(exc)},
                    )
                failed += 1

        return len(due_posts), published, failed

    def list_recent(self, limit: int = 20):
        return self._scheduler_repository.list_recent(limit)
