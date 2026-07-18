import json
import logging
from datetime import UTC, datetime
from logging.config import dictConfig

from opentelemetry import trace

from app.core.request_context import get_request_id


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        current_span = trace.get_current_span()
        span_context = current_span.get_span_context()

        trace_id = f"{span_context.trace_id:032x}" if span_context.is_valid else "-"
        span_id = f"{span_context.span_id:016x}" if span_context.is_valid else "-"

        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
            "trace_id": trace_id,
            "span_id": span_id,
        }

        for key in (
            "method",
            "path",
            "status_code",
            "elapsed_ms",
            "tracing_enabled",
            "tracing_service_name",
            "tracing_exporter",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO", *, json_logs: bool = True) -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
                },
                "json": {
                    "()": "app.core.logging.JsonFormatter",
                },
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "json" if json_logs else "standard",
                    "level": level,
                }
            },
            "root": {"handlers": ["default"], "level": level},
        }
    )


logger = logging.getLogger("app")
