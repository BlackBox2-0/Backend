from audit import get_audit_log
from enforcer import enforce_assessment, get_enforcement_events
from models import RiskAssessment, RiskDecision


def test_enforcer_blocks_high_risk_assessment(enterprise_event):
    assessment = RiskAssessment(
        event=enterprise_event,
        risk_score=0.9,
        decision=RiskDecision.ESCALATE,
        reasoning="High risk export.",
        flags=["high_risk"],
        assessed_at="2026-05-13T10:00:00",
    )

    result = enforce_assessment(assessment)

    assert result.final_decision == RiskDecision.BLOCK
    assert result.requires_human_approval is False
    assert result.enforcement_event["id"] == "enf-1"
    assert get_enforcement_events() == [result.enforcement_event]
    assert get_audit_log()[0]["audit_type"] == "enforcement"


def test_enforcer_escalates_non_blocking_assessment(enterprise_event):
    assessment = RiskAssessment(
        event=enterprise_event,
        risk_score=0.4,
        decision=RiskDecision.ALLOW,
        reasoning="Low analyst risk still requires review by policy.",
        flags=[],
        assessed_at="2026-05-13T10:00:00",
    )

    result = enforce_assessment(assessment)

    assert result.final_decision == RiskDecision.ESCALATE
    assert result.requires_human_approval is True
