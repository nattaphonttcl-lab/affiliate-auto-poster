from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.dashboard import (
    DashboardActivityItem,
    DashboardActivityResponse,
    DashboardSchedulerBreakdown,
    DashboardSummaryResponse,
    DashboardTotals,
)


class DashboardService:
    def __init__(self, repository: DashboardRepository) -> None:
        self._repository = repository

    def get_summary(self) -> DashboardSummaryResponse:
        breakdown = self._repository.scheduled_status_breakdown()

        return DashboardSummaryResponse(
            totals=DashboardTotals(
                products=self._repository.count_products(),
                caption_batches=self._repository.count_caption_batches(),
                promotional_images=self._repository.count_promotional_images(),
                scheduled_posts=self._repository.count_scheduled_posts(),
            ),
            scheduler=DashboardSchedulerBreakdown(
                awaiting_confirmation=breakdown.get("awaiting_confirmation", 0),
                confirmed=breakdown.get("confirmed", 0),
                processing=breakdown.get("processing", 0),
                published=breakdown.get("published", 0),
                failed=breakdown.get("failed", 0),
            ),
        )

    def get_activity(self, limit: int = 20) -> DashboardActivityResponse:
        items: list[DashboardActivityItem] = []

        for batch in self._repository.recent_caption_batches(limit=limit):
            items.append(
                DashboardActivityItem(
                    type="caption_batch",
                    reference_id=batch.id,
                    status=batch.style,
                    occurred_at=batch.created_at,
                    description=f"Caption batch generated for product {batch.product_id}",
                )
            )

        for image in self._repository.recent_promotional_images(limit=limit):
            items.append(
                DashboardActivityItem(
                    type="promotional_image",
                    reference_id=image.id,
                    status=image.template_name,
                    occurred_at=image.created_at,
                    description=f"Promotional image generated for product {image.product_id}",
                )
            )

        for post in self._repository.recent_scheduled_posts(limit=limit):
            items.append(
                DashboardActivityItem(
                    type="scheduled_post",
                    reference_id=post.id,
                    status=post.state,
                    occurred_at=post.created_at,
                    description=f"Scheduled post created for target {post.target}",
                )
            )

        items.sort(key=lambda item: item.occurred_at, reverse=True)
        return DashboardActivityResponse(items=items[:limit])
