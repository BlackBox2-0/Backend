from pydantic import BaseModel
from typing import Optional
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


class EnterpriseEvent(BaseModel):
    user: str
    role: str
    department: str
    action: EventType
    resource: str
    context: Optional[str] = None
    timestamp: Optional[str] = None


class RiskAssessment(BaseModel):
    event: EnterpriseEvent
    risk_score: float
    decision: RiskDecision
    reasoning: str
    flags: list[str]
    assessed_at: str