from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.analytics_event import AnalyticsEvent
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
    UsageRecord,
    Workspace,
    WorkspaceMember,
)


class SaaSRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_tenant(self, *, slug: str, name: str, billing_email: str) -> Tenant:
        row = Tenant(slug=slug, name=name, billing_email=billing_email)
        self._db.add(row)
        self._db.flush()
        return row

    def list_tenants(self) -> list[Tenant]:
        return list(self._db.scalars(select(Tenant).order_by(Tenant.id.asc())))

    def get_tenant(self, tenant_id: int) -> Tenant | None:
        return self._db.get(Tenant, tenant_id)

    def create_organization(self, *, tenant_id: int, name: str) -> Organization:
        row = Organization(tenant_id=tenant_id, name=name)
        self._db.add(row)
        self._db.flush()
        return row

    def get_organization(self, organization_id: int) -> Organization | None:
        return self._db.get(Organization, organization_id)

    def create_workspace(
        self, *, tenant_id: int, organization_id: int, slug: str, name: str
    ) -> Workspace:
        row = Workspace(
            tenant_id=tenant_id,
            organization_id=organization_id,
            slug=slug,
            name=name,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def get_workspace(self, workspace_id: int) -> Workspace | None:
        return self._db.get(Workspace, workspace_id)

    def get_workspace_member(
        self, *, workspace_id: int, user_id: int
    ) -> WorkspaceMember | None:
        stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        return self._db.scalar(stmt)

    def upsert_member(
        self,
        *,
        tenant_id: int,
        workspace_id: int,
        user_id: int,
        role: str,
        permissions: list[str],
    ) -> WorkspaceMember:
        stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        row = self._db.scalar(stmt)
        if row is None:
            row = WorkspaceMember(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                user_id=user_id,
                role=role,
                permissions=permissions,
            )
        else:
            row.role = role
            row.permissions = permissions
        self._db.add(row)
        self._db.flush()
        return row

    def create_invitation(
        self,
        *,
        tenant_id: int,
        workspace_id: int,
        email: str,
        role: str,
        token: str,
        expires_at: datetime,
    ) -> Invitation:
        row = Invitation(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            email=email,
            role=role,
            token=token,
            expires_at=expires_at,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def upsert_subscription(
        self,
        *,
        tenant_id: int,
        plan: str,
        status: str,
        trial_ends_at: datetime | None,
        current_period_end: datetime | None,
        grace_period_ends_at: datetime | None,
        limits: dict[str, int],
        feature_flags: dict[str, bool],
    ) -> Subscription:
        stmt = select(Subscription).where(Subscription.tenant_id == tenant_id)
        row = self._db.scalar(stmt)
        if row is None:
            row = Subscription(
                tenant_id=tenant_id,
                plan=plan,
                status=status,
                trial_ends_at=trial_ends_at,
                current_period_end=current_period_end,
                grace_period_ends_at=grace_period_ends_at,
                limits=limits,
                feature_flags=feature_flags,
            )
        else:
            row.plan = plan
            row.status = status
            row.trial_ends_at = trial_ends_at
            row.current_period_end = current_period_end
            row.grace_period_ends_at = grace_period_ends_at
            row.limits = limits
            row.feature_flags = feature_flags
        self._db.add(row)
        self._db.flush()
        return row

    def create_payment(
        self,
        *,
        tenant_id: int,
        provider: str,
        external_payment_id: str,
        amount: float,
        currency: str,
        status: str,
        payload: dict[str, str | int | float | bool | None],
    ) -> PaymentTransaction:
        row = PaymentTransaction(
            tenant_id=tenant_id,
            provider=provider,
            external_payment_id=external_payment_id,
            amount=amount,
            currency=currency,
            status=status,
            payload=payload,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def list_payments(self, *, tenant_id: int) -> list[PaymentTransaction]:
        stmt = select(PaymentTransaction).where(
            PaymentTransaction.tenant_id == tenant_id
        )
        return list(self._db.scalars(stmt))

    def record_usage(
        self,
        *,
        tenant_id: int,
        workspace_id: int | None,
        metric: str,
        quantity: int,
        metadata: dict[str, str | int | float | bool | None],
    ) -> UsageRecord:
        row = UsageRecord(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            metric=metric,
            quantity=quantity,
            usage_metadata=metadata,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def usage_summary(self, *, tenant_id: int) -> list[tuple[str, int]]:
        stmt = (
            select(UsageRecord.metric, func.sum(UsageRecord.quantity))
            .where(UsageRecord.tenant_id == tenant_id)
            .group_by(UsageRecord.metric)
            .order_by(UsageRecord.metric.asc())
        )
        rows = self._db.execute(stmt).all()
        return [(str(metric), int(total or 0)) for metric, total in rows]

    def create_api_key(
        self,
        *,
        tenant_id: int,
        workspace_id: int | None,
        user_id: int,
        key_name: str,
        key_prefix: str,
        key_hash: str,
        key_scope: str,
        expires_at: datetime | None,
    ) -> ApiKey:
        row = ApiKey(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            user_id=user_id,
            key_name=key_name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            key_scope=key_scope,
            expires_at=expires_at,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def list_api_keys(self, *, tenant_id: int) -> list[ApiKey]:
        stmt = (
            select(ApiKey)
            .where(ApiKey.tenant_id == tenant_id)
            .order_by(ApiKey.id.asc())
        )
        return list(self._db.scalars(stmt))

    def get_api_key(self, api_key_id: int) -> ApiKey | None:
        return self._db.get(ApiKey, api_key_id)

    def revoke_api_key(self, *, api_key_id: int) -> ApiKey | None:
        row = self.get_api_key(api_key_id)
        if row is None:
            return None
        row.revoked_at = datetime.now(UTC)
        self._db.add(row)
        self._db.flush()
        return row

    def create_audit_event(
        self,
        *,
        tenant_id: int,
        workspace_id: int | None,
        actor_user_id: int | None,
        event_type: str,
        action: str,
        details: dict[str, str | int | float | bool | None],
    ) -> AuditEvent:
        row = AuditEvent(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            action=action,
            details=details,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def list_audit_events(self, *, tenant_id: int, limit: int) -> list[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .where(AuditEvent.tenant_id == tenant_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
        )
        return list(self._db.scalars(stmt))

    def create_notification_channel(
        self,
        *,
        tenant_id: int,
        workspace_id: int | None,
        channel_type: str,
        endpoint: str,
        secret_encrypted: str | None,
    ) -> NotificationChannel:
        row = NotificationChannel(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            channel_type=channel_type,
            endpoint=endpoint,
            secret_encrypted=secret_encrypted,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def get_notification_channel(self, channel_id: int) -> NotificationChannel | None:
        return self._db.get(NotificationChannel, channel_id)

    def create_notification_event(
        self,
        *,
        tenant_id: int,
        channel_id: int,
        template: str,
        payload: dict[str, str | int | float | bool | None],
        status: str,
    ) -> NotificationEvent:
        row = NotificationEvent(
            tenant_id=tenant_id,
            channel_id=channel_id,
            template=template,
            payload=payload,
            status=status,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def list_notification_events(
        self, *, tenant_id: int, limit: int
    ) -> list[NotificationEvent]:
        stmt = (
            select(NotificationEvent)
            .where(NotificationEvent.tenant_id == tenant_id)
            .order_by(NotificationEvent.created_at.desc())
            .limit(limit)
        )
        return list(self._db.scalars(stmt))

    def create_calendar_item(
        self,
        *,
        tenant_id: int,
        workspace_id: int,
        title: str,
        platform: str,
        suggested_at: datetime,
        topic: str,
        campaign: str | None,
        confidence_score: float,
    ) -> ContentCalendarItem:
        row = ContentCalendarItem(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            title=title,
            platform=platform,
            suggested_at=suggested_at,
            topic=topic,
            campaign=campaign,
            confidence_score=confidence_score,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def list_calendar_items(
        self, *, workspace_id: int, limit: int
    ) -> list[ContentCalendarItem]:
        stmt = (
            select(ContentCalendarItem)
            .where(ContentCalendarItem.workspace_id == workspace_id)
            .order_by(ContentCalendarItem.suggested_at.asc())
            .limit(limit)
        )
        return list(self._db.scalars(stmt))

    def create_affiliate_insight(
        self,
        *,
        tenant_id: int,
        workspace_id: int | None,
        insight_type: str,
        subject: str,
        score: float,
        payload: dict[str, str | int | float | bool | None],
    ) -> AffiliateInsight:
        row = AffiliateInsight(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            insight_type=insight_type,
            subject=subject,
            score=score,
            payload=payload,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def list_affiliate_insights(
        self, *, tenant_id: int, limit: int
    ) -> list[AffiliateInsight]:
        stmt = (
            select(AffiliateInsight)
            .where(AffiliateInsight.tenant_id == tenant_id)
            .order_by(AffiliateInsight.created_at.desc())
            .limit(limit)
        )
        return list(self._db.scalars(stmt))

    def create_feedback(
        self,
        *,
        tenant_id: int,
        workspace_id: int | None,
        user_id: int | None,
        category: str,
        title: str,
        description: str,
    ) -> CustomerFeedback:
        row = CustomerFeedback(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            user_id=user_id,
            category=category,
            title=title,
            description=description,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def list_feedback(self, *, tenant_id: int, limit: int) -> list[CustomerFeedback]:
        stmt = (
            select(CustomerFeedback)
            .where(CustomerFeedback.tenant_id == tenant_id)
            .order_by(CustomerFeedback.created_at.desc())
            .limit(limit)
        )
        return list(self._db.scalars(stmt))

    def analytics_event_counts(self) -> dict[str, int]:
        stmt = (
            select(AnalyticsEvent.event_type, func.count(AnalyticsEvent.id))
            .group_by(AnalyticsEvent.event_type)
            .order_by(AnalyticsEvent.event_type.asc())
        )
        rows = self._db.execute(stmt).all()
        return {str(k): int(v or 0) for k, v in rows}

    def commit(self) -> None:
        self._db.commit()

    def rollback(self) -> None:
        self._db.rollback()
