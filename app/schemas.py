from typing import Literal, Optional
from pydantic import BaseModel, Field

Decision = Literal["update", "ask_info", "escalate"]
ToolName = Literal["get_shipment", "search_policies", "get_weather"]  # get_weather is unused until M5

class Citation(BaseModel):
    doc: str
    clause_id: str

class Draft(BaseModel):
    channel: Literal["email", "whatsapp"]
    subject: Optional[str] = None
    body: str

class FinalAnswer(BaseModel):
    decision: Decision
    reply_to_user: str
    citations: list[Citation] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)
    draft_message: Optional[Draft] = None

class AgentStep(BaseModel):
    rationale: str                     # one short sentence
    action: Literal["call_tool", "final"]
    tool: Optional[ToolName] = None
    tracking_id: Optional[str] = None  # for get_shipment
    query: Optional[str] = None        # for search_policies
    city: Optional[str] = None         # for get_weather (M5)
    start_date: Optional[str] = None   # for get_weather (M5)
    end_date: Optional[str] = None     # for get_weather (M5)
    final: Optional[FinalAnswer] = None

class AgentResult(BaseModel):
    run_id: str
    final: FinalAnswer
    guardrail_flags: list[str] = Field(default_factory=list)

