# Runbook

## Incident: API returns 5xx
1. Check readiness probe:
```bash
curl -f http://localhost:8000/api/v1/health/readiness
```
2. Inspect backend logs:
```bash
docker compose logs --tail=200 backend
```
3. Restart backend:
```bash
docker compose restart backend
```

## Incident: queue stuck
1. Inspect worker logs:
```bash
docker compose logs --tail=200 queue-worker retry-worker
```
2. Restart workers:
```bash
docker compose restart queue-worker retry-worker analytics-worker cleanup-worker
```

## Incident: high latency
1. Open Grafana and inspect request duration histogram.
2. Check Redis health and cache hit behavior.
3. Run performance baselines from tests/performance.

## Disaster recovery
1. Create backup:
```bash
python scripts/backup.py --db affiliate.db --images generated_images --out backups
```
2. Restore from backup:
```bash
python scripts/restore.py backups/backup-<timestamp>
```
3. Verify probes and smoke tests.
