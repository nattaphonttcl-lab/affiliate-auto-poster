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
			captions.py
			dependencies.py
			health.py
			images.py
			products.py
			router.py
			scheduler.py
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
			caption.py
			product.py
			promotional_image.py
			scheduled_post.py
			user.py
		repositories/
			caption_repository.py
			image_repository.py
			product_repository.py
			scheduler_repository.py
			user_repository.py
		schemas/
			auth.py
			caption.py
			common.py
			image.py
			product.py
			scheduler.py
			user.py
		services/
			auth_service.py
			caption_service.py
			image_service.py
			scheduler_service.py
			shopee_product_service.py
			user_service.py
		utils/
			ai_caption_engine.py
			caption_prompt_templates.py
			image_generator_engine.py
			image_templates.py
			post_publisher.py
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
- AI Caption Engine: product lookup -> prompt template selection by style -> 10 caption generation -> persistent storage.
- Image Generator: product lookup -> Pillow template rendering for Facebook cover -> PNG file generation -> metadata persistence.
- Scheduler: schedule storage -> due-job executor -> publisher adapter (audit/webhook) -> execution logs.

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
- `POST /api/v1/captions/generate` (JWT required)
- `POST /api/v1/images/promotional` (JWT required)
- `POST /api/v1/scheduler/posts` (JWT required)
- `POST /api/v1/scheduler/run` (JWT required)
- `GET /api/v1/scheduler/posts` (JWT required)

## Testing

```bash
pytest -q
```

## Shopee Product Service

- Input: Shopee product URL.
- Output fields: `title`, `price`, `original_price`, `discount`, `rating`, `sold_count`, `images`, `shop_name`, `category`, `affiliate_url`.
- Cache: persisted in `products` table with TTL (`SHOPEE_CACHE_TTL_MINUTES`).
- Parser timeout: `SHOPEE_REQUEST_TIMEOUT_SECONDS`.

## AI Caption Engine

- Input: `product_id` and style.
- Supported styles: `funny`, `review`, `promotion`, `storytelling`, `urgency`.
- Output: exactly 10 Facebook-ready captions; each item contains `hook`, `cta`, `emoji`, `hashtags`, and `caption_text`.
- Prompt templates: centralized in `app/utils/caption_prompt_templates.py` and used by `AICaptionEngine`.
- Persistence: generated caption batches and caption items are stored in `caption_batches` and `captions` tables.

## Image Generator

- Input: `product_id`, `template`, optional `shop_logo_url`.
- Templates supported: `classic`, `bold`, `minimal`.
- Rendering engine: Pillow-based promotional image generation as Facebook Cover (`820x312`) in PNG format.
- Content used: product image, price, discount, shop logo (or placeholder), CTA banner.
- Persistence: metadata stored in `promotional_images` table (path, size, format, source URLs).
- Config:
	- `IMAGE_OUTPUT_DIR`
	- `IMAGE_REQUEST_TIMEOUT_SECONDS`

## Scheduler

- Create scheduled posts for Facebook with product, optional caption batch, and optional promotional image.
- Run due jobs via API-triggered executor for deterministic operations.
- Publisher modes:
	- `audit`: marks scheduled posts as published and logs execution.
	- `webhook`: posts payload to configured webhook.
- Config:
	- `SCHEDULER_PUBLISHER_MODE`
	- `SCHEDULER_WEBHOOK_URL`
	- `SCHEDULER_WEBHOOK_TIMEOUT_SECONDS`

## Logging

- Configurable log level via `LOG_LEVEL`.
- HTTP request logs include method, path, status code, and latency.

