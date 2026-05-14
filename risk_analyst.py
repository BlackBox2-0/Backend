import json
import os
from datetime import datetime

import httpx

from models import EnterpriseEvent, RiskAssessment, RiskDecision

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"


async def assess_risk(event: EnterpriseEvent) -> RiskAssessment:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
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
