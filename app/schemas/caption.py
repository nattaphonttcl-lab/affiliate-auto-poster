from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CaptionStyle(StrEnum):
    FUNNY = "funny"
    REVIEW = "review"
    PROMOTION = "promotion"
    STORYTELLING = "storytelling"
    URGENCY = "urgency"


class CaptionGenerateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    product_id: int = Field(ge=1)
    style: CaptionStyle


class CaptionItemRead(BaseModel):
    hook: str
    cta: str
    emoji: str
    hashtags: list[str]
    caption_text: str


class CaptionGenerateResponse(BaseModel):
    batch_id: int
    product_id: int
    style: CaptionStyle
    generated_at: datetime
    captions: list[CaptionItemRead]
