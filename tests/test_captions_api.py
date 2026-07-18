import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.schemas.caption import CaptionStyle
from app.services.shopee_product_service import ShopeeProductService


def _create_user_and_token(client: TestClient) -> str:
    client.post(
        "/api/v1/users",
        json={"email": "captions@example.com", "password": "StrongPass123"},
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "captions@example.com", "password": "StrongPass123"},
    )
    return login_response.json()["access_token"]


def _create_product(client: TestClient, token: str) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/products/shopee",
        json={"url": "https://shopee.co.id/p/portable-blender"},
        headers=headers,
    )
    return response.json()["id"]


@pytest.mark.parametrize("style", [style.value for style in CaptionStyle])
def test_generate_captions_returns_10_items(
    style: str,
    client: TestClient,
    db_session: Session,
    shopee_service_with_static_parser: ShopeeProductService,
) -> None:
    _ = db_session
    _ = shopee_service_with_static_parser

    token = _create_user_and_token(client)
    product_id = _create_product(client, token)

    response = client.post(
        "/api/v1/captions/generate",
        json={"product_id": product_id, "style": style},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["style"] == style
    assert len(body["captions"]) == 10
    assert all(
        "hook" in item and "cta" in item and "emoji" in item and "hashtags" in item
        for item in body["captions"]
    )


def test_generate_captions_returns_404_for_missing_product(client: TestClient) -> None:
    token = _create_user_and_token(client)

    response = client.post(
        "/api/v1/captions/generate",
        json={"product_id": 99999, "style": "funny"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
