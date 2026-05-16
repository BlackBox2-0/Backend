from __future__ import annotations

from datetime import datetime
from typing import Any

from database import fetch_all, insert_record, next_id

_ROLE_LEVEL: dict[str, int] = {
    "employee": 0,
    "manager": 1,
    "director": 2,
    "admin": 3,
}


def can_override(role: str, original_decision: str) -> bool:
    level = _ROLE_LEVEL.get(role.lower(), 0)
    if original_decision == "BLOCK":
        return level >= 3  # admin only
    return level >= 1  # manager+ for ESCALATE or ALLOW


def create_override(
    event_id: str,
    actor: str,
    role: str,
    reason: str,
    new_decision: str,
) -> dict[str, Any]:
    override_id = next_id("overrides", "ovr")
    created_at = datetime.utcnow().isoformat()
    record = {
        "id": override_id,
        "original_event_id": event_id,
        "actor": actor,
        "role": role,
        "reason": reason,
        "new_decision": new_decision,
        "created_at": created_at,
    }
    insert_record("overrides", record)
    return record


def get_overrides() -> list[dict[str, Any]]:
    return fetch_all("overrides", "created_at DESC")
