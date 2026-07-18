from __future__ import annotations

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from sqlalchemy.engine import Engine

from app.core.config import Settings
from app.core.logging import logger


def configure_tracing(*, app: FastAPI, engine: Engine, settings: Settings) -> None:
    if not settings.tracing_enabled:
        return

    resource = Resource.create({"service.name": settings.tracing_service_name})
    provider = TracerProvider(resource=resource)

    if settings.tracing_otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=settings.tracing_otlp_endpoint)
    else:
        exporter = ConsoleSpanExporter()

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine)

    logger.info(
        "Tracing configured",
        extra={
            "tracing_enabled": True,
            "tracing_service_name": settings.tracing_service_name,
            "tracing_exporter": "otlp" if settings.tracing_otlp_endpoint else "console",
        },
    )
