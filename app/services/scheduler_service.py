from datetime import UTC, datetime

from app.core.exceptions import AppException
from app.repositories.scheduler_repository import SchedulerRepositoryProtocol
from app.schemas.scheduler import ScheduledPostStatus
from app.utils.post_publisher import PostPublisherProtocol


class SchedulerService:
    def __init__(
        self,
        scheduler_repository: SchedulerRepositoryProtocol,
        publisher: PostPublisherProtocol,
    ) -> None:
        self._scheduler_repository = scheduler_repository
        self._publisher = publisher

    def schedule_post(
        self,
        *,
        product_id: int,
        caption_batch_id: int | None,
        promotional_image_id: int | None,
        platform: str,
        target: str,
        scheduled_for: datetime,
    ):
        now = datetime.now(UTC)
        if scheduled_for < now:
            raise AppException(status_code=422, detail="Scheduled time must be in the future")

        return self._scheduler_repository.create(
            product_id=product_id,
            caption_batch_id=caption_batch_id,
            promotional_image_id=promotional_image_id,
            platform=platform,
            target=target,
            scheduled_for=scheduled_for,
        )

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
                failed += 1

        return len(due_posts), published, failed

    def list_recent(self, limit: int = 20):
        return self._scheduler_repository.list_recent(limit)
