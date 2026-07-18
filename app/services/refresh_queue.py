from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class RefreshTask:
    product_id: int
    requested_by_user_id: int
    queued_at: datetime


class ProductRefreshQueue(Protocol):
    def enqueue_refresh(
        self, *, product_id: int, requested_by_user_id: int
    ) -> None: ...


class InMemoryProductRefreshQueue(ProductRefreshQueue):
    def __init__(self) -> None:
        self._tasks: list[RefreshTask] = []

    def enqueue_refresh(self, *, product_id: int, requested_by_user_id: int) -> None:
        self._tasks.append(
            RefreshTask(
                product_id=product_id,
                requested_by_user_id=requested_by_user_id,
                queued_at=datetime.now(UTC),
            )
        )

    @property
    def tasks(self) -> list[RefreshTask]:
        return list(self._tasks)
