import asyncio

import orchestrator
from models import CollectorEventInput, RiskAssessment, RiskDecision


async def fake_assess_risk(event):
    return RiskAssessment(
        event=event,
        risk_score=0.7,
        decision=RiskDecision.ESCALATE,
        reasoning="Risk requires review.",
        flags=["review_required"],
        assessed_at="2026-05-13T10:00:00",
    )


def test_orchestrator_runs_full_agent_flow(monkeypatch):
    monkeypatch.setattr(orchestrator, "assess_risk", fake_assess_risk)
    incoming = CollectorEventInput(
        source="simulation",
        payload={
            "employee_id": "u-100",
            "position": "Analyst",
            "area": "Finance",
            "event_type": "export_data",
            "target": "finance/report.csv",
            "details": "Export requested from simulator",
        },
    )

    result = asyncio.run(orchestrator.orchestrate_event(incoming))

    assert result.id == "orc-1"
    assert result.collected_event.id == "col-1"
    assert result.activity.id == "act-1"
    assert result.productivity.user == "u-100"
    assert result.risk_assessment.decision == RiskDecision.ESCALATE
    assert result.enforcement.final_decision == RiskDecision.ESCALATE
    assert orchestrator.get_orchestration_runs() == [result]
