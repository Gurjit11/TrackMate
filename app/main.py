from typing import Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.agent import run_agent
from app.drafts import approve_draft, create_draft
from app.trace import load_trace

app = FastAPI(title="TrackMate API")


class InvestigateRequest(BaseModel):
    tracking_id: Optional[str] = None
    question: str = Field(..., min_length=1, max_length=500)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be empty or whitespace only")
        return v


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

