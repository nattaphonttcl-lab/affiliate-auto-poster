from datetime import datetime
from enum import StrEnum

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class ImageTemplate(StrEnum):
    CLASSIC = "classic"
    BOLD = "bold"
    MINIMAL = "minimal"


class PromotionalImageGenerateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    product_id: int = Field(ge=1)
    template: ImageTemplate = ImageTemplate.CLASSIC
    shop_logo_url: AnyHttpUrl | None = None


class PromotionalImageRead(BaseModel):
    id: int
    product_id: int
    template: ImageTemplate
    output_format: str
    width: int
    height: int
    image_path: str
    product_image_url: str
    shop_logo_url: str | None
    created_at: datetime
