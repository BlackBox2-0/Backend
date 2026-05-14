from datetime import datetime
from typing import Any

from audit import log_enforcement
from models import EnforcementResult, RiskAssessment, RiskDecision

_enforcement_events: list[dict[str, Any]] = []


def enforce_assessment(assessment: RiskAssessment) -> EnforcementResult:
    final_decision = _final_decision(assessment)
    enforced_at = datetime.utcnow().isoformat()
    requires_human_approval = final_decision == RiskDecision.ESCALATE

    enforcement_event = {
        "id": f"enf-{len(_enforcement_events) + 1}",
        "type": "ENFORCEMENT_DECISION",
        "timestamp": enforced_at,
        "user": assessment.event.user,
        "resource": assessment.event.resource,
        "analyst_decision": assessment.decision,
        "final_decision": final_decision,
        "requires_human_approval": requires_human_approval,
    }

    result = EnforcementResult(
        event=assessment.event,
        risk_score=assessment.risk_score,
        analyst_decision=assessment.decision,
        final_decision=final_decision,
        requires_human_approval=requires_human_approval,
        reasoning=_build_reasoning(assessment, final_decision),
        flags=assessment.flags,
        enforcement_event=enforcement_event,
        enforced_at=enforced_at,
    )

    _enforcement_events.append(enforcement_event)
    log_enforcement(result)
    return result


def get_enforcement_events() -> list[dict[str, Any]]:
    return list(reversed(_enforcement_events))


def _final_decision(assessment: RiskAssessment) -> RiskDecision:
    if assessment.decision == RiskDecision.BLOCK or assessment.risk_score >= 0.8:
        return RiskDecision.BLOCK
    return RiskDecision.ESCALATE


def _build_reasoning(
    assessment: RiskAssessment,
    final_decision: RiskDecision,
) -> str:
    if final_decision == RiskDecision.BLOCK:
        prefix = "Final decision BLOCK: policy enforcement blocks the action."
    else:
        prefix = "Final decision ESCALATE: human approval is required before continuing."

    return f"{prefix} Analyst decision was {assessment.decision}. {assessment.reasoning}"
