from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_analytics_service, get_current_user_id
from app.schemas.analytics import AnalyticsEventsResponse, AnalyticsOverviewResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    status_code=status.HTTP_200_OK,
)
def analytics_overview(
    days: int = Query(default=30, ge=1, le=365),
    _: int = Depends(get_current_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsOverviewResponse:
    return service.overview(days=days)


@router.get(
    "/events", response_model=AnalyticsEventsResponse, status_code=status.HTTP_200_OK
)
def analytics_events(
    limit: int = Query(default=50, ge=1, le=200),
    _: int = Depends(get_current_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsEventsResponse:
    return service.events(limit=limit)
