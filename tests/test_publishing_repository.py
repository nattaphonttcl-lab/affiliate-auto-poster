from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.repositories.publishing_repository import PublishingRepository


def test_social_account_and_job_lifecycle(db_session: Session) -> None:
    repo = PublishingRepository(db_session)

    account = repo.create_social_account(
        owner_user_id=1,
        platform="facebook",
        account_name="Main",
        account_identifier="page_1",
        permissions=["publish_posts"],
        timezone="UTC",
        business_hours_start=9,
        business_hours_end=18,
        rate_limit_per_minute=60,
    )
    repo.upsert_platform_credential(
        social_account_id=account.id,
        access_token="access-token",
        refresh_token="refresh-token",
        token_expires_at=None,
        scopes=["publish"],
        encryption_key="repo-test-key",
    )
    job = repo.create_job(
        owner_user_id=1,
        social_account_id=account.id,
        product_id=None,
        caption_content_id=None,
        generated_image_id=None,
        post_type="facebook_feed",
        platform="facebook",
        status="pending",
        caption_text="caption",
        hashtags_text="#sale",
        mentions_text="@shop",
        cta_text="buy",
        affiliate_link="https://example.com",
        alt_text="alt",
        idempotency_key="repo-idem-1",
        scheduled_for=None,
        recurrence_rule=None,
        timezone="UTC",
        business_hours_enforced=False,
        max_retries=5,
        expires_at=None,
    )
    queue = repo.create_queue_entry(
        job_id=job.id,
        owner_user_id=1,
        status="pending",
        scheduled_for=None,
        priority=100,
        visible_at=datetime.now(UTC),
    )
    repo.add_media_attachment(
        job_id=job.id,
        media_type="image",
        source_type="external",
        uri="https://cdn.example.com/img.jpg",
    )
    repo.create_history(
        job_id=job.id,
        owner_user_id=1,
        platform="facebook",
        account_identifier="page_1",
        caption="caption",
        hashtags="#sale",
        mentions="@shop",
        cta="buy",
        affiliate_link="https://example.com",
        media_refs=["https://cdn.example.com/img.jpg"],
        provider_response={"ok": True},
        published_at=datetime.now(UTC),
        status="published",
        retry_count=0,
        latency_ms=100,
    )
    repo.commit()

    creds = repo.get_decrypted_credentials(
        social_account_id=account.id,
        encryption_key="repo-test-key",
    )
    assert creds["access_token"] == "access-token"

    listed = repo.list_jobs(owner_user_id=1, limit=10, offset=0)
    assert len(listed) == 1
    assert listed[0].id == job.id

    queue_row = repo.get_queue_entry(job_id=job.id)
    assert queue_row is not None
    assert queue_row.id == queue.id
