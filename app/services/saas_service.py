from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
import secrets

from app.core.exceptions import AppException
from app.models.saas import (
    AffiliateInsight,
    ApiKey,
    AuditEvent,
    ContentCalendarItem,
    CustomerFeedback,
    Invitation,
    NotificationChannel,
    NotificationEvent,
    Organization,
    PaymentTransaction,
    Subscription,
    Tenant,
    Workspace,
    WorkspaceMember,
)
from app.repositories.saas_repository import SaaSRepository
from app.schemas.saas import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ContentCalendarGenerateRequest,
    CustomerHealthResponse,
    FeedbackCreateRequest,
    InvitationCreateRequest,
    MarketplaceConnectorResponse,
    MarketplaceConnectorStatus,
    NotificationChannelCreateRequest,
    NotificationDispatchRequest,
    OptimizerScoreResponse,
    OrganizationCreateRequest,
    PaymentWebhookRequest,
    SubscriptionPlan,
    SubscriptionUpsertRequest,
    TenantCreateRequest,
    UsageRecordCreateRequest,
    UsageSummaryRead,
    WorkspaceCreateRequest,
    WorkspaceMemberUpsertRequest,
)


class SaaSService:
    def __init__(self, repository: SaaSRepository) -> None:
        self._repository = repository

    def create_tenant(
        self, payload: TenantCreateRequest, *, actor_user_id: int
    ) -> Tenant:
        row = self._repository.create_tenant(
            slug=payload.slug.strip().lower(),
            name=payload.name.strip(),
            billing_email=payload.billing_email.strip().lower(),
        )
        self._repository.create_audit_event(
            tenant_id=row.id,
            workspace_id=None,
            actor_user_id=actor_user_id,
            event_type="tenant",
            action="tenant_created",
            details={"slug": row.slug},
        )
        self._repository.commit()
        return row

    def list_tenants(self) -> list[Tenant]:
        return self._repository.list_tenants()

    def create_organization(
        self, payload: OrganizationCreateRequest, *, actor_user_id: int
    ) -> Organization:
        tenant = self._ensure_tenant(payload.tenant_id)
        row = self._repository.create_organization(
            tenant_id=tenant.id,
            name=payload.name.strip(),
        )
        self._repository.create_audit_event(
            tenant_id=tenant.id,
            workspace_id=None,
            actor_user_id=actor_user_id,
            event_type="organization",
            action="organization_created",
            details={"organization_id": row.id},
        )
        self._repository.commit()
        return row

    def create_workspace(
        self, payload: WorkspaceCreateRequest, *, actor_user_id: int
    ) -> Workspace:
        tenant = self._ensure_tenant(payload.tenant_id)
        organization = self._repository.get_organization(payload.organization_id)
        if organization is None or organization.tenant_id != tenant.id:
            raise AppException(status_code=404, detail="Organization not found")
        row = self._repository.create_workspace(
            tenant_id=tenant.id,
            organization_id=payload.organization_id,
            slug=payload.slug.strip().lower(),
            name=payload.name.strip(),
        )
        self._repository.upsert_member(
            tenant_id=tenant.id,
            workspace_id=row.id,
            user_id=actor_user_id,
            role="owner",
            permissions=["workspace:admin", "workspace:write", "workspace:read"],
        )
        self._repository.create_audit_event(
            tenant_id=tenant.id,
            workspace_id=row.id,
            actor_user_id=actor_user_id,
            event_type="workspace",
            action="workspace_created",
            details={"workspace_id": row.id},
        )
        self._repository.commit()
        return row

    def upsert_workspace_member(
        self, payload: WorkspaceMemberUpsertRequest, *, actor_user_id: int
    ) -> WorkspaceMember:
        workspace = self._ensure_workspace(payload.tenant_id, payload.workspace_id)
        self._assert_workspace_admin(workspace.id, actor_user_id)
        row = self._repository.upsert_member(
            tenant_id=payload.tenant_id,
            workspace_id=workspace.id,
            user_id=payload.user_id,
            role=payload.role.value,
            permissions=payload.permissions,
        )
        self._repository.create_audit_event(
            tenant_id=payload.tenant_id,
            workspace_id=workspace.id,
            actor_user_id=actor_user_id,
            event_type="membership",
            action="workspace_member_upserted",
            details={"member_user_id": payload.user_id, "role": payload.role.value},
        )
        self._repository.commit()
        return row

    def create_invitation(
        self, payload: InvitationCreateRequest, *, actor_user_id: int
    ) -> Invitation:
        workspace = self._ensure_workspace(payload.tenant_id, payload.workspace_id)
        self._assert_workspace_admin(workspace.id, actor_user_id)
        token = secrets.token_urlsafe(24)
        row = self._repository.create_invitation(
            tenant_id=payload.tenant_id,
            workspace_id=workspace.id,
            email=payload.email.strip().lower(),
            role=payload.role.value,
            token=token,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        self._repository.create_audit_event(
            tenant_id=payload.tenant_id,
            workspace_id=workspace.id,
            actor_user_id=actor_user_id,
            event_type="invitation",
            action="workspace_invitation_created",
            details={"invitation_id": row.id, "email": row.email},
        )
        self._repository.commit()
        return row

    def upsert_subscription(
        self, payload: SubscriptionUpsertRequest, *, actor_user_id: int
    ) -> Subscription:
        self._ensure_tenant(payload.tenant_id)
        now = datetime.now(UTC)
        limits, flags = self._plan_defaults(payload.plan)
        trial_ends_at = (
            now + timedelta(days=payload.trial_days) if payload.trial_days else None
        )
        current_period_end = now + timedelta(days=30)
        grace_period_ends_at = current_period_end + timedelta(days=7)
        row = self._repository.upsert_subscription(
            tenant_id=payload.tenant_id,
            plan=payload.plan.value,
            status=payload.status,
            trial_ends_at=trial_ends_at,
            current_period_end=current_period_end,
            grace_period_ends_at=grace_period_ends_at,
            limits=limits,
            feature_flags=flags,
        )
        self._repository.create_audit_event(
            tenant_id=payload.tenant_id,
            workspace_id=None,
            actor_user_id=actor_user_id,
            event_type="subscription",
            action="subscription_upserted",
            details={"plan": payload.plan.value, "status": payload.status},
        )
        self._repository.commit()
        return row

    def record_payment_webhook(
        self, payload: PaymentWebhookRequest, *, actor_user_id: int
    ) -> PaymentTransaction:
        self._ensure_tenant(payload.tenant_id)
        row = self._repository.create_payment(
            tenant_id=payload.tenant_id,
            provider=payload.provider,
            external_payment_id=payload.external_payment_id,
            amount=payload.amount,
            currency=payload.currency,
            status=payload.status,
            payload=payload.payload,
        )
        self._repository.create_audit_event(
            tenant_id=payload.tenant_id,
            workspace_id=None,
            actor_user_id=actor_user_id,
            event_type="billing",
            action="payment_webhook_ingested",
            details={"payment_id": row.id, "status": row.status},
        )
        self._repository.commit()
        return row

    def list_payments(self, *, tenant_id: int) -> list[PaymentTransaction]:
        self._ensure_tenant(tenant_id)
        return self._repository.list_payments(tenant_id=tenant_id)

    def record_usage(
        self, payload: UsageRecordCreateRequest, *, actor_user_id: int
    ) -> None:
        self._ensure_tenant(payload.tenant_id)
        if payload.workspace_id is not None:
            workspace = self._ensure_workspace(payload.tenant_id, payload.workspace_id)
            self._assert_workspace_member(workspace.id, actor_user_id)
        self._repository.record_usage(
            tenant_id=payload.tenant_id,
            workspace_id=payload.workspace_id,
            metric=payload.metric,
            quantity=payload.quantity,
            metadata=payload.metadata,
        )
        self._repository.create_audit_event(
            tenant_id=payload.tenant_id,
            workspace_id=payload.workspace_id,
            actor_user_id=actor_user_id,
            event_type="usage",
            action="usage_recorded",
            details={"metric": payload.metric, "quantity": payload.quantity},
        )
        self._repository.commit()

    def usage_summary(self, *, tenant_id: int) -> list[UsageSummaryRead]:
        self._ensure_tenant(tenant_id)
        rows = self._repository.usage_summary(tenant_id=tenant_id)
        return [UsageSummaryRead(metric=metric, total=total) for metric, total in rows]

    def create_api_key(
        self, payload: ApiKeyCreateRequest, *, actor_user_id: int
    ) -> ApiKeyCreateResponse:
        self._ensure_tenant(payload.tenant_id)
        if payload.workspace_id is not None:
            self._assert_workspace_member(payload.workspace_id, actor_user_id)

        plaintext = f"sak_{secrets.token_urlsafe(32)}"
        key_hash = sha256(plaintext.encode("utf-8")).hexdigest()
        key_prefix = plaintext[:14]
        row = self._repository.create_api_key(
            tenant_id=payload.tenant_id,
            workspace_id=payload.workspace_id,
            user_id=actor_user_id,
            key_name=payload.key_name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            key_scope=payload.key_scope,
            expires_at=payload.expires_at,
        )
        self._repository.create_audit_event(
            tenant_id=payload.tenant_id,
            workspace_id=payload.workspace_id,
            actor_user_id=actor_user_id,
            event_type="apikey",
            action="api_key_created",
            details={"api_key_id": row.id, "scope": row.key_scope},
        )
        self._repository.commit()
        return ApiKeyCreateResponse(
            id=row.id,
            key_name=row.key_name,
            key_scope=row.key_scope,
            key_prefix=row.key_prefix,
            token=plaintext,
        )

    def list_api_keys(self, *, tenant_id: int) -> list[ApiKey]:
        self._ensure_tenant(tenant_id)
        return self._repository.list_api_keys(tenant_id=tenant_id)

    def revoke_api_key(self, *, api_key_id: int, actor_user_id: int) -> ApiKey:
        row = self._repository.get_api_key(api_key_id)
        if row is None:
            raise AppException(status_code=404, detail="API key not found")
        self._assert_workspace_member(row.workspace_id, actor_user_id)
        revoked = self._repository.revoke_api_key(api_key_id=api_key_id)
        if revoked is None:
            raise AppException(status_code=404, detail="API key not found")
        self._repository.create_audit_event(
            tenant_id=revoked.tenant_id,
            workspace_id=revoked.workspace_id,
            actor_user_id=actor_user_id,
            event_type="apikey",
            action="api_key_revoked",
            details={"api_key_id": revoked.id},
        )
        self._repository.commit()
        return revoked

    def list_audit_timeline(self, *, tenant_id: int, limit: int) -> list[AuditEvent]:
        self._ensure_tenant(tenant_id)
        return self._repository.list_audit_events(tenant_id=tenant_id, limit=limit)

    def create_notification_channel(
        self, payload: NotificationChannelCreateRequest, *, actor_user_id: int
    ) -> NotificationChannel:
        self._ensure_tenant(payload.tenant_id)
        if payload.workspace_id is not None:
            self._assert_workspace_member(payload.workspace_id, actor_user_id)
        row = self._repository.create_notification_channel(
            tenant_id=payload.tenant_id,
            workspace_id=payload.workspace_id,
            channel_type=payload.channel_type,
            endpoint=payload.endpoint,
            secret_encrypted=None,
        )
        self._repository.create_audit_event(
            tenant_id=payload.tenant_id,
            workspace_id=payload.workspace_id,
            actor_user_id=actor_user_id,
            event_type="notification",
            action="channel_created",
            details={"channel_id": row.id, "type": row.channel_type},
        )
        self._repository.commit()
        return row

    def dispatch_notification(
        self, payload: NotificationDispatchRequest, *, actor_user_id: int
    ) -> NotificationEvent:
        self._ensure_tenant(payload.tenant_id)
        channel = self._repository.get_notification_channel(payload.channel_id)
        if channel is None or channel.tenant_id != payload.tenant_id:
            raise AppException(status_code=404, detail="Notification channel not found")
        row = self._repository.create_notification_event(
            tenant_id=payload.tenant_id,
            channel_id=payload.channel_id,
            template=payload.template,
            payload=payload.payload,
            status="queued",
        )
        self._repository.create_audit_event(
            tenant_id=payload.tenant_id,
            workspace_id=channel.workspace_id,
            actor_user_id=actor_user_id,
            event_type="notification",
            action="notification_dispatched",
            details={"event_id": row.id, "channel_id": channel.id},
        )
        self._repository.commit()
        return row

    def list_notification_events(
        self, *, tenant_id: int, limit: int
    ) -> list[NotificationEvent]:
        self._ensure_tenant(tenant_id)
        return self._repository.list_notification_events(
            tenant_id=tenant_id, limit=limit
        )

    def generate_content_calendar(
        self, payload: ContentCalendarGenerateRequest, *, actor_user_id: int
    ) -> list[ContentCalendarItem]:
        workspace = self._ensure_workspace(payload.tenant_id, payload.workspace_id)
        self._assert_workspace_member(workspace.id, actor_user_id)

        platforms = ["facebook", "instagram", "tiktok", "youtube_shorts"]
        topics = ["product_demo", "deal_alert", "ugc_story", "comparison"]
        created: list[ContentCalendarItem] = []

        for day in range(payload.days):
            suggested_at = payload.start_date + timedelta(days=day)
            platform = platforms[day % len(platforms)]
            topic = topics[day % len(topics)]
            row = self._repository.create_calendar_item(
                tenant_id=payload.tenant_id,
                workspace_id=payload.workspace_id,
                title=f"{topic.replace('_', ' ').title()} #{day + 1}",
                platform=platform,
                suggested_at=suggested_at,
                topic=topic,
                campaign="always_on",
                confidence_score=0.75 + ((day % 5) * 0.04),
            )
            created.append(row)

        self._repository.create_audit_event(
            tenant_id=payload.tenant_id,
            workspace_id=payload.workspace_id,
            actor_user_id=actor_user_id,
            event_type="calendar",
            action="calendar_generated",
            details={"count": len(created)},
        )
        self._repository.commit()
        return created

    def affiliate_insights(
        self, *, tenant_id: int, limit: int
    ) -> list[AffiliateInsight]:
        self._ensure_tenant(tenant_id)
        items = self._repository.list_affiliate_insights(
            tenant_id=tenant_id, limit=limit
        )
        if items:
            return items

        event_counts = self._repository.analytics_event_counts()
        generated = self._repository.create_affiliate_insight(
            tenant_id=tenant_id,
            workspace_id=None,
            insight_type="trend",
            subject="engagement_lift_opportunity",
            score=0.82,
            payload={
                "observed_events": sum(event_counts.values()),
                "top_event": (
                    max(event_counts, key=event_counts.get) if event_counts else "none"
                ),
            },
        )
        self._repository.commit()
        return [generated]

    def create_feedback(
        self, payload: FeedbackCreateRequest, *, actor_user_id: int
    ) -> CustomerFeedback:
        self._ensure_tenant(payload.tenant_id)
        if payload.workspace_id is not None:
            self._assert_workspace_member(payload.workspace_id, actor_user_id)
        row = self._repository.create_feedback(
            tenant_id=payload.tenant_id,
            workspace_id=payload.workspace_id,
            user_id=actor_user_id,
            category=payload.category,
            title=payload.title,
            description=payload.description,
        )
        self._repository.create_audit_event(
            tenant_id=payload.tenant_id,
            workspace_id=payload.workspace_id,
            actor_user_id=actor_user_id,
            event_type="feedback",
            action="feedback_created",
            details={"feedback_id": row.id, "category": row.category},
        )
        self._repository.commit()
        return row

    def list_feedback(self, *, tenant_id: int, limit: int) -> list[CustomerFeedback]:
        self._ensure_tenant(tenant_id)
        return self._repository.list_feedback(tenant_id=tenant_id, limit=limit)

    def customer_health(
        self, *, tenant_id: int, workspace_id: int | None
    ) -> CustomerHealthResponse:
        self._ensure_tenant(tenant_id)
        usage = self._repository.usage_summary(tenant_id=tenant_id)
        feedback = self._repository.list_feedback(tenant_id=tenant_id, limit=200)

        usage_total = sum(item[1] for item in usage)
        open_feedback = sum(1 for item in feedback if item.status == "open")

        score = 50.0
        score += min(35.0, usage_total / 20)
        score -= min(25.0, open_feedback * 3.0)
        score = max(0.0, min(100.0, round(score, 2)))

        if score >= 75:
            risk = "low"
        elif score >= 45:
            risk = "medium"
        else:
            risk = "high"

        factors = [
            f"usage_total={usage_total}",
            f"open_feedback={open_feedback}",
        ]
        return CustomerHealthResponse(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            health_score=score,
            risk_level=risk,
            factors=factors,
        )

    def optimizer_score(self, *, tenant_id: int) -> OptimizerScoreResponse:
        self._ensure_tenant(tenant_id)
        usage = dict(self._repository.usage_summary(tenant_id=tenant_id))
        events = self._repository.analytics_event_counts()

        quality = min(100.0, 60.0 + usage.get("content_generated", 0) * 0.2)
        cost = max(0.0, 90.0 - usage.get("api_calls", 0) * 0.1)
        performance = min(100.0, 50.0 + events.get("post_published", 0) * 0.5)

        return OptimizerScoreResponse(
            tenant_id=tenant_id,
            quality_score=round(quality, 2),
            cost_score=round(cost, 2),
            performance_score=round(performance, 2),
        )

    def marketplace_connector_status(self) -> MarketplaceConnectorResponse:
        return MarketplaceConnectorResponse(
            items=[
                MarketplaceConnectorStatus(
                    connector="shopee",
                    status="active",
                    notes="Real-time parser and validator online",
                ),
                MarketplaceConnectorStatus(
                    connector="lazada",
                    status="beta",
                    notes="Read-only ingestion enabled",
                ),
                MarketplaceConnectorStatus(
                    connector="tiktok_shop",
                    status="planned",
                    notes="Connector scaffold ready for rollout",
                ),
            ]
        )

    def _ensure_tenant(self, tenant_id: int) -> Tenant:
        tenant = self._repository.get_tenant(tenant_id)
        if tenant is None:
            raise AppException(status_code=404, detail="Tenant not found")
        return tenant

    def _ensure_workspace(self, tenant_id: int, workspace_id: int) -> Workspace:
        workspace = self._repository.get_workspace(workspace_id)
        if workspace is None or workspace.tenant_id != tenant_id:
            raise AppException(status_code=404, detail="Workspace not found")
        return workspace

    def _assert_workspace_member(self, workspace_id: int | None, user_id: int) -> None:
        if workspace_id is None:
            return
        member = self._repository.get_workspace_member(
            workspace_id=workspace_id, user_id=user_id
        )
        if member is None:
            raise AppException(status_code=403, detail="Workspace access denied")

    def _assert_workspace_admin(self, workspace_id: int, user_id: int) -> None:
        member = self._repository.get_workspace_member(
            workspace_id=workspace_id, user_id=user_id
        )
        if member is None:
            raise AppException(status_code=403, detail="Workspace access denied")
        if member.role not in {"owner", "admin"}:
            raise AppException(status_code=403, detail="Admin access required")

    def _plan_defaults(
        self, plan: SubscriptionPlan
    ) -> tuple[dict[str, int], dict[str, bool]]:
        if plan == SubscriptionPlan.FREE:
            return (
                {"workspaces": 1, "users": 2, "api_keys": 2, "monthly_posts": 100},
                {
                    "advanced_analytics": False,
                    "priority_support": False,
                    "ab_testing": False,
                },
            )
        if plan == SubscriptionPlan.STARTER:
            return (
                {"workspaces": 3, "users": 10, "api_keys": 10, "monthly_posts": 2000},
                {
                    "advanced_analytics": True,
                    "priority_support": False,
                    "ab_testing": False,
                },
            )
        if plan == SubscriptionPlan.PRO:
            return (
                {"workspaces": 10, "users": 30, "api_keys": 30, "monthly_posts": 20000},
                {
                    "advanced_analytics": True,
                    "priority_support": True,
                    "ab_testing": True,
                },
            )
        if plan == SubscriptionPlan.BUSINESS:
            return (
                {
                    "workspaces": 25,
                    "users": 100,
                    "api_keys": 100,
                    "monthly_posts": 100000,
                },
                {
                    "advanced_analytics": True,
                    "priority_support": True,
                    "ab_testing": True,
                },
            )
        return (
            {
                "workspaces": 100,
                "users": 1000,
                "api_keys": 1000,
                "monthly_posts": 1000000,
            },
            {"advanced_analytics": True, "priority_support": True, "ab_testing": True},
        )
