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
			analytics.py
			auth.py
			captions.py
			dashboard.py
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
			analytics_event.py
			caption.py
			product.py
			promotional_image.py
			scheduled_post.py
			user.py
		repositories/
			analytics_repository.py
			caption_repository.py
			dashboard_repository.py
			image_repository.py
			product_repository.py
			scheduler_repository.py
			user_repository.py
		schemas/
			analytics.py
			auth.py
			caption.py
			common.py
			dashboard.py
			image.py
			product.py
			scheduler.py
			user.py
		services/
			analytics_service.py
			auth_service.py
			caption_service.py
			dashboard_service.py
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
- Marketplace Product Module: provider registry/factory -> URL normalizer -> product fingerprint -> cache-aware aggregate repository upsert.
- Enterprise AI Content Engine: prompt template repository -> provider factory -> quality guardrails -> content history/versioning.
- AI Caption Engine: product lookup -> prompt template selection by style -> 10 caption generation -> persistent storage.
- Image Generator: product lookup -> Pillow template rendering for Facebook cover -> PNG file generation -> metadata persistence.
- Scheduler: schedule storage -> due-job executor -> publisher adapter (audit/webhook) -> execution logs.
- Dashboard: aggregated operational KPIs and recent activity feed across products, captions, images, and scheduler.
- Analytics: event tracking with aggregated overview metrics and event timeline APIs.
- Scheduler aggregate uses optimistic locking via `scheduled_posts.version` for safe concurrent state transitions.
- Domain events are captured in an Outbox table (`outbox_events`) for reliable asynchronous publication.

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
- `POST /api/v1/products/shopee` (JWT required, backward-compatible legacy endpoint)
- `POST /api/v1/products/import` (JWT required)
- `GET /api/v1/products` (JWT required)
- `GET /api/v1/products/{product_id}` (JWT required)
- `PATCH /api/v1/products/{product_id}` (JWT required)
- `DELETE /api/v1/products/{product_id}` (JWT required)
- `POST /api/v1/products/{product_id}/refresh` (JWT required)
- `POST /api/v1/ai/generate` (JWT required)
- `POST /api/v1/ai/regenerate` (JWT required)
- `GET /api/v1/ai/history` (JWT required)
- `GET /api/v1/ai/templates` (JWT required)
- `POST /api/v1/ai/templates` (JWT required)
- `PATCH /api/v1/ai/templates/{template_id}` (JWT required)
- `DELETE /api/v1/ai/templates/{template_id}` (JWT required)
- `POST /api/v1/captions/generate` (JWT required)
- `POST /api/v1/images/promotional` (JWT required)
- `POST /api/v1/scheduler/posts` (JWT required)
- `POST /api/v1/scheduler/posts/{scheduled_post_id}/confirm` (JWT required)
- `POST /api/v1/scheduler/run` (JWT required)
- `GET /api/v1/scheduler/posts` (JWT required)
- `GET /api/v1/dashboard/summary` (JWT required)
- `GET /api/v1/dashboard/activities` (JWT required)
- `GET /api/v1/analytics/overview` (JWT required)
- `GET /api/v1/analytics/events` (JWT required)

## Testing

```bash
pytest -q
```

## Validation Commands

```bash
ruff check .
black --check .
pytest -q --cov=app --cov-report=term-missing
alembic upgrade head
python -m compileall app tests alembic
```

## Marketplace Product Module

- Aggregate entities:
	- `products`
	- `product_images`
	- `product_price_histories`
	- `product_categories`
	- `product_version_histories`
- Provider architecture:
	- `MarketplaceProvider`
	- `ShopeeProvider`
	- `LazadaProvider` (stub)
	- `TikTokShopProvider` (stub)
	- `MarketplaceProviderRegistry`
	- `build_provider_registry` provider factory
- URL security and normalization:
	- Public-network URL validation
	- Host normalization and canonical URL generation
	- Unsupported marketplace rejection
- Duplicate prevention:
	- Product fingerprint (`sha256`) from marketplace + external product id + normalized URL
	- Repository upsert by fingerprint/normalized URL
- Cache layer:
	- In-memory TTL cache abstraction (`CacheBackend`, `InMemoryTTLCache`)
	- Cache-first lookup before provider fetch
- Refresh queue:
	- Queue abstraction (`ProductRefreshQueue`)
	- In-memory implementation (`InMemoryProductRefreshQueue`)
- Backward compatibility:
	- Legacy endpoint `POST /api/v1/products/shopee` remains supported

## Enterprise AI Content Engine

- Provider interface and implementations:
	- `AIProvider`
	- `OpenAIProvider`
	- `GeminiProvider`
	- `ClaudeProvider`
	- `DeepSeekProvider`
	- `OpenRouterProvider`
	- `ProviderFactory` with provider client reuse
