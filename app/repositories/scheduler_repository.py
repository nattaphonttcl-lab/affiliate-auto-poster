from datetime import datetime
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.scheduled_post import ScheduledPost, ScheduledPostExecution
from app.schemas.scheduler import ScheduledPostStatus


class SchedulerRepositoryProtocol(Protocol):
    def create(
        self,
        *,
        product_id: int,
        caption_batch_id: int | None,
        promotional_image_id: int | None,
        platform: str,
        target: str,
        scheduled_for: datetime,
    ) -> ScheduledPost: ...

    def get_by_id(self, scheduled_post_id: int) -> ScheduledPost | None: ...

    def list_due_pending(self, now: datetime) -> list[ScheduledPost]: ...

    def list_recent(self, limit: int = 20) -> list[ScheduledPost]: ...

    def update_status(
        self,
        *,
        scheduled_post: ScheduledPost,
        status: str,
        error_message: str | None = None,
        published_at: datetime | None = None,
    ) -> ScheduledPost: ...

    def create_execution(self, *, scheduled_post_id: int, status: str, message: str) -> ScheduledPostExecution: ...

    def count_by_status(self) -> dict[str, int]: ...


class SchedulerRepository(SchedulerRepositoryProtocol):
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        product_id: int,
        caption_batch_id: int | None,
        promotional_image_id: int | None,
        platform: str,
        target: str,
        scheduled_for: datetime,
    ) -> ScheduledPost:
        scheduled_post = ScheduledPost(
            product_id=product_id,
            caption_batch_id=caption_batch_id,
            promotional_image_id=promotional_image_id,
            platform=platform,
            target=target,
            scheduled_for=scheduled_for,
            status=ScheduledPostStatus.PENDING.value,
        )
        self._db.add(scheduled_post)
        self._db.commit()
        self._db.refresh(scheduled_post)
        return scheduled_post

    def get_by_id(self, scheduled_post_id: int) -> ScheduledPost | None:
        return self._db.get(ScheduledPost, scheduled_post_id)

    def list_due_pending(self, now: datetime) -> list[ScheduledPost]:
        stmt = (
            select(ScheduledPost)
            .where(
                ScheduledPost.status == ScheduledPostStatus.PENDING.value,
                ScheduledPost.scheduled_for <= now,
            )
            .order_by(ScheduledPost.scheduled_for.asc())
        )
        return list(self._db.scalars(stmt))

    def list_recent(self, limit: int = 20) -> list[ScheduledPost]:
        stmt = select(ScheduledPost).order_by(ScheduledPost.created_at.desc()).limit(limit)
        return list(self._db.scalars(stmt))

    def update_status(
        self,
        *,
        scheduled_post: ScheduledPost,
        status: str,
        error_message: str | None = None,
        published_at: datetime | None = None,
    ) -> ScheduledPost:
        scheduled_post.status = status
        scheduled_post.error_message = error_message
        if published_at is not None:
            scheduled_post.published_at = published_at

        self._db.add(scheduled_post)
        self._db.commit()
        self._db.refresh(scheduled_post)
        return scheduled_post

    def create_execution(self, *, scheduled_post_id: int, status: str, message: str) -> ScheduledPostExecution:
        execution = ScheduledPostExecution(
            scheduled_post_id=scheduled_post_id,
            status=status,
            message=message,
        )
        self._db.add(execution)
        self._db.commit()
        self._db.refresh(execution)
        return execution

    def count_by_status(self) -> dict[str, int]:
        stmt = select(ScheduledPost.status, func.count(ScheduledPost.id)).group_by(ScheduledPost.status)
        rows = list(self._db.execute(stmt).all())
        return {status: count for status, count in rows}
