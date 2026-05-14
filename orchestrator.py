from datetime import datetime

from activity_monitor import get_activity_summary, monitor_collected_event
from collector import collect_event
from enforcer import enforce_assessment
from models import CollectorEventInput, OrchestrationResult
from productivity_detector import detect_productivity
from risk_analyst import assess_risk

_orchestration_runs: list[OrchestrationResult] = []


async def orchestrate_event(incoming: CollectorEventInput) -> OrchestrationResult:
    collected_event = collect_event(incoming)
    activity = monitor_collected_event(collected_event)
    event = collected_event.normalized_event

    user_summary = _latest_user_summary(event.user)
    productivity = detect_productivity(event, activity, user_summary)
    risk_assessment = await assess_risk(event)
    enforcement = enforce_assessment(risk_assessment)

    result = OrchestrationResult(
        id=f"orc-{len(_orchestration_runs) + 1}",
        source=incoming.source,
        collected_event=collected_event,
        activity=activity,
        productivity=productivity,
        risk_assessment=risk_assessment,
        enforcement=enforcement,
        completed_at=datetime.utcnow().isoformat(),
    )
    _orchestration_runs.append(result)
    return result


def get_orchestration_runs() -> list[OrchestrationResult]:
    return list(reversed(_orchestration_runs))


def _latest_user_summary(user: str):
    summaries = get_activity_summary(user)
    if not summaries:
        return None
    return summaries[0]
