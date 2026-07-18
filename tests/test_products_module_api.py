from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import get_product_service
from app.core.cache import InMemoryTTLCache
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductPayload
from app.services.product_service import ProductService
from app.services.refresh_queue import InMemoryProductRefreshQueue
from app.services.marketplace_provider import (
    MarketplaceProviderRegistry,
    ShopeeProvider,
)


class _Parser:
    def parse(self, url: str) -> ProductPayload:
        return ProductPayload(
            marketplace="shopee",
            normalized_url=url,
            external_product_id="7788",
            title="API Product",
            price=Decimal("129.00"),
            original_price=Decimal("149.00"),
            discount="13%",
            rating=4.9,
            sold_count=300,
            images=["https://cdn.example.com/api.png"],
            shop_name="API Shop",
            category="Home",
            affiliate_url=url,
        )


class _Validator:
    def validate_url(self, _: str) -> None:
        return None

    def validate_payload(self, _: ProductPayload) -> None:
        return None


def _create_user_and_token(client: TestClient) -> str:
    client.post(
        "/api/v1/users",
        json={"email": "products-api@example.com", "password": "StrongPass123"},
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "products-api@example.com", "password": "StrongPass123"},
    )
    return login_response.json()["access_token"]


def test_products_api_import_list_get_update_refresh_delete(
    client: TestClient,
    db_session: Session,
) -> None:
    repository = ProductRepository(db_session)
    registry = MarketplaceProviderRegistry(
        providers=[ShopeeProvider(parser=_Parser(), validator=_Validator())]
    )
    service = ProductService(
        repository,
        registry,
        InMemoryTTLCache(),
        InMemoryProductRefreshQueue(),
        cache_ttl_minutes=60,
    )

    client.app.dependency_overrides[get_product_service] = lambda: service
    try:
        token = _create_user_and_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        import_response = client.post(
            "/api/v1/products/import",
            json={"url": "https://shopee.co.id/product/1/7788?ref=abc"},
            headers=headers,
        )
        assert import_response.status_code == 201
        product_id = import_response.json()["id"]

        list_response = client.get(
            "/api/v1/products?limit=10&offset=0", headers=headers
        )
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 1

        get_response = client.get(f"/api/v1/products/{product_id}", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["title"] == "API Product"

        patch_response = client.patch(
            f"/api/v1/products/{product_id}",
            json={"title": "API Product Updated"},
            headers=headers,
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["title"] == "API Product Updated"

        refresh_response = client.post(
            f"/api/v1/products/{product_id}/refresh?background=false",
            headers=headers,
        )
        assert refresh_response.status_code == 200

        delete_response = client.delete(
            f"/api/v1/products/{product_id}",
            headers=headers,
        )
        assert delete_response.status_code == 204
    finally:
        client.app.dependency_overrides.pop(get_product_service, None)
