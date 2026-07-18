from app.core.exceptions import AppException
from app.models.caption import Caption, CaptionBatch
from app.repositories.analytics_repository import AnalyticsRepositoryProtocol
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
        analytics_repository: AnalyticsRepositoryProtocol | None = None,
    ) -> None:
        self._product_repository = product_repository
        self._caption_repository = caption_repository
        self._engine = engine
        self._analytics_repository = analytics_repository

    def generate_for_product(self, *, product_id: int, style: CaptionStyle) -> tuple[CaptionBatch, list[Caption]]:
        product = self._product_repository.get_by_id(product_id)
        if product is None:
            raise AppException(status_code=404, detail="Product not found")

        prompt_template = self._engine.get_prompt_template(style)
        generated = self._engine.generate(product, style)

        batch, captions = self._caption_repository.create_batch(
            product_id=product.id,
            style=style.value,
            prompt_template=prompt_template,
            captions=generated,
        )

        if self._analytics_repository is not None:
            self._analytics_repository.record_event(
                event_type="caption_generated",
                entity_type="caption_batch",
                entity_id=batch.id,
                metadata={"product_id": product.id, "style": style.value, "count": len(captions)},
            )

        return batch, captions
