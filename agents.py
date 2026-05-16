from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, TypedDict

from activity_monitor import get_activity_observations, monitor_event
from audit import get_audit_log, get_stats
from collector import collect_event, get_collected_events
from enforcer import enforce_assessment, get_enforcement_events
from models import AgentTestInput, CollectorEventInput, EnterpriseEvent, EventType
from orchestrator import get_orchestration_runs, orchestrate_event
from productivity_detector import detect_productivity, get_productivity_detections
from risk_engine import assess_risk, assess_risk_locally


class AgentDefinition(TypedDict):
    id: str
    role: str
    module: str
    endpoint: str
    color: str
    accuracy: float
    test_label: str
    status_builder: Callable[[], tuple[str, str]]


def _collector_status() -> tuple[str, str]:
    count = len(get_collected_events())
    status = "MONITORING" if count else "IDLE"
    task = f"Normalized {count} incoming event{'s' if count != 1 else ''}"
    return status, task


def _activity_status() -> tuple[str, str]:
    count = len(get_activity_observations())
    status = "WATCHING" if count else "IDLE"
    task = f"Watching {count} activity observation{'s' if count != 1 else ''}"
    return status, task


def _risk_status() -> tuple[str, str]:
    runs = get_orchestration_runs()
    if not runs:
        return "READY", "Awaiting the next risk assessment"

    latest = runs[0].risk_assessment
    task = f"{latest.event.action.value} on {latest.event.resource}"
    return "ANALYZING", task


def _enforcer_status() -> tuple[str, str]:
    events = get_enforcement_events()
    if not events:
        return "READY", "No enforcement decisions yet"

    latest = events[0]
    task = f"{latest['final_decision']} for {latest['user']}"
    return "ENFORCING", task


def _productivity_status() -> tuple[str, str]:
    detections = get_productivity_detections()
    if not detections:
        return "IDLE", "No productivity detections generated"

    latest = detections[0]
    task = f"{latest.user}: {latest.decision.value}"
    return "SCANNING", task


def _orchestrator_status() -> tuple[str, str]:
    runs = get_orchestration_runs()
    count = len(runs)
    status = "INVESTIGATING" if count else "READY"
    task = f"Completed {count} full pipeline run{'s' if count != 1 else ''}"
    return status, task


def _audit_status() -> tuple[str, str]:
    audit_entries = get_audit_log()
    count = len(audit_entries)
    status = "MONITORING" if count else "IDLE"
    task = f"Tracking {count} audit record{'s' if count != 1 else ''}"
    return status, task


def _core_status() -> tuple[str, str]:
    active_agents = sum(
        1
        for definition in AGENT_DEFINITIONS
        if definition["id"] != "CORE" and definition["status_builder"]()[0] != "IDLE"
    )
    return "CORE", f"Coordinating {active_agents} active backend agents"


AGENT_DEFINITIONS: list[AgentDefinition] = [
    {
        "id": "Agent-01",
        "role": "Collector",
        "module": "collector",
        "endpoint": "/collector/events",
        "color": "var(--alert-red)",
        "accuracy": 96.2,
        "test_label": "Run Collector",
        "status_builder": _collector_status,
    },
    {
        "id": "Agent-02",
        "role": "Activity Monitor",
        "module": "activity",
        "endpoint": "/activity/events",
        "color": "var(--glow-blue)",
        "accuracy": 98.4,
        "test_label": "Run Activity",
        "status_builder": _activity_status,
    },
    {
        "id": "Agent-03",
        "role": "Risk Analyst",
        "module": "risk_analyst",
        "endpoint": "/evaluate",
        "color": "var(--glow-violet)",
        "accuracy": 94.7,
        "test_label": "Run Risk",
        "status_builder": _risk_status,
    },
    {
        "id": "Agent-04",
        "role": "Enforcer",
        "module": "enforcer",
        "endpoint": "/enforcer/decisions",
        "color": "var(--glow-cyan)",
        "accuracy": 97.9,
        "test_label": "Run Enforcer",
        "status_builder": _enforcer_status,
    },
    {
        "id": "Agent-05",
        "role": "Productivity Detector",
        "module": "productivity",
        "endpoint": "/productivity/events",
        "color": "var(--bb-idle)",
        "accuracy": 91.5,
        "test_label": "Run Productivity",
        "status_builder": _productivity_status,
    },
    {
        "id": "Agent-06",
        "role": "Orchestrator",
        "module": "orchestrator",
        "endpoint": "/orchestrator/events",
        "color": "var(--alert-orange)",
        "accuracy": 95.8,
        "test_label": "Run Flow",
        "status_builder": _orchestrator_status,
    },
    {
        "id": "Agent-07",
        "role": "Audit Trail",
        "module": "audit",
        "endpoint": "/audit",
        "color": "var(--glow-purple)",
        "accuracy": 93.6,
        "test_label": "Refresh Audit",
        "status_builder": _audit_status,
    },
    {
        "id": "CORE",
        "role": "BlackBooks AI Core",
        "module": "core",
        "endpoint": "/agents/CORE/test",
        "color": "var(--glow-purple)",
        "accuracy": 99.1,
        "test_label": "Run Core",
        "status_builder": _core_status,
    },
]

