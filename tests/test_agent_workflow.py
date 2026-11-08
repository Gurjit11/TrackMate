from app import agent
from app.schemas import AgentResult, Citation, Draft, FinalAnswer


def test_missing_or_unknown_tracking_is_forced_to_ask_info(monkeypatch):
    trace = {}
    monkeypatch.setattr(
        agent.ShipmentInvestigator,
        "investigate",
        lambda self, tracking_id: (
            {"shipment_lookup": {"found": False}},
            [],
            [],
        ),
    )
    monkeypatch.setattr(agent, "save_trace", lambda value: trace.update(value))

    result = agent.run_agent("TM9999", "Where is my delivery?")

    assert result.final.decision == "ask_info"
    assert result.final.missing_info == ["a valid tracking number"]
    assert result.final.draft_message.channel == "whatsapp"
    assert trace["roles"][0]["name"] == "shipment_investigator"
    assert trace["guardrail_flags"] == ["forced_ask_info"]


def test_unretrieved_policy_citation_escalates_and_is_removed(monkeypatch):
    trace = {}
    evidence = {
        "shipment_lookup": {
            "found": True,
            "shipment": {
                "tracking_id": "TM1001",
                "status": "in_transit",
                "events": [],
                "derived": {"days_past_estimate": 0, "days_since_last_scan": 1},
            },
        },
        "route": {"source": "simulated", "disruptions": []},
        "weather": None,
    }
    monkeypatch.setattr(
        agent.ShipmentInvestigator,
        "investigate",
        lambda self, tracking_id: (evidence, [], []),
    )
    monkeypatch.setattr(
        agent.PolicyResearcher,
        "research",
        lambda self, question, shipment_evidence: (
            "delay rules",
            [{"doc": "delivery_policy", "clause_id": "1.1"}],
            {"role": "policy_researcher", "action": "call_tool", "tool": "search_policies"},
        ),
    )
    monkeypatch.setattr(
        agent.ResolutionSpecialist,
        "resolve",
        lambda self, question, shipment_evidence, policy_results: FinalAnswer(
            decision="update",
            reply_to_user="Your package is moving.",
            citations=[Citation(doc="invented", clause_id="9.9")],
        ),
    )
    monkeypatch.setattr(agent, "save_trace", lambda value: trace.update(value))

    result = agent.run_agent("TM1001", "Where is my package?")

    assert result.final.decision == "escalate"
    assert result.final.citations == []
    assert result.final.draft_message.channel == "email"
    assert "invalid_citation_escalated" in result.guardrail_flags
    assert [role["name"] for role in trace["roles"]] == [
        "shipment_investigator",
        "policy_researcher",
        "resolution_specialist",
    ]


def test_deterministic_decision_guardrail_corrects_llm_choice(monkeypatch):
    evidence = {
        "shipment_lookup": {
            "found": True,
            "shipment": {
                "tracking_id": "TM1006",
                "status": "in_transit",
                "exception": "damaged",
                "events": [],
                "derived": {"days_past_estimate": 1, "days_since_last_scan": 1},
            },
        },
        "route": {"source": "simulated", "disruptions": []},
        "weather": None,
    }
    monkeypatch.setattr(
        agent.ShipmentInvestigator,
        "investigate",
        lambda self, tracking_id: (evidence, [], []),
    )
    monkeypatch.setattr(
        agent.PolicyResearcher,
        "research",
        lambda self, question, shipment_evidence: (
            "damaged shipment",
            [],
            {"role": "policy_researcher", "action": "call_tool", "tool": "search_policies"},
        ),
    )
    monkeypatch.setattr(
        agent.ResolutionSpecialist,
        "resolve",
        lambda self, question, shipment_evidence, policy_results: FinalAnswer(
            decision="update", reply_to_user="It is moving.", draft_message=None
        ),
    )
    monkeypatch.setattr(agent, "save_trace", lambda value: None)

    result = agent.run_agent("TM1006", "The item arrived broken.")

    assert result.final.decision == "escalate"
    assert result.final.draft_message.channel == "email"
    assert "decision_corrected" in result.guardrail_flags
