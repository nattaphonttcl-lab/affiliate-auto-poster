from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_current_user_id, get_dashboard_service
from app.schemas.dashboard import DashboardActivityResponse, DashboardSummaryResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/summary", response_model=DashboardSummaryResponse, status_code=status.HTTP_200_OK
)
def dashboard_summary(
    _: int = Depends(get_current_user_id),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardSummaryResponse:
    return service.get_summary()


@router.get(
    "/activities",
    response_model=DashboardActivityResponse,
    status_code=status.HTTP_200_OK,
)
def dashboard_activities(
    limit: int = Query(default=20, ge=1, le=100),
    _: int = Depends(get_current_user_id),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardActivityResponse:
    return service.get_activity(limit=limit)
