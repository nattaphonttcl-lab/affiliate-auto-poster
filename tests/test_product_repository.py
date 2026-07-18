from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductPayload


def _payload(url: str) -> ProductPayload:
    return ProductPayload(
        marketplace="shopee",
        normalized_url=url,
        external_product_id="1001",
        title="Repo Product",
        price=Decimal("88.00"),
        original_price=Decimal("99.00"),
        discount="11%",
        rating=4.6,
        sold_count=120,
        images=["https://cdn.example.com/repo.png"],
        shop_name="Repo Shop",
        category="Electronics",
        affiliate_url=url,
    )


def test_upsert_from_provider_creates_aggregate_and_history(
    db_session: Session,
) -> None:
    repository = ProductRepository(db_session)
    now = datetime.now(UTC)

    product = repository.upsert_from_provider(
        source_url="https://shopee.co.id/product/1/1001?x=1",
        normalized_url="https://shopee.co.id/product/1/1001",
        marketplace="shopee",
        external_product_id="1001",
        fingerprint="fp-1001",
        payload=_payload("https://shopee.co.id/product/1/1001"),
        now=now,
        ttl_minutes=60,
        change_reason="import",
    )

    assert product.id > 0
    assert product.category == "Electronics"
    assert product.images == ["https://cdn.example.com/repo.png"]
    assert product.aggregate_version == 1
    assert len(product.image_items) == 1
    assert len(product.price_history_items) == 1
    assert len(product.version_history_items) == 1
