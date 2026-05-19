from datetime import datetime
from urllib.parse import urlparse

from database import fetch_all, insert_record, next_id
from models import (
    ActivityObservation,
    ActivitySummary,
    EnterpriseEvent,
    ProductivityDecision,
    ProductivityDetection,
)

_productivity_detections: list[ProductivityDetection] = []

NON_WORK_KEYWORDS = {
    "facebook",
    "instagram",
    "netflix",
    "tiktok",
    "youtube",
    "spotify",
    "reddit",
    "gaming",
    "games",
}


def detect_productivity(
    event: EnterpriseEvent,
    activity: ActivityObservation,
    summary: ActivitySummary | None = None,
) -> ProductivityDetection:
    signals = _collect_signals(event, activity, summary)
    decision = _decision_from_signals(signals)
    score = _score_from_decision(decision)

    detection = ProductivityDetection(
        id=next_id("productivity_detections", "prd"),
        user=event.user,
        decision=decision,
        score=score,
        signals=signals,
        reasoning=_build_reasoning(decision, signals),
        observed_at=datetime.utcnow().isoformat(),
        event=event,
        summary=summary,
    )
    _productivity_detections.append(detection)
    insert_record(
        "productivity_detections",
        {
            "id": detection.id,
            "user": detection.user,
            "decision": detection.decision.value,
            "score": detection.score,
            "observed_at": detection.observed_at,
            "payload_json": detection.model_dump_json(),
        },
    )
    return detection


def detect_productivity_from_summary(summary: ActivitySummary) -> ProductivityDetection:
    signals = _collect_summary_signals(summary)
    decision = _decision_from_signals(signals)
    score = _score_from_decision(decision)

    detection = ProductivityDetection(
        id=next_id("productivity_detections", "prd"),
        user=summary.user,
        decision=decision,
        score=score,
        signals=signals,
        reasoning=_build_reasoning(decision, signals),
        observed_at=datetime.utcnow().isoformat(),
        summary=summary,
    )
    _productivity_detections.append(detection)
    insert_record(
        "productivity_detections",
        {
            "id": detection.id,
            "user": detection.user,
            "decision": detection.decision.value,
            "score": detection.score,
            "observed_at": detection.observed_at,
            "payload_json": detection.model_dump_json(),
        },
    )
    return detection


def get_productivity_detections(user: str | None = None) -> list[ProductivityDetection]:
    rows = fetch_all("productivity_detections", "observed_at DESC")
    detections = (
        [ProductivityDetection.model_validate_json(row["payload_json"]) for row in rows]
        if rows
        else list(reversed(_productivity_detections))
    )
    if user:
        detections = [item for item in detections if item.user == user]
    return detections


def _collect_signals(
    event: EnterpriseEvent,
    activity: ActivityObservation,
    summary: ActivitySummary | None,
) -> list[str]:
    signals = []

    if _is_non_work_resource(event.resource) or _is_non_work_resource(activity.system):
        signals.append("non_work_resource")

    if summary:
        signals.extend(_collect_summary_signals(summary))

    if not signals:
        signals.append("productive_activity")

    return sorted(set(signals))


def _collect_summary_signals(summary: ActivitySummary) -> list[str]:
    signals = []

    if summary.productivity_signal == "low_activity":
        signals.append("low_activity")
    if summary.events_per_hour < 1:
        signals.append("inactive_pattern")
    if summary.total_events <= 1:
        signals.append("insufficient_activity")
    if any(_is_non_work_resource(system) for system in summary.systems_used):
        signals.append("non_work_resource")

    if not signals:
        signals.append("productive_activity")

    return signals


def _decision_from_signals(signals: list[str]) -> ProductivityDecision:
    if "inactive_pattern" in signals:
        return ProductivityDecision.INACTIVE
    if "non_work_resource" in signals:
        return ProductivityDecision.NON_WORK_RELATED
    if "low_activity" in signals or "insufficient_activity" in signals:
        return ProductivityDecision.LOW_PRODUCTIVITY
    return ProductivityDecision.PRODUCTIVE


def _score_from_decision(decision: ProductivityDecision) -> float:
    scores = {
        ProductivityDecision.PRODUCTIVE: 0.95,
        ProductivityDecision.LOW_PRODUCTIVITY: 0.45,
        ProductivityDecision.INACTIVE: 0.2,
        ProductivityDecision.NON_WORK_RELATED: 0.25,
    }
    return scores[decision]


def _build_reasoning(
    decision: ProductivityDecision,
    signals: list[str],
) -> str:
    if decision == ProductivityDecision.PRODUCTIVE:
        return "Activity matches expected work patterns."
    if decision == ProductivityDecision.INACTIVE:
        return "Activity frequency is below the minimum expected threshold."
    if decision == ProductivityDecision.NON_WORK_RELATED:
        return "A resource or system appears unrelated to work activity."
    return "Activity exists, but the observed frequency is low."


def _is_non_work_resource(resource: str) -> bool:
    parsed = urlparse(resource)
    candidate = (parsed.netloc or resource).lower()
    return any(keyword in candidate for keyword in NON_WORK_KEYWORDS)
