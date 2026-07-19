from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from zoneinfo import ZoneInfo

from app.core.config import Settings
from app.core.exceptions import AppException
from app.repositories.ai_content_repository import AIContentRepository
from app.repositories.analytics_repository import AnalyticsRepositoryProtocol
from app.repositories.image_engine_repository import ImageEngineRepository
from app.repositories.product_repository import ProductRepositoryProtocol
from app.repositories.publishing_repository import PublishingRepository
from app.schemas.publishing import (
    MediaSourceType,
    MediaType,
    PublishActionResponse,
    PublishCancelRequest,
    PublishingHistoryRead,
    PublishingHistoryResponse,
    PublishingJobRead,
    PublishingJobsResponse,
    PublishingStatus,
    PublishRequest,
    PublishRetryRequest,
    PublishScheduleRequest,
    SocialAccountCreateRequest,
    SocialAccountRead,
    SocialAccountUpdateRequest,
)
from app.services.social_providers import ProviderRegistry, PublishPayload


@dataclass(frozen=True)
class CircuitState:
    failures: int = 0
    opened_until: datetime | None = None


class PublishingService:
    def __init__(
        self,
        product_repository: ProductRepositoryProtocol,
        ai_repository: AIContentRepository,
        image_repository: ImageEngineRepository,
        repository: PublishingRepository,
        provider_registry: ProviderRegistry,
        settings: Settings,
        analytics_repository: AnalyticsRepositoryProtocol | None = None,
    ) -> None:
        self._product_repository = product_repository
        self._ai_repository = ai_repository
        self._image_repository = image_repository
        self._repository = repository
        self._provider_registry = provider_registry
        self._settings = settings
        self._analytics_repository = analytics_repository
        self._circuit_by_platform: dict[str, CircuitState] = {}

    def create_social_account(
        self, *, owner_user_id: int, payload: SocialAccountCreateRequest
    ) -> SocialAccountRead:
        self._validate_permissions(payload.permissions)
        self._validate_business_hours(
            payload.business_hours_start,
            payload.business_hours_end,
        )

        try:
            account = self._repository.create_social_account(
                owner_user_id=owner_user_id,
                platform=payload.platform.value,
                account_name=payload.account_name,
                account_identifier=payload.account_identifier,
                permissions=payload.permissions,
                timezone=payload.timezone,
                business_hours_start=payload.business_hours_start,
                business_hours_end=payload.business_hours_end,
                rate_limit_per_minute=payload.rate_limit_per_minute,
            )
            self._repository.upsert_platform_credential(
                social_account_id=account.id,
                access_token=payload.access_token,
                refresh_token=payload.refresh_token,
                token_expires_at=payload.token_expires_at,
                scopes=payload.scopes,
                encryption_key=self._settings.ai_provider_encryption_key,
            )
            self._repository.create_audit_log(
                owner_user_id=owner_user_id,
                action="social_account_created",
                details={
                    "social_account_id": account.id,
                    "platform": account.platform,
                    "account_identifier": account.account_identifier,
                },
            )
            self._repository.commit()
            return SocialAccountRead.model_validate(account)
        except Exception:
            self._repository.rollback()
            raise

    def list_social_accounts(self, *, owner_user_id: int) -> list[SocialAccountRead]:
        rows = self._repository.list_social_accounts(owner_user_id=owner_user_id)
        return [SocialAccountRead.model_validate(item) for item in rows]

    def update_social_account(
        self,
        *,
        owner_user_id: int,
        social_account_id: int,
        payload: SocialAccountUpdateRequest,
    ) -> SocialAccountRead:
        updates = payload.model_dump(exclude_unset=True)
        self._validate_business_hours(
            updates.get("business_hours_start"),
            updates.get("business_hours_end"),
        )

        access_token = updates.pop("access_token", None)
        refresh_token = updates.pop("refresh_token", None)
        token_expires_at = updates.pop("token_expires_at", None)
        scopes = updates.pop("scopes", None)

        try:
            account = self._repository.update_social_account(
                social_account_id=social_account_id,
                owner_user_id=owner_user_id,
                data=updates,
            )
            if account is None:
                raise AppException(status_code=404, detail="Social account not found")

            if access_token is not None:
                self._repository.upsert_platform_credential(
                    social_account_id=social_account_id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_expires_at=token_expires_at,
                    scopes=scopes or [],
                    encryption_key=self._settings.ai_provider_encryption_key,
                )

            self._repository.create_audit_log(
                owner_user_id=owner_user_id,
                action="social_account_updated",
                details={"social_account_id": social_account_id},
                job_id=None,
            )
            self._repository.commit()
            return SocialAccountRead.model_validate(account)
        except AppException:
            self._repository.rollback()
            raise
        except Exception:
            self._repository.rollback()
            raise

    def delete_social_account(
        self, *, owner_user_id: int, social_account_id: int
    ) -> None:
        try:
            deleted = self._repository.delete_social_account(
                social_account_id=social_account_id,
                owner_user_id=owner_user_id,
            )
            if not deleted:
                raise AppException(status_code=404, detail="Social account not found")
            self._repository.create_audit_log(
                owner_user_id=owner_user_id,
                action="social_account_deleted",
                details={"social_account_id": social_account_id},
            )
            self._repository.commit()
        except AppException:
            self._repository.rollback()
            raise
        except Exception:
            self._repository.rollback()
            raise

    def publish_now(
        self,
        *,
        owner_user_id: int,
        payload: PublishRequest,
    ) -> PublishActionResponse:
        return self._create_and_optionally_publish(
            owner_user_id=owner_user_id,
            payload=payload,
            scheduled_for=None,
            recurrence_rule=None,
            timezone="UTC",
            enforce_business_hours=False,
        )

    def schedule_publish(
        self,
        *,
        owner_user_id: int,
        payload: PublishScheduleRequest,
    ) -> PublishActionResponse:
        now = datetime.now(UTC)
        if payload.scheduled_for < now:
            raise AppException(
                status_code=422, detail="Scheduled time must be in the future"
            )

        return self._create_and_optionally_publish(
            owner_user_id=owner_user_id,
            payload=payload,
            scheduled_for=payload.scheduled_for,
            recurrence_rule=payload.recurrence_rule,
            timezone=payload.timezone,
            enforce_business_hours=payload.enforce_business_hours,
        )

    def retry_publish(
        self,
        *,
        owner_user_id: int,
        payload: PublishRetryRequest,
    ) -> PublishActionResponse:
        job = self._repository.get_job(payload.job_id)
        if job is None or job.owner_user_id != owner_user_id:
            raise AppException(status_code=404, detail="Publishing job not found")

        if job.status not in {
            PublishingStatus.FAILED.value,
            PublishingStatus.RETRY.value,
        }:
            raise AppException(
                status_code=422, detail="Only failed/retry jobs can be retried"
            )

        try:
            self._repository.update_job_status(
                job_id=job.id,
                status=PublishingStatus.RETRY.value,
                next_retry_at=datetime.now(UTC),
                last_error=None,
            )
            queue = self._repository.update_queue_status(
                job_id=job.id,
                status=PublishingStatus.RETRY.value,
                visible_at=datetime.now(UTC),
                lock_owner=None,
            )
            self._repository.create_audit_log(
                owner_user_id=owner_user_id,
                action="publish_retry_requested",
                details={"job_id": job.id},
                job_id=job.id,
            )
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

        refreshed = self._repository.get_job(job.id)
        if refreshed is None:
            raise AppException(status_code=500, detail="Failed to refresh job")
        return PublishActionResponse(
            job=PublishingJobRead.model_validate(refreshed),
            queue_status=PublishingStatus(queue.status),
        )

    def cancel_publish(
        self,
        *,
        owner_user_id: int,
        payload: PublishCancelRequest,
    ) -> PublishActionResponse:
        job = self._repository.get_job(payload.job_id)
        if job is None or job.owner_user_id != owner_user_id:
            raise AppException(status_code=404, detail="Publishing job not found")

        if job.status in {
            PublishingStatus.PUBLISHED.value,
            PublishingStatus.CANCELLED.value,
            PublishingStatus.EXPIRED.value,
        }:
            raise AppException(status_code=422, detail="Job cannot be cancelled")

        try:
            updated = self._repository.update_job_status(
                job_id=job.id,
                status=PublishingStatus.CANCELLED.value,
                cancelled_at=datetime.now(UTC),
            )
            queue = self._repository.update_queue_status(
                job_id=job.id,
                status=PublishingStatus.CANCELLED.value,
                visible_at=datetime.now(UTC),
                lock_owner=None,
            )
            self._repository.create_audit_log(
                owner_user_id=owner_user_id,
                action="publish_cancelled",
                details={"job_id": job.id},
                job_id=job.id,
            )
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

        return PublishActionResponse(
            job=PublishingJobRead.model_validate(updated),
            queue_status=PublishingStatus(queue.status),
        )

    def list_jobs(
        self, *, owner_user_id: int, limit: int, offset: int
    ) -> PublishingJobsResponse:
        rows = self._repository.list_jobs(
            owner_user_id=owner_user_id, limit=limit, offset=offset
        )
        total = self._repository.count_jobs(owner_user_id=owner_user_id)
        return PublishingJobsResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=[PublishingJobRead.model_validate(item) for item in rows],
        )

    def list_history(
        self, *, owner_user_id: int, limit: int, offset: int
    ) -> PublishingHistoryResponse:
        rows = self._repository.list_history(
            owner_user_id=owner_user_id, limit=limit, offset=offset
        )
        total = self._repository.count_history(owner_user_id=owner_user_id)
        return PublishingHistoryResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=[PublishingHistoryRead.model_validate(item) for item in rows],
        )

    def process_queue(self, *, worker_id: str, limit: int = 20) -> tuple[int, int, int]:
        now = datetime.now(UTC)
        entries = self._repository.claim_due_queue_jobs(
            now=now, limit=limit, worker_id=worker_id
        )
        self._repository.commit()

        processed = len(entries)
        published = 0
        failed = 0

        for entry in entries:
            try:
                self._process_single_job(entry.job_id, worker_id=worker_id)
                published += 1
            except Exception:
                failed += 1

        return processed, published, failed

    def process_retry(self, *, worker_id: str, limit: int = 20) -> tuple[int, int, int]:
        return self.process_queue(worker_id=worker_id, limit=limit)

    def sync_analytics(self, *, owner_user_id: int, limit: int = 50) -> int:
        rows = self._repository.list_history(
            owner_user_id=owner_user_id, limit=limit, offset=0
        )
        for row in rows:
            if row.clicks > 0 and row.views > 0:
                row.ctr = row.clicks / row.views
        self._repository.commit()
        return len(rows)

    def process_dead_letter(self, *, limit: int = 100) -> int:
        _ = limit
        return 0

    def cleanup_expired(self, *, now: datetime | None = None) -> int:
        now_value = now or datetime.now(UTC)
        updated = 0
        jobs = self._repository.list_jobs(owner_user_id=0, limit=1000, offset=0)
        for job in jobs:
            if (
                job.expires_at is not None
                and job.expires_at < now_value
                and job.status
                in {
                    PublishingStatus.PENDING.value,
                    PublishingStatus.SCHEDULED.value,
                    PublishingStatus.RETRY.value,
                }
            ):
                self._repository.update_job_status(
                    job_id=job.id,
                    status=PublishingStatus.EXPIRED.value,
                )
                self._repository.update_queue_status(
                    job_id=job.id,
                    status=PublishingStatus.EXPIRED.value,
                    visible_at=now_value,
                    lock_owner=None,
                )
                updated += 1
        if updated:
            self._repository.commit()
        return updated

    def _create_and_optionally_publish(
        self,
        *,
        owner_user_id: int,
        payload: PublishRequest,
        scheduled_for: datetime | None,
        recurrence_rule: str | None,
        timezone: str,
        enforce_business_hours: bool,
    ) -> PublishActionResponse:
        account = self._repository.get_social_account(payload.social_account_id)
        if account is None or account.owner_user_id != owner_user_id:
            raise AppException(status_code=404, detail="Social account not found")
        if not account.is_active:
            raise AppException(status_code=422, detail="Social account is inactive")

        now = datetime.now(UTC)
        effective_schedule = scheduled_for
        if effective_schedule is not None and enforce_business_hours:
            effective_schedule = self._apply_business_hours(
                when=effective_schedule,
                timezone=timezone,
                business_hours_start=account.business_hours_start,
                business_hours_end=account.business_hours_end,
            )

        idempotency_key = payload.idempotency_key or self._derive_idempotency_key(
            owner_user_id=owner_user_id,
            social_account_id=payload.social_account_id,
            product_id=payload.product_id,
            post_type=payload.post_type.value,
            caption_content_id=payload.caption_content_id,
            generated_image_id=payload.generated_image_id,
            scheduled_for=effective_schedule,
        )
        duplicate = self._repository.get_job_by_idempotency_key(
            owner_user_id=owner_user_id,
            idempotency_key=idempotency_key,
        )
        if duplicate is not None:
            queue = self._repository.get_queue_entry(job_id=duplicate.id)
            queue_status = queue.status if queue is not None else duplicate.status
            return PublishActionResponse(
                job=PublishingJobRead.model_validate(duplicate),
                queue_status=PublishingStatus(queue_status),
            )

        caption_text = self._resolve_caption(payload.caption_content_id)
        if not caption_text:
            caption_text = self._fallback_caption(
                payload.product_id, payload.post_type.value
            )

        status = (
            PublishingStatus.PENDING.value
            if effective_schedule is None
            else PublishingStatus.SCHEDULED.value
        )

        try:
            job = self._repository.create_job(
                owner_user_id=owner_user_id,
                social_account_id=payload.social_account_id,
                product_id=payload.product_id,
                caption_content_id=payload.caption_content_id,
                generated_image_id=payload.generated_image_id,
                post_type=payload.post_type.value,
                platform=account.platform,
                status=status,
                caption_text=caption_text,
                hashtags_text=" ".join(payload.hashtags) if payload.hashtags else None,
                mentions_text=" ".join(payload.mentions) if payload.mentions else None,
                cta_text=payload.cta,
                affiliate_link=payload.affiliate_link,
                alt_text=payload.alt_text,
                idempotency_key=idempotency_key,
                scheduled_for=effective_schedule,
                recurrence_rule=recurrence_rule,
                timezone=timezone,
                business_hours_enforced=enforce_business_hours,
                max_retries=5,
                expires_at=(
                    (effective_schedule + timedelta(days=30))
                    if effective_schedule
                    else None
                ),
            )

            media_refs = self._collect_media(payload=payload)
            for uri in media_refs:
                media_type = (
                    MediaType.VIDEO.value
                    if uri.endswith(".mp4")
                    else MediaType.IMAGE.value
                )
                self._repository.add_media_attachment(
                    job_id=job.id,
                    media_type=media_type,
                    source_type=MediaSourceType.EXTERNAL.value,
                    uri=uri,
                )

            if payload.generated_image_id is not None:
                generated = self._image_repository.get_generated_image(
                    payload.generated_image_id
                )
                if generated is not None and generated.versions:
                    latest = sorted(
                        generated.versions, key=lambda item: item.version, reverse=True
                    )[0]
                    self._repository.add_media_attachment(
                        job_id=job.id,
                        media_type=MediaType.IMAGE.value,
                        source_type=MediaSourceType.GENERATED.value,
                        uri=latest.image_uri,
                        thumbnail_uri=latest.thumbnail_uri,
                    )

            queue = self._repository.create_queue_entry(
                job_id=job.id,
                owner_user_id=owner_user_id,
                status=status,
                scheduled_for=effective_schedule,
                priority=100,
                visible_at=effective_schedule or now,
            )
            self._repository.create_audit_log(
                owner_user_id=owner_user_id,
                action="publishing_job_created",
                details={"job_id": job.id, "status": status},
                job_id=job.id,
            )
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

        if effective_schedule is None:
            self._process_single_job(job.id, worker_id="immediate")
            refreshed = self._repository.get_job(job.id)
            if refreshed is None:
                raise AppException(
                    status_code=500, detail="Failed to refresh publishing job"
                )
            queue = self._repository.get_queue_entry(job_id=job.id)
            queue_status = queue.status if queue is not None else refreshed.status
            return PublishActionResponse(
                job=PublishingJobRead.model_validate(refreshed),
                queue_status=PublishingStatus(queue_status),
            )

        return PublishActionResponse(
            job=PublishingJobRead.model_validate(job),
            queue_status=PublishingStatus(queue.status),
        )

    def _process_single_job(self, job_id: int, *, worker_id: str) -> None:
        job = self._repository.get_job(job_id)
        if job is None:
            return

        if job.expires_at is not None and job.expires_at < datetime.now(UTC):
            self._repository.update_job_status(
                job_id=job.id, status=PublishingStatus.EXPIRED.value
            )
            self._repository.update_queue_status(
                job_id=job.id,
                status=PublishingStatus.EXPIRED.value,
                visible_at=datetime.now(UTC),
                lock_owner=None,
            )
            self._repository.commit()
            return

        account = self._repository.get_social_account(job.social_account_id)
        if account is None or not account.is_active:
            self._mark_failure(
                job=job, reason="Social account unavailable", worker_id=worker_id
            )
            return

        circuit = self._circuit_by_platform.get(job.platform, CircuitState())
        if circuit.opened_until is not None and circuit.opened_until > datetime.now(
            UTC
        ):
            self._mark_retry(
                job=job, reason="Circuit breaker is open", worker_id=worker_id
            )
            return

        credentials = self._repository.get_decrypted_credentials(
            social_account_id=job.social_account_id,
            encryption_key=self._settings.ai_provider_encryption_key,
        )
        media = self._repository.list_media_attachments(job_id=job.id)
        media_uris = [item.uri for item in media]
        thumb_uri = next(
            (item.thumbnail_uri for item in media if item.thumbnail_uri), None
        )

        payload = PublishPayload(
            caption=job.caption_text,
            hashtags=(job.hashtags_text or "").split(),
            mentions=(job.mentions_text or "").split(),
            cta=job.cta_text,
            affiliate_link=job.affiliate_link,
            media_uris=media_uris,
            thumbnail_uri=thumb_uri,
            alt_text=job.alt_text,
            idempotency_key=job.idempotency_key,
        )

        provider_sequence = self._provider_sequence_for(job.platform)
        try:
            provider_name, result = self._provider_registry.publish_with_failover(
                provider_sequence=provider_sequence,
                account_identifier=account.account_identifier,
                post_type=job.post_type,
                payload=payload,
                credentials=credentials,
            )
        except AppException as exc:
            self._mark_retry(job=job, reason=str(exc.detail), worker_id=worker_id)
            self._trip_circuit(job.platform)
            return

        try:
            updated_job = self._repository.update_job_status(
                job_id=job.id,
                status=PublishingStatus.PUBLISHED.value,
                retry_count=job.retry_count,
                next_retry_at=None,
                last_error=None,
                latency_ms=result.latency_ms,
                published_at=datetime.now(UTC),
                provider_response={
                    **result.response_payload,
                    "provider": provider_name,
                },
            )
            self._repository.update_queue_status(
                job_id=job.id,
                status=PublishingStatus.PUBLISHED.value,
                visible_at=datetime.now(UTC),
                lock_owner=None,
            )
            self._repository.create_history(
                job_id=job.id,
                owner_user_id=job.owner_user_id,
                platform=job.platform,
                account_identifier=account.account_identifier,
                caption=job.caption_text,
                hashtags=job.hashtags_text,
                mentions=job.mentions_text,
                cta=job.cta_text,
                affiliate_link=job.affiliate_link,
                media_refs=media_uris,
                provider_response=updated_job.provider_response,
                published_at=updated_job.published_at,
                status=updated_job.status,
                retry_count=updated_job.retry_count,
                latency_ms=updated_job.latency_ms,
            )
            self._repository.create_audit_log(
                owner_user_id=job.owner_user_id,
                action="publishing_job_published",
                details={"job_id": job.id, "provider": provider_name},
                job_id=job.id,
            )
            self._track_event(
                event_type="social_publish_success",
                entity_id=job.id,
                metadata={"platform": job.platform, "post_type": job.post_type},
            )
            self._circuit_by_platform[job.platform] = CircuitState(
                failures=0, opened_until=None
            )
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

    def _mark_retry(self, *, job, reason: str, worker_id: str) -> None:
        next_retry = self._compute_next_retry(job.retry_count)
        retry_count = job.retry_count + 1

        try:
            if retry_count > job.max_retries:
                self._repository.update_job_status(
                    job_id=job.id,
                    status=PublishingStatus.FAILED.value,
                    retry_count=retry_count,
                    next_retry_at=None,
                    last_error=reason,
                )
                self._repository.update_queue_status(
                    job_id=job.id,
                    status=PublishingStatus.FAILED.value,
                    visible_at=datetime.now(UTC),
                    lock_owner=None,
                )
                self._repository.add_dead_letter(
                    job_id=job.id,
                    owner_user_id=job.owner_user_id,
                    reason=reason,
                    payload={"worker_id": worker_id, "retry_count": retry_count},
                )
                self._track_event(
                    event_type="social_publish_dead_letter",
                    entity_id=job.id,
                    metadata={"platform": job.platform, "error": reason},
                )
            else:
                self._repository.update_job_status(
                    job_id=job.id,
                    status=PublishingStatus.RETRY.value,
                    retry_count=retry_count,
                    next_retry_at=next_retry,
                    last_error=reason,
                )
                self._repository.update_queue_status(
                    job_id=job.id,
                    status=PublishingStatus.RETRY.value,
                    visible_at=next_retry,
                    lock_owner=None,
                )
                self._track_event(
                    event_type="social_publish_retry",
                    entity_id=job.id,
                    metadata={"platform": job.platform, "retry_count": retry_count},
                )
            self._repository.create_audit_log(
                owner_user_id=job.owner_user_id,
                action="publishing_job_retry",
                details={"job_id": job.id, "reason": reason},
                job_id=job.id,
            )
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

    def _mark_failure(self, *, job, reason: str, worker_id: str) -> None:
        try:
            self._repository.update_job_status(
                job_id=job.id,
                status=PublishingStatus.FAILED.value,
                retry_count=job.retry_count,
                next_retry_at=None,
                last_error=reason,
            )
            self._repository.update_queue_status(
                job_id=job.id,
                status=PublishingStatus.FAILED.value,
                visible_at=datetime.now(UTC),
                lock_owner=None,
            )
            self._repository.add_dead_letter(
                job_id=job.id,
                owner_user_id=job.owner_user_id,
                reason=reason,
                payload={"worker_id": worker_id, "retry_count": job.retry_count},
            )
            self._repository.create_audit_log(
                owner_user_id=job.owner_user_id,
                action="publishing_job_failed",
                details={"job_id": job.id, "reason": reason},
                job_id=job.id,
            )
            self._track_event(
                event_type="social_publish_failed",
                entity_id=job.id,
                metadata={"platform": job.platform, "error": reason},
            )
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

    def _provider_sequence_for(self, primary: str) -> list[str]:
        order_raw = getattr(
            self._settings,
            "publishing_provider_failover_order",
            "facebook,facebook_page,instagram,threads,tiktok,youtube_shorts,shopee_video",
        )
        order = [item.strip() for item in order_raw.split(",") if item.strip()]
        normalized = [primary] + [item for item in order if item != primary]
        return normalized

    def _compute_next_retry(self, current_retry_count: int) -> datetime:
        base_seconds = max(
            1, int(getattr(self._settings, "publishing_retry_base_seconds", 30))
        )
        max_seconds = max(
            base_seconds,
            int(getattr(self._settings, "publishing_retry_max_seconds", 3600)),
        )
        delay = min(max_seconds, base_seconds * (2**current_retry_count))
        return datetime.now(UTC) + timedelta(seconds=delay)

    def _trip_circuit(self, platform: str) -> None:
        threshold = max(
            1, int(getattr(self._settings, "publishing_circuit_breaker_failures", 3))
        )
        cool_down = max(
            5, int(getattr(self._settings, "publishing_circuit_breaker_seconds", 120))
        )

        state = self._circuit_by_platform.get(platform, CircuitState())
        failures = state.failures + 1
        opened_until = state.opened_until
        if failures >= threshold:
            opened_until = datetime.now(UTC) + timedelta(seconds=cool_down)
        self._circuit_by_platform[platform] = CircuitState(
            failures=failures,
            opened_until=opened_until,
        )

    def _resolve_caption(self, caption_content_id: int | None) -> str:
        if caption_content_id is None:
            return ""
        row = self._ai_repository.get_content_by_id(caption_content_id)
        if row is None:
            raise AppException(status_code=404, detail="Caption content not found")
        latest = sorted(row.versions, key=lambda item: item.version, reverse=True)[0]
        return self._pick_caption_text(latest.generated_text)

    def _pick_caption_text(self, generated_text: dict[str, str]) -> str:
        for key in (
            "facebook_caption",
            "tiktok_caption",
            "short_description",
            "long_description",
        ):
            text = generated_text.get(key)
            if text and text.strip():
                return text.strip()
        for value in generated_text.values():
            if value and value.strip():
                return value.strip()
        return ""

    def _fallback_caption(self, product_id: int, post_type: str) -> str:
        product = self._product_repository.get_by_id(product_id)
        if product is None:
            raise AppException(status_code=404, detail="Product not found")
        return (
            f"{product.title} now available. Ideal for {post_type.replace('_', ' ')}."
        )

    def _collect_media(self, *, payload: PublishRequest) -> list[str]:
        media = [item.strip() for item in payload.media_attachments if item.strip()]
        return media

    def _derive_idempotency_key(
        self,
        *,
        owner_user_id: int,
        social_account_id: int,
        product_id: int,
        post_type: str,
        caption_content_id: int | None,
        generated_image_id: int | None,
        scheduled_for: datetime | None,
    ) -> str:
        seed = (
            f"{owner_user_id}:{social_account_id}:{product_id}:{post_type}:"
            f"{caption_content_id}:{generated_image_id}:{scheduled_for.isoformat() if scheduled_for else 'now'}"
        )
        return sha256(seed.encode("utf-8")).hexdigest()

    def _validate_permissions(self, permissions: list[str]) -> None:
        if not permissions:
            return
        invalid = [
            item
            for item in permissions
            if "publish" not in item.lower() and "manage" not in item.lower()
        ]
        if invalid:
            raise AppException(status_code=422, detail="Invalid platform permissions")

    def _validate_business_hours(
        self, start_hour: int | None, end_hour: int | None
    ) -> None:
        if start_hour is None and end_hour is None:
            return
        if start_hour is None or end_hour is None:
            raise AppException(
                status_code=422, detail="Both business hours must be provided"
            )
        if start_hour == end_hour:
            raise AppException(
                status_code=422, detail="Business hours window cannot be zero"
            )

    def _apply_business_hours(
        self,
        *,
        when: datetime,
        timezone: str,
        business_hours_start: int | None,
        business_hours_end: int | None,
    ) -> datetime:
        if business_hours_start is None or business_hours_end is None:
            return when

        if timezone.upper() == "UTC":
            tz = UTC
        else:
            try:
                tz = ZoneInfo(timezone)
            except Exception as exc:
                raise AppException(status_code=422, detail="Invalid timezone") from exc

        try:
            local_dt = when.astimezone(tz)
        except Exception as exc:
            raise AppException(status_code=422, detail="Invalid timezone") from exc
        local_hour = local_dt.hour
        if business_hours_start < business_hours_end:
            within = business_hours_start <= local_hour < business_hours_end
        else:
            within = (
                local_hour >= business_hours_start or local_hour < business_hours_end
            )

        if within:
            return when

        candidate = local_dt.replace(
            hour=business_hours_start,
            minute=0,
            second=0,
            microsecond=0,
        )
        if candidate <= local_dt:
            candidate = candidate + timedelta(days=1)
        return candidate.astimezone(UTC)

    def _track_event(
        self,
        *,
        event_type: str,
        entity_id: int,
        metadata: dict[str, str | int | float | bool | None],
    ) -> None:
        if self._analytics_repository is None:
            return
        self._analytics_repository.record_event(
            event_type=event_type,
            entity_type="publishing_job",
            entity_id=entity_id,
            metadata=metadata,
        )
