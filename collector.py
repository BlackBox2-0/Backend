
from datetime import datetime
from typing import Any

from models import CollectedEvent, CollectorEventInput, EnterpriseEvent, EventType

_collected_events: list[CollectedEvent] = []

FIELD_ALIASES = {
    "user": ("user", "user_id", "employee", "employee_id", "actor"),
    "role": ("role", "user_role", "position"),
    "department": ("department", "area", "team", "business_unit"),
    "action": ("action", "event_type", "type", "activity"),
    "resource": ("resource", "target", "asset", "system", "url"),
    "context": ("context", "details", "metadata", "message", "description"),
    "timestamp": ("timestamp", "time", "occurred_at", "created_at"),
}

ACTION_ALIASES = {
    "EXPORT_DATA": EventType.DATA_EXPORT,
    "DOWNLOAD_DATA": EventType.DATA_EXPORT,
    "PERMISSIONS_CHANGE": EventType.PERMISSION_CHANGE,
    "CHANGE_PERMISSION": EventType.PERMISSION_CHANGE,
    "AFTER_HOURS_ACCESS": EventType.ACCESS_AFTER_HOURS,
    "DELETE_MASS": EventType.MASS_DELETE,
    "ADMIN_ESCALATION": EventType.PRIVILEGE_ESCALATION,
    "API_CALL_UNUSUAL": EventType.UNUSUAL_API_CALL,
}


def collect_event(incoming: CollectorEventInput) -> CollectedEvent:
    raw_event = _extract_raw_event(incoming)
    normalized_event = _normalize_event(raw_event)

    collected = CollectedEvent(
        id=f"col-{len(_collected_events) + 1}",
        source=incoming.source or "api",
        normalized_event=normalized_event,
        raw_event=raw_event,
        received_at=datetime.utcnow().isoformat(),
    )
    _collected_events.append(collected)
    return collected


def get_collected_events() -> list[CollectedEvent]:
    return list(reversed(_collected_events))


def _extract_raw_event(incoming: CollectorEventInput) -> dict[str, Any]:
    if incoming.payload is not None:
        return incoming.payload

    raw = incoming.model_dump(exclude={"source", "payload"}, exclude_none=True)
    return raw


def _normalize_event(raw_event: dict[str, Any]) -> EnterpriseEvent:
    normalized: dict[str, Any] = {}

    for target_field, aliases in FIELD_ALIASES.items():
        value = _first_present(raw_event, aliases)
        if value is not None:
            normalized[target_field] = value

    missing = [
        field
        for field in ("user", "role", "department", "action", "resource")
        if not normalized.get(field)
    ]
    if missing:
        raise ValueError(f"Missing required event fields: {', '.join(missing)}")

    normalized["action"] = _normalize_action(str(normalized["action"]))
    if "timestamp" not in normalized:
        normalized["timestamp"] = datetime.utcnow().isoformat()

    context = normalized.get("context")
    if isinstance(context, (dict, list)):
        normalized["context"] = str(context)

    return EnterpriseEvent(**normalized)


def _first_present(raw_event: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = raw_event.get(key)
        if value is not None and value != "":
            return value
    return None


def _normalize_action(action: str) -> EventType:
    candidate = action.strip().replace("-", "_").replace(" ", "_").upper()
    if candidate in ACTION_ALIASES:
        return ACTION_ALIASES[candidate]
    return EventType(candidate)
