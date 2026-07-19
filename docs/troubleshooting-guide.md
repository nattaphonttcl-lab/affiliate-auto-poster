# Troubleshooting Guide

## API returns 429 in production
- Check RATE_LIMIT_REQUESTS_PER_MINUTE value.
- Confirm source IP behavior behind reverse proxy.

## Publishing jobs stuck in scheduled/pending
- Inspect queue-worker logs.
- Verify queue visible_at timestamps and worker health.
- Use dead-letter recovery worker for failed jobs.

## Image/AI generation fails
- Verify provider credentials.
- Confirm provider/model configuration is active.
- Check fallback provider order in settings.

## Readiness returns degraded
- Validate Redis connectivity and REDIS_URL.
- Check database connectivity and migrations.

## Frontend blank page behind nginx
- Verify frontend upstream and static build artifacts.
- Ensure TLS certificates are mounted correctly.
