import json
import os
from datetime import datetime

import httpx

from models import EnterpriseEvent, RiskAssessment, RiskDecision

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
LOCAL_MODE = "local"
PLACEHOLDER_KEYS = {"", "your_gemini_api_key_here"}


async def assess_risk(event: EnterpriseEvent) -> RiskAssessment:
    if os.getenv("RISK_ANALYST_MODE", "").lower() == LOCAL_MODE:
        return assess_risk_locally(event)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key in PLACEHOLDER_KEYS:
        raise ValueError("GEMINI_API_KEY not set")

    prompt = f"""You are an enterprise security AI. Analyze this internal action and assess its risk.

Event details:
- User: {event.user}
- Role: {event.role}
- Department: {event.department}
- Action: {event.action}
- Resource: {event.resource}
- Context: {event.context or "No additional context"}
- Timestamp: {event.timestamp or datetime.utcnow().isoformat()}

Respond ONLY with a valid JSON object in this exact format:
{{
  "risk_score": <float between 0.0 and 1.0>,
  "decision": <"ALLOW", "BLOCK", or "ESCALATE">,
  "reasoning": "<one paragraph explaining the decision>",
  "flags": ["<flag1>", "<flag2>"]
}}

Rules:
- risk_score >= 0.8 -> decision must be BLOCK
- risk_score >= 0.6 -> decision must be ESCALATE
- risk_score < 0.6 -> decision must be ALLOW
- flags are specific security concerns detected (empty list if none)"""

    payload = {
        "model": "gemini-2.5-flash",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            GEMINI_URL,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"}
        )
        response.raise_for_status()
        data = response.json()

    raw = data["choices"][0]["message"]["content"]
    result = json.loads(raw)

    return RiskAssessment(
        event=event,
        risk_score=result["risk_score"],
        decision=RiskDecision(result["decision"]),
        reasoning=result["reasoning"],
        flags=result.get("flags", []),
        assessed_at=datetime.utcnow().isoformat()
    )


def assess_risk_locally(event: EnterpriseEvent) -> RiskAssessment:
    score = 0.15
    flags: list[str] = []
    action = event.action.value
    context = (event.context or "").lower()
    resource = event.resource.lower()

    if action in {"DATA_EXPORT", "MASS_DELETE", "PRIVILEGE_ESCALATION"}:
        score += 0.35
        flags.append(action.lower())

    if "finance" in event.department.lower() or "customer" in resource:
        score += 0.2
        flags.append("sensitive_data")

    if "2am" in context or "after hours" in context or "unusual" in context:
        score += 0.2
        flags.append("unusual_context")

    score = min(round(score, 2), 1.0)
    if score >= 0.8:
        decision = RiskDecision.BLOCK
    elif score >= 0.6:
        decision = RiskDecision.ESCALATE
    else:
        decision = RiskDecision.ALLOW

    return RiskAssessment(
        event=event,
        risk_score=score,
        decision=decision,
        reasoning="Local development risk assessment based on action, department, resource, and context.",
        flags=sorted(set(flags)),
        assessed_at=datetime.utcnow().isoformat(),
    )
