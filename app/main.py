import time
from uuid import uuid4
from collections.abc import Awaitable
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.metrics import http_request_duration_seconds
from app.core.metrics import http_requests_total
from app.core.middleware import RateLimitMiddleware
from app.core.middleware import SecurityHeadersMiddleware
from app.core.request_context import set_request_id
from app.core.tracing import configure_tracing
from app.core.logging import configure_logging, logger
from app.db.session import get_engine


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, json_logs=settings.log_json)

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins_list or ["*"],
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_middleware(
        SecurityHeadersMiddleware,
        csp=settings.security_csp,
        hsts_enabled=settings.security_hsts_enabled,
        hsts_max_age=settings.security_hsts_max_age,
    )
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.rate_limit_requests_per_minute,
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    configure_tracing(app=app, engine=get_engine(), settings=settings)

    @app.middleware("http")
    async def request_logging_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid4())
        set_request_id(request_id)
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        response.headers["x-request-id"] = request_id
        http_requests_total.labels(
            method=request.method,
            path=request.url.path,
            status_code=str(response.status_code),
        ).inc()
        http_request_duration_seconds.labels(
            method=request.method,
            path=request.url.path,
        ).observe(elapsed_ms / 1000)
        logger.info(
            "http_request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "elapsed_ms": round(elapsed_ms, 2),
            },
        )
        return response

    return app


app = create_app()
