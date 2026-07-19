from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import text

from app.core.logging import configure_logging, logger
from app.db.session import SessionLocal
from app.workers.runtime import get_runtime_settings, run_forever


def _run_once() -> None:
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
        logger.info(
            "health_worker_ok",
            extra={"component": "database", "checked_at": datetime.now(UTC)},
        )


def main() -> None:
    settings = get_runtime_settings()
    configure_logging(settings.log_level, json_logs=settings.log_json)
    run_forever("health-worker", _run_once, settings)


if __name__ == "__main__":
    main()
