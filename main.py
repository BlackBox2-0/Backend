from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from models import EnterpriseEvent
from risk_engine import assess_risk
from audit import log_assessment, get_audit_log, get_stats

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
        entry = log_assessment(assessment)
        return entry
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audit")
def audit_log():
    return get_audit_log()


@app.get("/stats")
def stats():
    return get_stats()