_AGENT_BY_ID = {definition["id"]: definition for definition in AGENT_DEFINITIONS}


def get_agents_dashboard() -> dict[str, Any]:
    agents = [_serialize_agent(definition) for definition in AGENT_DEFINITIONS]
    stats = get_stats()

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_agents": len(agents),
            "active_agents": sum(1 for agent in agents if agent["status"] not in {"IDLE", "READY"}),
            "tests_available": len(agents),
            "processed_events": len(get_collected_events()),
            "orchestration_runs": len(get_orchestration_runs()),
            "escalated_cases": stats["escalated"],
            "model_health": round(sum(agent["accuracy_value"] for agent in agents) / len(agents), 1),
        },
        "agents": agents,
    }


async def run_agent_test(agent_id: str, test_input: AgentTestInput | None = None) -> dict[str, Any]:
    definition = _AGENT_BY_ID.get(agent_id)
    if not definition:
        raise KeyError(agent_id)

    if agent_id == "Agent-01":
        payload = _collector_payload(test_input)
        result = collect_event(payload)
        return _test_response(
            definition,
            f"Collector normalized {result.normalized_event.action.value} for {result.normalized_event.user}.",
            result.model_dump(),
        )

    if agent_id == "Agent-02":
        event = _activity_event(test_input)
        result = monitor_event(event, source=_source(test_input))
        return _test_response(
            definition,
            f"Activity Monitor recorded {result.action} on {result.system}.",
            result.model_dump(),
        )

    if agent_id == "Agent-03":
        event = _risk_event(test_input)
        result = await _safe_assess_risk(event)
        return _test_response(
            definition,
            f"Risk Analyst scored {result.risk_score:.2f} and decided {result.decision.value}.",
            result.model_dump(),
        )

    if agent_id == "Agent-04":
        event = _enforcer_event(test_input)
        assessment = await _safe_assess_risk(event)
        result = enforce_assessment(assessment)
        return _test_response(
            definition,
            f"Enforcer produced {result.final_decision.value} for {result.event.user}.",
            result.model_dump(),
        )

    if agent_id == "Agent-05":
        event = _productivity_event(test_input)
        activity = monitor_event(event, source=_source(test_input))
        result = detect_productivity(event, activity)
        return _test_response(
            definition,
            f"Productivity Detector classified {result.user} as {result.decision.value}.",
            result.model_dump(),
        )

    if agent_id == "Agent-06":
        payload = _orchestrator_payload(test_input)
        result = await orchestrate_event(payload)
        return _test_response(
            definition,
            f"Orchestrator completed run {result.id} for {result.collected_event.normalized_event.user}.",
            result.model_dump(),
        )

    if agent_id == "Agent-07":
        event = _audit_event(test_input)
        assessment = await _safe_assess_risk(event)
        enforcement = enforce_assessment(assessment)
        return _test_response(
            definition,
            f"Audit Trail appended {enforcement.enforcement_event['id']} and now tracks {len(get_audit_log())} entries.",
            {
                "latest_entry": get_audit_log()[0],
                "stats": get_stats(),
            },
        )

    payload = _core_payload(test_input)
    result = await orchestrate_event(payload)
    return _test_response(
        definition,
        f"Core coordinated run {result.id} across collector, activity, productivity, risk, and enforcement.",
        result.model_dump(),
    )


def _serialize_agent(definition: AgentDefinition) -> dict[str, Any]:
    status, task = definition["status_builder"]()
    return {
        "id": definition["id"],
        "role": definition["role"],
        "module": definition["module"],
        "endpoint": definition["endpoint"],
        "status": status,
        "task": task,
        "color": definition["color"],
        "accuracy": f"{definition['accuracy']:.1f}%",
        "accuracy_value": definition["accuracy"],
        "test_label": definition["test_label"],
    }


def _test_response(
    definition: AgentDefinition,
    message: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "agent_id": definition["id"],
        "agent_role": definition["role"],
        "tested_at": datetime.utcnow().isoformat(),
        "message": message,
        "result": result,
        "dashboard": get_agents_dashboard(),
    }


async def _safe_assess_risk(event: EnterpriseEvent):
    try:
        return await assess_risk(event)
    except ValueError as exc:
        if str(exc) == "GEMINI_API_KEY not set":
            return assess_risk_locally(event)
        raise


def _source(test_input: AgentTestInput | None) -> str:
    return test_input.source if test_input and test_input.source else "agent-test"


