from __future__ import annotations

import json
import re
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.core.exceptions import AppException
from app.schemas.product import ProductPayload


class ShopeeProductParser:
    def __init__(
        self,
        *,
        timeout_seconds: float,
        html_fetcher: Callable[[str], str] | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._html_fetcher = html_fetcher

    def parse(self, url: str) -> ProductPayload:
        html = self._fetch_html(url)

        state = self._extract_state_blob(html)
        candidate = self._find_product_candidate(state) if state else None

        payload = self._build_payload_from_candidate(url, candidate)
        if payload:
            return payload

        fallback_payload = self._build_payload_from_meta(url, html)
        if fallback_payload:
            return fallback_payload

        raise AppException(
            status_code=422,
            detail="Unable to parse Shopee product from the provided URL",
        )

    def _fetch_html(self, url: str) -> str:
        if self._html_fetcher is not None:
            return self._html_fetcher(url)

        try:
            response = httpx.get(
                url, follow_redirects=True, timeout=self._timeout_seconds
            )
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as exc:
            raise AppException(
                status_code=502, detail="Failed to fetch Shopee product page"
            ) from exc

    def _extract_state_blob(self, html: str) -> dict[str, Any] | None:
        markers = [
            "window.__INITIAL_STATE__",
            "window.__PRELOADED_STATE__",
            "window.__NEXT_DATA__",
        ]

        for marker in markers:
            extracted = self._extract_json_object_after_marker(html, marker)
            if extracted is not None:
                return extracted

        return None

    def _extract_json_object_after_marker(
        self, text: str, marker: str
    ) -> dict[str, Any] | None:
        index = text.find(marker)
        if index < 0:
            return None

        start = text.find("{", index)
        if start < 0:
            return None

        end = self._find_matching_brace(text, start)
        if end < 0:
            return None

        raw = text[start : end + 1]
        try:
            loaded = json.loads(raw)
            if isinstance(loaded, dict):
                return loaded
        except json.JSONDecodeError:
            return None

        return None

    def _find_matching_brace(self, text: str, start: int) -> int:
        depth = 0
        in_string = False
        escaped = False

        for idx in range(start, len(text)):
            char = text[idx]

            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return idx

        return -1

    def _find_product_candidate(self, state: dict[str, Any]) -> dict[str, Any] | None:
        stack: list[Any] = [state]
        while stack:
            node = stack.pop()

            if isinstance(node, dict):
                keys = set(node.keys())
                if (
                    {"name", "price"}.issubset(keys)
                    or {"title", "price"}.issubset(keys)
                ) and ("image" in keys or "images" in keys):
                    return node

                for value in node.values():
                    stack.append(value)
            elif isinstance(node, list):
                stack.extend(node)

        return None

    def _build_payload_from_candidate(
        self, url: str, candidate: dict[str, Any] | None
    ) -> ProductPayload | None:
        if candidate is None:
            return None

        title = self._first_string(candidate, ["title", "name"])
        price_raw = self._first_value(candidate, ["price", "price_min", "price_max"])
        price = self._to_decimal(price_raw)
        if title is None or price is None:
            return None

        original_price = self._to_decimal(
            self._first_value(candidate, ["price_before_discount", "original_price"])
        )
        discount = self._first_string(candidate, ["discount", "raw_discount"])
        rating = self._to_float(
            self._nested_value(candidate, ["item_rating", "rating_star"])
        )
        sold_count = self._to_int(
            self._first_value(candidate, ["historical_sold", "sold", "sold_count"])
        )

        image_values = self._first_value(candidate, ["images", "image"])
        images = self._normalize_images(image_values)

        shop_name = self._first_string(candidate, ["shop_name"]) or self._nested_string(
            candidate, ["shop", "name"]
        )
        category = self._first_string(candidate, ["category"]) or self._nested_string(
            candidate, ["cat", "name"]
        )

        return ProductPayload(
            title=title.strip(),
            price=price,
            original_price=original_price,
            discount=discount,
            rating=rating,
            sold_count=sold_count,
            images=images,
            shop_name=shop_name,
            category=category,
            affiliate_url=url,
        )

    def _build_payload_from_meta(self, url: str, html: str) -> ProductPayload | None:
        title = self._extract_meta(html, "property", "og:title")
        image = self._extract_meta(html, "property", "og:image")
        price_text = self._extract_meta(html, "property", "product:price:amount")

        if title is None or price_text is None:
            return None

        price = self._to_decimal(price_text)
        if price is None:
            return None

        images = [image] if image else []

        return ProductPayload(
            title=title.strip(),
            price=price,
            images=images,
            affiliate_url=url,
        )

    def _extract_meta(self, html: str, attr: str, key: str) -> str | None:
        pattern = rf'<meta[^>]*{attr}=["\']{re.escape(key)}["\'][^>]*content=["\']([^"\']+)["\']'
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _normalize_images(self, value: Any) -> list[str]:
        if value is None:
            return []

        items: list[Any]
        if isinstance(value, list):
            items = value
        else:
            items = [value]

        normalized: list[str] = []
        for item in items:
            if not isinstance(item, str):
                continue
            trimmed = item.strip()
            if not trimmed:
                continue
            if trimmed.startswith(("http://", "https://")):
                normalized.append(trimmed)
            else:
                normalized.append(f"https://cf.shopee.com/file/{trimmed}")

        return normalized

    def _first_value(self, source: dict[str, Any], keys: list[str]) -> Any:
        for key in keys:
            if key in source:
                return source[key]
        return None

    def _first_string(self, source: dict[str, Any], keys: list[str]) -> str | None:
        value = self._first_value(source, keys)
        return value if isinstance(value, str) else None

    def _nested_value(self, source: dict[str, Any], keys: list[str]) -> Any:
        current: Any = source
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        return current

    def _nested_string(self, source: dict[str, Any], keys: list[str]) -> str | None:
        value = self._nested_value(source, keys)
        return value if isinstance(value, str) else None

    def _to_decimal(self, value: Any) -> Decimal | None:
        if value is None:
            return None

        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

        if number > Decimal("100000"):
            number = number / Decimal("100000")

        return number.quantize(Decimal("0.01"))

    def _to_float(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _to_int(self, value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
