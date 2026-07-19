from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import (
    get_current_user_id,
    get_image_engine_service,
    get_image_service,
)
from app.schemas.image_engine import (
    ImageGenerateRequest,
    ImageGenerateResponse,
    ImageHistoryResponse,
    ImagePreviewRequest,
    ImagePreviewResponse,
    ImageRegenerateRequest,
    ImageTemplateCreateRequest,
    ImageTemplateRead,
    ImageTemplateStatus,
    ImageTemplateUpdateRequest,
    ImageType,
)
from app.schemas.image import (
    ImageTemplate,
    PromotionalImageGenerateRequest,
    PromotionalImageRead,
)
from app.services.image_engine_service import ImageEngineService
from app.services.image_service import ImageService

router = APIRouter(prefix="/images", tags=["images"])


@router.post(
    "/promotional", response_model=PromotionalImageRead, status_code=status.HTTP_200_OK
)
def generate_promotional_image(
    payload: PromotionalImageGenerateRequest,
    _: int = Depends(get_current_user_id),
    service: ImageService = Depends(get_image_service),
) -> PromotionalImageRead:
    created = service.generate_promotional_image(
        product_id=payload.product_id,
        template=payload.template,
        shop_logo_url=(
            str(payload.shop_logo_url) if payload.shop_logo_url is not None else None
        ),
    )

    return PromotionalImageRead(
        id=created.id,
        product_id=created.product_id,
        template=ImageTemplate(created.template_name),
        output_format=created.output_format,
        width=created.width,
        height=created.height,
        image_path=created.image_path,
        product_image_url=created.product_image_url,
        shop_logo_url=created.shop_logo_url,
        created_at=created.created_at,
    )


@router.post(
    "/generate",
    response_model=ImageGenerateResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_image(
    payload: ImageGenerateRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: ImageEngineService = Depends(get_image_engine_service),
) -> ImageGenerateResponse:
    return await service.generate(payload=payload, owner_user_id=current_user_id)


@router.post(
    "/regenerate",
    response_model=ImageGenerateResponse,
    status_code=status.HTTP_200_OK,
)
async def regenerate_image(
    payload: ImageRegenerateRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: ImageEngineService = Depends(get_image_engine_service),
) -> ImageGenerateResponse:
    return await service.regenerate(
        generated_image_id=payload.generated_image_id,
        provider=payload.provider.value if payload.provider is not None else None,
        model=payload.model,
        owner_user_id=current_user_id,
    )


@router.get(
    "/history",
    response_model=ImageHistoryResponse,
    status_code=status.HTTP_200_OK,
)
def list_image_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user_id: int = Depends(get_current_user_id),
    service: ImageEngineService = Depends(get_image_engine_service),
) -> ImageHistoryResponse:
    return service.history(owner_user_id=current_user_id, limit=limit, offset=offset)


@router.get(
    "/templates",
    response_model=list[ImageTemplateRead],
    status_code=status.HTTP_200_OK,
)
def list_templates(
    image_type: ImageType | None = Query(default=None),
    template_status: ImageTemplateStatus | None = Query(default=None, alias="status"),
    _: int = Depends(get_current_user_id),
    service: ImageEngineService = Depends(get_image_engine_service),
) -> list[ImageTemplateRead]:
    return service.list_templates(image_type=image_type, status=template_status)


@router.post(
    "/templates",
    response_model=ImageTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
def create_template(
    payload: ImageTemplateCreateRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: ImageEngineService = Depends(get_image_engine_service),
) -> ImageTemplateRead:
    return service.create_template(payload=payload, created_by=current_user_id)


@router.patch(
    "/templates/{template_id}",
    response_model=ImageTemplateRead,
    status_code=status.HTTP_200_OK,
)
def update_template(
    template_id: int,
    payload: ImageTemplateUpdateRequest,
    _: int = Depends(get_current_user_id),
    service: ImageEngineService = Depends(get_image_engine_service),
) -> ImageTemplateRead:
    return service.update_template(template_id=template_id, payload=payload)


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_template(
    template_id: int,
    _: int = Depends(get_current_user_id),
    service: ImageEngineService = Depends(get_image_engine_service),
) -> Response:
    service.delete_template(template_id=template_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/preview",
    response_model=ImagePreviewResponse,
    status_code=status.HTTP_200_OK,
)
async def preview_image(
    payload: ImagePreviewRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: ImageEngineService = Depends(get_image_engine_service),
) -> ImagePreviewResponse:
    return await service.preview(payload=payload, owner_user_id=current_user_id)
