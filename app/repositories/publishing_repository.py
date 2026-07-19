from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from typing import Protocol

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.credentials import decrypt_secret, encrypt_secret
from app.models.publishing import (
    DeadLetterQueue,
    MediaAttachment,
    PlatformCredential,
    PublishingAuditLog,
    PublishingHistory,
    PublishingJob,
    PublishingQueue,
    SocialAccount,
)


class PublishingRepositoryProtocol(Protocol):
    def create_social_account(
        self,
        *,
        owner_user_id: int,
        platform: str,
        account_name: str,
        account_identifier: str,
        permissions: list[str],
        timezone: str,
        business_hours_start: int | None,
        business_hours_end: int | None,
        rate_limit_per_minute: int,
    ) -> SocialAccount: ...


class PublishingRepository(PublishingRepositoryProtocol):
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_social_account(
        self,
        *,
        owner_user_id: int,
        platform: str,
        account_name: str,
        account_identifier: str,
        permissions: list[str],
        timezone: str,
        business_hours_start: int | None,
        business_hours_end: int | None,
        rate_limit_per_minute: int,
    ) -> SocialAccount:
        account = SocialAccount(
            owner_user_id=owner_user_id,
            platform=platform,
            account_name=account_name,
            account_identifier=account_identifier,
            permissions=permissions,
            timezone=timezone,
            business_hours_start=business_hours_start,
            business_hours_end=business_hours_end,
            rate_limit_per_minute=rate_limit_per_minute,
        )
        self._db.add(account)
        self._db.flush()
        return account

    def get_social_account(self, social_account_id: int) -> SocialAccount | None:
        return self._db.get(SocialAccount, social_account_id)

    def list_social_accounts(self, *, owner_user_id: int) -> list[SocialAccount]:
        stmt = (
            select(SocialAccount)
            .where(SocialAccount.owner_user_id == owner_user_id)
            .order_by(SocialAccount.created_at.desc())
        )
        return list(self._db.scalars(stmt))

    def update_social_account(
        self,
        *,
        social_account_id: int,
        owner_user_id: int,
        data: dict[str, object],
    ) -> SocialAccount | None:
        account = self.get_social_account(social_account_id)
        if account is None or account.owner_user_id != owner_user_id:
            return None
        for key, value in data.items():
            setattr(account, key, value)
        self._db.add(account)
        self._db.flush()
        return account

    def delete_social_account(
        self, *, social_account_id: int, owner_user_id: int
    ) -> bool:
        account = self.get_social_account(social_account_id)
        if account is None or account.owner_user_id != owner_user_id:
            return False
        self._db.delete(account)
        self._db.flush()
        return True

    def upsert_platform_credential(
        self,
        *,
        social_account_id: int,
        access_token: str,
        refresh_token: str | None,
        token_expires_at: datetime | None,
        scopes: list[str],
        encryption_key: str,
    ) -> PlatformCredential:
        stmt = select(PlatformCredential).where(
            PlatformCredential.social_account_id == social_account_id
        )
        row = self._db.execute(stmt).scalar_one_or_none()

        access_token_encrypted = encrypt_secret(
            plaintext=access_token,
            secret_key=encryption_key,
        )
        refresh_token_encrypted: str | None = None
        if refresh_token:
            refresh_token_encrypted = encrypt_secret(
                plaintext=refresh_token,
                secret_key=encryption_key,
            )

        if row is None:
            row = PlatformCredential(
                social_account_id=social_account_id,
                access_token_encrypted=access_token_encrypted,
                refresh_token_encrypted=refresh_token_encrypted,
                token_expires_at=token_expires_at,
                scopes=scopes,
            )
        else:
            row.access_token_encrypted = access_token_encrypted
            row.refresh_token_encrypted = refresh_token_encrypted
            row.token_expires_at = token_expires_at
            row.scopes = scopes
            row.rotated_at = datetime.now(UTC)

        self._db.add(row)
        self._db.flush()
        return row

    def get_decrypted_credentials(
        self, *, social_account_id: int, encryption_key: str
    ) -> dict[str, str | None]:
        stmt = select(PlatformCredential).where(
            PlatformCredential.social_account_id == social_account_id
        )
        row = self._db.execute(stmt).scalar_one_or_none()
        if row is None:
            return {"access_token": None, "refresh_token": None}

        access_token = decrypt_secret(
            ciphertext=row.access_token_encrypted,
            secret_key=encryption_key,
        )
        refresh_token: str | None = None
        if row.refresh_token_encrypted:
            refresh_token = decrypt_secret(
                ciphertext=row.refresh_token_encrypted,
                secret_key=encryption_key,
            )
        return {"access_token": access_token, "refresh_token": refresh_token}

    def create_job(
        self,
        *,
        owner_user_id: int,
        social_account_id: int,
        product_id: int | None,
        caption_content_id: int | None,
        generated_image_id: int | None,
        post_type: str,
        platform: str,
        status: str,
        caption_text: str,
        hashtags_text: str | None,
        mentions_text: str | None,
        cta_text: str | None,
        affiliate_link: str | None,
        alt_text: str | None,
        idempotency_key: str,
        scheduled_for: datetime | None,
        recurrence_rule: str | None,
        timezone: str,
        business_hours_enforced: bool,
        max_retries: int,
        expires_at: datetime | None,
    ) -> PublishingJob:
        item = PublishingJob(
            owner_user_id=owner_user_id,
            social_account_id=social_account_id,
            product_id=product_id,
            caption_content_id=caption_content_id,
            generated_image_id=generated_image_id,
            post_type=post_type,
            platform=platform,
            status=status,
            caption_text=caption_text,
            hashtags_text=hashtags_text,
            mentions_text=mentions_text,
            cta_text=cta_text,
            affiliate_link=affiliate_link,
            alt_text=alt_text,
            idempotency_key=idempotency_key,
            scheduled_for=scheduled_for,
            recurrence_rule=recurrence_rule,
            timezone=timezone,
            business_hours_enforced=business_hours_enforced,
            max_retries=max_retries,
            expires_at=expires_at,
            provider_response={},
        )
        self._db.add(item)
        self._db.flush()
        return item

    def get_job(self, job_id: int) -> PublishingJob | None:
        return self._db.get(PublishingJob, job_id)

    def get_job_by_idempotency_key(
        self, *, owner_user_id: int, idempotency_key: str
    ) -> PublishingJob | None:
        stmt = select(PublishingJob).where(
            PublishingJob.owner_user_id == owner_user_id,
            PublishingJob.idempotency_key == idempotency_key,
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def list_jobs(
        self, *, owner_user_id: int, limit: int, offset: int
    ) -> list[PublishingJob]:
        stmt = (
            select(PublishingJob)
            .where(PublishingJob.owner_user_id == owner_user_id)
            .order_by(PublishingJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self._db.scalars(stmt))

    def count_jobs(self, *, owner_user_id: int) -> int:
        stmt = select(func.count(PublishingJob.id)).where(
            PublishingJob.owner_user_id == owner_user_id
        )
        return int(self._db.scalar(stmt) or 0)

    def create_queue_entry(
        self,
        *,
        job_id: int,
        owner_user_id: int,
        status: str,
        scheduled_for: datetime | None,
        priority: int,
        visible_at: datetime,
    ) -> PublishingQueue:
        row = PublishingQueue(
            job_id=job_id,
            owner_user_id=owner_user_id,
            status=status,
            scheduled_for=scheduled_for,
            priority=priority,
            visible_at=visible_at,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def get_queue_entry(self, *, job_id: int) -> PublishingQueue | None:
        stmt = select(PublishingQueue).where(PublishingQueue.job_id == job_id)
        return self._db.execute(stmt).scalar_one_or_none()

    def claim_due_queue_jobs(
        self,
        *,
        now: datetime,
        limit: int,
        worker_id: str,
    ) -> list[PublishingQueue]:
        stmt = (
            select(PublishingQueue.id)
            .where(
                PublishingQueue.status.in_(["pending", "scheduled", "retry"]),
                PublishingQueue.visible_at <= now,
            )
            .order_by(PublishingQueue.priority.asc(), PublishingQueue.visible_at.asc())
            .limit(limit)
        )
        candidates = [row[0] for row in self._db.execute(stmt).all()]

        claimed: list[int] = []
        for queue_id in candidates:
            update_stmt = (
                update(PublishingQueue)
                .where(
                    PublishingQueue.id == queue_id,
                    PublishingQueue.status.in_(["pending", "scheduled", "retry"]),
                )
                .values(
                    status="publishing",
                    locked_at=now,
                    lock_owner=worker_id,
                )
            )
            result = self._db.execute(update_stmt)
            if result.rowcount == 1:
                claimed.append(queue_id)

        if not claimed:
            return []

        self._db.flush()
        rows = (
            select(PublishingQueue)
            .where(PublishingQueue.id.in_(claimed))
            .order_by(PublishingQueue.priority.asc())
        )
        return list(self._db.scalars(rows))

    def update_job_status(
        self,
        *,
        job_id: int,
        status: str,
        retry_count: int | None = None,
        next_retry_at: datetime | None = None,
        last_error: str | None = None,
        latency_ms: int | None = None,
        published_at: datetime | None = None,
        cancelled_at: datetime | None = None,
        provider_response: dict[str, str | int | float | bool | None] | None = None,
    ) -> PublishingJob:
        item = self.get_job(job_id)
        if item is None:
            raise ValueError("Publishing job not found")

        item.status = status
        if retry_count is not None:
            item.retry_count = retry_count
        item.next_retry_at = next_retry_at
        item.last_error = last_error
        if latency_ms is not None:
            item.latency_ms = latency_ms
        if published_at is not None:
            item.published_at = published_at
        if cancelled_at is not None:
            item.cancelled_at = cancelled_at
        if provider_response is not None:
            item.provider_response = provider_response
        self._db.add(item)
        self._db.flush()
        return item

    def update_queue_status(
        self,
        *,
        job_id: int,
        status: str,
        visible_at: datetime | None = None,
        lock_owner: str | None = None,
    ) -> PublishingQueue:
        row = self.get_queue_entry(job_id=job_id)
        if row is None:
            raise ValueError("Publishing queue entry not found")
        row.status = status
        row.lock_owner = lock_owner
        row.locked_at = datetime.now(UTC)
        if visible_at is not None:
            row.visible_at = visible_at
        self._db.add(row)
        self._db.flush()
        return row

    def add_media_attachment(
        self,
        *,
        job_id: int,
        media_type: str,
        source_type: str,
        uri: str,
        thumbnail_uri: str | None = None,
    ) -> MediaAttachment:
        checksum = sha256(uri.encode("utf-8")).hexdigest()
        item = MediaAttachment(
            job_id=job_id,
            media_type=media_type,
            source_type=source_type,
            uri=uri,
            checksum=checksum,
            thumbnail_uri=thumbnail_uri,
        )
        self._db.add(item)
        self._db.flush()
        return item

    def list_media_attachments(self, *, job_id: int) -> list[MediaAttachment]:
        stmt = (
            select(MediaAttachment)
            .where(MediaAttachment.job_id == job_id)
            .order_by(MediaAttachment.id.asc())
        )
        return list(self._db.scalars(stmt))

    def create_history(
        self,
        *,
        job_id: int,
        owner_user_id: int,
        platform: str,
        account_identifier: str,
        caption: str,
        hashtags: str | None,
        mentions: str | None,
        cta: str | None,
        affiliate_link: str | None,
        media_refs: list[str],
        provider_response: dict[str, str | int | float | bool | None],
        published_at: datetime | None,
        status: str,
        retry_count: int,
        latency_ms: int | None,
    ) -> PublishingHistory:
        row = PublishingHistory(
            job_id=job_id,
            owner_user_id=owner_user_id,
            platform=platform,
            account_identifier=account_identifier,
            caption=caption,
            hashtags=hashtags,
            mentions=mentions,
            cta=cta,
            affiliate_link=affiliate_link,
            media_refs=media_refs,
            provider_response=provider_response,
            published_at=published_at,
            status=status,
            retry_count=retry_count,
            latency_ms=latency_ms,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def list_history(
        self, *, owner_user_id: int, limit: int, offset: int
    ) -> list[PublishingHistory]:
        stmt = (
            select(PublishingHistory)
            .where(PublishingHistory.owner_user_id == owner_user_id)
            .order_by(PublishingHistory.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self._db.scalars(stmt))

    def count_history(self, *, owner_user_id: int) -> int:
        stmt = select(func.count(PublishingHistory.id)).where(
            PublishingHistory.owner_user_id == owner_user_id
        )
        return int(self._db.scalar(stmt) or 0)

    def add_dead_letter(
        self,
        *,
        job_id: int,
        owner_user_id: int,
        reason: str,
        payload: dict[str, str | int | float | bool | None],
    ) -> DeadLetterQueue:
        row = DeadLetterQueue(
            job_id=job_id,
            owner_user_id=owner_user_id,
            reason=reason,
            payload=payload,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def create_audit_log(
        self,
        *,
        owner_user_id: int,
        action: str,
        details: dict[str, str | int | float | bool | None],
        job_id: int | None = None,
    ) -> PublishingAuditLog:
        row = PublishingAuditLog(
            owner_user_id=owner_user_id,
            action=action,
            details=details,
            job_id=job_id,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def commit(self) -> None:
        self._db.commit()

    def rollback(self) -> None:
        self._db.rollback()