- Prompt template system (versioned):
	- `PromptTemplate`
	- `PromptVariable`
	- `PromptRepository` behavior through `AIContentRepository`
	- Categories: `facebook`, `tiktok`, `instagram`, `youtube_shorts`, `shopee_live`, `general_affiliate`
	- Template fields: `system_prompt`, `user_prompt`, `variables`, `temperature`, `max_tokens`, `version`, `status`
- Content history and versioning:
	- `GeneratedContent` as content history root
	- `GeneratedContentVersion` for immutable generated snapshots
	- Tracks provider, model, prompt version, generated text, cost, latency, creator, and timestamps
- Generation support:
	- Content types: Facebook/TikTok captions, hook, CTA, SEO keywords, hashtags, short/long description, product/comparison review, buying guide, FAQ
	- Writing styles: professional, friendly, mother_blogger, luxury, minimal, emotional, sales, urgency, storytelling
	- Audience profiles: parents, students, office_workers, beauty, fashion, gaming, pets, home, electronics, health
	- Regeneration preserves full version history
- Security:
	- Provider credentials are encrypted at rest (`ai_provider_configs.api_key_encrypted`)
	- API keys are never returned by API responses
	- Prompt instruction validation blocks unsafe override/jailbreak patterns
	- Per-user generation rate limiting
- Quality guardrails:
	- Minimum length checks
	- Duplicate detection for regeneration and cross-content outputs
	- Banned words filtering
	- Emoji optimization for captions
	- Hashtag normalization and cap
	- Platform-specific length limits
- Performance:
	- Prompt template cache with TTL
	- Provider client reuse through factory cache
	- Async provider generation path

### AI Configuration

- `AI_PROVIDER_ENCRYPTION_KEY`
- `AI_TEMPLATE_CACHE_TTL_SECONDS`
- `AI_GENERATION_RATE_LIMIT_PER_MINUTE`
- `AI_BANNED_WORDS`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `CLAUDE_API_KEY`
- `DEEPSEEK_API_KEY`
- `OPENROUTER_API_KEY`

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
- Every scheduled post is owner-scoped (`owner_user_id`) and is only visible/actionable by its owner.
- Explicit user confirmation is required before any scheduled post can be executed.
- Confirmation is idempotent and writes audit entries to `scheduled_post_audits`.
- State machine: `awaiting_confirmation -> confirmed -> processing -> published|failed`.
- Optimistic locking: every transition validates `version` and increments it on success.
- Outbox pattern: every scheduler domain event (`created`, `confirmed`, `published`, `failed`) is persisted to `outbox_events` in the same transaction.
- Run due jobs via API-triggered executor for deterministic operations and worker-safe claim semantics.
- Publisher modes:
	- `audit`: marks scheduled posts as published and logs execution.
	- `webhook`: posts payload to configured webhook.
- Config:
	- `SCHEDULER_PUBLISHER_MODE`
	- `SCHEDULER_WEBHOOK_URL`
	- `SCHEDULER_WEBHOOK_TIMEOUT_SECONDS`

## Platform Safety Policy

- This system does not implement or encourage unsafe Facebook group auto-posting behavior.
- Publishing flow is constrained to supported integration adapters or explicit user-confirmed execution.
- Scheduler execution will skip unconfirmed jobs until confirmation is provided.

## Dashboard

- Summary endpoint exposes total counts for products, caption batches, promotional images, and scheduled posts.
- Scheduler breakdown includes `awaiting_confirmation`, `confirmed`, `processing`, `published`, and `failed` jobs.
- Activities endpoint merges recent caption batches, generated images, and scheduled posts into a single feed.

## Analytics

- Event tracking stored in `analytics_events` table for key actions across product parsing, caption generation, image generation, and scheduler execution.
- Overview endpoint provides totals by event type and daily event volumes over a configurable time window.
- Events endpoint returns recent analytics event timeline entries with metadata payloads.

## Logging

- Configurable log level via `LOG_LEVEL`.
- Structured JSON logging enabled by default (`LOG_JSON=true`).
- HTTP request logs include method, path, status code, latency, request id, and trace/span ids.

## Tracing

- OpenTelemetry tracing is supported and opt-in by configuration (`TRACING_ENABLED=false` by default).
- FastAPI and SQLAlchemy are instrumented automatically on app startup.
- Configure service identity and exporter target with:
	- `TRACING_SERVICE_NAME`
	- `TRACING_OTLP_ENDPOINT` (optional; falls back to console exporter when empty)

## CI

- GitHub Actions workflow at `.github/workflows/ci.yml` runs:
	- Ruff
	- Black
	- Pytest + coverage
	- Bandit
	- Docker image build

