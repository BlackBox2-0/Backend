from activity_monitor import (
    get_activity_observations,
    get_activity_summary,
    monitor_event,
)
from models import EnterpriseEvent, EventType


def test_monitor_event_builds_observation_with_system(enterprise_event):
    result = monitor_event(enterprise_event, source="unit-test")

    assert result.id == "act-1"
    assert result.source == "unit-test"
    assert result.user == "u-100"
    assert result.action == "DATA_EXPORT"
    assert result.system == "finance"
    assert get_activity_observations() == [result]


def test_activity_summary_groups_events_by_user():
    first = EnterpriseEvent(
        user="u-100",
        role="Analyst",
        department="Finance",
        action=EventType.DATA_EXPORT,
        resource="https://erp.company.local/report",
        timestamp="2026-05-13T10:00:00",
    )
    second = EnterpriseEvent(
        user="u-100",
        role="Analyst",
        department="Finance",
        action=EventType.PERMISSION_CHANGE,
        resource="admin:permissions",
        timestamp="2026-05-13T10:30:00",
    )

    monitor_event(first)
    monitor_event(second)

    summary = get_activity_summary("u-100")[0]

    assert summary.total_events == 2
    assert summary.resources_accessed == [
        "admin:permissions",
        "https://erp.company.local/report",
    ]
    assert summary.systems_used == ["admin", "erp.company.local"]
    assert summary.actions_by_type == {
        "DATA_EXPORT": 1,
        "PERMISSION_CHANGE": 1,
    }
    assert summary.productivity_signal == "active_workflow"
