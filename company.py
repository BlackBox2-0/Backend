from __future__ import annotations

from datetime import datetime

from database import dump_json, fetch_all, insert_record, next_id, update_record
from models import CompanyUser, IncidentActionInput, IncidentActionResult, IncidentDecisionInput


COMPANY_USERS: list[CompanyUser] = [
    CompanyUser(
        id="usr-admin-001",
        username="daniela.blackwood",
        name="Daniela Blackwood",
        email="daniela.blackwood@blackbooks.ai",
        title="CEO / Company Admin",
        department="Executive",
        level="ADMIN",
    ),
    CompanyUser(
        id="usr-dir-001",
        username="marcos.ortega",
        name="Marcos Ortega",
        email="marcos.ortega@blackbooks.ai",
        title="Chief Operations Officer",
        department="Operations",
        level="DIRECTOR",
        manager_id="usr-admin-001",
    ),
    CompanyUser(
        id="usr-dir-002",
        username="valeria.soto",
        name="Valeria Soto",
        email="valeria.soto@blackbooks.ai",
        title="Chief Financial Officer",
        department="Finance",
        level="DIRECTOR",
        manager_id="usr-admin-001",
    ),
    CompanyUser(
        id="usr-dir-003",
        username="nicolas.ibarra",
        name="Nicolas Ibarra",
        email="nicolas.ibarra@blackbooks.ai",
        title="Head of Security",
        department="Security",
        level="DIRECTOR",
        manager_id="usr-admin-001",
    ),
    CompanyUser(
        id="usr-mgr-001",
        username="alejandro.reyes",
        name="Alejandro Reyes",
        email="alejandro.reyes@blackbooks.ai",
        title="Security Analyst",
        department="Security",
        level="MANAGER",
        manager_id="usr-dir-003",
    ),
    CompanyUser(
        id="usr-mgr-002",
        username="julia.morales",
        name="Julia Morales",
        email="julia.morales@blackbooks.ai",
        title="Finance Manager",
        department="Finance",
        level="MANAGER",
        manager_id="usr-dir-002",
    ),
    CompanyUser(
        id="usr-mgr-003",
        username="rafael.castro",
        name="Rafael Castro",
        email="rafael.castro@blackbooks.ai",
        title="Operations Manager",
        department="Operations",
        level="MANAGER",
        manager_id="usr-dir-001",
    ),
    CompanyUser(
        id="usr-mgr-004",
        username="camila.vera",
        name="Camila Vera",
        email="camila.vera@blackbooks.ai",
        title="Infrastructure Manager",
        department="Infrastructure",
        level="MANAGER",
        manager_id="usr-dir-001",
    ),
    CompanyUser(
        id="usr-emp-001",
        username="carlos.mendez",
        name="Carlos Mendez",
        email="carlos.mendez@blackbooks.ai",
        title="Finance Analyst",
        department="Finance",
        level="EMPLOYEE",
        manager_id="usr-mgr-002",
    ),
    CompanyUser(
        id="usr-emp-002",
        username="sofia.ramirez",
        name="Sofia Ramirez",
        email="sofia.ramirez@blackbooks.ai",
        title="Customer Success Manager",
        department="Operations",
        level="EMPLOYEE",
        manager_id="usr-mgr-003",
    ),
    CompanyUser(
        id="usr-emp-003",
        username="juan.perez",
        name="Juan Perez",
        email="juan.perez@blackbooks.ai",
        title="Support Engineer",
        department="Infrastructure",
        level="EMPLOYEE",
        manager_id="usr-mgr-004",
    ),
    CompanyUser(
        id="usr-emp-004",
        username="ana.torres",
        name="Ana Torres",
        email="ana.torres@blackbooks.ai",
        title="Payroll Specialist",
        department="Finance",
        level="EMPLOYEE",
        manager_id="usr-mgr-002",
    ),
    CompanyUser(
        id="usr-emp-005",
        username="luis.garcia",
        name="Luis Garcia",
        email="luis.garcia@blackbooks.ai",
        title="Platform Engineer",
        department="Platform",
        level="EMPLOYEE",
        manager_id="usr-mgr-004",
    ),
    CompanyUser(
        id="usr-emp-006",
        username="maria.lopez",
        name="Maria Lopez",
        email="maria.lopez@blackbooks.ai",
        title="Accounts Payable",
        department="Finance",
        level="EMPLOYEE",
        manager_id="usr-mgr-002",
    ),
    CompanyUser(
        id="usr-emp-007",
        username="empleado1",
        name="Empleado Uno",
        email="empleado1@blackbooks.ai",
        title="Analyst",
        department="Finance",
        level="EMPLOYEE",
        manager_id="usr-mgr-002",
    ),
]

