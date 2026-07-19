from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_ai_content_service, get_current_user_id
from app.schemas.ai_content import (
    AIContentGenerateRequest,
    AIContentGenerateResponse,
    AIContentRegenerateRequest,
    AIHistoryResponse,
    PromptCategory,
    PromptTemplateCreateRequest,
    PromptTemplateRead,
    PromptTemplateStatus,
    PromptTemplateUpdateRequest,
)
from app.services.ai_content_service import AIContentService

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post(
    "/generate",
    response_model=AIContentGenerateResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_content(
    payload: AIContentGenerateRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: AIContentService = Depends(get_ai_content_service),
) -> AIContentGenerateResponse:
    return await service.generate(payload=payload, created_by=current_user_id)


@router.post(
    "/regenerate",
    response_model=AIContentGenerateResponse,
    status_code=status.HTTP_200_OK,
)
async def regenerate_content(
    payload: AIContentRegenerateRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: AIContentService = Depends(get_ai_content_service),
) -> AIContentGenerateResponse:
    return await service.regenerate(payload=payload, created_by=current_user_id)


@router.get(
    "/history",
    response_model=AIHistoryResponse,
    status_code=status.HTTP_200_OK,
)
def list_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    product_id: int | None = Query(default=None, ge=1),
    _: int = Depends(get_current_user_id),
    service: AIContentService = Depends(get_ai_content_service),
) -> AIHistoryResponse:
    return service.history(limit=limit, offset=offset, product_id=product_id)


@router.get(
    "/templates",
    response_model=list[PromptTemplateRead],
    status_code=status.HTTP_200_OK,
)
def list_templates(
    category: PromptCategory | None = Query(default=None),
    template_status: PromptTemplateStatus | None = Query(default=None, alias="status"),
    _: int = Depends(get_current_user_id),
    service: AIContentService = Depends(get_ai_content_service),
) -> list[PromptTemplateRead]:
    return service.list_templates(category=category, status=template_status)


@router.post(
    "/templates",
    response_model=PromptTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
def create_template(
    payload: PromptTemplateCreateRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: AIContentService = Depends(get_ai_content_service),
) -> PromptTemplateRead:
    return service.create_template(payload=payload, created_by=current_user_id)


@router.patch(
    "/templates/{template_id}",
    response_model=PromptTemplateRead,
    status_code=status.HTTP_200_OK,
)
def update_template(
    template_id: int,
    payload: PromptTemplateUpdateRequest,
    _: int = Depends(get_current_user_id),
    service: AIContentService = Depends(get_ai_content_service),
) -> PromptTemplateRead:
    return service.update_template(template_id=template_id, payload=payload)


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_template(
    template_id: int,
    _: int = Depends(get_current_user_id),
    service: AIContentService = Depends(get_ai_content_service),
) -> Response:
    service.delete_template(template_id=template_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
