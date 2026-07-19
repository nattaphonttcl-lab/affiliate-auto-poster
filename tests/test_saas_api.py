from datetime import UTC, datetime

from fastapi.testclient import TestClient


def _create_user_and_token(client: TestClient, email: str) -> tuple[int, str]:
    create_response = client.post(
        "/api/v1/users",
        json={"email": email, "password": "StrongPass123"},
    )
    user_id = create_response.json()["id"]
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    return user_id, login_response.json()["access_token"]


def test_saas_core_flow(client: TestClient) -> None:
    _, token = _create_user_and_token(client, "saas-owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    tenant_response = client.post(
        "/api/v1/saas/tenants",
        json={
            "slug": "tenant-alpha",
            "name": "Tenant Alpha",
            "billing_email": "billing@tenant-alpha.example",
        },
        headers=headers,
    )
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    org_response = client.post(
        "/api/v1/saas/organizations",
        json={"tenant_id": tenant_id, "name": "Alpha Org"},
        headers=headers,
    )
    assert org_response.status_code == 201
    organization_id = org_response.json()["id"]

    workspace_response = client.post(
        "/api/v1/saas/workspaces",
        json={
            "tenant_id": tenant_id,
            "organization_id": organization_id,
            "slug": "main",
            "name": "Main Workspace",
        },
        headers=headers,
    )
    assert workspace_response.status_code == 201
    workspace_id = workspace_response.json()["id"]

    subscription_response = client.put(
        "/api/v1/saas/subscription",
        json={
            "tenant_id": tenant_id,
            "plan": "pro",
            "status": "active",
            "trial_days": 14,
        },
        headers=headers,
    )
    assert subscription_response.status_code == 200
    assert subscription_response.json()["plan"] == "pro"

    usage_response = client.post(
        "/api/v1/saas/usage",
        json={
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "metric": "content_generated",
            "quantity": 7,
            "metadata": {"source": "api-test"},
        },
        headers=headers,
    )
    assert usage_response.status_code == 204

    usage_summary_response = client.get(
        f"/api/v1/saas/usage/{tenant_id}/summary",
        headers=headers,
    )
    assert usage_summary_response.status_code == 200
    items = usage_summary_response.json()
    assert any(item["metric"] == "content_generated" for item in items)

    api_key_response = client.post(
        "/api/v1/saas/api-keys",
        json={
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "key_name": "integration-key",
            "key_scope": "publish",
        },
        headers=headers,
    )
    assert api_key_response.status_code == 201
    api_key_id = api_key_response.json()["id"]
    assert api_key_response.json()["token"].startswith("sak_")

    api_key_list_response = client.get(
        f"/api/v1/saas/api-keys/{tenant_id}",
        headers=headers,
    )
    assert api_key_list_response.status_code == 200
    assert any(item["id"] == api_key_id for item in api_key_list_response.json())

    revoke_response = client.post(
        f"/api/v1/saas/api-keys/{api_key_id}/revoke",
        headers=headers,
    )
    assert revoke_response.status_code == 200
    assert revoke_response.json()["revoked_at"] is not None

    channel_response = client.post(
        "/api/v1/saas/notification-channels",
        json={
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "channel_type": "email",
            "endpoint": "ops@tenant-alpha.example",
        },
        headers=headers,
    )
    assert channel_response.status_code == 201
    channel_id = channel_response.json()["id"]

    dispatch_response = client.post(
        "/api/v1/saas/notifications/dispatch",
        json={
            "tenant_id": tenant_id,
            "channel_id": channel_id,
            "template": "billing_notice",
            "payload": {"amount": 120.5},
        },
        headers=headers,
    )
    assert dispatch_response.status_code == 201

    notification_list_response = client.get(
        f"/api/v1/saas/notifications/{tenant_id}",
        headers=headers,
    )
    assert notification_list_response.status_code == 200
    assert len(notification_list_response.json()) >= 1

    calendar_response = client.post(
        "/api/v1/saas/content-calendar/generate",
        json={
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "start_date": datetime.now(UTC).isoformat(),
            "days": 5,
        },
        headers=headers,
    )
    assert calendar_response.status_code == 201
    assert len(calendar_response.json()) == 5

    feedback_response = client.post(
        "/api/v1/saas/feedback",
        json={
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "category": "ux",
            "title": "Need better report filters",
            "description": "Please add date presets and channel presets.",
        },
        headers=headers,
    )
    assert feedback_response.status_code == 201

    health_response = client.get(
        f"/api/v1/saas/customer-health?tenant_id={tenant_id}&workspace_id={workspace_id}",
        headers=headers,
    )
    assert health_response.status_code == 200
    assert health_response.json()["risk_level"] in {"low", "medium", "high"}

    optimizer_response = client.get(
        f"/api/v1/saas/optimizer/{tenant_id}",
        headers=headers,
    )
    assert optimizer_response.status_code == 200

    connectors_response = client.get(
        "/api/v1/saas/marketplace/connectors",
        headers=headers,
    )
    assert connectors_response.status_code == 200
    assert len(connectors_response.json()["items"]) >= 3

    insights_response = client.get(
        f"/api/v1/saas/insights/{tenant_id}",
        headers=headers,
    )
    assert insights_response.status_code == 200
    assert len(insights_response.json()) >= 1

    audit_response = client.get(
        f"/api/v1/saas/audit/{tenant_id}?limit=20",
        headers=headers,
    )
    assert audit_response.status_code == 200
    assert len(audit_response.json()) >= 1


def test_saas_protected_routes_require_auth(client: TestClient) -> None:
    response = client.get("/api/v1/saas/tenants")
    assert response.status_code == 401
