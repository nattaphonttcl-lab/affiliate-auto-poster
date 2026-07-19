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

        json_ld_payload = self._build_payload_from_json_ld(url, html)
        if json_ld_payload:
            return json_ld_payload

        fallback_payload = self._build_payload_from_meta(url, html)
        if fallback_payload:
            return fallback_payload

        api_payload = self._build_payload_from_shopee_item_api(url)
        if api_payload:
            return api_payload

        url_fallback_payload = self._build_payload_from_url_fallback(url)
        if url_fallback_payload:
            return url_fallback_payload

        raise AppException(
            status_code=422,
            detail="Unable to parse Shopee product from the provided URL",
        )

    def _fetch_html(self, url: str) -> str:
        if self._html_fetcher is not None:
            return self._html_fetcher(url)

        try:
            response = httpx.get(
                url,
                follow_redirects=True,
                timeout=self._timeout_seconds,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/126.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            response.raise_for_status()
            return response.text
        except httpx.TimeoutException as exc:
            raise AppException(
                status_code=504,
                detail="Marketplace provider timeout",
            ) from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise AppException(
                    status_code=429,
                    detail="Marketplace rate limit exceeded",
                ) from exc
            raise AppException(
                status_code=503,
                detail="Marketplace provider unavailable",
            ) from exc
        except httpx.HTTPError as exc:
            raise AppException(
                status_code=503,
                detail="Marketplace provider unavailable",
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
            marketplace="shopee",
            normalized_url=url,
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
            marketplace="shopee",
            normalized_url=url,
            title=title.strip(),
            price=price,
            images=images,
            affiliate_url=url,
        )

    def _build_payload_from_json_ld(self, url: str, html: str) -> ProductPayload | None:
        candidates = self._extract_json_ld_candidates(html)
        for candidate in candidates:
            candidate_type = candidate.get("@type")
            if isinstance(candidate_type, list):
                is_product = "Product" in candidate_type
            else:
                is_product = candidate_type == "Product"
            if not is_product:
                continue

            title_raw = candidate.get("name")
            title = title_raw.strip() if isinstance(title_raw, str) else None
            if not title:
                continue

            offers = candidate.get("offers")
            offer_obj = offers[0] if isinstance(offers, list) and offers else offers
            price = None
            if isinstance(offer_obj, dict):
                price = self._to_decimal(offer_obj.get("price"))
            if price is None:
                price = self._to_decimal(candidate.get("price"))
            if price is None:
                continue

            image_value = candidate.get("image")
            images = self._normalize_images(image_value)

            rating = None
            aggregate = candidate.get("aggregateRating")
            if isinstance(aggregate, dict):
                rating = self._to_float(aggregate.get("ratingValue"))

            return ProductPayload(
                marketplace="shopee",
                normalized_url=url,
                title=title,
                price=price,
                images=images,
                rating=rating,
                affiliate_url=url,
            )

        return None

    def _extract_json_ld_candidates(self, html: str) -> list[dict[str, Any]]:
        matches = re.findall(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        items: list[dict[str, Any]] = []
        for raw in matches:
            content = raw.strip()
            if not content:
                continue
            try:
                loaded = json.loads(content)
            except json.JSONDecodeError:
                continue

            if isinstance(loaded, dict):
                if "@graph" in loaded and isinstance(loaded["@graph"], list):
                    for graph_item in loaded["@graph"]:
                        if isinstance(graph_item, dict):
                            items.append(graph_item)
                else:
                    items.append(loaded)
            elif isinstance(loaded, list):
                for entry in loaded:
                    if isinstance(entry, dict):
                        items.append(entry)

        return items

    def _extract_meta(self, html: str, attr: str, key: str) -> str | None:
        pattern = rf'<meta[^>]*{attr}=["\']{re.escape(key)}["\'][^>]*content=["\']([^"\']+)["\']'
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _build_payload_from_shopee_item_api(self, url: str) -> ProductPayload | None:
        ids = self._extract_shop_item_ids(url)
        if ids is None:
            return None

        shop_id, item_id = ids
        api_url = (
            "https://shopee.co.id/api/v4/item/get" f"?itemid={item_id}&shopid={shop_id}"
        )
        try:
            response = httpx.get(
                api_url,
                timeout=self._timeout_seconds,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/126.0.0.0 Safari/537.36"
                    ),
                    "Accept": "application/json",
                    "Referer": url,
                },
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError):
            return None

        item = body.get("data") if isinstance(body, dict) else None
        if not isinstance(item, dict):
            return None

        title = item.get("name")
        if not isinstance(title, str) or not title.strip():
            return None

        price = self._to_decimal(item.get("price") or item.get("price_min"))
        if price is None:
            return None

        original_price = self._to_decimal(item.get("price_before_discount"))
        sold_count = self._to_int(item.get("historical_sold"))

        rating = None
        item_rating = item.get("item_rating")
        if isinstance(item_rating, dict):
            rating = self._to_float(item_rating.get("rating_star"))

        images = self._normalize_images(item.get("images"))
        shop_name = self._nested_string(item, ["shop_info", "shop_name"])

        return ProductPayload(
            marketplace="shopee",
            normalized_url=url,
            title=title.strip(),
            price=price,
            original_price=original_price,
            discount=None,
            rating=rating,
            sold_count=sold_count,
            images=images,
            shop_name=shop_name,
            category=None,
            affiliate_url=url,
        )

    def _extract_shop_item_ids(self, url: str) -> tuple[str, str] | None:
        match = re.search(r"/product/(\d+)/(\d+)", url)
        if match:
            return match.group(1), match.group(2)

        match = re.search(r"/i\.(\d+)\.(\d+)", url)
        if match:
            return match.group(1), match.group(2)

        return None

    def _build_payload_from_url_fallback(self, url: str) -> ProductPayload | None:
        ids = self._extract_shop_item_ids(url)
        if ids is None:
            return None

        _, item_id = ids
        slug_match = re.search(r"/([^/?#]+)-i\.\d+\.\d+", url)
        if slug_match:
            slug_title = slug_match.group(1).replace("-", " ").strip()
            title = slug_title if slug_title else f"Shopee Product {item_id}"
        else:
            title = f"Shopee Product {item_id}"

        return ProductPayload(
            marketplace="shopee",
            normalized_url=url,
            title=title,
            price=Decimal("1.00"),
            images=[],
            affiliate_url=url,
        )

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
