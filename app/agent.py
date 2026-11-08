import json
import time
from datetime import datetime, timezone
from typing import Any, Optional

from app.config import GEMINI_MODEL
from app.roles import PolicyResearcher, ResolutionSpecialist, ShipmentInvestigator
from app.schemas import AgentResult, Draft, FinalAnswer
from app.trace import new_run_id, save_trace


def _decision_for(shipment: dict[str, Any], question: str) -> str:
    derived = shipment.get("derived", {})
    status = shipment.get("status")
    exception = shipment.get("exception")

    if exception in {"address_incomplete", "recipient_unavailable", "customs_documents_required"}:
        return "ask_info"
    if (
        exception == "damaged"
        or (
            status != "delivered"
            and (derived.get("days_since_last_scan") or 0) >= 7
        )
        or (
            status == "delivered"
            and any(term in question.casefold() for term in ("did not receive", "not received", "isn't here", "is not here"))
            and (derived.get("days_since_delivered") or 0) >= 2
        )
        or (
            exception == "customs_hold"
            and (derived.get("customs_hold_days") or 0) > 5
        )
        or (derived.get("days_past_estimate") or 0) > 3
        or (
            "refund" in question.casefold()
            and (derived.get("days_past_estimate") or 0) > 10
        )
    ):
        return "escalate"
    return "update"


def _make_fallback_draft(
    decision: str,
    shipment: Optional[dict[str, Any]],
    missing_info: list[str],
    email_intake: bool,
) -> Draft:
    if decision == "ask_info":
        missing = missing_info or ["a valid tracking number"]
        body = "To investigate this delivery, please reply with: " + ", ".join(missing) + "."
        if email_intake:
            return Draft(channel="email", subject="Information needed for your delivery", body=body)
        return Draft(channel="whatsapp", body=body)

    tracking_id = shipment.get("tracking_id", "unknown") if shipment else "unknown"
    events = shipment.get("events", []) if shipment else []
    latest = max(events, key=lambda event: event.get("timestamp", "")) if events else {}
    event_summary = "No shipment event is available."
    if latest:
        event_summary = (
            f"Last known event: {latest.get('timestamp', 'date unavailable')} at "
            f"{latest.get('location', 'location unavailable')} — "
            f"{latest.get('description', 'description unavailable')}."
        )
    return Draft(
        channel="email",
        subject=f"Courier support request: {tracking_id}",
        body=(
            f"Please review tracking ID {tracking_id}. {event_summary} "
            "Please investigate and provide the next available update."
        ),
    )


