import json
from models import EnforcementResult, RiskAssessment
from typing import List
from database import dump_json, fetch_all, insert_record, next_id

# In-memory audit log (persiste mientras el contenedor corre)
_audit_log: List[dict] = []


def log_assessment(assessment: RiskAssessment) -> dict:
    model_recommendation = assessment.model_recommendation or assessment.decision
    final_decision = assessment.policy_decision.final_decision if assessment.policy_decision else assessment.decision
    final_decision_source = (
        assessment.policy_decision.final_decision_source if assessment.policy_decision else "model"
    )
    policy_rule_matched = assessment.policy_decision.policy_rule_matched if assessment.policy_decision else None
    policy_version = assessment.policy_decision.policy_version if assessment.policy_decision else None
    entry = {
        "id": next_id("audit_log", "evt"),
        "timestamp": assessment.assessed_at,
        "audit_type": "assessment",
        "user": assessment.event.user,
        "role": assessment.event.role,
        "department": assessment.event.department,
        "action": assessment.event.action,
        "resource": assessment.event.resource,
        "risk_score": assessment.risk_score,
        "model_recommendation": model_recommendation,
        "policy_rule_matched": policy_rule_matched,
        "decision": final_decision,
        "final_decision_source": final_decision_source,
        "policy_version": policy_version,
        "reasoning": assessment.reasoning,
        "flags": assessment.flags,
        "policy_decision": assessment.policy_decision.model_dump() if assessment.policy_decision else None,
    }
    _audit_log.append(entry)
    insert_record(
        "audit_log",
        {
            "id": entry["id"],
            "timestamp": entry["timestamp"],
            "audit_type": entry.get("audit_type"),
            "user": entry["user"],
            "role": entry["role"],
            "department": entry["department"],
            "action": entry["action"].value,
            "resource": entry["resource"],
            "risk_score": entry["risk_score"],
            "decision": entry["decision"].value,
            "analyst_decision": entry["model_recommendation"].value,
            "requires_human_approval": 1 if entry["decision"] == "ESCALATE" else 0,
            "payload_json": dump_json(entry),
        },
    )
    return entry


def log_enforcement(result: EnforcementResult) -> dict:
    final_decision_source = (
        result.policy_decision.final_decision_source if result.policy_decision else "policy"
    )
    policy_rule_matched = result.policy_decision.policy_rule_matched if result.policy_decision else None
    policy_version = result.policy_decision.policy_version if result.policy_decision else None
    entry = {
        "id": next_id("audit_log", "evt"),
        "timestamp": result.enforced_at,
        "audit_type": "enforcement",
        "user": result.event.user,
        "role": result.event.role,
        "department": result.event.department,
        "action": result.event.action,
        "resource": result.event.resource,
        "risk_score": result.risk_score,
        "model_recommendation": result.analyst_decision,
        "policy_rule_matched": policy_rule_matched,
        "analyst_decision": result.analyst_decision,
        "decision": result.final_decision,
        "final_decision_source": final_decision_source,
        "policy_version": policy_version,
        "requires_human_approval": result.requires_human_approval,
        "reasoning": result.reasoning,
        "flags": result.flags,
        "enforcement_event": result.enforcement_event,
        "policy_decision": result.policy_decision.model_dump() if result.policy_decision else None,
    }
    _audit_log.append(entry)
    insert_record(
        "audit_log",
        {
            "id": entry["id"],
            "timestamp": entry["timestamp"],
            "audit_type": entry.get("audit_type"),
            "user": entry["user"],
            "role": entry["role"],
            "department": entry["department"],
            "action": entry["action"].value,
            "resource": entry["resource"],
            "risk_score": entry["risk_score"],
            "decision": entry["decision"].value,
            "analyst_decision": entry["model_recommendation"].value,
            "requires_human_approval": 1 if entry["requires_human_approval"] else 0,
            "payload_json": dump_json(entry),
        },
    )
    return entry


def get_audit_log() -> List[dict]:
    rows = fetch_all("audit_log", "timestamp DESC")
    if rows:
        return [json.loads(row["payload_json"]) for row in rows]
    return list(reversed(_audit_log))


def get_stats() -> dict:
    total = len(_audit_log)
    if total == 0:
        return {"total": 0, "blocked": 0, "escalated": 0, "allowed": 0, "avg_risk": 0}

    blocked = sum(1 for e in _audit_log if e["decision"] == "BLOCK")
    escalated = sum(1 for e in _audit_log if e["decision"] == "ESCALATE")
    allowed = sum(1 for e in _audit_log if e["decision"] == "ALLOW")
    avg_risk = sum(e["risk_score"] for e in _audit_log) / total

    return {
        "total": total,
        "blocked": blocked,
        "escalated": escalated,
        "allowed": allowed,
        "avg_risk": round(avg_risk, 3)
    }
