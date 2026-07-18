from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class DomainEvent:
    aggregate_type: str
    aggregate_id: int
    event_type: str
    payload: dict[str, Any]
    occurred_at: datetime


class SchedulerEvents:
    AGGREGATE_TYPE = "scheduled_post"

    @staticmethod
    def scheduled_post_created(
        *,
        scheduled_post_id: int,
        owner_user_id: int,
        product_id: int,
        target: str,
        state: str,
    ) -> DomainEvent:
        return DomainEvent(
            aggregate_type=SchedulerEvents.AGGREGATE_TYPE,
            aggregate_id=scheduled_post_id,
            event_type="scheduled_post.created",
            payload={
                "owner_user_id": owner_user_id,
                "product_id": product_id,
                "target": target,
                "state": state,
            },
            occurred_at=datetime.now(UTC),
        )

    @staticmethod
    def scheduled_post_confirmed(
        *,
        scheduled_post_id: int,
        owner_user_id: int,
        from_state: str,
        to_state: str,
    ) -> DomainEvent:
        return DomainEvent(
            aggregate_type=SchedulerEvents.AGGREGATE_TYPE,
            aggregate_id=scheduled_post_id,
            event_type="scheduled_post.confirmed",
            payload={
                "owner_user_id": owner_user_id,
                "from_state": from_state,
                "to_state": to_state,
            },
            occurred_at=datetime.now(UTC),
        )

    @staticmethod
    def scheduled_post_published(
        *,
        scheduled_post_id: int,
        owner_user_id: int,
        target: str,
    ) -> DomainEvent:
        return DomainEvent(
            aggregate_type=SchedulerEvents.AGGREGATE_TYPE,
            aggregate_id=scheduled_post_id,
            event_type="scheduled_post.published",
            payload={
                "owner_user_id": owner_user_id,
                "target": target,
            },
            occurred_at=datetime.now(UTC),
        )

    @staticmethod
    def scheduled_post_failed(
        *,
        scheduled_post_id: int,
        owner_user_id: int,
        error: str,
    ) -> DomainEvent:
        return DomainEvent(
            aggregate_type=SchedulerEvents.AGGREGATE_TYPE,
            aggregate_id=scheduled_post_id,
            event_type="scheduled_post.failed",
            payload={
                "owner_user_id": owner_user_id,
                "error": error,
            },
            occurred_at=datetime.now(UTC),
        )
