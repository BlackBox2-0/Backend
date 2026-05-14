from models import ActivityObservation, ActivitySummary, ProductivityDecision
from productivity_detector import (
    detect_productivity,
    detect_productivity_from_summary,
    get_productivity_detections,
)


def test_detect_productivity_flags_non_work_resource(enterprise_event):
    event = enterprise_event.model_copy(update={"resource": "https://youtube.com/watch"})
    activity = ActivityObservation(
        id="act-1",
        event_id="evt-1",
        source="unit-test",
        user=event.user,
        role=event.role,
        department=event.department,
        action=event.action.value,
        resource=event.resource,
        system="youtube.com",
        event_timestamp=event.timestamp,
        observed_at="2026-05-13T10:00:00",
    )

    result = detect_productivity(event, activity)

    assert result.decision == ProductivityDecision.NON_WORK_RELATED
    assert result.score == 0.25
    assert result.signals == ["non_work_resource"]
    assert get_productivity_detections() == [result]


def test_detect_productivity_from_summary_flags_inactive_pattern():
    summary = ActivitySummary(
        user="u-100",
        role="Analyst",
        department="Finance",
        total_events=2,
        resources_accessed=["finance/report.csv"],
        systems_used=["finance"],
        actions_by_type={"DATA_EXPORT": 2},
        first_seen="2026-05-13T08:00:00",
        last_seen="2026-05-13T12:00:00",
        events_per_hour=0.5,
        frequency_label="low",
        productivity_signal="low_activity",
    )

    result = detect_productivity_from_summary(summary)

    assert result.decision == ProductivityDecision.INACTIVE
    assert "inactive_pattern" in result.signals
    assert result.summary == summary
