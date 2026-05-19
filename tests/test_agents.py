import asyncio

import agents
from models import RiskAssessment, RiskDecision


async def fake_assess_risk(event):
    return RiskAssessment(
        event=event,
        risk_score=0.82,
        decision=RiskDecision.BLOCK,
        reasoning="Synthetic test result.",
        flags=["synthetic"],
        assessed_at="2026-05-15T10:00:00",
    )


def test_get_agents_dashboard_exposes_backend_catalog():
    dashboard = agents.get_agents_dashboard()

    assert dashboard["summary"]["total_agents"] == 8
    assert len(dashboard["agents"]) == 8
    assert dashboard["agents"][0]["id"] == "Agent-01"
    assert dashboard["agents"][-1]["id"] == "CORE"


def test_run_agent_test_returns_updated_dashboard(monkeypatch):
    monkeypatch.setattr(agents, "assess_risk", fake_assess_risk)

    result = asyncio.run(agents.run_agent_test("Agent-06"))

    assert result["agent_id"] == "Agent-06"
    assert "dashboard" in result
    assert result["dashboard"]["summary"]["orchestration_runs"] == 1
    assert result["dashboard"]["summary"]["processed_events"] == 1
