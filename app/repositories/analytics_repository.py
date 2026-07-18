from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.analytics_event import AnalyticsEvent


class AnalyticsRepositoryProtocol(Protocol):
    def record_event(
        self,
        *,
        event_type: str,
        entity_type: str,
        entity_id: int | None,
        metadata: dict[str, str | int | float | bool | None] | None = None,
    ) -> AnalyticsEvent: ...


class AnalyticsRepository(AnalyticsRepositoryProtocol):
    def __init__(self, db: Session) -> None:
        self._db = db

    def record_event(
        self,
        *,
        event_type: str,
        entity_type: str,
        entity_id: int | None,
        metadata: dict[str, str | int | float | bool | None] | None = None,
    ) -> AnalyticsEvent:
        event = AnalyticsEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            event_metadata=metadata or {},
        )
        self._db.add(event)
        self._db.commit()
        self._db.refresh(event)
        return event

    def totals(self, *, days: int) -> dict[str, int]:
        since = datetime.now(UTC) - timedelta(days=days)
        stmt = (
            select(AnalyticsEvent.event_type, func.count(AnalyticsEvent.id))
            .where(AnalyticsEvent.occurred_at >= since)
            .group_by(AnalyticsEvent.event_type)
        )
        rows = list(self._db.execute(stmt).all())
        return {event_type: int(count) for event_type, count in rows}

    def daily_counts(self, *, days: int) -> list[dict[str, int | str]]:
        since = datetime.now(UTC) - timedelta(days=days)
        date_col = func.date(AnalyticsEvent.occurred_at)
        stmt = (
            select(date_col.label("day"), func.count(AnalyticsEvent.id).label("count"))
            .where(AnalyticsEvent.occurred_at >= since)
            .group_by(date_col)
            .order_by(date_col.asc())
        )
        rows = list(self._db.execute(stmt).all())
        return [{"day": str(day), "count": int(count)} for day, count in rows]

    def recent_events(self, *, limit: int) -> list[AnalyticsEvent]:
        stmt = (
            select(AnalyticsEvent)
            .order_by(AnalyticsEvent.occurred_at.desc())
            .limit(limit)
        )
        return list(self._db.scalars(stmt))
