from datetime import UTC, datetime
from decimal import Decimal

from app.models.product import Product
from app.schemas.caption import CaptionStyle
from app.utils.ai_caption_engine import AICaptionEngine


def _sample_product() -> Product:
    return Product(
        source_url="https://shopee.co.id/sample",
        title="Portable Blender",
        price=Decimal("149.00"),
        original_price=Decimal("199.00"),
        discount="25%",
        rating=4.9,
        sold_count=1200,
        images=["https://cdn.example.com/blender.jpg"],
        shop_name="Kitchen Hub",
        category="Home Appliances",
        affiliate_url="https://aff.example.com/blender",
        expires_at=datetime.now(UTC),
    )


def test_ai_caption_engine_generates_10_captions_for_each_style() -> None:
    engine = AICaptionEngine()
    product = _sample_product()

    for style in CaptionStyle:
        generated = engine.generate(product, style)
        assert len(generated) == 10
        for item in generated:
            assert item.hook
            assert item.cta
            assert item.emoji
            assert item.hashtags
            assert item.caption_text
            assert "#" in item.caption_text
