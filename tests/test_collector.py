import pytest

from collector import collect_event, get_collected_events
from models import CollectorEventInput, EventType


def test_collect_event_normalizes_payload_aliases():
    incoming = CollectorEventInput(
        source="simulation",
        payload={
            "employee_id": "u-100",
            "position": "Analyst",
            "area": "Finance",
            "event_type": "export_data",
            "target": "quarterly-report.csv",
            "details": "Export requested from simulator",
        },
    )

    result = collect_event(incoming)

    assert result.id == "col-1"
    assert result.source == "simulation"
    assert result.normalized_event.user == "u-100"
    assert result.normalized_event.role == "Analyst"
    assert result.normalized_event.department == "Finance"
    assert result.normalized_event.action == EventType.DATA_EXPORT
    assert result.normalized_event.resource == "quarterly-report.csv"
    assert result.normalized_event.context == "Export requested from simulator"
    assert get_collected_events() == [result]


def test_collect_event_rejects_missing_required_fields():
    incoming = CollectorEventInput(
        payload={
            "employee_id": "u-100",
            "position": "Analyst",
        },
    )

    with pytest.raises(ValueError, match="Missing required event fields"):
        collect_event(incoming)
