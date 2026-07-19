# Production Checklist

## Infrastructure

- Docker Engine and Compose versions validated
- Persistent volumes provisioned for SQLite, images, Redis, MinIO, and backups
- Host disk capacity reviewed
- Host timezone set or `TZ=UTC` supplied
- TLS certificate and key installed

## Security

- HTTPS enabled through Nginx
- `CORS_ALLOWED_ORIGINS` restricted to production origins
- production secrets are not placeholder defaults
- secret files use restricted file permissions
- JWT expiration reviewed (`ACCESS_TOKEN_EXPIRE_MINUTES`)
- password hashing remains bcrypt-based
- MinIO and Grafana admin credentials rotated
- least-privilege access applied to deployment users and secret storage

## Deployment

- `.env.production` created from `production.env.example`
- `docker-compose.production.yml` validated with `docker compose config`
- `migrate` job completed successfully
- backend, frontend, nginx, redis, and minio are healthy
- worker containers are running and restarting automatically

## Monitoring

- health endpoints responding
- Prometheus scraping metrics
- Loki receiving logs
- Grafana datasource connectivity verified
- alert rules configured for readiness, queue backlog, and failure spikes

## Backup

- scheduled backup job configured
- backup output written to persistent storage
- `manifest.json` verification included in backup review
- off-host backup copy enabled

## Recovery

- restore procedure tested with `scripts/restore.py`
- database backup integrity verified
- image archive restore verified
- RPO and RTO accepted by stakeholders

## Performance

- cold startup measured in the deployment environment
- memory usage recorded under normal load
- health, login, publishing, analytics, and image generation latencies sampled
- queue throughput validated under expected traffic

## Operations

- smoke test documented and rehearsed
- on-call team has access to deployment and recovery docs
- log retention and rotation settings verified
- rollback plan documented