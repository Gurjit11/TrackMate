import json
import time
from datetime import datetime, timezone
from typing import Any, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.config import GEMINI_MODEL, MAX_AGENT_STEPS
from app.llm import call_structured
from app.prompts import SYSTEM_PROMPT
from app.schemas import AgentResult, AgentStep, FinalAnswer
from app.tools import get_shipment, search_policies
from app.trace import new_run_id, save_trace

def run_agent(tracking_id: Optional[str], question: str) -> AgentResult:
    run_id = new_run_id()
    started_at = datetime.now(timezone.utc).isoformat()
    start_time = time.time()

    input_data = {"tracking_id": tracking_id, "question": question}
    messages: list[Any] = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=json.dumps(input_data)),
    ]

    steps: list[dict[str, Any]] = []
    retrieved_clauses: set[tuple[str, str]] = set()
    guardrail_events: list[dict[str, str]] = []
    guardrail_flags: list[str] = []

    called_tools: list[str] = []
    shipment_not_found = False
    guardrail_retried = False
    final_answer: Optional[FinalAnswer] = None

    for step_idx in range(1, MAX_AGENT_STEPS + 1):
        step_start = time.time()
        step: AgentStep = call_structured(messages, AgentStep)
        latency_ms = int((time.time() - step_start) * 1000)

        step_record: dict[str, Any] = {
            "index": step_idx,
            "rationale": step.rationale,
            "action": step.action,
            "tool": step.tool,
            "tool_args": None,
            "tool_result": None,
            "llm_latency_ms": latency_ms,
            "error": None,
        }

        if step.action == "call_tool":
            tool_name = step.tool
            called_tools.append(tool_name)
            tool_result: dict[str, Any] = {}

            if tool_name == "get_shipment":
                tid = step.tracking_id or tracking_id or ""
                step_record["tool_args"] = {"tracking_id": tid}
                tool_result = get_shipment(tid)
                if not tool_result.get("found", False):
                    shipment_not_found = True
            elif tool_name == "search_policies":
                query_text = step.query or question
                step_record["tool_args"] = {"query": query_text}
                tool_result = search_policies(query_text)
                for item in tool_result.get("results", []):
                    retrieved_clauses.add((item["doc"], item["clause_id"]))
            elif tool_name == "get_weather":
                # Used in M5
                from app.tools import get_weather
                city = step.city or ""
                s_date = step.start_date or ""
                e_date = step.end_date or ""
                step_record["tool_args"] = {"city": city, "start_date": s_date, "end_date": e_date}
                tool_result = get_weather(city, s_date, e_date)
                if not tool_result.get("available", False):
                    if "weather_unavailable" not in guardrail_flags:
                        guardrail_flags.append("weather_unavailable")
            else:
                tool_result = {"error": f"Unknown tool: {tool_name}"}

            result_str = json.dumps(tool_result)
            step_record["tool_result"] = (
                result_str[:2000] + "..." if len(result_str) > 2000 else result_str
            )
            steps.append(step_record)

            messages.append(AIMessage(content=step.model_dump_json()))
            messages.append(
                HumanMessage(content=f"TOOL RESULT ({tool_name}): {result_str}")
            )
            continue

        elif step.action == "final":
            steps.append(step_record)
            final = step.final
            if not final:
                final = FinalAnswer(
                    decision="escalate",
                    reply_to_user="I could not verify this against policy, so I am escalating it for human review.",
                    citations=[],
                    missing_info=[],
                    draft_message=None,
                )

            # G1: Shipment lookup required
            if tracking_id and "get_shipment" not in called_tools:
                if not guardrail_retried:
                    guardrail_retried = True
                    reason = "You must call get_shipment before answering"
                    guardrail_events.append({"guardrail": "G1", "detail": reason})
                    messages.append(AIMessage(content=step.model_dump_json()))
                    messages.append(
                        HumanMessage(
                            content=f"GUARDRAIL: {reason}. Fix this and return a corrected final answer."
                        )
                    )
                    continue

            # G2: Not found forces ask_info
            if shipment_not_found or not tracking_id:
                final.decision = "ask_info"
                if not final.missing_info:
                    final.missing_info = ["a valid tracking ID"]
                if "forced_ask_info" not in guardrail_flags:
                    guardrail_flags.append("forced_ask_info")
                guardrail_events.append(
                    {
                        "guardrail": "G2",
                        "detail": "No valid tracking ID found or provided; forced ask_info.",
                    }
                )

            # G3: Citation validity
            invalid_citations = [
                f"{c.doc}:{c.clause_id}"
                for c in final.citations
                if (c.doc, c.clause_id) not in retrieved_clauses
            ]
            if invalid_citations:
                if not guardrail_retried:
                    guardrail_retried = True
                    reason = f"Citations not in retrieved clauses: {', '.join(invalid_citations)}"
                    guardrail_events.append({"guardrail": "G3", "detail": reason})
                    messages.append(AIMessage(content=step.model_dump_json()))
                    messages.append(
                        HumanMessage(
                            content=f"GUARDRAIL: {reason}. Fix this and return a corrected final answer."
                        )
                    )
                    continue
                else:
                    final.decision = "escalate"
                    final.reply_to_user = (
                        "I could not verify this against policy, so I am escalating it for human review."
                    )
                    final.citations = []
                    if "invalid_citation_escalated" not in guardrail_flags:
                        guardrail_flags.append("invalid_citation_escalated")
                    guardrail_events.append(
                        {
                            "guardrail": "G3",
                            "detail": "Invalid citations persisted after retry; escalated.",
                        }
                    )

            # G5: Draft rule
            if final.decision == "update":
                final.draft_message = None
            elif final.decision in ("escalate", "ask_info"):
                if final.draft_message is None:
                    if not guardrail_retried:
                        guardrail_retried = True
                        reason = "Draft a message per the drafting rules"
                        guardrail_events.append({"guardrail": "G5", "detail": reason})
                        messages.append(AIMessage(content=step.model_dump_json()))
                        messages.append(
                            HumanMessage(
                                content=f"GUARDRAIL: {reason}. Fix this and return a corrected final answer."
                            )
                        )
                        continue
                    else:
                        final.draft_message = None
                        if "draft_missing" not in guardrail_flags:
                            guardrail_flags.append("draft_missing")
                        guardrail_events.append(
                            {
                                "guardrail": "G5",
                                "detail": "Draft missing after retry; left None.",
                            }
                        )

            final_answer = final
            break

    # G4: Step limit
    if final_answer is None:
        final_answer = FinalAnswer(
            decision="escalate",
            reply_to_user="I could not verify this against policy, so I am escalating it for human review.",
            citations=[],
            missing_info=[],
            draft_message=None,
        )
        if "step_limit_reached" not in guardrail_flags:
            guardrail_flags.append("step_limit_reached")
        guardrail_events.append(
            {"guardrail": "G4", "detail": "Maximum agent steps reached without final answer."}
        )

    duration_ms = int((time.time() - start_time) * 1000)

    trace = {
        "run_id": run_id,
        "started_at": started_at,
        "model": GEMINI_MODEL,
        "input": input_data,
        "steps": steps,
        "retrieved_clauses": [list(c) for c in sorted(retrieved_clauses)],
        "guardrail_events": guardrail_events,
        "guardrail_flags": guardrail_flags,
        "final": final_answer.model_dump(),
        "duration_ms": duration_ms,
    }
    save_trace(trace)

    return AgentResult(
        run_id=run_id,
        final=final_answer,
        guardrail_flags=guardrail_flags,
    )

