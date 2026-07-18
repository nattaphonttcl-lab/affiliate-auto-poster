from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_current_user_id, get_shopee_product_service
from app.schemas.product import ProductRead, ShopeeProductRequest
from app.services.shopee_product_service import ShopeeProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/shopee", response_model=ProductRead, status_code=status.HTTP_200_OK, summary="Parse Shopee product")
def parse_shopee_product(
    payload: ShopeeProductRequest,
    _: int = Depends(get_current_user_id),
    service: ShopeeProductService = Depends(get_shopee_product_service),
) -> ProductRead:
    product = service.get_product(str(payload.url))
    return ProductRead.model_validate(product)
