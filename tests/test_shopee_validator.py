import pytest

from app.core.exceptions import AppException
from app.schemas.product import ProductPayload
from app.utils.shopee_validator import ShopeeProductValidator


@pytest.mark.parametrize(
    "invalid_url",
    [
        "ftp://shopee.co.id/product",
        "https://example.com/product",
    ],
)
def test_validate_url_rejects_invalid_hosts_or_schemes(invalid_url: str) -> None:
    validator = ShopeeProductValidator()

    with pytest.raises(AppException):
        validator.validate_url(invalid_url)


def test_validate_payload_rejects_non_positive_price() -> None:
    validator = ShopeeProductValidator()
    payload = ProductPayload(
        marketplace="shopee",
        normalized_url="https://shopee.co.id/product",
        title="Product",
        price=0,
        images=[],
        affiliate_url="https://shopee.co.id/product",
    )

    with pytest.raises(AppException):
        validator.validate_payload(payload)
