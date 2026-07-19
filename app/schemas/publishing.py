from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ORMModel


class SocialPlatform(StrEnum):
    FACEBOOK = "facebook"
    FACEBOOK_PAGE = "facebook_page"
    INSTAGRAM = "instagram"
    THREADS = "threads"
    TIKTOK = "tiktok"
    YOUTUBE_SHORTS = "youtube_shorts"
    SHOPEE_VIDEO = "shopee_video"


class SocialPostType(StrEnum):
    FACEBOOK_FEED = "facebook_feed"
    FACEBOOK_REEL = "facebook_reel"
    FACEBOOK_STORY = "facebook_story"
    FACEBOOK_COVER = "facebook_cover"
    INSTAGRAM_FEED = "instagram_feed"
    INSTAGRAM_STORY = "instagram_story"
    INSTAGRAM_REEL = "instagram_reel"
    THREADS = "threads"
    TIKTOK_VIDEO = "tiktok_video"
    TIKTOK_IMAGE_POST = "tiktok_image_post"
    YOUTUBE_SHORTS = "youtube_shorts"
    SHOPEE_FEED = "shopee_feed"


class PublishingStatus(StrEnum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    RETRY = "retry"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class MediaType(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    THUMBNAIL = "thumbnail"


class MediaSourceType(StrEnum):
    GENERATED = "generated"
    EXTERNAL = "external"


class SocialAccountCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    platform: SocialPlatform
    account_name: str = Field(min_length=2, max_length=255)
    account_identifier: str = Field(min_length=2, max_length=255)
    permissions: list[str] = Field(default_factory=list)
    timezone: str = Field(default="UTC", min_length=2, max_length=64)
    business_hours_start: int | None = Field(default=None, ge=0, le=23)
    business_hours_end: int | None = Field(default=None, ge=0, le=23)
    rate_limit_per_minute: int = Field(default=60, ge=1, le=10000)
    access_token: str = Field(min_length=4)
    refresh_token: str | None = Field(default=None, min_length=4)
    token_expires_at: datetime | None = None
    scopes: list[str] = Field(default_factory=list)


class SocialAccountUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    account_name: str | None = Field(default=None, min_length=2, max_length=255)
    permissions: list[str] | None = None
    timezone: str | None = Field(default=None, min_length=2, max_length=64)
    business_hours_start: int | None = Field(default=None, ge=0, le=23)
    business_hours_end: int | None = Field(default=None, ge=0, le=23)
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=10000)
    is_active: bool | None = None
    access_token: str | None = Field(default=None, min_length=4)
    refresh_token: str | None = Field(default=None, min_length=4)
    token_expires_at: datetime | None = None
    scopes: list[str] | None = None


class SocialAccountRead(ORMModel):
    id: int
    owner_user_id: int
    platform: SocialPlatform
    account_name: str
    account_identifier: str
    permissions: list[str]
    is_active: bool
    timezone: str
    business_hours_start: int | None
    business_hours_end: int | None
    rate_limit_per_minute: int
    created_at: datetime
    updated_at: datetime


class PublishRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    social_account_id: int = Field(ge=1)
    product_id: int = Field(ge=1)
    post_type: SocialPostType
    caption_content_id: int | None = Field(default=None, ge=1)
    generated_image_id: int | None = Field(default=None, ge=1)
    media_attachments: list[str] = Field(default_factory=list)
    mentions: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    cta: str | None = Field(default=None, max_length=255)
    affiliate_link: str | None = Field(default=None, max_length=2048)
    alt_text: str | None = Field(default=None, max_length=500)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=128)


class PublishScheduleRequest(PublishRequest):
    scheduled_for: datetime
    recurrence_rule: str | None = Field(default=None, max_length=255)
    timezone: str = Field(default="UTC", min_length=2, max_length=64)
    enforce_business_hours: bool = False


class PublishRetryRequest(BaseModel):
    job_id: int = Field(ge=1)


class PublishCancelRequest(BaseModel):
    job_id: int = Field(ge=1)


class PublishingJobRead(ORMModel):
    id: int
    owner_user_id: int
    social_account_id: int
    product_id: int | None
    caption_content_id: int | None
    generated_image_id: int | None
    post_type: str
    platform: str
    status: PublishingStatus
    scheduled_for: datetime | None
    recurrence_rule: str | None
    timezone: str
    business_hours_enforced: bool
    idempotency_key: str
    retry_count: int
    max_retries: int
    next_retry_at: datetime | None
    last_error: str | None
    latency_ms: int | None
    published_at: datetime | None
    cancelled_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PublishingHistoryRead(ORMModel):
    id: int
    job_id: int
    platform: str
    account_identifier: str
    caption: str
    hashtags: str | None
    mentions: str | None
    cta: str | None
    affiliate_link: str | None
    media_refs: list[str]
    published_at: datetime | None
    status: str
    retry_count: int
    latency_ms: int | None
    views: int
    likes: int
    comments: int
    shares: int
    clicks: int
    ctr: Decimal
    conversion: Decimal
    revenue: Decimal
    commission: Decimal
    created_at: datetime


class PublishingJobsResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[PublishingJobRead]


class PublishingHistoryResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[PublishingHistoryRead]


class PublishActionResponse(BaseModel):
    job: PublishingJobRead
    queue_status: PublishingStatus
