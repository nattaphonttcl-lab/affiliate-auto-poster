# Contributing

## Branching
- Base branch for ongoing work: `develop` (recommended)
- Protected production branch: `main`
- Naming:
  - `feature/<short-name>`
  - `release/<version>`
  - `hotfix/<short-name>`

## Development Setup
1. Create virtual environment and install backend dependencies.
2. Install frontend dependencies in `frontend/`.
3. Run migrations before local testing.

## Validation Before PR
- `python -m ruff check .`
- `python -m black --check .`
- `python -m pytest -q`
- `npm run test`
- `npm run build`

## Pull Requests
- Keep PRs focused and small.
- Reference related issues.
- Include risk notes and rollout considerations.
