from datetime import datetime
from typing import Protocol

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.domain_events import DomainEvent
from app.models.outbox_event import OutboxEvent
from app.models.scheduled_post import (
    ScheduledPost,
    ScheduledPostAudit,
    ScheduledPostExecution,
)
from app.schemas.scheduler import ScheduledPostState


class OptimisticLockError(Exception):
    pass


class SchedulerRepositoryProtocol(Protocol):
    def create(
        self,
        *,
        owner_user_id: int,
        product_id: int,
        caption_batch_id: int | None,
        promotional_image_id: int | None,
        platform: str,
        target: str,
        scheduled_for: datetime,
    ) -> ScheduledPost: ...

    def get_by_id(self, scheduled_post_id: int) -> ScheduledPost | None: ...

    def list_recent_for_owner(
        self, *, owner_user_id: int, limit: int = 20
    ) -> list[ScheduledPost]: ...

    def claim_due_confirmed(
        self, *, owner_user_id: int, now: datetime, limit: int = 50
    ) -> list[ScheduledPost]: ...

    def update_status(
        self,
        *,
        scheduled_post_id: int,
        expected_version: int,
        state: str,
        from_state: str | None = None,
        error_message: str | None = None,
        published_at: datetime | None = None,
    ) -> ScheduledPost: ...

    def create_execution(
        self, *, scheduled_post_id: int, status: str, message: str
    ) -> ScheduledPostExecution: ...

    def confirm_if_awaiting(
        self, *, scheduled_post_id: int, expected_version: int
    ) -> ScheduledPost: ...

    def enqueue_domain_event(self, *, event: DomainEvent) -> OutboxEvent: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def create_audit(
        self,
        *,
        scheduled_post_id: int,
        actor_user_id: int,
        action: str,
        from_state: str,
        to_state: str,
        message: str,
    ) -> ScheduledPostAudit: ...

    def count_by_status(self) -> dict[str, int]: ...


