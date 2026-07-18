from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_caption_service, get_current_user_id
from app.schemas.caption import (
    CaptionGenerateRequest,
    CaptionGenerateResponse,
    CaptionItemRead,
    CaptionStyle,
)
from app.services.caption_service import CaptionService

router = APIRouter(prefix="/captions", tags=["captions"])


@router.post(
    "/generate", response_model=CaptionGenerateResponse, status_code=status.HTTP_200_OK
)
def generate_captions(
    payload: CaptionGenerateRequest,
    _: int = Depends(get_current_user_id),
    service: CaptionService = Depends(get_caption_service),
) -> CaptionGenerateResponse:
    batch, captions = service.generate_for_product(
        product_id=payload.product_id, style=payload.style
    )

    return CaptionGenerateResponse(
        batch_id=batch.id,
        product_id=batch.product_id,
        style=CaptionStyle(batch.style),
        generated_at=batch.created_at,
        captions=[
            CaptionItemRead(
                hook=caption.hook,
                cta=caption.cta,
                emoji=caption.emoji,
                hashtags=[tag for tag in caption.hashtags.split(" ") if tag],
                caption_text=caption.caption_text,
            )
            for caption in captions
        ],
    )
