from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_current_user_id, get_scheduler_service
from app.schemas.scheduler import (
    ScheduledPostCreateRequest,
    ScheduledPostRead,
    ScheduledPostState,
    SchedulePlatform,
    SchedulerRunResponse,
)
from app.services.scheduler_service import SchedulerService

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


def _to_scheduled_post_read(item) -> ScheduledPostRead:
    return ScheduledPostRead(
        id=item.id,
        version=item.version,
        owner_user_id=item.owner_user_id,
        product_id=item.product_id,
        caption_batch_id=item.caption_batch_id,
        promotional_image_id=item.promotional_image_id,
        platform=SchedulePlatform(item.platform),
        target=item.target,
        scheduled_for=item.scheduled_for,
        state=ScheduledPostState(item.state),
        published_at=item.published_at,
        error_message=item.error_message,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post(
    "/posts",
    response_model=ScheduledPostRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create scheduled post",
    description="Create a scheduled publish job in awaiting_confirmation state. Owner confirmation is required before execution.",
)
def create_scheduled_post(
    payload: ScheduledPostCreateRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: SchedulerService = Depends(get_scheduler_service),
) -> ScheduledPostRead:
    created = service.schedule_post(
        owner_user_id=current_user_id,
        product_id=payload.product_id,
        caption_batch_id=payload.caption_batch_id,
        promotional_image_id=payload.promotional_image_id,
        platform=payload.platform.value,
        target=payload.target,
        scheduled_for=payload.scheduled_for,
    )

    return _to_scheduled_post_read(created)


@router.post(
    "/run",
    response_model=SchedulerRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Run due scheduled jobs",
    description="Execute due jobs owned by the current user. Only confirmed jobs are eligible.",
)
def run_scheduler(
    current_user_id: int = Depends(get_current_user_id),
    service: SchedulerService = Depends(get_scheduler_service),
) -> SchedulerRunResponse:
    processed, published, failed = service.run_due(owner_user_id=current_user_id)
    return SchedulerRunResponse(processed=processed, published=published, failed=failed)


@router.post(
    "/posts/{scheduled_post_id}/confirm",
    response_model=ScheduledPostRead,
    status_code=status.HTTP_200_OK,
    summary="Confirm scheduled post",
    description="Idempotent owner-confirm action that transitions awaiting_confirmation to confirmed and creates an audit log entry.",
)
def confirm_scheduled_post(
    scheduled_post_id: int,
    current_user_id: int = Depends(get_current_user_id),
    service: SchedulerService = Depends(get_scheduler_service),
) -> ScheduledPostRead:
    item = service.confirm_post(
        scheduled_post_id=scheduled_post_id, actor_user_id=current_user_id
    )
    return _to_scheduled_post_read(item)


@router.get(
    "/posts",
    response_model=list[ScheduledPostRead],
    status_code=status.HTTP_200_OK,
    summary="List recent scheduled posts",
    description="List recent scheduled jobs owned by the current user.",
)
def list_recent_scheduled_posts(
    current_user_id: int = Depends(get_current_user_id),
    service: SchedulerService = Depends(get_scheduler_service),
) -> list[ScheduledPostRead]:
    rows = service.list_recent(owner_user_id=current_user_id, limit=20)
    return [_to_scheduled_post_read(item) for item in rows]
