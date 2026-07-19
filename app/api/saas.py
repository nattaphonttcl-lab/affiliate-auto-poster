from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_current_user_id, get_saas_service
from app.schemas.saas import (
    AffiliateInsightRead,
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyRead,
    AuditEventRead,
    ContentCalendarGenerateRequest,
    ContentCalendarItemRead,
    CustomerHealthResponse,
    FeedbackCreateRequest,
    FeedbackRead,
    InvitationCreateRequest,
    InvitationRead,
    MarketplaceConnectorResponse,
    NotificationChannelCreateRequest,
    NotificationChannelRead,
    NotificationDispatchRequest,
    NotificationEventRead,
    OptimizerScoreResponse,
    OrganizationCreateRequest,
    OrganizationRead,
    PaymentTransactionRead,
    PaymentWebhookRequest,
    SubscriptionRead,
    SubscriptionUpsertRequest,
    TenantCreateRequest,
    TenantRead,
    UsageRecordCreateRequest,
    UsageSummaryRead,
    WorkspaceCreateRequest,
    WorkspaceMemberRead,
    WorkspaceMemberUpsertRequest,
    WorkspaceRead,
)
from app.services.saas_service import SaaSService

router = APIRouter(prefix="/saas", tags=["saas"])


@router.post("/tenants", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
def create_tenant(
    payload: TenantCreateRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> TenantRead:
    return TenantRead.model_validate(
        service.create_tenant(payload=payload, actor_user_id=current_user_id)
    )


@router.get("/tenants", response_model=list[TenantRead], status_code=status.HTTP_200_OK)
def list_tenants(
    _: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> list[TenantRead]:
    return [TenantRead.model_validate(item) for item in service.list_tenants()]


@router.post(
    "/organizations",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_organization(
    payload: OrganizationCreateRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> OrganizationRead:
    return OrganizationRead.model_validate(
        service.create_organization(payload=payload, actor_user_id=current_user_id)
    )


@router.post(
    "/workspaces", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED
)
def create_workspace(
    payload: WorkspaceCreateRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> WorkspaceRead:
    return WorkspaceRead.model_validate(
        service.create_workspace(payload=payload, actor_user_id=current_user_id)
    )


@router.put(
    "/workspace-members",
    response_model=WorkspaceMemberRead,
    status_code=status.HTTP_200_OK,
)
def upsert_workspace_member(
    payload: WorkspaceMemberUpsertRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> WorkspaceMemberRead:
    return WorkspaceMemberRead.model_validate(
        service.upsert_workspace_member(payload=payload, actor_user_id=current_user_id)
    )


@router.post(
    "/invitations", response_model=InvitationRead, status_code=status.HTTP_201_CREATED
)
def create_invitation(
    payload: InvitationCreateRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> InvitationRead:
    return InvitationRead.model_validate(
        service.create_invitation(payload=payload, actor_user_id=current_user_id)
    )


@router.put(
    "/subscription",
    response_model=SubscriptionRead,
    status_code=status.HTTP_200_OK,
)
def upsert_subscription(
    payload: SubscriptionUpsertRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> SubscriptionRead:
    return SubscriptionRead.model_validate(
        service.upsert_subscription(payload=payload, actor_user_id=current_user_id)
    )


@router.post(
    "/payments/webhook",
    response_model=PaymentTransactionRead,
    status_code=status.HTTP_201_CREATED,
)
def payment_webhook(
    payload: PaymentWebhookRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> PaymentTransactionRead:
    return PaymentTransactionRead.model_validate(
        service.record_payment_webhook(payload=payload, actor_user_id=current_user_id)
    )


@router.get(
    "/payments/{tenant_id}",
    response_model=list[PaymentTransactionRead],
    status_code=status.HTTP_200_OK,
)
def list_payments(
    tenant_id: int,
    _: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> list[PaymentTransactionRead]:
    return [
        PaymentTransactionRead.model_validate(item)
        for item in service.list_payments(tenant_id=tenant_id)
    ]


@router.post("/usage", status_code=status.HTTP_204_NO_CONTENT)
def record_usage(
    payload: UsageRecordCreateRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> Response:
    service.record_usage(payload=payload, actor_user_id=current_user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/usage/{tenant_id}/summary",
    response_model=list[UsageSummaryRead],
    status_code=status.HTTP_200_OK,
)
def usage_summary(
    tenant_id: int,
    _: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> list[UsageSummaryRead]:
    return service.usage_summary(tenant_id=tenant_id)


@router.post(
    "/api-keys",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_api_key(
    payload: ApiKeyCreateRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> ApiKeyCreateResponse:
    return service.create_api_key(payload=payload, actor_user_id=current_user_id)


@router.get(
    "/api-keys/{tenant_id}",
    response_model=list[ApiKeyRead],
    status_code=status.HTTP_200_OK,
)
def list_api_keys(
    tenant_id: int,
    _: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> list[ApiKeyRead]:
    return [
        ApiKeyRead.model_validate(item)
        for item in service.list_api_keys(tenant_id=tenant_id)
    ]


@router.post(
    "/api-keys/{api_key_id}/revoke",
    response_model=ApiKeyRead,
    status_code=status.HTTP_200_OK,
)
def revoke_api_key(
    api_key_id: int,
    current_user_id: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> ApiKeyRead:
    return ApiKeyRead.model_validate(
        service.revoke_api_key(api_key_id=api_key_id, actor_user_id=current_user_id)
    )


@router.get(
    "/audit/{tenant_id}",
    response_model=list[AuditEventRead],
    status_code=status.HTTP_200_OK,
)
def list_audit_timeline(
    tenant_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    _: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> list[AuditEventRead]:
    return [
        AuditEventRead.model_validate(item)
        for item in service.list_audit_timeline(tenant_id=tenant_id, limit=limit)
    ]


@router.post(
    "/notification-channels",
    response_model=NotificationChannelRead,
    status_code=status.HTTP_201_CREATED,
)
def create_notification_channel(
    payload: NotificationChannelCreateRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> NotificationChannelRead:
    return NotificationChannelRead.model_validate(
        service.create_notification_channel(
            payload=payload, actor_user_id=current_user_id
        )
    )


@router.post(
    "/notifications/dispatch",
    response_model=NotificationEventRead,
    status_code=status.HTTP_201_CREATED,
)
def dispatch_notification(
    payload: NotificationDispatchRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> NotificationEventRead:
    return NotificationEventRead.model_validate(
        service.dispatch_notification(payload=payload, actor_user_id=current_user_id)
    )


@router.get(
    "/notifications/{tenant_id}",
    response_model=list[NotificationEventRead],
    status_code=status.HTTP_200_OK,
)
def list_notification_events(
    tenant_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    _: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> list[NotificationEventRead]:
    return [
        NotificationEventRead.model_validate(item)
        for item in service.list_notification_events(tenant_id=tenant_id, limit=limit)
    ]


@router.post(
    "/content-calendar/generate",
    response_model=list[ContentCalendarItemRead],
    status_code=status.HTTP_201_CREATED,
)
def generate_content_calendar(
    payload: ContentCalendarGenerateRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> list[ContentCalendarItemRead]:
    return [
        ContentCalendarItemRead.model_validate(item)
        for item in service.generate_content_calendar(
            payload=payload, actor_user_id=current_user_id
        )
    ]


@router.get(
    "/insights/{tenant_id}",
    response_model=list[AffiliateInsightRead],
    status_code=status.HTTP_200_OK,
)
def list_insights(
    tenant_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    _: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> list[AffiliateInsightRead]:
    return [
        AffiliateInsightRead.model_validate(item)
        for item in service.affiliate_insights(tenant_id=tenant_id, limit=limit)
    ]


@router.post(
    "/feedback", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED
)
def create_feedback(
    payload: FeedbackCreateRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> FeedbackRead:
    return FeedbackRead.model_validate(
        service.create_feedback(payload=payload, actor_user_id=current_user_id)
    )


@router.get(
    "/feedback/{tenant_id}",
    response_model=list[FeedbackRead],
    status_code=status.HTTP_200_OK,
)
def list_feedback(
    tenant_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    _: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> list[FeedbackRead]:
    return [
        FeedbackRead.model_validate(item)
        for item in service.list_feedback(tenant_id=tenant_id, limit=limit)
    ]


@router.get(
    "/customer-health",
    response_model=CustomerHealthResponse,
    status_code=status.HTTP_200_OK,
)
def customer_health(
    tenant_id: int = Query(ge=1),
    workspace_id: int | None = Query(default=None, ge=1),
    _: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> CustomerHealthResponse:
    return service.customer_health(tenant_id=tenant_id, workspace_id=workspace_id)


@router.get(
    "/optimizer/{tenant_id}",
    response_model=OptimizerScoreResponse,
    status_code=status.HTTP_200_OK,
)
def optimizer_score(
    tenant_id: int,
    _: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> OptimizerScoreResponse:
    return service.optimizer_score(tenant_id=tenant_id)


@router.get(
    "/marketplace/connectors",
    response_model=MarketplaceConnectorResponse,
    status_code=status.HTTP_200_OK,
)
def marketplace_connectors(
    _: int = Depends(get_current_user_id),
    service: SaaSService = Depends(get_saas_service),
) -> MarketplaceConnectorResponse:
    return service.marketplace_connector_status()
