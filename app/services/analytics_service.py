from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import AnalyticsEventRead, AnalyticsEventsResponse, AnalyticsOverviewResponse


class AnalyticsService:
    def __init__(self, repository: AnalyticsRepository) -> None:
        self._repository = repository

    def overview(self, *, days: int) -> AnalyticsOverviewResponse:
        totals = self._repository.totals(days=days)
        daily = self._repository.daily_counts(days=days)
        return AnalyticsOverviewResponse(totals=totals, daily=daily)

    def events(self, *, limit: int) -> AnalyticsEventsResponse:
        events = self._repository.recent_events(limit=limit)
        return AnalyticsEventsResponse(
            items=[
                AnalyticsEventRead(
                    id=event.id,
                    event_type=event.event_type,
                    entity_type=event.entity_type,
                    entity_id=event.entity_id,
                    metadata=event.event_metadata,
                    occurred_at=event.occurred_at,
                )
                for event in events
            ]
        )
