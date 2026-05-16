from datetime import datetime
from typing import Any

from audit import log_enforcement
from database import dump_json, fetch_all, insert_record, next_id
from models import EnforcementResult, RiskAssessment, RiskDecision

_enforcement_events: list[dict[str, Any]] = []


def enforce_assessment(assessment: RiskAssessment) -> EnforcementResult:
    analyst_decision = assessment.model_recommendation or assessment.decision
    final_decision = (
        assessment.policy_decision.final_decision
        if assessment.policy_decision
        else assessment.decision
    )
    enforced_at = datetime.utcnow().isoformat()
    requires_human_approval = final_decision == RiskDecision.ESCALATE

    enforcement_event = {
        "id": next_id("enforcement_events", "enf"),
        "type": "ENFORCEMENT_DECISION",
        "timestamp": enforced_at,
        "user": assessment.event.user,
        "resource": assessment.event.resource,
        "analyst_decision": analyst_decision,
        "final_decision": final_decision,
        "requires_human_approval": requires_human_approval,
        "final_decision_source": (
            assessment.policy_decision.final_decision_source if assessment.policy_decision else "policy"
        ),
        "policy_rule_matched": (
            assessment.policy_decision.policy_rule_matched if assessment.policy_decision else None
        ),
        "policy_version": assessment.policy_decision.policy_version if assessment.policy_decision else None,
    }

    result = EnforcementResult(
        event=assessment.event,
        risk_score=assessment.risk_score,
        analyst_decision=analyst_decision,
        final_decision=final_decision,
        requires_human_approval=requires_human_approval,
        reasoning=_build_reasoning(assessment, analyst_decision, final_decision),
        flags=assessment.flags,
        enforcement_event=enforcement_event,
        enforced_at=enforced_at,
        policy_decision=assessment.policy_decision,
        executive_summary=assessment.executive_summary,
    )

    _enforcement_events.append(enforcement_event)
    insert_record(
        "enforcement_events",
        {
            "id": enforcement_event["id"],
            "event_type": enforcement_event["type"],
            "timestamp": enforcement_event["timestamp"],
            "user": enforcement_event["user"],
            "resource": enforcement_event["resource"],
            "analyst_decision": enforcement_event["analyst_decision"].value,
            "final_decision": enforcement_event["final_decision"].value,
            "requires_human_approval": 1 if enforcement_event["requires_human_approval"] else 0,
            "payload_json": dump_json(enforcement_event),
        },
    )
    log_enforcement(result)
    return result


def get_enforcement_events() -> list[dict[str, Any]]:
    rows = fetch_all("enforcement_events", "timestamp DESC")
    if rows:
        return [__import__("json").loads(row["payload_json"]) for row in rows]
    return list(reversed(_enforcement_events))


def _build_reasoning(
    assessment: RiskAssessment,
    analyst_decision: RiskDecision,
    final_decision: RiskDecision,
) -> str:
    if final_decision == RiskDecision.BLOCK:
        prefix = "Final decision BLOCK: policy enforcement blocks the action."
    elif final_decision == RiskDecision.ALLOW:
        prefix = "Final decision ALLOW: the action can continue under the active policy."
    else:
        prefix = "Final decision ESCALATE: human approval is required before continuing."

    source = assessment.policy_decision.final_decision_source if assessment.policy_decision else "policy"
    rule = assessment.policy_decision.policy_rule_matched if assessment.policy_decision else None
    rule_fragment = f" Rule matched: {rule}." if rule else ""
    return (
        f"{prefix} Analyst decision was {analyst_decision.value}. "
        f"Final decision source: {source}.{rule_fragment} {assessment.reasoning}"
    )