_USER_BY_ID = {user.id: user for user in COMPANY_USERS}


def get_company_users() -> list[CompanyUser]:
    return COMPANY_USERS


def investigate_incident(payload: IncidentActionInput) -> IncidentActionResult:
    assigned_to = get_security_operator()
    chain = _reporting_chain(payload.affected_user, payload.department)
    result = IncidentActionResult(
        id=next_id("incident_actions", "case"),
        action_type="INVESTIGATE",
        status="ASSIGNED",
        incident_title=payload.incident_title,
        incident_type=payload.incident_type,
        affected_user=payload.affected_user,
        department=payload.department,
        requested_by=payload.requested_by,
        assigned_to=assigned_to,
        escalation_chain=chain[:1],
        notes=f"Assigned to {assigned_to.name} for triage. Department contact: {chain[0].name if chain else 'N/A'}.",
        created_at=datetime.utcnow().isoformat(),
    )
    _persist_incident_action(result, payload.resource)
    return result


def escalate_incident(payload: IncidentActionInput) -> IncidentActionResult:
    chain = _reporting_chain(payload.affected_user, payload.department)
    result = IncidentActionResult(
        id=next_id("incident_actions", "case"),
        action_type="ESCALATE",
        status="PENDING_APPROVAL",
        incident_title=payload.incident_title,
        incident_type=payload.incident_type,
        affected_user=payload.affected_user,
        department=payload.department,
        requested_by=payload.requested_by,
        assigned_to=chain[0] if chain else get_company_admin(),
        escalation_chain=chain if chain else [get_company_admin()],
        notes=_build_escalation_note(payload, chain),
        created_at=datetime.utcnow().isoformat(),
    )
    _persist_incident_action(result, payload.resource)
    return result


def get_incident_actions() -> list[IncidentActionResult]:
    rows = fetch_all("incident_actions", "created_at DESC")
    return [IncidentActionResult.model_validate_json(row["payload_json"]) for row in rows]


def get_incident_summary() -> dict:
    actions = get_incident_actions()
    total = len(actions)
    approved = sum(1 for action in actions if action.status == "APPROVED")
    blocked = sum(1 for action in actions if action.status == "BLOCKED")
    pending = sum(1 for action in actions if action.status == "PENDING_APPROVAL")
    assigned = sum(1 for action in actions if action.status == "ASSIGNED")
    active = pending + assigned

    return {
        "total": total,
        "approved": approved,
        "blocked": blocked,
        "pending": pending,
        "assigned": assigned,
        "active": active,
        "approval_rate": round((approved / total) * 100, 1) if total else 0,
        "block_rate": round((blocked / total) * 100, 1) if total else 0,
    }


def approve_incident(case_id: str, payload: IncidentDecisionInput | None = None) -> IncidentActionResult:
    incident = _find_incident_action(case_id)
    approver = _resolve_approver(payload, incident)
    now = datetime.utcnow().isoformat()

    completed = [*incident.approvals_completed]
    if approver and not any(user.id == approver.id for user in completed):
        completed.append(approver)

    next_step = incident.current_step + 1
    if next_step >= len(incident.escalation_chain):
        updated = incident.model_copy(
            update={
                "status": "APPROVED",
                "current_step": len(incident.escalation_chain),
                "approvals_completed": completed,
                "assigned_to": None,
                "resolved_by": approver,
                "resolved_at": now,
                "resolution_note": payload.comment if payload and payload.comment else f"Approved by {approver.name if approver else 'approver'}.",
                "notes": f"Incident approved. Final approval by {approver.name if approver else 'approver'}.",
            }
        )
    else:
        next_approver = incident.escalation_chain[next_step]
        updated = incident.model_copy(
            update={
                "status": "PENDING_APPROVAL",
                "current_step": next_step,
                "approvals_completed": completed,
                "assigned_to": next_approver,
                "resolved_at": None,
                "resolution_note": payload.comment if payload and payload.comment else None,
                "notes": f"Approved by {approver.name if approver else 'approver'}. Routed to {next_approver.name}.",
            }
        )

    _persist_incident_action_update(updated)
    return updated


