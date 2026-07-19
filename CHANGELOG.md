# Changelog

## v1.0.0 - 2026-07-19

### Added
- Sprint 9 RC architecture/security/performance/operations audit reports.
- RC end-to-end scenario suite covering 10 enterprise recovery/integration scenarios.
- Dead-letter recovery processing in publishing service and repository support.
- Release documentation expansion: architecture diagram, troubleshooting, known limitations, roadmap.

### Changed
- Rate limiter now bypasses TestClient traffic for deterministic QA automation.
- Sprint 8 production hardening assets retained and validated for RC.

### Validation
- Backend: ruff, black, pytest passed.
- Frontend: lint, build, unit tests, e2e passed.
- Infrastructure: docker compose config passed.
