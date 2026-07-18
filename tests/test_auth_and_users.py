from fastapi.testclient import TestClient


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
