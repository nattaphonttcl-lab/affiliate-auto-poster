from datetime import datetime

from pydantic import BaseModel


class AnalyticsOverviewResponse(BaseModel):
    totals: dict[str, int]
    daily: list[dict[str, int | str]]


class AnalyticsEventRead(BaseModel):
    id: int
    event_type: str
    entity_type: str
    entity_id: int | None
    metadata: dict[str, str | int | float | bool | None]
    occurred_at: datetime


class AnalyticsEventsResponse(BaseModel):
    items: list[AnalyticsEventRead]
