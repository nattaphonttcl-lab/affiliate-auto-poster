from fastapi import APIRouter
from fastapi import Depends
from fastapi import Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.core.config import get_settings
from app.core.distributed_cache import RedisHealth
from app.core.metrics import export_metrics

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/liveness", summary="Liveness probe")
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/health/readiness", summary="Readiness probe")
def readiness(db: Session = Depends(get_db_session)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    settings = get_settings()
    if settings.redis_enabled:
        if not RedisHealth(settings.redis_url).ping():
            return {"status": "degraded"}
    return {"status": "ready"}


@router.get("/health/metrics", summary="Prometheus metrics")
def metrics() -> Response:
    payload, content_type = export_metrics()
    return Response(content=payload, media_type=content_type)
