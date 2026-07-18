from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import get_shopee_product_service
from app.core.config import get_settings
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductPayload
from app.services.shopee_product_service import ShopeeProductService
from app.utils.shopee_validator import ShopeeProductValidator


class CountingParser:
    def __init__(self) -> None:
        self.calls = 0

    def parse(self, url: str) -> ProductPayload:
        self.calls += 1
        return ProductPayload(
            title="Shopee Keyboard",
            price=Decimal("49.90"),
            original_price=Decimal("59.90"),
            discount="17%",
            rating=4.7,
            sold_count=200,
            images=["https://cdn.example.com/image.jpg"],
            shop_name="Keyboard Store",
            category="Electronics",
            affiliate_url=url,
        )


def _create_user_and_token(client: TestClient) -> str:
    client.post(
        "/api/v1/users",
        json={"email": "shopper@example.com", "password": "StrongPass123"},
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "shopper@example.com", "password": "StrongPass123"},
    )
    return login_response.json()["access_token"]


def test_shopee_product_endpoint_uses_cache(client: TestClient, db_session: Session) -> None:
    parser = CountingParser()
    settings = get_settings()
    repository = ProductRepository(db_session)
    service = ShopeeProductService(repository, parser, ShopeeProductValidator(), settings)

    def override_service() -> ShopeeProductService:
        return service

    client.app.dependency_overrides[get_shopee_product_service] = override_service

    try:
        token = _create_user_and_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"url": "https://shopee.co.id/product/123"}

        first_response = client.post("/api/v1/products/shopee", json=payload, headers=headers)
        second_response = client.post("/api/v1/products/shopee", json=payload, headers=headers)

        assert first_response.status_code == 200
        assert second_response.status_code == 200
        assert first_response.json()["title"] == "Shopee Keyboard"
        assert second_response.json()["title"] == "Shopee Keyboard"
        assert parser.calls == 1
    finally:
        client.app.dependency_overrides.pop(get_shopee_product_service, None)
