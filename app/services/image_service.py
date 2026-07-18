from app.core.exceptions import AppException
from app.models.promotional_image import PromotionalImage
from app.repositories.analytics_repository import AnalyticsRepositoryProtocol
from app.repositories.image_repository import ImageRepositoryProtocol
from app.repositories.product_repository import ProductRepositoryProtocol
from app.schemas.image import ImageTemplate
from app.utils.image_generator_engine import ImageGeneratorEngine


class ImageService:
    def __init__(
        self,
        product_repository: ProductRepositoryProtocol,
        image_repository: ImageRepositoryProtocol,
        generator: ImageGeneratorEngine,
        analytics_repository: AnalyticsRepositoryProtocol | None = None,
    ) -> None:
        self._product_repository = product_repository
        self._image_repository = image_repository
        self._generator = generator
        self._analytics_repository = analytics_repository

    def generate_promotional_image(
        self,
        *,
        product_id: int,
        template: ImageTemplate,
        shop_logo_url: str | None,
    ) -> PromotionalImage:
        product = self._product_repository.get_by_id(product_id)
        if product is None:
            raise AppException(status_code=404, detail="Product not found")

        result = self._generator.generate_promotional_cover(
            product=product,
            template=template,
            shop_logo_url=shop_logo_url,
        )

        created = self._image_repository.create(
            product_id=product.id,
            template_name=template.value,
            output_format=result.output_format,
            width=result.width,
            height=result.height,
            image_path=result.output_path,
            product_image_url=result.product_image_url,
            shop_logo_url=result.shop_logo_url,
        )

        if self._analytics_repository is not None:
            self._analytics_repository.record_event(
                event_type="image_generated",
                entity_type="promotional_image",
                entity_id=created.id,
                metadata={"product_id": product.id, "template": template.value},
            )

        return created
