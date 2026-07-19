from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_current_user_id, get_publishing_service
from app.schemas.publishing import (
    PublishActionResponse,
    PublishCancelRequest,
    PublishingHistoryResponse,
    PublishingJobsResponse,
    PublishRequest,
    PublishRetryRequest,
    PublishScheduleRequest,
    SocialAccountCreateRequest,
    SocialAccountRead,
    SocialAccountUpdateRequest,
)
from app.services.publishing_service import PublishingService

router = APIRouter(prefix="/publish", tags=["publishing"])


@router.post("", response_model=PublishActionResponse, status_code=status.HTTP_200_OK)
def publish_now(
    payload: PublishRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: PublishingService = Depends(get_publishing_service),
) -> PublishActionResponse:
    return service.publish_now(owner_user_id=current_user_id, payload=payload)


@router.post(
    "/schedule",
    response_model=PublishActionResponse,
    status_code=status.HTTP_200_OK,
)
def schedule_publish(
    payload: PublishScheduleRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: PublishingService = Depends(get_publishing_service),
) -> PublishActionResponse:
    return service.schedule_publish(owner_user_id=current_user_id, payload=payload)


@router.post(
    "/retry",
    response_model=PublishActionResponse,
    status_code=status.HTTP_200_OK,
)
def retry_publish(
    payload: PublishRetryRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: PublishingService = Depends(get_publishing_service),
) -> PublishActionResponse:
    return service.retry_publish(owner_user_id=current_user_id, payload=payload)


@router.post(
    "/cancel",
    response_model=PublishActionResponse,
    status_code=status.HTTP_200_OK,
)
def cancel_publish(
    payload: PublishCancelRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: PublishingService = Depends(get_publishing_service),
) -> PublishActionResponse:
    return service.cancel_publish(owner_user_id=current_user_id, payload=payload)


@router.get(
    "/jobs", response_model=PublishingJobsResponse, status_code=status.HTTP_200_OK
)
def list_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user_id: int = Depends(get_current_user_id),
    service: PublishingService = Depends(get_publishing_service),
) -> PublishingJobsResponse:
    return service.list_jobs(owner_user_id=current_user_id, limit=limit, offset=offset)


@router.get(
    "/history",
    response_model=PublishingHistoryResponse,
    status_code=status.HTTP_200_OK,
)
def list_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user_id: int = Depends(get_current_user_id),
    service: PublishingService = Depends(get_publishing_service),
) -> PublishingHistoryResponse:
    return service.list_history(
        owner_user_id=current_user_id, limit=limit, offset=offset
    )


social_router = APIRouter(prefix="/social/accounts", tags=["social-accounts"])


@social_router.get(
    "", response_model=list[SocialAccountRead], status_code=status.HTTP_200_OK
)
def list_social_accounts(
    current_user_id: int = Depends(get_current_user_id),
    service: PublishingService = Depends(get_publishing_service),
) -> list[SocialAccountRead]:
    return service.list_social_accounts(owner_user_id=current_user_id)


@social_router.post(
    "", response_model=SocialAccountRead, status_code=status.HTTP_201_CREATED
)
def create_social_account(
    payload: SocialAccountCreateRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: PublishingService = Depends(get_publishing_service),
) -> SocialAccountRead:
    return service.create_social_account(owner_user_id=current_user_id, payload=payload)


@social_router.patch("/{social_account_id}", response_model=SocialAccountRead)
def update_social_account(
    social_account_id: int,
    payload: SocialAccountUpdateRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: PublishingService = Depends(get_publishing_service),
) -> SocialAccountRead:
    return service.update_social_account(
        owner_user_id=current_user_id,
        social_account_id=social_account_id,
        payload=payload,
    )


@social_router.delete("/{social_account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_social_account(
    social_account_id: int,
    current_user_id: int = Depends(get_current_user_id),
    service: PublishingService = Depends(get_publishing_service),
) -> Response:
    service.delete_social_account(
        owner_user_id=current_user_id,
        social_account_id=social_account_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
