from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.security import SECURITY_HEADERS


def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "catalog_version": "test-small-2"}


def test_root_ok(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == "ShopSmart AI API"


@pytest.mark.parametrize(
    ("method", "path", "headers"),
    [
        ("GET", "/health", {}),
        ("GET", "/nope", {}),  # 404
        ("POST", "/generate", {}),  # 422 from the error handlers
        (
            "OPTIONS",
            "/generate",
            {"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
        ),
    ],
)
def test_security_headers_on_every_response(
    client: TestClient, method: str, path: str, headers: dict[str, str]
) -> None:
    response = client.request(method, path, headers=headers)

    for name, value in SECURITY_HEADERS.items():
        assert response.headers[name] == value


def test_docs_available_in_development(make_client: Callable[..., TestClient]) -> None:
    client = make_client(environment="development")

    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 200


def test_docs_disabled_in_production(make_client: Callable[..., TestClient]) -> None:
    client = make_client(environment="production")

    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404
