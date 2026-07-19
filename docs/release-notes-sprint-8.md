# Sprint 8 Release Notes

## Summary
Sprint 8 delivers a production platform extension layer with container orchestration, background workers, observability, security hardening, performance tooling, CI/CD updates, and backup/restore workflows.

## Added
- Multi-stage Dockerfiles for backend and frontend
- Production compose stack with nginx, Redis, MinIO, Prometheus, Grafana, Loki, and Promtail
- Development compose override
- Five worker entrypoints: queue, retry, analytics, cleanup, health
- Liveness, readiness, and metrics endpoints
- Structured logging and Prometheus metrics middleware
- CORS hardening, security headers, and rate limiting middleware
- Connection pool settings for non-SQLite DBs
- Backup and restore scripts
- Load, stress, and benchmark test scripts
- CI workflow extension and tag-based release workflow

## Compatibility
No existing API route was removed or renamed. Existing functionality remains backward compatible.
