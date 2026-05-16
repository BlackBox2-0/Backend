from collections import Counter
from datetime import datetime
from urllib.parse import urlparse

from database import fetch_all, insert_record, next_id
from models import ActivityObservation, ActivitySummary, CollectedEvent, EnterpriseEvent

_activity_observations: list[ActivityObservation] = []


def monitor_collected_event(collected_event: CollectedEvent) -> ActivityObservation:
    event = collected_event.normalized_event
    observation = _build_observation(
        event=event,
        event_id=collected_event.id,
        source=collected_event.source,
    )
    _activity_observations.append(observation)
    return observation


def monitor_event(event: EnterpriseEvent, source: str = "api") -> ActivityObservation:
    observation = _build_observation(
        event=event,
        event_id=f"direct-{len(_activity_observations) + 1}",
        source=source,
    )
    _activity_observations.append(observation)
    return observation


def get_activity_observations() -> list[ActivityObservation]:
    rows = fetch_all("activity_observations", "observed_at DESC")
    if rows:
        return [ActivityObservation.model_validate_json(row["payload_json"]) for row in rows]
    return list(reversed(_activity_observations))


def get_activity_summary(user: str | None = None) -> list[ActivitySummary]:
    observations = get_activity_observations()
    if user:
        observations = [obs for obs in observations if obs.user == user]

    users = sorted({obs.user for obs in observations})
    return [_summarize_user(user_id, observations) for user_id in users]


def _build_observation(
    event: EnterpriseEvent,
    event_id: str,
    source: str,
) -> ActivityObservation:
    timestamp = event.timestamp or datetime.utcnow().isoformat()
    observation = ActivityObservation(
        id=next_id("activity_observations", "act"),
        event_id=event_id,
        source=source,
        user=event.user,
        role=event.role,
        department=event.department,
        action=event.action.value,
        resource=event.resource,
        system=_extract_system(event.resource),
        event_timestamp=timestamp,
        observed_at=datetime.utcnow().isoformat(),
    )
    insert_record(
        "activity_observations",
        {
            "id": observation.id,
            "event_id": observation.event_id,
            "source": observation.source,
            "user": observation.user,
            "role": observation.role,
            "department": observation.department,
            "action": observation.action,
            "resource": observation.resource,
            "system": observation.system,
            "event_timestamp": observation.event_timestamp,
            "observed_at": observation.observed_at,
            "payload_json": observation.model_dump_json(),
        },
    )
    return observation


def _summarize_user(
    user: str,
    observations: list[ActivityObservation],
) -> ActivitySummary:
    user_observations = [obs for obs in observations if obs.user == user]
    sorted_observations = sorted(user_observations, key=lambda obs: obs.event_timestamp)
    first = sorted_observations[0]
    last = sorted_observations[-1]
    actions = Counter(obs.action for obs in user_observations)
    events_per_hour = _calculate_events_per_hour(sorted_observations)

    return ActivitySummary(
        user=user,
        role=last.role,
        department=last.department,
        total_events=len(user_observations),
        resources_accessed=sorted({obs.resource for obs in user_observations}),
        systems_used=sorted({obs.system for obs in user_observations}),
        actions_by_type=dict(actions),
        first_seen=first.event_timestamp,
        last_seen=last.event_timestamp,
        events_per_hour=events_per_hour,
        frequency_label=_frequency_label(events_per_hour),
        productivity_signal=_productivity_signal(events_per_hour, user_observations),
    )


def _extract_system(resource: str) -> str:
    parsed = urlparse(resource)
    if parsed.netloc:
        return parsed.netloc

    if "/" in resource:
        return resource.split("/", 1)[0]

    if ":" in resource:
        return resource.split(":", 1)[0]

    return "local-resource"


def _calculate_events_per_hour(observations: list[ActivityObservation]) -> float:
    if len(observations) <= 1:
        return float(len(observations))

    start = _parse_datetime(observations[0].event_timestamp)
    end = _parse_datetime(observations[-1].event_timestamp)
    elapsed_hours = max((end - start).total_seconds() / 3600, 1)
    return round(len(observations) / elapsed_hours, 2)


def _parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.utcnow()


def _frequency_label(events_per_hour: float) -> str:
    if events_per_hour >= 12:
        return "high"
    if events_per_hour >= 3:
        return "normal"
    return "low"


def _productivity_signal(
    events_per_hour: float,
    observations: list[ActivityObservation],
) -> str:
    unique_resources = {obs.resource for obs in observations}
    unique_systems = {obs.system for obs in observations}

    if events_per_hour < 1:
        return "low_activity"
    if len(unique_resources) >= 3 or len(unique_systems) >= 2:
        return "active_workflow"
    return "focused_activity"
