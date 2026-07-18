from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_current_user_id, get_image_service
from app.schemas.image import (
    ImageTemplate,
    PromotionalImageGenerateRequest,
    PromotionalImageRead,
)
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
