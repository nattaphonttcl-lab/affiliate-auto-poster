# Risk Assessment (v1.0.0 RC)

## High
- External provider dependencies (social + AI + image providers) require valid production credentials and quota controls.

## Medium
- In-memory rate limiter and caches are single-instance behaviors; distributed consistency requires Redis-backed implementation for horizontal scale.
- SQLite default database is not suitable for production multi-writer workloads; production should use managed PostgreSQL/MySQL.
- Some provider implementations are integration stubs by design; manual verification is required before go-live.

## Low
- Build warning on frontend bundle size (>500k) indicates optimization opportunity, not immediate blocker.
- Monitoring alert rules are not yet codified; dashboards/datasources are present.

## Mitigations
- Use production env + secret files and rotate keys.
- Replace SQLite with production RDBMS before scale deployment.
- Complete manual provider integration checklist in operations runbook.
- Add alert rules and retention policy tuning in observability stack.
