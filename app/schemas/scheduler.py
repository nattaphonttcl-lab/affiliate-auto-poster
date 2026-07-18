from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SchedulePlatform(StrEnum):
    FACEBOOK = "facebook"


class ScheduledPostStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"


class ScheduledPostCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    product_id: int = Field(ge=1)
    caption_batch_id: int | None = Field(default=None, ge=1)
    promotional_image_id: int | None = Field(default=None, ge=1)
    target: str = Field(min_length=3, max_length=255)
    scheduled_for: datetime
    platform: SchedulePlatform = SchedulePlatform.FACEBOOK


class ScheduledPostRead(BaseModel):
    id: int
    product_id: int
    caption_batch_id: int | None
    promotional_image_id: int | None
    platform: SchedulePlatform
    target: str
    scheduled_for: datetime
    status: ScheduledPostStatus
    published_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class SchedulerRunResponse(BaseModel):
    processed: int
    published: int
    failed: int
