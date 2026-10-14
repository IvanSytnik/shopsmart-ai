import httpx
import openai
import pytest
from fastapi.testclient import TestClient

from tests.conftest import FakeLLMClient

BODY = {"supermarkets": ["Lidl"], "budget": 50}
OPENAI_URL = "https://api.openai.com/v1/chat/completions"


@pytest.mark.parametrize(
    "content",
    [
        "Sure! Here is your list: milk, bread",
        "```json\n{not json}\n```",
        '{"items": [{"product": "Milk"}]}',
        None,
    ],
    ids=["prose", "broken-json", "wrong-shape", "empty"],
)
def test_unusable_llm_output_returns_502(
    client: TestClient,
    fake_llm: FakeLLMClient,
    caplog: pytest.LogCaptureFixture,
    content: str | None,
) -> None:
    fake_llm.reply_raw(content)

    response = client.post("/generate", json=BODY)

    assert response.status_code == 502
    assert response.json() == {"detail": "Failed to generate plan"}
    assert "LLM returned an unusable plan" in caplog.text


def test_openai_connection_error_returns_503(
    client: TestClient, fake_llm: FakeLLMClient, caplog: pytest.LogCaptureFixture
) -> None:
    fake_llm.fail_with(openai.APIConnectionError(request=httpx.Request("POST", OPENAI_URL)))

    response = client.post("/generate", json=BODY)

    assert response.status_code == 503
    assert response.json() == {"detail": "AI service unavailable"}
    assert "OpenAI request failed" in caplog.text


def test_openai_status_error_does_not_leak_message(
    client: TestClient, fake_llm: FakeLLMClient, caplog: pytest.LogCaptureFixture
) -> None:
    request = httpx.Request("POST", OPENAI_URL)
    fake_llm.fail_with(
        openai.AuthenticationError(
            "Incorrect API key provided: sk-internal-detail",
            response=httpx.Response(401, request=request),
            body=None,
        )
    )

    response = client.post("/generate", json=BODY)

    assert response.status_code == 503
    assert response.json() == {"detail": "AI service unavailable"}
    assert "sk-internal-detail" not in response.text
    assert "sk-internal-detail" in caplog.text  # the real error is logged server-side


def test_unexpected_error_returns_generic_500(
    client: TestClient, fake_llm: FakeLLMClient, caplog: pytest.LogCaptureFixture
) -> None:
    fake_llm.fail_with(RuntimeError("internal stack detail"))

    response = client.post("/generate", json=BODY)

    assert response.status_code == 500
    assert response.json() == {"detail": "Failed to generate plan"}
    assert "internal stack detail" not in response.text
    assert "internal stack detail" in caplog.text
