# Operations Guide

## Runtime services
- API: backend
- Frontend UI: frontend + nginx
- Background workers: queue-worker, retry-worker, analytics-worker, cleanup-worker, health-worker
- Data services: redis, minio
- Observability: prometheus, grafana, loki, promtail

## Health checks
- /api/v1/health
- /api/v1/health/readiness
- /api/v1/health/liveness
- /api/v1/health/metrics

## Common operations
Restart backend only:
```bash
docker compose restart backend
```

Scale queue workers:
```bash
docker compose up -d --scale queue-worker=3
```

Inspect logs:
```bash
docker compose logs -f backend queue-worker retry-worker
```

## Security baseline
- HTTPS enforced by nginx redirect 80 -> 443
- Security headers set in nginx and FastAPI middleware
- CORS explicit allow-list via CORS_ALLOWED_ORIGINS
- Per-IP rate limiting via RATE_LIMIT_REQUESTS_PER_MINUTE

## Dependency audits
- Python: python -m pip_audit
- Node: npm audit --audit-level=high (from frontend)
