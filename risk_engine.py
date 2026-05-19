from __future__ import annotations

import json
import os
from datetime import datetime

import httpx

from models import EnterpriseEvent, RiskAssessment, RiskDecision
from policy_engine import evaluate_policy, log_policy_evaluation
from risk_analyst import GEMINI_URL, PLACEHOLDER_KEYS
from risk_analyst import assess_risk as assess_model_risk
from risk_analyst import assess_risk_locally as assess_model_risk_locally


async def assess_risk(event: EnterpriseEvent) -> RiskAssessment:
    try:
        model_assessment = await assess_model_risk(event)
    except Exception as exc:
        if _is_model_unavailable(exc):
            return _fail_safe_assessment(event, exc)
        raise

    assessment = _apply_policy(model_assessment)
    log_policy_evaluation(assessment)

    if assessment.decision in (RiskDecision.BLOCK, RiskDecision.ESCALATE):
        assessment = assessment.model_copy(
            update={"executive_summary": await _generate_executive_summary(assessment)}
        )

    return assessment


def assess_risk_locally(event: EnterpriseEvent) -> RiskAssessment:
    model_assessment = assess_model_risk_locally(event)
    assessment = _apply_policy(model_assessment)
    log_policy_evaluation(assessment)
    return assessment


def _apply_policy(model_assessment: RiskAssessment) -> RiskAssessment:
    model_recommendation = model_assessment.model_recommendation or model_assessment.decision
    policy_decision = evaluate_policy(
        event=model_assessment.event,
        risk_score=model_assessment.risk_score,
        model_recommendation=model_recommendation,
        flags=model_assessment.flags,
        model_available=True,
    )
    return RiskAssessment(
        event=model_assessment.event,
        risk_score=model_assessment.risk_score,
        decision=policy_decision.final_decision,
        reasoning=model_assessment.reasoning,
        flags=model_assessment.flags,
        assessed_at=model_assessment.assessed_at,
        model_recommendation=model_recommendation,
        policy_decision=policy_decision,
    )


def _fail_safe_assessment(event: EnterpriseEvent, exc: Exception) -> RiskAssessment:
    assessed_at = datetime.utcnow().isoformat()
    flags = ["model_unavailable"]
    policy_decision = evaluate_policy(
        event=event,
        risk_score=1.0,
        model_recommendation=RiskDecision.BLOCK,
        flags=flags,
        model_available=False,
    )
    assessment = RiskAssessment(
        event=event,
        risk_score=1.0,
        decision=policy_decision.final_decision,
        reasoning=f"Gemini unavailable. Fail-safe policy block applied. {exc}",
        flags=flags,
        assessed_at=assessed_at,
        model_recommendation=RiskDecision.BLOCK,
        policy_decision=policy_decision,
    )
    log_policy_evaluation(assessment)
    return assessment


async def _generate_executive_summary(assessment: RiskAssessment) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key in PLACEHOLDER_KEYS:
        return None

    event = assessment.event
    rule = (
        assessment.policy_decision.policy_rule_matched
        if assessment.policy_decision and assessment.policy_decision.policy_rule_matched
        else "AI recommendation"
    )
    flags_str = ", ".join(assessment.flags) if assessment.flags else "none"

    prompt = (
        f'Write a 2-sentence executive security summary for this decision:\n'
        f'- User: {event.user} ({event.role}, {event.department})\n'
        f'- Action: {event.action} on {event.resource}\n'
        f'- Risk Score: {assessment.risk_score}\n'
        f'- Decision: {assessment.decision.value}\n'
        f'- Rule: {rule}\n'
        f'- Flags: {flags_str}\n\n'
        f'Format: "Access by [user] was [decision]. [One sentence explaining why, '
        f'suitable for a security audit report]." Return only the two sentences.'
    )

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                GEMINI_URL,
                json={
                    "model": "gemini-2.5-flash",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 100,
                },
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def _is_model_unavailable(exc: Exception) -> bool:
    return isinstance(exc, (ValueError, httpx.HTTPError, json.JSONDecodeError, KeyError))


__all__ = ["assess_risk", "assess_risk_locally"]
