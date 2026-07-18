from typing import Protocol

import httpx

from app.core.exceptions import AppException
from app.models.scheduled_post import ScheduledPost


class PostPublisherProtocol(Protocol):
    def publish(self, scheduled_post: ScheduledPost) -> str: ...


class AuditPostPublisher(PostPublisherProtocol):
    def publish(self, scheduled_post: ScheduledPost) -> str:
        return f"AUDIT-PUBLISHED:{scheduled_post.id}:{scheduled_post.target}"


class WebhookPostPublisher(PostPublisherProtocol):
    def __init__(self, *, webhook_url: str, timeout_seconds: float) -> None:
        self._webhook_url = webhook_url
        self._timeout_seconds = timeout_seconds

    def publish(self, scheduled_post: ScheduledPost) -> str:
        try:
            response = httpx.post(
                self._webhook_url,
                timeout=self._timeout_seconds,
                json={
                    "scheduled_post_id": scheduled_post.id,
                    "platform": scheduled_post.platform,
                    "target": scheduled_post.target,
                    "product_id": scheduled_post.product_id,
                    "caption_batch_id": scheduled_post.caption_batch_id,
                    "promotional_image_id": scheduled_post.promotional_image_id,
                },
            )
            response.raise_for_status()
            return f"WEBHOOK-PUBLISHED:{scheduled_post.id}"
        except httpx.HTTPError as exc:
            raise AppException(status_code=502, detail="Failed to publish scheduled post to webhook") from exc
