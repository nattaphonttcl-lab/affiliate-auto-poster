from fastapi.testclient import TestClient


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
    assert response.json()["status"] in {"ready", "degraded"}


def test_health_metrics_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/health/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text


def test_security_headers_present(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
