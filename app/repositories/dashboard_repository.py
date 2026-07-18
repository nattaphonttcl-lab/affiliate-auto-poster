from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.caption import CaptionBatch
from app.models.product import Product
from app.models.promotional_image import PromotionalImage
from app.models.scheduled_post import ScheduledPost


class DashboardRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def count_products(self) -> int:
        return int(self._db.scalar(select(func.count(Product.id))) or 0)

    def count_caption_batches(self) -> int:
        return int(self._db.scalar(select(func.count(CaptionBatch.id))) or 0)

    def count_promotional_images(self) -> int:
        return int(self._db.scalar(select(func.count(PromotionalImage.id))) or 0)

    def count_scheduled_posts(self) -> int:
        return int(self._db.scalar(select(func.count(ScheduledPost.id))) or 0)

    def scheduled_status_breakdown(self) -> dict[str, int]:
        stmt = select(ScheduledPost.state, func.count(ScheduledPost.id)).group_by(
            ScheduledPost.state
        )
        rows = list(self._db.execute(stmt).all())
        return {state: int(count) for state, count in rows}

    def recent_caption_batches(self, limit: int = 10) -> list[CaptionBatch]:
        stmt = (
            select(CaptionBatch).order_by(CaptionBatch.created_at.desc()).limit(limit)
        )
        return list(self._db.scalars(stmt))

    def recent_promotional_images(self, limit: int = 10) -> list[PromotionalImage]:
        stmt = (
            select(PromotionalImage)
            .order_by(PromotionalImage.created_at.desc())
            .limit(limit)
        )
        return list(self._db.scalars(stmt))

    def recent_scheduled_posts(self, limit: int = 10) -> list[ScheduledPost]:
        stmt = (
            select(ScheduledPost).order_by(ScheduledPost.created_at.desc()).limit(limit)
        )
        return list(self._db.scalars(stmt))