def reject_incident(case_id: str, payload: IncidentDecisionInput | None = None) -> IncidentActionResult:
    incident = _find_incident_action(case_id)
    approver = _resolve_approver(payload, incident)
    now = datetime.utcnow().isoformat()
    updated = incident.model_copy(
        update={
            "status": "BLOCKED",
            "assigned_to": None,
            "resolved_by": approver,
            "resolved_at": now,
            "resolution_note": payload.comment if payload and payload.comment else f"Blocked by {approver.name if approver else 'approver'}.",
            "notes": f"Incident blocked by {approver.name if approver else 'approver'}.",
        }
    )
    _persist_incident_action_update(updated)
    return updated


def get_security_operator() -> CompanyUser:
    return next(user for user in COMPANY_USERS if user.username == "alejandro.reyes")


def get_company_admin() -> CompanyUser:
    return next(user for user in COMPANY_USERS if user.level == "ADMIN")


def _persist_incident_action(result: IncidentActionResult, resource: str) -> None:
    insert_record(
        "incident_actions",
        {
            "id": result.id,
            "action_type": result.action_type,
            "status": result.status,
            "incident_title": result.incident_title,
            "incident_type": result.incident_type,
            "affected_user": result.affected_user,
            "department": result.department,
            "resource": resource,
            "requested_by": result.requested_by,
            "assigned_to_id": result.assigned_to.id if result.assigned_to else None,
            "created_at": result.created_at,
            "payload_json": result.model_dump_json(),
        },
    )


def _persist_incident_action_update(result: IncidentActionResult) -> None:
    rows = fetch_all("incident_actions", "created_at DESC")
    resource = next((row["resource"] for row in rows if row["id"] == result.id), "")
    update_record(
        "incident_actions",
        result.id,
        {
            "status": result.status,
            "assigned_to_id": result.assigned_to.id if result.assigned_to else None,
            "payload_json": result.model_dump_json(),
            "resource": resource,
        },
    )


def _reporting_chain(affected_user: str, department: str) -> list[CompanyUser]:
    employee = _find_user(affected_user)
    if employee:
        return _chain_from_manager(employee.manager_id)

    manager = next((user for user in COMPANY_USERS if user.department == department and user.level == "MANAGER"), None)
    if manager:
        return [manager, *_chain_from_manager(manager.manager_id)]

    director = next((user for user in COMPANY_USERS if user.department == department and user.level == "DIRECTOR"), None)
    if director:
        return [director, get_company_admin()]

    return [get_company_admin()]


def _chain_from_manager(manager_id: str | None) -> list[CompanyUser]:
    chain: list[CompanyUser] = []
    current = _USER_BY_ID.get(manager_id) if manager_id else None
    while current:
        chain.append(current)
        current = _USER_BY_ID.get(current.manager_id) if current.manager_id else None
    return chain


def _find_user(value: str) -> CompanyUser | None:
    candidate = value.strip().lower()
    return next(
        (
            user
            for user in COMPANY_USERS
            if user.username.lower() == candidate or user.name.lower() == candidate or user.id.lower() == candidate
        ),
        None,
    )


def _build_escalation_note(payload: IncidentActionInput, chain: list[CompanyUser]) -> str:
    if not chain:
        return f"Escalated directly to company admin for incident {payload.incident_title}."
    names = " -> ".join(user.name for user in chain)
    return f"Escalation chain for {payload.affected_user}: {names}."


def _find_incident_action(case_id: str) -> IncidentActionResult:
    incident = next((item for item in get_incident_actions() if item.id == case_id), None)
    if incident is None:
        raise ValueError(f"Incident action {case_id} not found")
    return incident


def _resolve_approver(payload: IncidentDecisionInput | None, incident: IncidentActionResult) -> CompanyUser | None:
    if payload and payload.approver_username:
        return _find_user(payload.approver_username)
    return incident.assigned_to
