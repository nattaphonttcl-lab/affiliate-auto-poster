from __future__ import annotations

import hashlib


def build_product_fingerprint(
    *, marketplace: str, normalized_url: str, external_product_id: str | None
) -> str:
    basis = f"{marketplace.strip().lower()}|{(external_product_id or '').strip()}|{normalized_url.strip().lower()}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()
