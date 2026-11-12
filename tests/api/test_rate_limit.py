from fastapi.testclient import TestClient

from src.api.app import create_app


class Limiter:
    def __init__(self, allow):
        self.result = allow

    def allow(self):
        return self.result


def test_exhausted_limit_rejects_before_body_validation():
    with TestClient(create_app(rate_limiter=Limiter(False))) as client:
        response = client.post("/matches", content="private-invalid-body")
        assert response.status_code == 429
        assert response.headers["retry-after"] == "60"
        assert response.headers["content-type"] == "application/problem+json"
        assert "private-invalid-body" not in response.text


def test_admitted_health_preserves_contract_without_cors():
    with TestClient(create_app(rate_limiter=Limiter(True))) as client:
        response = client.get("/health", headers={"Origin": "https://example.invalid"})
        assert response.json() == {"status": "ok"}
        assert "access-control-allow-origin" not in response.headers


def test_limiter_failure_fails_closed_without_exception_text():
    class FailedLimiter:
        def allow(self):
            raise RuntimeError("private database credentials")

    with TestClient(create_app(rate_limiter=FailedLimiter())) as client:
        response = client.get("/health")
        assert response.status_code == 503
        assert "private" not in response.text
