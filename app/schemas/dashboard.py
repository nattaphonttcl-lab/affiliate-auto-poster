from datetime import datetime

from pydantic import BaseModel


class DashboardTotals(BaseModel):
    products: int
    caption_batches: int
    promotional_images: int
    scheduled_posts: int


class DashboardSchedulerBreakdown(BaseModel):
    pending: int
    processing: int
    published: int
    failed: int


class DashboardSummaryResponse(BaseModel):
    totals: DashboardTotals
    scheduler: DashboardSchedulerBreakdown


class DashboardActivityItem(BaseModel):
    type: str
    reference_id: int
    status: str | None
    occurred_at: datetime
    description: str


class DashboardActivityResponse(BaseModel):
    items: list[DashboardActivityItem]
