from fastapi.testclient import TestClient

from tests.conftest import ALLOWED_ORIGIN

PREFLIGHT_HEADERS = {
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "content-type",
}


def test_preflight_from_listed_origin_is_allowed(client: TestClient) -> None:
    response = client.options("/generate", headers={"Origin": ALLOWED_ORIGIN, **PREFLIGHT_HEADERS})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "access-control-allow-credentials" not in response.headers


def test_preflight_from_unlisted_origin_is_rejected(client: TestClient) -> None:
    response = client.options(
        "/generate", headers={"Origin": "https://evil.example", **PREFLIGHT_HEADERS}
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_simple_request_from_unlisted_origin_gets_no_cors_header(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers
