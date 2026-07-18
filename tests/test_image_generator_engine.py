from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from PIL import Image

from app.models.product import Product
from app.schemas.image import ImageTemplate
from app.utils.image_generator_engine import ImageGeneratorEngine


def _png_bytes(color: tuple[int, int, int]) -> bytes:
    image = Image.new("RGB", (300, 300), color)
    from io import BytesIO

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_image_generator_creates_png_file(tmp_path: Path) -> None:
    product_image_url = "https://cdn.example.com/product.png"
    logo_url = "https://cdn.example.com/logo.png"

    payloads = {
        product_image_url: _png_bytes((220, 130, 90)),
        logo_url: _png_bytes((20, 90, 160)),
    }

    engine = ImageGeneratorEngine(
        output_dir=str(tmp_path),
        timeout_seconds=1.0,
        image_fetcher=lambda source: payloads[source],
    )

    product = Product(
        source_url="https://shopee.co.id/p/test",
        title="Wireless Headset",
        price=Decimal("99.90"),
        original_price=Decimal("129.90"),
        discount="23%",
        rating=4.7,
        sold_count=500,
        images=[product_image_url],
        shop_name="Audio Hub",
        category="Electronics",
        affiliate_url="https://aff.example.com/headset",
        expires_at=datetime.now(UTC),
    )

    result = engine.generate_promotional_cover(product=product, template=ImageTemplate.BOLD, shop_logo_url=logo_url)

    output_path = Path(result.output_path)
    assert output_path.exists()
    assert output_path.suffix.lower() == ".png"
    assert result.width == 820
    assert result.height == 312
