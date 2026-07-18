from __future__ import annotations

import io
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import httpx
from PIL import Image, ImageDraw, ImageFont

from app.core.exceptions import AppException
from app.models.product import Product
from app.schemas.image import ImageTemplate
from app.utils.image_templates import TEMPLATE_STYLES


@dataclass(frozen=True)
class GeneratedImageResult:
    output_path: str
    width: int
    height: int
    output_format: str
    product_image_url: str
    shop_logo_url: str | None


class ImageGeneratorEngine:
    def __init__(
        self,
        *,
        output_dir: str,
        timeout_seconds: float,
        image_fetcher: Callable[[str], bytes] | None = None,
    ) -> None:
        self._output_dir = Path(output_dir)
        self._timeout_seconds = timeout_seconds
        self._image_fetcher = image_fetcher
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def generate_promotional_cover(
        self,
        *,
        product: Product,
        template: ImageTemplate,
        shop_logo_url: str | None,
    ) -> GeneratedImageResult:
        if not product.images:
            raise AppException(status_code=422, detail="Product does not have an image for promotional cover")

        width, height = 820, 312
        canvas = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(canvas)

        style = TEMPLATE_STYLES[template]
        self._draw_gradient(canvas, style.background_start, style.background_end)

        product_image_url = product.images[0]
        product_image = self._load_image(product_image_url).convert("RGBA")
        product_image = self._fit_image(product_image, (300, 272))
        canvas.paste(product_image, (16, 20), product_image)

        if shop_logo_url:
            logo_image = self._fit_image(self._load_image(shop_logo_url).convert("RGBA"), (56, 56))
            canvas.paste(logo_image, (744, 16), logo_image)
        else:
            self._draw_logo_placeholder(draw, product.shop_name or "SHOP", (744, 16, 800, 72), style.accent)

        font_title = self._load_font(30)
        font_price = self._load_font(42)
        font_meta = self._load_font(22)
        font_cta = self._load_font(24)

        title = (product.title[:54] + "...") if len(product.title) > 57 else product.title
        price_text = f"Rp {product.price:,.2f}"
        discount_text = product.discount or "Best Offer"

        draw.text((336, 44), title, fill=style.text_primary, font=font_title)
        draw.text((336, 104), price_text, fill=style.accent, font=font_price)
        draw.text((336, 164), f"Discount: {discount_text}", fill=style.text_secondary, font=font_meta)

        if product.original_price is not None:
            draw.text((336, 196), f"Before: Rp {product.original_price:,.2f}", fill=style.text_secondary, font=font_meta)

        shop_label = product.shop_name or "Official Shop"
        draw.text((336, 228), f"Shop: {shop_label}", fill=style.text_secondary, font=font_meta)

        cta_box = (336, 258, 564, 298)
        draw.rounded_rectangle(cta_box, radius=12, fill=style.accent)
        draw.text((354, 265), "SHOP NOW ON SHOPEE", fill=(0, 0, 0), font=font_cta)

        filename = f"promo_{uuid4().hex}.png"
        output_file = self._output_dir / filename
        canvas.convert("RGB").save(output_file, format="PNG")

        return GeneratedImageResult(
            output_path=str(output_file),
            width=width,
            height=height,
            output_format="png",
            product_image_url=product_image_url,
            shop_logo_url=shop_logo_url,
        )

    def _draw_gradient(self, image: Image.Image, start: tuple[int, int, int], end: tuple[int, int, int]) -> None:
        width, height = image.size
        draw = ImageDraw.Draw(image)
        for y in range(height):
            ratio = y / max(height - 1, 1)
            color = tuple(int(start[idx] + (end[idx] - start[idx]) * ratio) for idx in range(3))
            draw.line([(0, y), (width, y)], fill=color)

    def _load_image(self, source: str) -> Image.Image:
        data = self._fetch_bytes(source)
        try:
            return Image.open(io.BytesIO(data))
        except Exception as exc:
            raise AppException(status_code=422, detail="Failed to decode image content") from exc

    def _fetch_bytes(self, source: str) -> bytes:
        if self._image_fetcher is not None:
            return self._image_fetcher(source)

        if source.startswith(("http://", "https://")):
            try:
                response = httpx.get(source, timeout=self._timeout_seconds)
                response.raise_for_status()
                return response.content
            except httpx.HTTPError as exc:
                raise AppException(status_code=502, detail="Failed to fetch remote image") from exc

        path = Path(source)
        if not path.exists():
            raise AppException(status_code=422, detail="Image source path does not exist")

        return path.read_bytes()

    def _fit_image(self, image: Image.Image, target_size: tuple[int, int]) -> Image.Image:
        target_w, target_h = target_size
        src_w, src_h = image.size

        scale = max(target_w / src_w, target_h / src_h)
        resized = image.resize((int(src_w * scale), int(src_h * scale)))

        left = max((resized.width - target_w) // 2, 0)
        top = max((resized.height - target_h) // 2, 0)
        right = left + target_w
        bottom = top + target_h
        return resized.crop((left, top, right, bottom))

    def _load_font(self, size: int) -> ImageFont.ImageFont:
        for candidate in ("DejaVuSans-Bold.ttf", "arial.ttf"):
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def _draw_logo_placeholder(
        self,
        draw: ImageDraw.ImageDraw,
        shop_name: str,
        box: tuple[int, int, int, int],
        accent: tuple[int, int, int],
    ) -> None:
        draw.rounded_rectangle(box, radius=12, fill=accent)
        initials = "".join(word[0] for word in shop_name.split()[:2]).upper() or "S"
        draw.text((box[0] + 12, box[1] + 16), initials, fill=(0, 0, 0), font=self._load_font(24))
