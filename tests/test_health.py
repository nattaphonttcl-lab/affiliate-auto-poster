from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.distributed_cache import RedisHealth


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_liveness_probe(client: TestClient) -> None:
    response = client.get("/api/v1/health/liveness")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_probe(client: TestClient) -> None:
    response = client.get("/api/v1/health/readiness")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_readiness_probe_returns_503_when_redis_is_unavailable(
    client: TestClient, monkeypatch
) -> None:
    settings = get_settings()
    previous = settings.redis_enabled
    settings.redis_enabled = True
    monkeypatch.setattr(RedisHealth, "ping", lambda self: False)

    try:
        response = client.get("/api/v1/health/readiness")
    finally:
        settings.redis_enabled = previous

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"


def test_health_metrics_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/health/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text


def test_security_headers_present(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
