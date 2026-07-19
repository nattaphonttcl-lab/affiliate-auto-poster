# Health Monitoring

## Health Endpoints

- `GET /api/v1/health`: process responds
- `GET /api/v1/health/liveness`: application event loop is alive
- `GET /api/v1/health/readiness`: application is ready for traffic
- `GET /api/v1/health/metrics`: Prometheus metrics endpoint

## Readiness Semantics

Readiness verifies:

1. database query succeeds
2. Redis connectivity succeeds when `REDIS_ENABLED=true`

Readiness returns `503` when required dependencies are degraded. This endpoint should be used for load balancer and container health decisions.

## Metrics to Monitor

### Infrastructure

- CPU utilization per container
- memory RSS and container memory limit headroom
- disk usage for:
  - SQLite volume
  - image storage volume
  - Redis append-only data
  - MinIO object data

### Application

- HTTP request latency
- HTTP error rate
- readiness failures
- publishing failure count
- image generation failure count
- queue processing latency
- queue backlog length

### Data Services

- SQLite file growth rate
- Redis health and reconnect failures
- MinIO health and available capacity

## Logging Expectations

- structured JSON logs enabled via `LOG_JSON=true`
- request logs include request id and timing
- unhandled exceptions logged with stack traces
- worker lifecycle and iteration logs present

Do not log:

- passwords
- JWTs
- API keys
- refresh tokens
- secret file contents

## Monitoring Workflow

1. Prometheus scrapes `/api/v1/health/metrics`
2. Loki stores structured logs from containers
3. Grafana dashboards visualize health, latency, queue behavior, and failures

## Minimum Alerts

Configure alerts for:

1. readiness endpoint returning non-200
2. sustained 5xx error rate
3. queue backlog growth over threshold
4. publishing failure spikes
5. image generation failure spikes
6. disk usage above threshold on SQLite or image volumes
7. Redis unavailable when enabled

## Manual Verification

```bash
curl -f https://localhost/api/v1/health
curl -f https://localhost/api/v1/health/liveness
curl -f https://localhost/api/v1/health/readiness
curl -f https://localhost/api/v1/health/metrics
```