from fastapi.testclient import TestClient

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import verify_password
from app.repositories.user_repository import UserRepository
from app.services.bootstrap_service import BootstrapService


def test_create_user_and_login_and_access_protected_route(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/users",
        json={"email": "owner@example.com", "password": "StrongPass123"},
    )
    assert create_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "StrongPass123"},
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    protected_response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert protected_response.status_code == 200
    assert len(protected_response.json()) == 1


def test_protected_route_requires_token(client: TestClient) -> None:
    response = client.get("/api/v1/users")
    assert response.status_code == 401


def test_bootstrap_admin_login_and_password_rotation(
    client: TestClient, db_session: Session
) -> None:
    settings = get_settings()
    BootstrapService(lambda: db_session, settings).run()

    user = UserRepository(db_session).get_by_email(settings.initial_admin_email)
    assert user is not None
    assert verify_password(settings.initial_admin_password, user.hashed_password)

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": settings.initial_admin_email,
            "password": settings.initial_admin_password,
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    blocked_response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert blocked_response.status_code == 403
    assert blocked_response.json()["detail"] == "Password change required"

    change_response = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": settings.initial_admin_password,
            "new_password": "ChangedPass123!",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert change_response.status_code == 204

    relogin_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": settings.initial_admin_email,
            "password": "ChangedPass123!",
        },
    )
    assert relogin_response.status_code == 200

    fresh_token = relogin_response.json()["access_token"]
    allowed_response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {fresh_token}"},
    )
    assert allowed_response.status_code == 200
