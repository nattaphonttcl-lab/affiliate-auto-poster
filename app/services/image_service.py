from app.core.exceptions import AppException
from app.models.promotional_image import PromotionalImage
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
    ) -> None:
        self._product_repository = product_repository
        self._image_repository = image_repository
        self._generator = generator

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

        return self._image_repository.create(
            product_id=product.id,
            template_name=template.value,
            output_format=result.output_format,
            width=result.width,
            height=result.height,
            image_path=result.output_path,
            product_image_url=result.product_image_url,
            shop_logo_url=result.shop_logo_url,
        )
