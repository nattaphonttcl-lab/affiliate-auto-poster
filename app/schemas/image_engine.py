from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ORMModel


class ImageProviderName(StrEnum):
    OPENAI = "openai"
    GOOGLE_IMAGEN = "google_imagen"
    STABILITY_AI = "stability_ai"
    FLUX = "flux"
    LOCAL_TEMPLATE = "local_template"


class ImageType(StrEnum):
    FACEBOOK_POST = "facebook_post"
    FACEBOOK_COVER = "facebook_cover"
    TIKTOK_COVER = "tiktok_cover"
    TIKTOK_THUMBNAIL = "tiktok_thumbnail"
    INSTAGRAM_POST = "instagram_post"
    INSTAGRAM_STORY = "instagram_story"
    YOUTUBE_THUMBNAIL = "youtube_thumbnail"
    SHOPEE_PRODUCT_BANNER = "shopee_product_banner"
    PROMOTION_BANNER = "promotion_banner"
    CAROUSEL_SLIDE = "carousel_slide"
    PRODUCT_CARD = "product_card"
    SQUARE_IMAGE = "square_image"
    VERTICAL_IMAGE = "vertical_image"
    HORIZONTAL_IMAGE = "horizontal_image"


class ImageTemplateStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class OutputFormat(StrEnum):
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"
    AVIF = "avif"


class DynamicVariables(BaseModel):
    product_name: str | None = None
    price: str | None = None
    discount: str | None = None
    coupon: str | None = None
    shop_name: str | None = None
    rating: str | None = None
    sales: str | None = None
    caption: str | None = None
    hashtags: str | None = None
    brand: str | None = None
    logo: str | None = None
    background: str | None = None


class ImageTemplateCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=128)
    image_type: ImageType
    canvas_width: int = Field(ge=128, le=8192)
    canvas_height: int = Field(ge=128, le=8192)
    safe_area: dict[str, int]
    background: dict[str, str | int]
    layers: list[dict[str, str | int | float | bool]] = Field(default_factory=list)
    fonts: dict[str, str] = Field(default_factory=dict)
    colors: dict[str, str] = Field(default_factory=dict)
    logo_position: dict[str, int]
    watermark: dict[str, str | int | bool] = Field(default_factory=dict)
    overlay: dict[str, str | int | float | bool] = Field(default_factory=dict)
    dynamic_variables: list[str] = Field(default_factory=list)
    version: int = Field(default=1, ge=1)
    status: ImageTemplateStatus = ImageTemplateStatus.ACTIVE


class ImageTemplateUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=128)
    safe_area: dict[str, int] | None = None
    background: dict[str, str | int] | None = None
    layers: list[dict[str, str | int | float | bool]] | None = None
    fonts: dict[str, str] | None = None
    colors: dict[str, str] | None = None
    logo_position: dict[str, int] | None = None
    watermark: dict[str, str | int | bool] | None = None
    overlay: dict[str, str | int | float | bool] | None = None
    dynamic_variables: list[str] | None = None
    status: ImageTemplateStatus | None = None


class ImageTemplateRead(ORMModel):
    id: int
    name: str
    image_type: str
    canvas_width: int
    canvas_height: int
    safe_area: dict[str, int]
    background: dict[str, str | int]
    layers: list[dict[str, str | int | float | bool]]
    fonts: dict[str, str]
    colors: dict[str, str]
    logo_position: dict[str, int]
    watermark: dict[str, str | int | bool]
    overlay: dict[str, str | int | float | bool]
    dynamic_variables: list[str]
    version: int
    status: str
    created_by: int | None
    created_at: datetime
    updated_at: datetime


class ImageGenerateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    product_id: int = Field(ge=1)
    image_type: ImageType
    provider: ImageProviderName
    model: str = Field(min_length=1, max_length=128)
    output_format: OutputFormat = OutputFormat.PNG
    template_id: int | None = Field(default=None, ge=1)
    template_version: int | None = Field(default=None, ge=1)
    caption_content_id: int | None = Field(default=None, ge=1)
    variables: DynamicVariables = Field(default_factory=DynamicVariables)


class ImageRegenerateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    generated_image_id: int = Field(ge=1)
    provider: ImageProviderName | None = None
    model: str | None = Field(default=None, min_length=1, max_length=128)


class ImageGenerateResponse(BaseModel):
    generated_image_id: int
    version_id: int
    version: int
    provider: str
    model: str
    template_version: int
    output_format: str
    image_uri: str
    preview_uri: str
    thumbnail_uri: str
    cost_usd: Decimal
    latency_ms: int
    created_at: datetime


class ImageHistoryItemRead(BaseModel):
    generated_image_id: int
    version: int
    image_type: str
    provider: str
    model: str
    output_format: str
    image_uri: str
    preview_uri: str
    thumbnail_uri: str
    cost_usd: Decimal
    latency_ms: int
    created_at: datetime


class ImageHistoryResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ImageHistoryItemRead]


class ImagePreviewRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    product_id: int = Field(ge=1)
    image_type: ImageType
    template_id: int | None = Field(default=None, ge=1)
    variables: DynamicVariables = Field(default_factory=DynamicVariables)


class ImagePreviewResponse(BaseModel):
    preview_uri: str
    width: int
    height: int
