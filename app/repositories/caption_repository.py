from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.caption import Caption, CaptionBatch
from app.utils.ai_caption_engine import GeneratedCaption


class CaptionRepositoryProtocol(Protocol):
    def create_batch(
        self,
        *,
        product_id: int,
        style: str,
        prompt_template: str,
        captions: Sequence[GeneratedCaption],
    ) -> tuple[CaptionBatch, list[Caption]]: ...


class CaptionRepository(CaptionRepositoryProtocol):
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_batch(
        self,
        *,
        product_id: int,
        style: str,
        prompt_template: str,
        captions: Sequence[GeneratedCaption],
    ) -> tuple[CaptionBatch, list[Caption]]:
        batch = CaptionBatch(product_id=product_id, style=style, prompt_template=prompt_template)
        self._db.add(batch)
        self._db.flush()

        created: list[Caption] = []
        for index, generated in enumerate(captions, start=1):
            caption = Caption(
                batch_id=batch.id,
                sequence=index,
                hook=generated.hook,
                cta=generated.cta,
                emoji=generated.emoji,
                hashtags=" ".join(generated.hashtags),
                caption_text=generated.caption_text,
            )
            self._db.add(caption)
            created.append(caption)

        self._db.commit()
        self._db.refresh(batch)

        stmt = select(Caption).where(Caption.batch_id == batch.id).order_by(Caption.sequence.asc())
        persisted = list(self._db.scalars(stmt))
        return batch, persisted
