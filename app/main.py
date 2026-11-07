import json
from pathlib import Path
from typing import Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator

from app.agent import run_agent
from app.drafts import approve_draft, create_draft
from app.trace import load_trace
from app.tools import get_weather
from app.data_access import load_shipments, compute_derived_fields

PROJECT_ROOT = Path(__file__).resolve().parent.parent

app = FastAPI(title="TrackMate API")

STATIC_INDEX = PROJECT_ROOT / "app" / "static" / "index.html"
POLICIES_DIR = PROJECT_ROOT / "data" / "policies"
TRACES_DIR = PROJECT_ROOT / "traces"


class InvestigateRequest(BaseModel):
    tracking_id: Optional[str] = None
    question: str = Field(..., min_length=1, max_length=500)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be empty or whitespace only")
        return v


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    """Serve the TrackMate frontend application."""
    if STATIC_INDEX.exists():
        content = STATIC_INDEX.read_text(encoding="utf-8")
        return HTMLResponse(content=content)
    return HTMLResponse("<h1>TrackMate API</h1><p>Frontend template not found.</p>")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/investigate")
def investigate(req: InvestigateRequest) -> dict[str, Any]:
    result = run_agent(req.tracking_id, req.question)

    draft_data = None
    if result.final.draft_message is not None:
        draft_record = create_draft(
            run_id=result.run_id,
            channel=result.final.draft_message.channel,
            subject=result.final.draft_message.subject,
            body=result.final.draft_message.body,
        )
        draft_data = {
            "draft_id": draft_record["draft_id"],
            "channel": draft_record["channel"],
            "subject": draft_record["subject"],
            "body": draft_record["body"],
            "status": draft_record["status"],
        }

    return {
        "run_id": result.run_id,
        "decision": result.final.decision,
        "reply_to_user": result.final.reply_to_user,
        "citations": [c.model_dump() for c in result.final.citations],
        "missing_info": result.final.missing_info,
        "draft": draft_data,
        "guardrail_flags": result.guardrail_flags,
    }


@app.get("/trace/{run_id}")
def get_trace(run_id: str) -> dict[str, Any]:
    trace_data = load_trace(run_id)
    if trace_data is None:
        raise HTTPException(status_code=404, detail="trace not found")
    return trace_data


@app.post("/approve/{draft_id}")
def approve(draft_id: str) -> dict[str, Any]:
    record = approve_draft(draft_id)
    if record is None:
        raise HTTPException(status_code=404, detail="draft not found")
    return record


# --- Frontend Helper Endpoints ---

@app.get("/api/shipments")
def get_shipments() -> dict[str, Any]:
    """Return all mock shipments enriched with derived calculation fields."""
    shipments_dict = load_shipments()
    enriched = []
    for s in shipments_dict.values():
        s_copy = dict(s)
        s_copy["derived"] = compute_derived_fields(s_copy)
        enriched.append(s_copy)
    return {"shipments": enriched}


@app.get("/api/weather")
def api_weather(
    city: str = Query(..., min_length=1),
    start_date: str = Query(..., min_length=10, max_length=10),
    end_date: str = Query(..., min_length=10, max_length=10),
) -> dict[str, Any]:
    """Test get_weather directly via API."""
    return get_weather(city=city, start_date=start_date, end_date=end_date)


@app.get("/api/policies")
def get_policies() -> dict[str, str]:
    """Return raw text of company policy documents."""
    policies = {}
    courier_file = POLICIES_DIR / "courier_delivery_policy.md"
    escalation_file = POLICIES_DIR / "escalation_policy.md"
    refund_file = POLICIES_DIR / "retailer_refund_policy.md"

    if courier_file.exists():
        policies["courier"] = courier_file.read_text(encoding="utf-8")
    if escalation_file.exists():
        policies["escalation"] = escalation_file.read_text(encoding="utf-8")
    if refund_file.exists():
        policies["refund"] = refund_file.read_text(encoding="utf-8")

    return policies


@app.get("/api/traces")
def list_traces() -> list[dict[str, Any]]:
    """Return summary list of all execution traces in traces/ directory."""
    if not TRACES_DIR.exists():
        return []

    trace_files = [f for f in TRACES_DIR.glob("*.json") if f.is_file()]
    traces_summary = []

    for tf in trace_files:
        try:
            with open(tf, "r", encoding="utf-8") as f:
                data = json.load(f)
            traces_summary.append({
                "run_id": data.get("run_id", tf.stem),
                "started_at": data.get("started_at"),
                "tracking_id": data.get("input", {}).get("tracking_id"),
                "question": data.get("input", {}).get("question"),
                "decision": data.get("final", {}).get("decision"),
                "step_count": len(data.get("steps", [])),
                "duration_ms": data.get("duration_ms", 0),
                "guardrail_flags": data.get("guardrail_flags", []),
            })
        except Exception:
            continue

    # Sort newest first
    traces_summary.sort(key=lambda t: t.get("started_at") or "", reverse=True)
    return traces_summary