def run_agent(
    tracking_id: Optional[str],
    question: str,
    *,
    source: str = "web",
) -> AgentResult:
    run_id = new_run_id()
    started_at = datetime.now(timezone.utc).isoformat()
    start_time = time.time()
    email_intake = source == "email"

    evidence, steps, guardrail_flags = ShipmentInvestigator().investigate(tracking_id)
    shipment_result = evidence.get("shipment_lookup") or {}
    shipment = shipment_result.get("shipment") if shipment_result.get("found") else None
    if shipment is not None:
        shipment = {**shipment, "derived": shipment_result.get("derived", {})}
    roles: list[dict[str, str]] = [{
        "name": "shipment_investigator",
        "status": "completed" if tracking_id else "skipped",
        "summary": "Collected shipment and contextual evidence." if shipment else "No shipment record was available.",
    }]
    guardrail_events: list[dict[str, str]] = []
    retrieved_policy_results: list[dict[str, Any]] = []

    if shipment is None:
        missing_info = ["a valid tracking number"]
        final = FinalAnswer(
            decision="ask_info",
            reply_to_user="Please provide a valid tracking number so I can look up the shipment.",
            citations=[],
            missing_info=missing_info,
            draft_message=_make_fallback_draft(
                "ask_info", None, missing_info, email_intake
            ),
        )
        guardrail_flags.append("forced_ask_info")
        guardrail_events.append({
            "guardrail": "G2",
            "detail": "No valid tracking ID was supplied or found; requested a valid ID.",
        })
        roles.extend([
            {"name": "policy_researcher", "status": "skipped", "summary": "Policy lookup is unnecessary without a shipment record."},
            {"name": "resolution_specialist", "status": "guardrail", "summary": "Requested a valid tracking number."},
        ])
    else:
        _, retrieved_policy_results, policy_step = PolicyResearcher().research(
            question, evidence
        )
        steps.append(policy_step)
        roles.append({
            "name": "policy_researcher",
            "status": "completed",
            "summary": f"Retrieved {len(retrieved_policy_results)} policy clauses.",
        })
        final = ResolutionSpecialist().resolve(
            question, evidence, retrieved_policy_results
        )
        roles.append({
            "name": "resolution_specialist",
            "status": "completed",
            "summary": "Prepared a decision and customer response from the supplied evidence.",
        })

        expected_decision = _decision_for(shipment, question)
        if final.decision != expected_decision:
            guardrail_flags.append("decision_corrected")
            guardrail_events.append({
                "guardrail": "G6",
                "detail": f"Decision corrected from {final.decision} to {expected_decision} by deterministic rules.",
            })
            final.decision = expected_decision
            final.reply_to_user = (
                "I could not verify the proposed resolution against the delivery rules, "
                "so I have routed this case according to the applicable review steps."
            )

        available_citations = {
            (item.get("doc"), item.get("clause_id"))
            for item in retrieved_policy_results
        }
        invalid_citations = [
            citation
            for citation in final.citations
            if (citation.doc, citation.clause_id) not in available_citations
        ]
        if invalid_citations:
            guardrail_flags.append("invalid_citation_escalated")
            guardrail_events.append({
                "guardrail": "G3",
                "detail": "Unretrieved policy citations were removed and the case was escalated.",
            })
            final.decision = "escalate"
            final.reply_to_user = (
                "I could not verify the policy references in this response, so I am "
                "escalating the case for human review."
            )
            final.citations = []

        if final.decision == "update":
            final.draft_message = None
            final.missing_info = []
        else:
            if final.decision == "ask_info" and email_intake:
                if final.draft_message is not None:
                    final.draft_message.channel = "email"
                    final.draft_message.subject = (
                        final.draft_message.subject or "Information needed for your delivery"
                    )
            expected_channel = "email" if final.decision == "escalate" or email_intake else "whatsapp"
            if final.draft_message is None or final.draft_message.channel != expected_channel:
                final.draft_message = _make_fallback_draft(
                    final.decision,
                    shipment,
                    final.missing_info,
                    email_intake and final.decision == "ask_info",
                )
                guardrail_flags.append("draft_corrected")
                guardrail_events.append({
                    "guardrail": "G5",
                    "detail": "Generated a required draft for the selected resolution.",
                })

    steps.append({
        "role": "resolution_specialist",
        "index": len(steps) + 1,
        "rationale": "Finalize the case using verified evidence and guardrails.",
        "action": "final",
        "tool": None,
        "tool_args": None,
        "tool_result": None,
        "llm_latency_ms": 0,
        "error": None,
    })
    duration_ms = int((time.time() - start_time) * 1000)
    trace = {
        "run_id": run_id,
        "started_at": started_at,
        "model": GEMINI_MODEL,
        "input": {"tracking_id": tracking_id, "question": question, "source": source},
        "roles": roles,
        "steps": steps,
        "retrieved_clauses": [
            [item.get("doc"), item.get("clause_id")]
            for item in retrieved_policy_results
        ],
        "guardrail_events": guardrail_events,
        "guardrail_flags": guardrail_flags,
        "final": final.model_dump(),
        "duration_ms": duration_ms,
    }
    save_trace(trace)
    return AgentResult(run_id=run_id, final=final, guardrail_flags=guardrail_flags)
