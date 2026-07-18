from datetime import UTC, datetime

from app.core.domain_events import SchedulerEvents
from app.core.exceptions import AppException
from app.models.scheduled_post import ScheduledPost
from app.repositories.scheduler_repository import OptimisticLockError
from app.repositories.analytics_repository import AnalyticsRepositoryProtocol
from app.repositories.scheduler_repository import SchedulerRepositoryProtocol
from app.schemas.scheduler import ScheduledPostState
from app.utils.post_publisher import PostPublisherProtocol


class SchedulerService:
    def __init__(
        self,
        scheduler_repository: SchedulerRepositoryProtocol,
        publisher: PostPublisherProtocol,
        analytics_repository: AnalyticsRepositoryProtocol | None = None,
    ) -> None:
        self._scheduler_repository = scheduler_repository
        self._publisher = publisher
        self._analytics_repository = analytics_repository

    def schedule_post(
        self,
        *,
        owner_user_id: int,
        product_id: int,
        caption_batch_id: int | None,
        promotional_image_id: int | None,
        platform: str,
        target: str,
        scheduled_for: datetime,
    ) -> ScheduledPost:
        now = datetime.now(UTC)
        if scheduled_for < now:
            raise AppException(
                status_code=422, detail="Scheduled time must be in the future"
            )

        try:
            created = self._scheduler_repository.create(
                owner_user_id=owner_user_id,
                product_id=product_id,
                caption_batch_id=caption_batch_id,
                promotional_image_id=promotional_image_id,
                platform=platform,
                target=target,
                scheduled_for=scheduled_for,
            )

            self._scheduler_repository.enqueue_domain_event(
                event=SchedulerEvents.scheduled_post_created(
                    scheduled_post_id=created.id,
                    owner_user_id=created.owner_user_id,
                    product_id=created.product_id,
                    target=created.target,
                    state=created.state,
                )
            )

            if self._analytics_repository is not None:
                self._analytics_repository.record_event(
                    event_type="scheduled_post_created",
                    entity_type="scheduled_post",
                    entity_id=created.id,
                    metadata={
                        "product_id": product_id,
                        "platform": platform,
                        "target": target,
                    },
                )

            self._scheduler_repository.commit()
            return created
        except Exception:
            self._scheduler_repository.rollback()
            raise

    def run_due(self, *, owner_user_id: int) -> tuple[int, int, int]:
        now = datetime.now(UTC)
        due_posts = self._scheduler_repository.claim_due_confirmed(
            owner_user_id=owner_user_id, now=now
        )
        self._scheduler_repository.commit()

        published = 0
        failed = 0

        for scheduled_post in due_posts:
            try:
                message = self._publisher.publish(scheduled_post)
                updated = self._scheduler_repository.update_status(
                    scheduled_post_id=scheduled_post.id,
                    expected_version=scheduled_post.version,
                    state=ScheduledPostState.PUBLISHED.value,
                    published_at=datetime.now(UTC),
                    error_message=None,
                )
                self._scheduler_repository.create_execution(
                    scheduled_post_id=scheduled_post.id,
                    status=ScheduledPostState.PUBLISHED.value,
                    message=message,
                )
                self._scheduler_repository.enqueue_domain_event(
                    event=SchedulerEvents.scheduled_post_published(
                        scheduled_post_id=updated.id,
                        owner_user_id=updated.owner_user_id,
                        target=updated.target,
                    )
                )
                if self._analytics_repository is not None:
                    self._analytics_repository.record_event(
                        event_type="scheduled_post_published",
                        entity_type="scheduled_post",
                        entity_id=scheduled_post.id,
                        metadata={"target": scheduled_post.target},
                    )
                self._scheduler_repository.commit()
                published += 1
            except OptimisticLockError:
                self._scheduler_repository.rollback()
                continue
            except Exception as exc:
                try:
                    updated = self._scheduler_repository.update_status(
                        scheduled_post_id=scheduled_post.id,
                        expected_version=scheduled_post.version,
                        state=ScheduledPostState.FAILED.value,
                        error_message=str(exc),
                    )
                    self._scheduler_repository.create_execution(
                        scheduled_post_id=scheduled_post.id,
                        status=ScheduledPostState.FAILED.value,
                        message=str(exc),
                    )
                    self._scheduler_repository.enqueue_domain_event(
                        event=SchedulerEvents.scheduled_post_failed(
                            scheduled_post_id=updated.id,
                            owner_user_id=updated.owner_user_id,
                            error=str(exc),
                        )
                    )
                    if self._analytics_repository is not None:
                        self._analytics_repository.record_event(
                            event_type="scheduled_post_failed",
                            entity_type="scheduled_post",
                            entity_id=scheduled_post.id,
                            metadata={"error": str(exc)},
                        )
                    self._scheduler_repository.commit()
                except OptimisticLockError:
                    self._scheduler_repository.rollback()
                    continue
                except Exception:
                    self._scheduler_repository.rollback()
                    raise
                failed += 1

        return len(due_posts), published, failed

    def confirm_post(
        self, *, scheduled_post_id: int, actor_user_id: int
    ) -> ScheduledPost:
        scheduled_post = self._scheduler_repository.get_by_id(scheduled_post_id)
        if scheduled_post is None:
            raise AppException(status_code=404, detail="Scheduled post not found")

        if scheduled_post.owner_user_id != actor_user_id:
            raise AppException(
                status_code=403, detail="Not authorized to confirm this scheduled post"
            )

        try:
            from_state = scheduled_post.state
            if scheduled_post.state == ScheduledPostState.AWAITING_CONFIRMATION.value:
                updated = self._scheduler_repository.confirm_if_awaiting(
                    scheduled_post_id=scheduled_post.id,
                    expected_version=scheduled_post.version,
                )
                action = "confirm"
                message = "Scheduled post confirmed by owner"
            else:
                updated = scheduled_post
                action = "confirm_noop"
                message = "Confirm call is idempotent for non-awaiting states"

            self._scheduler_repository.create_audit(
                scheduled_post_id=updated.id,
                actor_user_id=actor_user_id,
                action=action,
                from_state=from_state,
                to_state=updated.state,
                message=message,
            )

            self._scheduler_repository.enqueue_domain_event(
                event=SchedulerEvents.scheduled_post_confirmed(
                    scheduled_post_id=updated.id,
                    owner_user_id=updated.owner_user_id,
                    from_state=from_state,
                    to_state=updated.state,
                )
            )

            if self._analytics_repository is not None:
                self._analytics_repository.record_event(
                    event_type="scheduled_post_confirmed",
                    entity_type="scheduled_post",
                    entity_id=updated.id,
                    metadata={"target": updated.target, "state": updated.state},
                )

            self._scheduler_repository.commit()
            return updated
        except OptimisticLockError as exc:
            self._scheduler_repository.rollback()
            raise AppException(
                status_code=409,
                detail="Scheduled post was modified by another request. Please retry.",
            ) from exc
        except Exception:
            self._scheduler_repository.rollback()
            raise

    def list_recent(self, *, owner_user_id: int, limit: int = 20):
        return self._scheduler_repository.list_recent_for_owner(
            owner_user_id=owner_user_id, limit=limit
        )
