# System Recovery

## Scope

This runbook covers operational recovery for a single-host production deployment.

## Recovery Scenarios

### Database lost

1. Stop backend and workers.
2. Restore the latest verified database backup.
3. Start backend.
4. Verify readiness, login, publishing history, and analytics.

### Image storage lost

1. Restore `generated_images` from the latest verified backup.
2. Verify image preview and generation endpoints.
3. Check disk capacity before resuming traffic.

### Redis lost

1. Restart Redis.
2. Confirm readiness returns `200`.
3. Restart workers if they do not recover automatically.
4. Verify scheduled publishing resumes.

### Server restart

1. Start the production Compose stack.
2. Confirm migration job success.
3. Verify backend readiness and worker logs.

### Server migration

1. Provision the target host.
2. Copy TLS certificates and `.env.production` securely.
3. Restore database and image backups.
4. Start `docker-compose.production.yml`.
5. Run smoke tests.

## Recovery Validation

After any recovery:

1. `GET /api/v1/health`
2. `GET /api/v1/health/readiness`
3. login test
4. image generation test
5. publishing test
6. analytics test

## RTO and RPO

- Recovery Time Objective: 30 to 60 minutes for host-level restore
- Recovery Point Objective: up to 24 hours with daily backups; lower if backups run more frequently

## Remaining Constraints

1. SQLite remains a single-host dependency.
2. Off-host backup storage is mandatory for meaningful disaster recovery.
3. Redis persistence reduces cache loss but does not replace database backup.