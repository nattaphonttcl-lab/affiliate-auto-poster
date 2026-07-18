from typing import Protocol

from sqlalchemy.orm import Session

from app.models.promotional_image import PromotionalImage


class ImageRepositoryProtocol(Protocol):
    def create(
        self,
        *,
        product_id: int,
        template_name: str,
        output_format: str,
        width: int,
        height: int,
        image_path: str,
        product_image_url: str,
        shop_logo_url: str | None,
    ) -> PromotionalImage: ...


class ImageRepository(ImageRepositoryProtocol):
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        product_id: int,
        template_name: str,
        output_format: str,
        width: int,
        height: int,
        image_path: str,
        product_image_url: str,
        shop_logo_url: str | None,
    ) -> PromotionalImage:
        image = PromotionalImage(
            product_id=product_id,
            template_name=template_name,
            output_format=output_format,
            width=width,
            height=height,
            image_path=image_path,
            product_image_url=product_image_url,
            shop_logo_url=shop_logo_url,
        )
        self._db.add(image)
        self._db.commit()
        self._db.refresh(image)
        return image