def _normalize_action(action: str | None, fallback: EventType) -> EventType:
    if not action:
        return fallback

    candidate = action.strip().replace("-", "_").replace(" ", "_").upper()
    alias_map = {
        "EXPORT_DATA": EventType.DATA_EXPORT,
        "DOWNLOAD_DATA": EventType.DATA_EXPORT,
        "PERMISSIONS_CHANGE": EventType.PERMISSION_CHANGE,
        "CHANGE_PERMISSION": EventType.PERMISSION_CHANGE,
        "AFTER_HOURS_ACCESS": EventType.ACCESS_AFTER_HOURS,
        "DELETE_MASS": EventType.MASS_DELETE,
        "ADMIN_ESCALATION": EventType.PRIVILEGE_ESCALATION,
        "API_CALL_UNUSUAL": EventType.UNUSUAL_API_CALL,
    }
    if candidate in alias_map:
        return alias_map[candidate]
    return EventType(candidate)


def _merge_event(
    test_input: AgentTestInput | None,
    *,
    user: str,
    role: str,
    department: str,
    action: EventType,
    resource: str,
    context: str,
) -> EnterpriseEvent:
    return EnterpriseEvent(
        user=test_input.user if test_input and test_input.user else user,
        role=test_input.role if test_input and test_input.role else role,
        department=test_input.department if test_input and test_input.department else department,
        action=_normalize_action(test_input.action if test_input else None, action),
        resource=test_input.resource if test_input and test_input.resource else resource,
        context=test_input.context if test_input and test_input.context else context,
        timestamp=test_input.timestamp if test_input and test_input.timestamp else datetime.utcnow().isoformat(),
    )


def _collector_payload(test_input: AgentTestInput | None = None) -> CollectorEventInput:
    event = _merge_event(
        test_input,
        user="u-collector-01",
        role="Analyst",
        department="Finance",
        action=EventType.DATA_EXPORT,
        resource="finance/quarterly-report.csv",
        context="Collector smoke test from dashboard",
    )
    return CollectorEventInput(
        source=_source(test_input),
        payload={
            "employee_id": event.user,
            "position": event.role,
            "area": event.department,
            "event_type": event.action.value,
            "target": event.resource,
            "details": event.context,
            "timestamp": event.timestamp,
        },
    )


def _activity_event(test_input: AgentTestInput | None = None) -> EnterpriseEvent:
    return _merge_event(
        test_input,
        user="u-activity-02",
        role="SOC Analyst",
        department="Security",
        action=EventType.ACCESS_AFTER_HOURS,
        resource="vpn://corp-gateway",
        context="Observed after-hours login from the dashboard agent test",
    )


def _risk_event(test_input: AgentTestInput | None = None) -> EnterpriseEvent:
    return _merge_event(
        test_input,
        user="u-risk-03",
        role="Finance Manager",
        department="Finance",
        action=EventType.DATA_EXPORT,
        resource="customer-records/export.csv",
        context="Unusual large export requested after hours",
    )


def _enforcer_event(test_input: AgentTestInput | None = None) -> EnterpriseEvent:
    return _merge_event(
        test_input,
        user="u-enforcer-04",
        role="DB Admin",
        department="Infrastructure",
        action=EventType.PRIVILEGE_ESCALATION,
        resource="customer-db/admin",
        context="Administrative escalation requested outside approved window",
    )


def _productivity_event(test_input: AgentTestInput | None = None) -> EnterpriseEvent:
    return _merge_event(
        test_input,
        user="u-productivity-05",
        role="Support Specialist",
        department="Support",
        action=EventType.UNUSUAL_API_CALL,
        resource="https://youtube.com/watch?v=debug-session",
        context="Repeated non-work browsing during shift",
    )


def _orchestrator_payload(test_input: AgentTestInput | None = None) -> CollectorEventInput:
    event = _merge_event(
        test_input,
        user="u-orchestrator-06",
        role="Analyst",
        department="Finance",
        action=EventType.MASS_DELETE,
        resource="finance/customer-ledger",
        context="Potential destructive workflow triggered by simulation",
    )
    return CollectorEventInput(
        source=_source(test_input),
        payload={
            "employee_id": event.user,
            "position": event.role,
            "area": event.department,
            "event_type": event.action.value,
            "target": event.resource,
            "details": event.context,
            "timestamp": event.timestamp,
        },
    )


def _audit_event(test_input: AgentTestInput | None = None) -> EnterpriseEvent:
    return _merge_event(
        test_input,
        user="u-audit-07",
        role="Compliance Lead",
        department="Compliance",
        action=EventType.PERMISSION_CHANGE,
        resource="customer-vault/policies",
        context="Sensitive policy change queued for review",
    )


def _core_payload(test_input: AgentTestInput | None = None) -> CollectorEventInput:
    event = _merge_event(
        test_input,
        user="u-core-99",
        role="Security Engineer",
        department="Platform",
        action=EventType.UNUSUAL_API_CALL,
        resource="api://payments/internal-transfer",
        context="Core mesh validation run initiated from dashboard",
    )
    return CollectorEventInput(
        source=_source(test_input),
        payload={
            "employee_id": event.user,
            "position": event.role,
            "area": event.department,
            "event_type": event.action.value,
            "target": event.resource,
            "details": event.context,
            "timestamp": event.timestamp,
        },
    )
