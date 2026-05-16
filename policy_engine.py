from __future__ import annotations

from datetime import datetime

from database import insert_record, next_id
from models import EnterpriseEvent, PolicyDecision, RiskAssessment, RiskDecision

POLICY_VERSION = "v1.0"


def evaluate_policy(
    *,
    event: EnterpriseEvent,
    risk_score: float,
    model_recommendation: RiskDecision,
    flags: list[str],
    model_available: bool,
) -> PolicyDecision:
    hour = _extract_hour(event.timestamp)

    if not model_available:
        matched_rule = "MODEL_UNAVAILABLE_FAILSAFE_BLOCK"
        final_decision = RiskDecision.BLOCK
    elif event.action.value == "PRIVILEGE_ESCALATION" and event.role.strip().lower() == "analyst":
        matched_rule = "PRIVILEGE_ESCALATION_ANALYST_BLOCK"
        final_decision = RiskDecision.BLOCK
    elif event.action.value == "DATA_EXPORT" and hour is not None and (hour >= 22 or hour <= 6):
        matched_rule = "DATA_EXPORT_AFTER_HOURS_BLOCK"
        final_decision = RiskDecision.BLOCK
    elif risk_score >= 0.8:
        matched_rule = "RISK_SCORE_GTE_0_8_BLOCK"
        final_decision = RiskDecision.BLOCK
    elif risk_score >= 0.6:
        matched_rule = "RISK_SCORE_GTE_0_6_ESCALATE"
        final_decision = RiskDecision.ESCALATE
    else:
        matched_rule = "RISK_SCORE_LT_0_6_ALLOW"
        final_decision = RiskDecision.ALLOW

    source = _decision_source(
        matched_rule=matched_rule,
        final_decision=final_decision,
        model_recommendation=model_recommendation,
        model_available=model_available,
    )
    return PolicyDecision(
        model_recommendation=model_recommendation,
        policy_rule_matched=matched_rule,
        final_decision=final_decision,
        final_decision_source=source,
        policy_version=POLICY_VERSION,
    )


def log_policy_evaluation(assessment: RiskAssessment) -> dict[str, str]:
    if not assessment.policy_decision:
        raise ValueError("policy_decision is required to log a policy evaluation")

    policy_id = next_id("policy_evaluations", "pol")
    entry = {
        "id": policy_id,
        "event_id": next_id("policy_evaluations", "evt"),
        "run_id": next_id("policy_evaluations", "run"),
        "model_recommendation": assessment.policy_decision.model_recommendation.value,
        "policy_rule_matched": assessment.policy_decision.policy_rule_matched,
        "final_decision": assessment.policy_decision.final_decision.value,
        "final_decision_source": assessment.policy_decision.final_decision_source,
        "policy_version": assessment.policy_decision.policy_version,
        "created_at": assessment.assessed_at or datetime.utcnow().isoformat(),
    }
    insert_record("policy_evaluations", entry)
    return entry


def _decision_source(
    *,
    matched_rule: str,
    final_decision: RiskDecision,
    model_recommendation: RiskDecision,
    model_available: bool,
) -> str:
    generic_score_rules = {
        "RISK_SCORE_GTE_0_8_BLOCK",
        "RISK_SCORE_GTE_0_6_ESCALATE",
        "RISK_SCORE_LT_0_6_ALLOW",
    }
    if model_available and matched_rule in generic_score_rules and final_decision == model_recommendation:
        return "model"
    return "policy"


def _extract_hour(timestamp: str | None) -> int | None:
    if not timestamp:
        return None

    normalized = timestamp.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).hour
    except ValueError:
        return None