class SchedulerRepository(SchedulerRepositoryProtocol):
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        owner_user_id: int,
        product_id: int,
        caption_batch_id: int | None,
        promotional_image_id: int | None,
        platform: str,
        target: str,
        scheduled_for: datetime,
    ) -> ScheduledPost:
        scheduled_post = ScheduledPost(
            owner_user_id=owner_user_id,
            product_id=product_id,
            caption_batch_id=caption_batch_id,
            promotional_image_id=promotional_image_id,
            platform=platform,
            target=target,
            scheduled_for=scheduled_for,
            state=ScheduledPostState.AWAITING_CONFIRMATION.value,
        )
        self._db.add(scheduled_post)
        self._db.flush()
        self._db.refresh(scheduled_post)
        return scheduled_post

    def get_by_id(self, scheduled_post_id: int) -> ScheduledPost | None:
        return self._db.get(ScheduledPost, scheduled_post_id)

    def list_recent_for_owner(
        self, *, owner_user_id: int, limit: int = 20
    ) -> list[ScheduledPost]:
        stmt = (
            select(ScheduledPost)
            .where(ScheduledPost.owner_user_id == owner_user_id)
            .order_by(ScheduledPost.created_at.desc())
            .limit(limit)
        )
        return list(self._db.scalars(stmt))

    def claim_due_confirmed(
        self, *, owner_user_id: int, now: datetime, limit: int = 50
    ) -> list[ScheduledPost]:
        stmt = (
            select(ScheduledPost.id, ScheduledPost.version)
            .where(
                ScheduledPost.owner_user_id == owner_user_id,
                ScheduledPost.state == ScheduledPostState.CONFIRMED.value,
                ScheduledPost.scheduled_for <= now,
            )
            .order_by(ScheduledPost.scheduled_for.asc())
            .limit(limit)
        )
        candidates = list(self._db.execute(stmt).all())

        claimed_ids: list[int] = []
        for candidate_id, candidate_version in candidates:
            claim_stmt = (
                update(ScheduledPost)
                .where(
                    ScheduledPost.id == candidate_id,
                    ScheduledPost.version == candidate_version,
                    ScheduledPost.state == ScheduledPostState.CONFIRMED.value,
                )
                .values(
                    state=ScheduledPostState.PROCESSING.value,
                    version=ScheduledPost.version + 1,
                )
            )
            result = self._db.execute(claim_stmt)
            if result.rowcount == 1:
                claimed_ids.append(candidate_id)

        if not claimed_ids:
            return []

        self._db.flush()
        fetch_stmt = (
            select(ScheduledPost)
            .where(ScheduledPost.id.in_(claimed_ids))
            .order_by(ScheduledPost.scheduled_for.asc())
        )
        return list(self._db.scalars(fetch_stmt))

    def update_status(
        self,
        *,
        scheduled_post_id: int,
        expected_version: int,
        state: str,
        from_state: str | None = None,
        error_message: str | None = None,
        published_at: datetime | None = None,
    ) -> ScheduledPost:
        values: dict[str, object | None] = {
            "state": state,
            "version": expected_version + 1,
            "error_message": error_message,
        }
        if published_at is not None:
            values["published_at"] = published_at

        stmt = update(ScheduledPost).where(
            ScheduledPost.id == scheduled_post_id,
            ScheduledPost.version == expected_version,
        )
        if from_state is not None:
            stmt = stmt.where(ScheduledPost.state == from_state)
        stmt = stmt.values(**values)

        result = self._db.execute(stmt)
        if result.rowcount != 1:
            raise OptimisticLockError(
                f"Optimistic lock failed for scheduled_post_id={scheduled_post_id} version={expected_version}"
            )

        self._db.flush()
        scheduled_post = self._db.get(ScheduledPost, scheduled_post_id)
        if scheduled_post is None:
            raise OptimisticLockError(
                f"Scheduled post disappeared during optimistic update: {scheduled_post_id}"
            )
        return scheduled_post

    def create_execution(
        self, *, scheduled_post_id: int, status: str, message: str
    ) -> ScheduledPostExecution:
        execution = ScheduledPostExecution(
            scheduled_post_id=scheduled_post_id,
            status=status,
            message=message,
        )
        self._db.add(execution)
        self._db.flush()
        self._db.refresh(execution)
        return execution

    def confirm_if_awaiting(
        self, *, scheduled_post_id: int, expected_version: int
    ) -> ScheduledPost:
        return self.update_status(
            scheduled_post_id=scheduled_post_id,
            expected_version=expected_version,
            from_state=ScheduledPostState.AWAITING_CONFIRMATION.value,
            state=ScheduledPostState.CONFIRMED.value,
        )

    def create_audit(
        self,
        *,
        scheduled_post_id: int,
        actor_user_id: int,
        action: str,
        from_state: str,
        to_state: str,
        message: str,
    ) -> ScheduledPostAudit:
        audit = ScheduledPostAudit(
            scheduled_post_id=scheduled_post_id,
            actor_user_id=actor_user_id,
            action=action,
            from_state=from_state,
            to_state=to_state,
            message=message,
        )
        self._db.add(audit)
        self._db.flush()
        self._db.refresh(audit)
        return audit

    def enqueue_domain_event(self, *, event: DomainEvent) -> OutboxEvent:
        outbox_event = OutboxEvent(
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            event_type=event.event_type,
            payload=event.payload,
            status="pending",
            attempts=0,
            occurred_at=event.occurred_at,
        )
        self._db.add(outbox_event)
        self._db.flush()
        self._db.refresh(outbox_event)
        return outbox_event

    def commit(self) -> None:
        self._db.commit()

    def rollback(self) -> None:
        self._db.rollback()

    def count_by_status(self) -> dict[str, int]:
        stmt = select(ScheduledPost.state, func.count(ScheduledPost.id)).group_by(
            ScheduledPost.state
        )
        rows = list(self._db.execute(stmt).all())
        return {state: count for state, count in rows}
