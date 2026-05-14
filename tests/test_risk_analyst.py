import asyncio
import json

import risk_analyst
from models import RiskDecision


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "risk_score": 0.87,
                                "decision": "BLOCK",
                                "reasoning": "Sensitive export from finance.",
                                "flags": ["data_export", "sensitive_department"],
                            }
                        )
                    }
                }
            ]
        }


class FakeAsyncClient:
    def __init__(self, timeout):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url, json, headers):
        assert url == risk_analyst.GEMINI_URL
        assert headers["Authorization"] == "Bearer test-key"
        assert json["model"] == "gemini-2.5-flash"
        return FakeResponse()


def test_assess_risk_maps_gemini_response(monkeypatch, enterprise_event):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(risk_analyst.httpx, "AsyncClient", FakeAsyncClient)

    result = asyncio.run(risk_analyst.assess_risk(enterprise_event))

    assert result.event == enterprise_event
    assert result.risk_score == 0.87
    assert result.decision == RiskDecision.BLOCK
    assert result.reasoning == "Sensitive export from finance."
    assert result.flags == ["data_export", "sensitive_department"]


def test_assess_risk_requires_api_key(monkeypatch, enterprise_event):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    try:
        asyncio.run(risk_analyst.assess_risk(enterprise_event))
    except ValueError as exc:
        assert str(exc) == "GEMINI_API_KEY not set"
    else:
        raise AssertionError("Expected ValueError when GEMINI_API_KEY is missing")
