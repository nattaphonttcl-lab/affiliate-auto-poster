from __future__ import annotations

import logging
import signal
import time
from collections.abc import Callable

from app.core.config import Settings, get_settings

logger = logging.getLogger("app.workers")

_running = True


def _signal_handler(signum: int, _frame: object) -> None:
    global _running
    _running = False
    logger.info("worker_signal_received", extra={"signal": signum})


def install_signal_handlers() -> None:
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)


def run_forever(name: str, runner: Callable[[], None], settings: Settings) -> None:
    install_signal_handlers()
    logger.info("worker_started", extra={"worker": name})

    while _running:
        start = time.perf_counter()
        try:
            runner()
        except Exception:
            logger.exception("worker_iteration_failed", extra={"worker": name})
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "worker_iteration_complete",
                extra={"worker": name, "elapsed_ms": elapsed_ms},
            )

        if _running:
            time.sleep(max(settings.workers_poll_seconds, 1))

    logger.info("worker_stopped", extra={"worker": name})


def get_runtime_settings() -> Settings:
    return get_settings()
