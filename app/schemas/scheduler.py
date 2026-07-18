from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SchedulePlatform(StrEnum):
    FACEBOOK = "facebook"


class ScheduledPostState(StrEnum):
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"


class ScheduledPostCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    product_id: int = Field(ge=1, description="Product to publish")
    caption_batch_id: int | None = Field(
        default=None, ge=1, description="Optional caption batch reference"
    )
    promotional_image_id: int | None = Field(
        default=None, ge=1, description="Optional generated image reference"
    )
    target: str = Field(
        min_length=3,
        max_length=255,
        description="Destination identifier (page/group/profile id)",
    )
    scheduled_for: datetime = Field(
        description="UTC datetime when publishing becomes eligible"
    )
    platform: SchedulePlatform = SchedulePlatform.FACEBOOK


class ScheduledPostRead(BaseModel):
    id: int
    version: int
    owner_user_id: int
    product_id: int
    caption_batch_id: int | None
    promotional_image_id: int | None
    platform: SchedulePlatform
    target: str
    scheduled_for: datetime
    state: ScheduledPostState
    published_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class SchedulerRunResponse(BaseModel):
    processed: int
    published: int
    failed: int
