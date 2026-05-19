from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Literal, Optional
from enum import Enum
from datetime import datetime


class EventType(str, Enum):
    FINANCIAL_CHANGE = "FINANCIAL_CHANGE"
    PERMISSION_CHANGE = "PERMISSION_CHANGE"
    DATA_EXPORT = "DATA_EXPORT"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    ACCESS_AFTER_HOURS = "ACCESS_AFTER_HOURS"
    MASS_DELETE = "MASS_DELETE"
    PRIVILEGE_ESCALATION = "PRIVILEGE_ESCALATION"
    UNUSUAL_API_CALL = "UNUSUAL_API_CALL"


class RiskDecision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"


class ProductivityDecision(str, Enum):
    PRODUCTIVE = "PRODUCTIVE"
    LOW_PRODUCTIVITY = "LOW_PRODUCTIVITY"
    INACTIVE = "INACTIVE"
    NON_WORK_RELATED = "NON_WORK_RELATED"


class EnterpriseEvent(BaseModel):
    user: str
    role: str
    department: str
    action: EventType
    resource: str
    context: Optional[str] = None
    timestamp: Optional[str] = None


class CollectorEventInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    source: str = "api"
    payload: Optional[dict[str, Any]] = None


class AgentTestInput(BaseModel):
    source: Optional[str] = "dashboard"
    user: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    action: Optional[str] = None
    resource: Optional[str] = None
    context: Optional[str] = None
    timestamp: Optional[str] = None


class CollectedEvent(BaseModel):
    id: str
    source: str
    normalized_event: EnterpriseEvent
    raw_event: dict[str, Any] = Field(default_factory=dict)
    received_at: str


class ActivityObservation(BaseModel):
    id: str
    event_id: str
    source: str
    user: str
    role: str
    department: str
    action: str
    resource: str
    system: str
    event_timestamp: str
    observed_at: str


class ActivitySummary(BaseModel):
    user: str
    role: str
    department: str
    total_events: int
    resources_accessed: list[str]
    systems_used: list[str]
    actions_by_type: dict[str, int]
    first_seen: str
    last_seen: str
    events_per_hour: float
    frequency_label: str
    productivity_signal: str


class ProductivityDetection(BaseModel):
    id: str
    user: str
    decision: ProductivityDecision
    score: float
    signals: list[str]
    reasoning: str
    observed_at: str
    event: EnterpriseEvent | None = None
    summary: ActivitySummary | None = None


class PolicyDecision(BaseModel):
    model_recommendation: RiskDecision
    policy_rule_matched: Optional[str]
    final_decision: RiskDecision
    final_decision_source: Literal["model", "policy", "human"]
    policy_version: str


class RiskAssessment(BaseModel):
    event: EnterpriseEvent
    risk_score: float
    decision: RiskDecision
    reasoning: str
    flags: list[str]
    assessed_at: str
    model_recommendation: RiskDecision | None = None
    policy_decision: PolicyDecision | None = None
    executive_summary: str | None = None


class EnforcementResult(BaseModel):
    event: EnterpriseEvent
    risk_score: float
    analyst_decision: RiskDecision
    final_decision: RiskDecision
    requires_human_approval: bool
    reasoning: str
    flags: list[str]
    enforcement_event: dict[str, Any]
    enforced_at: str
    policy_decision: PolicyDecision | None = None
    executive_summary: str | None = None


class OrchestrationResult(BaseModel):
    id: str
    source: str
    collected_event: CollectedEvent
    activity: ActivityObservation
    productivity: ProductivityDetection
    risk_assessment: RiskAssessment
    enforcement: EnforcementResult
    completed_at: str


class CompanyUser(BaseModel):
    id: str
    username: str
    name: str
    email: str
    title: str
    department: str
    level: str
    manager_id: str | None = None


class IncidentActionInput(BaseModel):
    incident_title: str
    incident_type: str
    affected_user: str
    department: str
    resource: str
    severity: str | None = None
    requested_by: str = "Alejandro Reyes"


class IncidentActionResult(BaseModel):
    id: str
    action_type: str
    status: str
    incident_title: str
    incident_type: str
    affected_user: str
    department: str
    requested_by: str
    assigned_to: CompanyUser | None = None
    escalation_chain: list[CompanyUser] = Field(default_factory=list)
    current_step: int = 0
    approvals_completed: list[CompanyUser] = Field(default_factory=list)
    resolved_by: CompanyUser | None = None
    resolved_at: str | None = None
    resolution_note: str | None = None
    notes: str
    created_at: str


class IncidentDecisionInput(BaseModel):
    approver_username: str | None = None
    comment: str | None = None
