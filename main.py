from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from models import CollectorEventInput, EnterpriseEvent
from risk_analyst import assess_risk
from audit import get_audit_log, get_stats
from collector import collect_event, get_collected_events
from enforcer import enforce_assessment, get_enforcement_events
from orchestrator import get_orchestration_runs, orchestrate_event
from productivity_detector import (
    detect_productivity,
    detect_productivity_from_summary,
    get_productivity_detections,
)
from activity_monitor import (
    get_activity_observations,
    get_activity_summary,
    monitor_collected_event,
    monitor_event,
)

load_dotenv()

app = FastAPI(
    title="BLACKBOX API",
    description="Enterprise Decision Firewall powered by Gemini",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "blackbox-firewall"}


@app.post("/evaluate")
async def evaluate_event(event: EnterpriseEvent):
    try:
        assessment = await assess_risk(event)
        return enforce_assessment(assessment)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/enforcer/decisions")
async def enforce_event(event: EnterpriseEvent):
    try:
        assessment = await assess_risk(event)
        return enforce_assessment(assessment)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/enforcer/events")
def enforcement_events():
    return get_enforcement_events()


@app.post("/orchestrator/events")
async def orchestrator_event(event: CollectorEventInput):
    try:
        return await orchestrate_event(event)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orchestrator/runs")
def orchestrator_runs():
    return get_orchestration_runs()


@app.post("/collector/events")
def collector_event(event: CollectorEventInput):
    try:
        collected_event = collect_event(event)
        activity = monitor_collected_event(collected_event)
        return {"collected_event": collected_event, "activity": activity}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/collector/events")
def collector_events():
    return get_collected_events()


@app.post("/activity/events")
def activity_event(event: EnterpriseEvent):
    return monitor_event(event)


@app.get("/activity/events")
def activity_events():
    return get_activity_observations()


@app.get("/activity/summary")
def activity_summary():
    return get_activity_summary()


@app.get("/activity/users/{user}/summary")
def activity_user_summary(user: str):
    summary = get_activity_summary(user)
    if not summary:
        raise HTTPException(status_code=404, detail="No activity found for user")
    return summary[0]


@app.post("/productivity/events")
def productivity_event(event: EnterpriseEvent):
    activity = monitor_event(event, source="productivity")
    summaries = get_activity_summary(event.user)
    summary = summaries[0] if summaries else None
    return detect_productivity(event, activity, summary)


@app.post("/productivity/users/{user}/detect")
def productivity_user_detect(user: str):
    summaries = get_activity_summary(user)
    if not summaries:
        raise HTTPException(status_code=404, detail="No activity found for user")
    return detect_productivity_from_summary(summaries[0])


@app.get("/productivity/detections")
def productivity_detections():
    return get_productivity_detections()


@app.get("/productivity/users/{user}/detections")
def productivity_user_detections(user: str):
    return get_productivity_detections(user)


@app.get("/audit")
def audit_log():
    return get_audit_log()


@app.get("/stats")
def stats():
    return get_stats()
