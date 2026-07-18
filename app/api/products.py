from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import (
    get_current_user_id,
    get_product_service,
    get_shopee_product_service,
)
from app.schemas.product import (
    ProductImportRequest,
    ProductListResponse,
    ProductRead,
    ProductUpdateRequest,
)
from app.services.product_service import ProductService
from app.services.shopee_product_service import ShopeeProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.post(
    "/shopee",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK,
    summary="Parse Shopee product (legacy endpoint)",
)
def parse_shopee_product(
    payload: ProductImportRequest,
    _: int = Depends(get_current_user_id),
    service: ShopeeProductService = Depends(get_shopee_product_service),
) -> ProductRead:
    product = service.get_product(str(payload.url))
    return ProductRead.model_validate(product)


@router.post(
    "/import",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Import product from marketplace URL",
)
def import_product(
    payload: ProductImportRequest,
    _: int = Depends(get_current_user_id),
    service: ProductService = Depends(get_product_service),
) -> ProductRead:
    item = service.import_product(source_url=str(payload.url))
    return ProductRead.model_validate(item)


@router.get(
    "",
    response_model=ProductListResponse,
    status_code=status.HTTP_200_OK,
    summary="List products",
)
def list_products(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, min_length=1, max_length=255),
    marketplace: str | None = Query(default=None, min_length=1, max_length=32),
    _: int = Depends(get_current_user_id),
    service: ProductService = Depends(get_product_service),
) -> ProductListResponse:
    return service.list_products(
        limit=limit,
        offset=offset,
        search=search,
        marketplace=marketplace,
    )


@router.get(
    "/{product_id}",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK,
    summary="Get product",
)
def get_product(
    product_id: int,
    _: int = Depends(get_current_user_id),
    service: ProductService = Depends(get_product_service),
) -> ProductRead:
    item = service.get_product(product_id=product_id)
    return ProductRead.model_validate(item)


@router.patch(
    "/{product_id}",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK,
    summary="Update product",
)
def update_product(
    product_id: int,
    payload: ProductUpdateRequest,
    _: int = Depends(get_current_user_id),
    service: ProductService = Depends(get_product_service),
) -> ProductRead:
    item = service.update_product(product_id=product_id, payload=payload)
    return ProductRead.model_validate(item)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete product",
)
def delete_product(
    product_id: int,
    _: int = Depends(get_current_user_id),
    service: ProductService = Depends(get_product_service),
) -> Response:
    service.delete_product(product_id=product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{product_id}/refresh",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK,
    summary="Refresh product from provider",
)
def refresh_product(
    product_id: int,
    background: bool = Query(default=False),
    current_user_id: int = Depends(get_current_user_id),
    service: ProductService = Depends(get_product_service),
) -> ProductRead:
    item = service.refresh_product(
        product_id=product_id,
        requested_by_user_id=current_user_id,
        background=background,
    )
    return ProductRead.model_validate(item)
