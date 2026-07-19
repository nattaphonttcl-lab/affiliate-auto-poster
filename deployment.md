# Production Deployment

## Scope

This deployment path is for a single-node production installation using Docker Compose, SQLite, Redis, MinIO, Nginx, and optional observability services. SQLite is suitable only for a single host with persistent storage and regular verified backups.

## Deployment Artifacts

- `docker-compose.production.yml`: production-only service topology
- `production.env.example`: required environment variables template
- `docs/database-backup.md`: backup, restore, verification, disaster recovery
- `PRODUCTION_CHECKLIST.md`: go-live checklist

## Prerequisites

1. Docker Engine 27+ and Docker Compose v2
2. TLS certificate and key mounted at `deploy/nginx/certs/fullchain.pem` and `deploy/nginx/certs/privkey.pem`
3. Persistent storage available for:
   - SQLite volume
   - generated images volume
   - Redis append-only files
   - MinIO object store data
   - backup volume
4. `.env.production` created from `production.env.example`

## Required Secret Handling

1. Do not use placeholder values from `production.env.example`.
2. Prefer `*_FILE` environment variables for:
   - `SECRET_KEY_FILE`
   - `INITIAL_ADMIN_PASSWORD_FILE`
   - provider API key files
   - `MINIO_ACCESS_KEY_FILE`
   - `MINIO_SECRET_KEY_FILE`
3. Restrict file permissions on secret files to the deployment user only.

## Deployment Steps

1. Create the production environment file.

```bash
cp production.env.example .env.production
```

2. Fill all production secrets and origin values.

3. Validate Compose configuration.

```bash
docker compose -f docker-compose.production.yml --env-file .env.production config
```

4. Run database migrations before the application starts.

```bash
docker compose -f docker-compose.production.yml --env-file .env.production run --rm migrate
```

5. Start the core production stack.

```bash
docker compose -f docker-compose.production.yml --env-file .env.production up -d backend frontend nginx redis minio queue-worker retry-worker analytics-worker cleanup-worker health-worker
```

6. Optionally start observability.

```bash
docker compose -f docker-compose.production.yml --env-file .env.production --profile observability up -d prometheus loki promtail grafana
```

## Health Validation

Verify:

```bash
curl -f https://localhost/api/v1/health
curl -f https://localhost/api/v1/health/liveness
curl -f https://localhost/api/v1/health/readiness
```

Expected behavior:

- `/health`: process is responding
- `/health/liveness`: process loop is alive
- `/health/readiness`: returns `200` only when database and required dependencies are ready

## Smoke Test

Run after every deployment:

1. Login with a known non-bootstrap account.
2. Verify image generation endpoint works.
3. Verify publishing endpoints work.
4. Verify analytics overview responds.
5. Verify queue-worker logs show successful iterations.

## Operational Settings Verified

- Restart policy: `unless-stopped` for long-running services
- Health checks: backend, frontend, nginx, redis, minio
- Persistent volumes: SQLite, images, backups, Redis, MinIO, observability stores
- Timezone: `TZ=UTC`
- Logging: JSON-file driver with rotation (`10m`, `5` files)
- Environment isolation: production values via `.env.production`

## Rollback

1. Restore the previous application image tag or Git revision.
2. Re-run migrations only if the rollback target supports the current schema.
3. If data rollback is required, use the procedure in `docs/database-backup.md`.
4. Re-run the smoke test and health checks.

## Remaining Operational Constraints

1. SQLite does not support multi-writer, multi-node production scaling.
2. Compose is suitable for single-host production, not high-availability orchestration.
3. Alert rules are not provisioned automatically; Grafana/Prometheus alerting still needs environment-specific setup.