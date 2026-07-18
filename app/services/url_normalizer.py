from __future__ import annotations

import ipaddress
from urllib.parse import SplitResult, urlsplit, urlunsplit

from app.core.exceptions import AppException


class URLNormalizer:
    def normalize(self, url: str) -> str:
        parsed = self.parse_and_validate_public_url(url)
        path = parsed.path.rstrip("/") or "/"
        return urlunsplit(
            SplitResult(
                scheme=parsed.scheme.lower(),
                netloc=parsed.netloc.lower(),
                path=path,
                query="",
                fragment="",
            )
        )

    def parse_and_validate_public_url(self, url: str) -> SplitResult:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"}:
            raise AppException(status_code=422, detail="Invalid URL scheme")

        if not parsed.netloc:
            raise AppException(status_code=422, detail="Invalid URL host")

        if parsed.username or parsed.password:
            raise AppException(
                status_code=422,
                detail="URL must not include credentials",
            )

        host = (parsed.hostname or "").strip().lower()
        if not host:
            raise AppException(status_code=422, detail="Invalid URL host")

        if host in {"localhost", "127.0.0.1", "::1"}:
            raise AppException(
                status_code=422,
                detail="Localhost URLs are not allowed",
            )

        try:
            ip = ipaddress.ip_address(host)
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
            ):
                raise AppException(
                    status_code=422,
                    detail="Private or local network URLs are not allowed",
                )
        except ValueError:
            pass

        if parsed.port and parsed.port not in {80, 443}:
            raise AppException(status_code=422, detail="URL port is not allowed")

        return parsed
