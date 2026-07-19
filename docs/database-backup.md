# Database Backup and Recovery

## Scope

This application uses SQLite for the primary database. Production backup and recovery must assume a single-node deployment with file-based persistence.

## Backup Objectives

- Protect `affiliate.db`
- Protect generated local images
- Produce verifiable backup artifacts
- Support host migration and disaster recovery

## Backup Procedure

Run from the backend container or the host with access to the same mounted paths.

```bash
python scripts/backup.py --db /data/affiliate.db --images /app/generated_images --out /backups
```

The backup creates:

- a SQLite backup produced through SQLite's backup API
- `generated_images.zip`
- `manifest.json` with checksums and database integrity results

## Verification

After backup completion, verify:

1. `manifest.json` exists
2. the manifest contains `integrity_check: ok`
3. the backup directory contains the database file and image archive

Recommended command:

```bash
python - <<'PY'
import json
from pathlib import Path

latest = sorted(Path('/backups').glob('backup-*'))[-1]
manifest = json.loads((latest / 'manifest.json').read_text(encoding='utf-8'))
print(manifest)
PY
```

## Restore Procedure

Stop application writers before restore:

```bash
docker compose -f docker-compose.production.yml --env-file .env.production stop backend queue-worker retry-worker analytics-worker cleanup-worker health-worker
```

Restore from a chosen backup directory:

```bash
python scripts/restore.py /backups/backup-YYYYMMDDTHHMMSSZ --db /data/affiliate.db --images /app/generated_images
```

The restore process:

- verifies backup checksums when `manifest.json` is present
- validates SQLite integrity before restore
- restores the database using SQLite backup semantics
- restores images from the archived snapshot

## Post-Restore Verification

1. Restart the application stack.

```bash
docker compose -f docker-compose.production.yml --env-file .env.production up -d backend queue-worker retry-worker analytics-worker cleanup-worker health-worker
```

2. Verify health and readiness.

```bash
curl -f https://localhost/api/v1/health
curl -f https://localhost/api/v1/health/readiness
```

3. Verify login, analytics, publishing history, and image history with a smoke test account.

## Corruption Recovery

If SQLite corruption is detected:

1. Stop backend and all workers immediately.
2. Preserve the corrupted file for forensic analysis.
3. Restore the most recent verified backup.
4. Re-run smoke tests before opening traffic.

## Disaster Recovery Guidance

### Database lost

1. Provision a clean host.
2. Restore `/data/affiliate.db` from the latest verified backup.
3. Start the stack and confirm readiness.

### Images lost

1. Restore `generated_images.zip` through `scripts/restore.py`.
2. Verify image generation and history endpoints.

### Full host loss

1. Restore `.env.production` from your secret manager or vault.
2. Restore database and images from the latest backup.
3. Reattach TLS certificates.
4. Redeploy with `docker-compose.production.yml`.

## Backup Frequency

- Minimum: daily full backup
- Recommended: hourly backup during active publishing windows if operationally feasible

## Retention

- Keep at least 7 daily backups
- Keep at least 4 weekly backups
- Store one backup copy off-host

## RPO and RTO

- Target RPO: 24 hours with daily backups, lower if scheduled more frequently
- Target RTO: 30 to 60 minutes for a single-node host restore