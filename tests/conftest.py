import pytest

import activity_monitor
import audit
import collector
import database
import enforcer
import orchestrator
import productivity_detector
from models import EnterpriseEvent, EventType


@pytest.fixture(autouse=True)
def clear_in_memory_state():
    collector._collected_events.clear()
    activity_monitor._activity_observations.clear()
    productivity_detector._productivity_detections.clear()
    enforcer._enforcement_events.clear()
    audit._audit_log.clear()
    orchestrator._orchestration_runs.clear()
    database.clear_all_tables()
    yield


@pytest.fixture
def enterprise_event():
    return EnterpriseEvent(
        user="u-100",
        role="Analyst",
        department="Finance",
        action=EventType.DATA_EXPORT,
        resource="finance/report.csv",
        context="Export requested from dashboard",
        timestamp="2026-05-13T10:00:00",
    )
