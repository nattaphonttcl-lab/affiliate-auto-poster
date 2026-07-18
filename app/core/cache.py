from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Protocol


class CacheBackend(Protocol):
    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str, ttl_seconds: int) -> None: ...

    def delete(self, key: str) -> None: ...


@dataclass
class _CacheItem:
    value: str
    expires_at: float


class InMemoryTTLCache(CacheBackend):
    def __init__(self) -> None:
        self._items: dict[str, _CacheItem] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> str | None:
        now = time.time()
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            if item.expires_at <= now:
                self._items.pop(key, None)
                return None
            return item.value

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        expires_at = time.time() + max(ttl_seconds, 1)
        with self._lock:
            self._items[key] = _CacheItem(value=value, expires_at=expires_at)

    def delete(self, key: str) -> None:
        with self._lock:
            self._items.pop(key, None)
