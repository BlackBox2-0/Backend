from datetime import datetime
from models import RiskAssessment
from typing import List

# In-memory audit log (persiste mientras el contenedor corre)
_audit_log: List[dict] = []


def log_assessment(assessment: RiskAssessment) -> dict:
    entry = {
        "id": f"evt-{len(_audit_log) + 1}",
        "timestamp": assessment.assessed_at,
        "user": assessment.event.user,
        "role": assessment.event.role,
        "department": assessment.event.department,
        "action": assessment.event.action,
        "resource": assessment.event.resource,
        "risk_score": assessment.risk_score,
        "decision": assessment.decision,
        "reasoning": assessment.reasoning,
        "flags": assessment.flags,
    }
    _audit_log.append(entry)
    return entry


def get_audit_log() -> List[dict]:
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