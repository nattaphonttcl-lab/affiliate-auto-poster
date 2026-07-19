from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class MemberRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"
    SUPPORT = "support"


class SubscriptionPlan(StrEnum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class TenantCreateRequest(BaseModel):
    slug: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=255)
    billing_email: str = Field(min_length=5, max_length=255)


class TenantRead(ORMModel):
    id: int
    slug: str
    name: str
    billing_email: str
    branding: dict[str, str | int | bool | None]
    storage_quota_mb: int
    is_active: bool


class OrganizationCreateRequest(BaseModel):
    tenant_id: int = Field(ge=1)
    name: str = Field(min_length=2, max_length=255)


class OrganizationRead(ORMModel):
    id: int
    tenant_id: int
    name: str
    settings: dict[str, str | int | bool | None]


class WorkspaceCreateRequest(BaseModel):
    tenant_id: int = Field(ge=1)
    organization_id: int = Field(ge=1)
    slug: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=255)


class WorkspaceRead(ORMModel):
    id: int
    tenant_id: int
    organization_id: int
    slug: str
    name: str
    settings: dict[str, str | int | bool | None]


class WorkspaceMemberUpsertRequest(BaseModel):
    tenant_id: int = Field(ge=1)
    workspace_id: int = Field(ge=1)
    user_id: int = Field(ge=1)
    role: MemberRole
    permissions: list[str] = Field(default_factory=list)


class WorkspaceMemberRead(ORMModel):
    id: int
    tenant_id: int
    workspace_id: int
    user_id: int
    role: str
    permissions: list[str]


class InvitationCreateRequest(BaseModel):
    tenant_id: int = Field(ge=1)
    workspace_id: int = Field(ge=1)
    email: str = Field(min_length=5, max_length=255)
    role: MemberRole


class InvitationRead(ORMModel):
    id: int
    tenant_id: int
    workspace_id: int
    email: str
    role: str
    token: str
    status: str


class SubscriptionUpsertRequest(BaseModel):
    tenant_id: int = Field(ge=1)
    plan: SubscriptionPlan
    status: str = Field(min_length=3, max_length=32)
    trial_days: int = Field(default=0, ge=0, le=365)


class SubscriptionRead(ORMModel):
    id: int
    tenant_id: int
    plan: str
    status: str
    trial_ends_at: datetime | None
    current_period_end: datetime | None
    grace_period_ends_at: datetime | None
    limits: dict[str, int]
    feature_flags: dict[str, bool]


class PaymentWebhookRequest(BaseModel):
    tenant_id: int = Field(ge=1)
    provider: str = Field(min_length=3, max_length=32)
    external_payment_id: str = Field(min_length=3, max_length=128)
    amount: float = Field(gt=0)
    currency: str = Field(default="THB", min_length=3, max_length=8)
    status: str = Field(min_length=3, max_length=32)
    payload: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class PaymentTransactionRead(ORMModel):
    id: int
    tenant_id: int
    provider: str
    external_payment_id: str
    amount: float
    currency: str
    status: str


class UsageRecordCreateRequest(BaseModel):
    tenant_id: int = Field(ge=1)
    workspace_id: int | None = Field(default=None, ge=1)
    metric: str = Field(min_length=2, max_length=64)
    quantity: int = Field(default=1, ge=1)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class UsageSummaryRead(BaseModel):
    metric: str
    total: int


class ApiKeyCreateRequest(BaseModel):
    tenant_id: int = Field(ge=1)
    workspace_id: int | None = Field(default=None, ge=1)
    key_name: str = Field(min_length=2, max_length=120)
    key_scope: str = Field(min_length=2, max_length=32)
    expires_at: datetime | None = None


class ApiKeyCreateResponse(BaseModel):
    id: int
    key_name: str
    key_scope: str
    key_prefix: str
    token: str


class ApiKeyRead(ORMModel):
    id: int
    tenant_id: int
    workspace_id: int | None
    user_id: int
    key_name: str
    key_prefix: str
    key_scope: str
    expires_at: datetime | None
    revoked_at: datetime | None


class NotificationChannelCreateRequest(BaseModel):
    tenant_id: int = Field(ge=1)
    workspace_id: int | None = Field(default=None, ge=1)
    channel_type: str = Field(min_length=3, max_length=32)
    endpoint: str = Field(min_length=5, max_length=512)


class NotificationChannelRead(ORMModel):
    id: int
    tenant_id: int
    workspace_id: int | None
    channel_type: str
    endpoint: str
    is_active: bool


class NotificationDispatchRequest(BaseModel):
    tenant_id: int = Field(ge=1)
    channel_id: int = Field(ge=1)
    template: str = Field(min_length=2, max_length=80)
    payload: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class NotificationEventRead(ORMModel):
    id: int
    tenant_id: int
    channel_id: int
    template: str
    status: str
    retry_count: int


class ContentCalendarGenerateRequest(BaseModel):
    tenant_id: int = Field(ge=1)
    workspace_id: int = Field(ge=1)
    start_date: datetime
    days: int = Field(default=14, ge=1, le=90)


class ContentCalendarItemRead(ORMModel):
    id: int
    tenant_id: int
    workspace_id: int
    title: str
    platform: str
    suggested_at: datetime
    topic: str
    campaign: str | None
    confidence_score: float


class AffiliateInsightRead(ORMModel):
    id: int
    tenant_id: int
    workspace_id: int | None
    insight_type: str
    subject: str
    score: float
    payload: dict[str, str | int | float | bool | None]


class FeedbackCreateRequest(BaseModel):
    tenant_id: int = Field(ge=1)
    workspace_id: int | None = Field(default=None, ge=1)
    category: str = Field(min_length=2, max_length=32)
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=5)


class FeedbackRead(ORMModel):
    id: int
    tenant_id: int
    workspace_id: int | None
    user_id: int | None
    category: str
    title: str
    description: str
    status: str


class AuditEventRead(ORMModel):
    id: int
    tenant_id: int
    workspace_id: int | None
    actor_user_id: int | None
    event_type: str
    action: str
    details: dict[str, str | int | float | bool | None]
    created_at: datetime


class CustomerHealthResponse(BaseModel):
    tenant_id: int
    workspace_id: int | None
    health_score: float
    risk_level: str
    factors: list[str]


class OptimizerScoreResponse(BaseModel):
    tenant_id: int
    quality_score: float
    cost_score: float
    performance_score: float


class MarketplaceConnectorStatus(BaseModel):
    connector: str
    status: str
    notes: str


class MarketplaceConnectorResponse(BaseModel):
    items: list[MarketplaceConnectorStatus]
