from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ORMModel


class AIProviderName(StrEnum):
    OPENAI = "openai"
    GEMINI = "gemini"
    CLAUDE = "claude"
    DEEPSEEK = "deepseek"
    OPENROUTER = "openrouter"


class PromptTemplateStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class PromptCategory(StrEnum):
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    YOUTUBE_SHORTS = "youtube_shorts"
    SHOPEE_LIVE = "shopee_live"
    GENERAL_AFFILIATE = "general_affiliate"


class ContentType(StrEnum):
    FACEBOOK_CAPTION = "facebook_caption"
    TIKTOK_CAPTION = "tiktok_caption"
    HOOK = "hook"
    CTA = "cta"
    SEO_KEYWORDS = "seo_keywords"
    HASHTAGS = "hashtags"
    SHORT_DESCRIPTION = "short_description"
    LONG_DESCRIPTION = "long_description"
    PRODUCT_REVIEW = "product_review"
    COMPARISON_REVIEW = "comparison_review"
    BUYING_GUIDE = "buying_guide"
    FAQ = "faq"


class WritingStyle(StrEnum):
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    MOTHER_BLOGGER = "mother_blogger"
    LUXURY = "luxury"
    MINIMAL = "minimal"
    EMOTIONAL = "emotional"
    SALES = "sales"
    URGENCY = "urgency"
    STORYTELLING = "storytelling"


class AudienceProfile(StrEnum):
    PARENTS = "parents"
    STUDENTS = "students"
    OFFICE_WORKERS = "office_workers"
    BEAUTY = "beauty"
    FASHION = "fashion"
    GAMING = "gaming"
    PETS = "pets"
    HOME = "home"
    ELECTRONICS = "electronics"
    HEALTH = "health"


class PromptVariableRead(BaseModel):
    name: str
    description: str | None = None
    required: bool = True
    default_value: str | None = None


class PromptTemplateCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=128)
    category: PromptCategory
    system_prompt: str = Field(min_length=10)
    user_prompt: str = Field(min_length=10)
    variables: list[PromptVariableRead] = Field(default_factory=list)
    temperature: Decimal = Field(default=Decimal("0.70"), ge=0, le=2)
    max_tokens: int = Field(default=800, ge=64, le=4000)
    version: int = Field(default=1, ge=1)
    status: PromptTemplateStatus = PromptTemplateStatus.ACTIVE


class PromptTemplateUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=128)
    system_prompt: str | None = Field(default=None, min_length=10)
    user_prompt: str | None = Field(default=None, min_length=10)
    variables: list[PromptVariableRead] | None = None
    temperature: Decimal | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=64, le=4000)
    status: PromptTemplateStatus | None = None


class PromptTemplateRead(ORMModel):
    id: int
    name: str
    category: PromptCategory
    system_prompt: str
    user_prompt: str
    variables: list[str]
    temperature: Decimal
    max_tokens: int
    version: int
    status: PromptTemplateStatus
    created_by: int | None
    created_at: datetime
    updated_at: datetime


class AIContentGenerateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    product_id: int = Field(ge=1)
    platform: PromptCategory
    content_types: list[ContentType] = Field(min_length=1)
    style: WritingStyle
    target_audience: AudienceProfile
    language: str = Field(default="id", min_length=2, max_length=10)
    provider: AIProviderName
    model: str = Field(min_length=2, max_length=128)
    template_id: int | None = Field(default=None, ge=1)
    template_version: int | None = Field(default=None, ge=1)
    benefits: list[str] | None = None
    features: list[str] | None = None


class AIContentRegenerateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    content_id: int = Field(ge=1)
    provider: AIProviderName | None = None
    model: str | None = Field(default=None, min_length=2, max_length=128)


class AIContentVersionRead(ORMModel):
    id: int
    content_id: int
    version: int
    provider: str
    model: str
    prompt_version: int
    generated_text: dict[str, str]
    cost_usd: Decimal
    latency_ms: int
    created_by: int
    created_at: datetime


class AIContentRead(ORMModel):
    id: int
    product_id: int
    template_id: int
    platform: str
    style: str
    target_audience: str
    language: str
    provider: str
    model: str
    current_version: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    latest_generated_text: dict[str, str]


class AIHistoryResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[AIContentRead]


class AIContentGenerateResponse(BaseModel):
    content_id: int
    version_id: int
    version: int
    provider: str
    model: str
    prompt_version: int
    generated_text: dict[str, str]
    cost_usd: Decimal
    latency_ms: int
    created_at: datetime
