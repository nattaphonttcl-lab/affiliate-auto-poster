# Affiliate Auto Poster Enterprise - Backend (Phase 1)

Production-ready FastAPI backend foundation with Clean Architecture-inspired layering, SQLAlchemy 2, Alembic migrations, JWT authentication, and automated tests.

## Tech Stack

- Python 3.12
- FastAPI
- SQLAlchemy 2.x
- Alembic
- SQLite
- JWT (python-jose)
- Password hashing (passlib + bcrypt)
- Pydantic v2 + pydantic-settings
- Docker + Docker Compose
- Pytest

## Project Structure

```text
backend/
	app/
		api/
			auth.py
			dependencies.py
			health.py
			products.py
			router.py
			users.py
		core/
			config.py
			exceptions.py
			logging.py
			security.py
		db/
			base.py
			session.py
		models/
			product.py
			user.py
		repositories/
			product_repository.py
			user_repository.py
		schemas/
			auth.py
			common.py
			product.py
			user.py
		services/
			shopee_product_service.py
			auth_service.py
			user_service.py
		utils/
			shopee_parser.py
			shopee_validator.py
		main.py
	alembic/
		versions/
	alembic.ini
	Dockerfile
	docker-compose.yml
	requirements.txt
	tests/
```

## Architecture Notes

- API Layer (`app/api`): request/response orchestration and dependency injection.
- Service Layer (`app/services`): business rules and application workflows.
- Repository Layer (`app/repositories`): persistence access through SQLAlchemy session.
- Domain Model Layer (`app/models`): SQLAlchemy ORM entities.
- Infrastructure Layer (`app/core`, `app/db`): settings, security, logging, DB session lifecycle.
- Shopee Product Service: URL validation -> parser -> cache lookup/upsert in repository -> API response.

## Local Setup

1. Create virtual environment and install dependencies:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

2. Create environment file:

```bash
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/macOS
```

3. Run migrations:

```bash
alembic upgrade head
```

4. Start API:

```bash
uvicorn app.main:app --reload
```

Swagger UI is available at `http://localhost:8000/docs`.

## Docker

Run backend with Docker Compose:

```bash
docker compose up --build
```

## API Endpoints (Phase 1)

- `GET /api/v1/health`
- `POST /api/v1/auth/login`
- `POST /api/v1/users`
- `GET /api/v1/users` (JWT required)
- `GET /api/v1/users/{user_id}` (JWT required)
- `PATCH /api/v1/users/{user_id}` (JWT required)
- `POST /api/v1/products/shopee` (JWT required)

## Testing

```bash
pytest -q
```

## Shopee Product Service

- Input: Shopee product URL.
- Output fields: `title`, `price`, `original_price`, `discount`, `rating`, `sold_count`, `images`, `shop_name`, `category`, `affiliate_url`.
- Cache: persisted in `products` table with TTL (`SHOPEE_CACHE_TTL_MINUTES`).
- Parser timeout: `SHOPEE_REQUEST_TIMEOUT_SECONDS`.

## Logging

- Configurable log level via `LOG_LEVEL`.
- HTTP request logs include method, path, status code, and latency.

