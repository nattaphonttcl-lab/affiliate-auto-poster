from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_current_user_id, get_scheduler_service
from app.schemas.scheduler import (
    ScheduledPostCreateRequest,
    ScheduledPostRead,
    ScheduledPostStatus,
    SchedulePlatform,
    SchedulerRunResponse,
)
from app.services.scheduler_service import SchedulerService

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.post("/posts", response_model=ScheduledPostRead, status_code=status.HTTP_201_CREATED)
def create_scheduled_post(
    payload: ScheduledPostCreateRequest,
    _: int = Depends(get_current_user_id),
    service: SchedulerService = Depends(get_scheduler_service),
) -> ScheduledPostRead:
    created = service.schedule_post(
        product_id=payload.product_id,
        caption_batch_id=payload.caption_batch_id,
        promotional_image_id=payload.promotional_image_id,
        platform=payload.platform.value,
        target=payload.target,
        scheduled_for=payload.scheduled_for,
    )

    return ScheduledPostRead(
        id=created.id,
        product_id=created.product_id,
        caption_batch_id=created.caption_batch_id,
        promotional_image_id=created.promotional_image_id,
        platform=SchedulePlatform(created.platform),
        target=created.target,
        scheduled_for=created.scheduled_for,
        status=ScheduledPostStatus(created.status),
        published_at=created.published_at,
        error_message=created.error_message,
        created_at=created.created_at,
        updated_at=created.updated_at,
    )


@router.post("/run", response_model=SchedulerRunResponse, status_code=status.HTTP_200_OK)
def run_scheduler(
    _: int = Depends(get_current_user_id),
    service: SchedulerService = Depends(get_scheduler_service),
) -> SchedulerRunResponse:
    processed, published, failed = service.run_due()
    return SchedulerRunResponse(processed=processed, published=published, failed=failed)


@router.get("/posts", response_model=list[ScheduledPostRead], status_code=status.HTTP_200_OK)
def list_recent_scheduled_posts(
    _: int = Depends(get_current_user_id),
    service: SchedulerService = Depends(get_scheduler_service),
) -> list[ScheduledPostRead]:
    rows = service.list_recent(limit=20)
    return [
        ScheduledPostRead(
            id=item.id,
            product_id=item.product_id,
            caption_batch_id=item.caption_batch_id,
            promotional_image_id=item.promotional_image_id,
            platform=SchedulePlatform(item.platform),
            target=item.target,
            scheduled_for=item.scheduled_for,
            status=ScheduledPostStatus(item.status),
            published_at=item.published_at,
            error_message=item.error_message,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in rows
    ]
