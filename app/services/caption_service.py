from app.core.exceptions import AppException
from app.models.caption import Caption, CaptionBatch
from app.repositories.caption_repository import CaptionRepositoryProtocol
from app.repositories.product_repository import ProductRepositoryProtocol
from app.schemas.caption import CaptionStyle
from app.utils.ai_caption_engine import AICaptionEngine


class CaptionService:
    def __init__(
        self,
        product_repository: ProductRepositoryProtocol,
        caption_repository: CaptionRepositoryProtocol,
        engine: AICaptionEngine,
    ) -> None:
        self._product_repository = product_repository
        self._caption_repository = caption_repository
        self._engine = engine

    def generate_for_product(self, *, product_id: int, style: CaptionStyle) -> tuple[CaptionBatch, list[Caption]]:
        product = self._product_repository.get_by_id(product_id)
        if product is None:
            raise AppException(status_code=404, detail="Product not found")

        prompt_template = self._engine.get_prompt_template(style)
        generated = self._engine.generate(product, style)

        return self._caption_repository.create_batch(
            product_id=product.id,
            style=style.value,
            prompt_template=prompt_template,
            captions=generated,
        )
