# TrackMate

TrackMate is an automated delivery investigation agent that analyzes package delivery inquiries, cross-references internal shipment event tracking, and verifies applicable courier and retailer policies. It autonomously determines whether to provide an update, ask for additional information, or escalate an issue for human attention. When escalation or user follow-up is necessary, TrackMate drafts an appropriate message and holds it for human approval before execution.

---

## 1. Honest Scope
- **Simulated Shipment Data:** All shipment records and tracking scan events are mock data loaded from local JSON (`data/mock_shipments.json`). All shipments operate relative to a simulated anchor date of `2026-11-02`.
- **Dry-Run Message Dispatch:** No real emails or WhatsApp messages are ever transmitted. Approved communications are appended to a local log file (`outbox.jsonl`) flagged as `"delivery": "dry_run_not_sent"`.
- **Live Weather via Open-Meteo:** Historical weather queries call the live Open-Meteo API. If dates are unavailable or external requests fail, the agent marks weather data as unavailable and proceeds without affecting decision logic.

---

## 2. How It Works

### Flow Diagram
```
User Request (tracking_id, question)
               │
               ▼
   [ FastAPI: POST /investigate ]
               │
               ▼
     Agent Loop (app/agent.py)
   ┌───────────┴───────────┐
   │ Tool Execution        │
   │ - get_shipment        │
   │ - search_policies     │
   │ - get_weather         │
   └───────────┬───────────┘
               │
               ▼
     Python Guardrails (G1 - G5)
               │
               ▼
 Decision: update | ask_info | escalate
   + reply_to_user & cited policy clauses
               │
       (If draft generated)
               ▼
     Human Approval Workflow
   [ POST /approve/{draft_id} ]
               │
               ▼
  outbox.jsonl ("dry_run_not_sent")
```

### Deterministic Python Guardrails
The custom agent loop strictly enforces five guardrails in Python code:
- **G1 (Lookup Required):** Rejects any final answer if a tracking ID was provided but `get_shipment` was never executed.
- **G2 (Not Found Forces Ask Info):** If the shipment is missing or no tracking ID is provided, the decision is forced to `ask_info` with a `forced_ask_info` flag.
- **G3 (Citation Validity):** Rejects any policy citation not returned in `search_policies` for that conversation. If uncorrected after one retry, the inquiry escalates to human review with `invalid_citation_escalated`.
- **G4 (Step Limit):** Hard-caps the loop at 6 steps. If no final answer is reached, forces an escalation with `step_limit_reached`.
- **G5 (Draft Rule):** For `update`, strips any draft message. For `escalate` or `ask_info`, demands an appropriate drafted message; if missing after a retry, flags `draft_missing`.

---

## 3. Run It

### Environment Setup
Clone the repository and configure your environment:

#### Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration (`.env`)
Create a `.env` file based on `.env.example`:
```env
GOOGLE_API_KEY=your_gemini_api_key
GEMINI_MODEL=models/gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001
```

### Build Knowledge Base & Run Server
```bash
# 1. Build ChromaDB policy index (28 clauses)
python -m app.rag build

# 2. Start the FastAPI server
uvicorn app.main:app --reload
```
Navigate to `http://127.0.0.1:8000/docs` in your browser for interactive API documentation and endpoint testing.

---

## 4. Example Run (an example from a development run)

### Request
`POST /investigate`
```json
{
  "tracking_id": "TM1006",
  "question": "Why is this so late?"
}
```

### Response
```json
{
  "run_id": "a5a6149b2b714dc9b6ef8eea4659754b",
  "decision": "escalate",
  "reply_to_user": "Your package (tracking ID TM1006) was estimated for delivery on 2026-10-28. The last status update on 2026-10-31T20:30:00 at Delhi Sorting Centre shows it was delayed in transit. Since the shipment is 5 days past its estimated delivery date, it meets the policy criteria for a significant delay. I am escalating this issue to the courier support desk to investigate the delay and expedite delivery.",
  "citations": [
    {
      "doc": "courier_delivery_policy",
      "clause_id": "1.3"
    },
    {
      "doc": "escalation_policy",
      "clause_id": "1.1"
    }
  ],
  "missing_info": [],
  "draft": {
    "draft_id": "8cc8b8171c3f45e493d0e5ebbb6c0e7f",
    "channel": "email",
    "subject": "Escalation Request: Delayed Shipment TM1006",
    "body": "Dear Courier Support Desk,\n\nI am escalating tracking ID TM1006 due to a significant delivery delay. The shipment was estimated to arrive on 2026-10-28 and is currently 5 days past the estimated delivery date.\n\nLast Known Event:\n- Date/Time: 2026-10-31T20:30:00\n- Location: Delhi Sorting Centre\n- Description: Delayed in transit\n\nProblem Description: The package is significantly delayed beyond the expected delivery timeline with no subsequent scan updates.\n\nPolicy Clauses Relied Upon: courier_delivery_policy clause 1.3, escalation_policy clause 1.1.\n\nPlease locate the shipment and provide an updated delivery schedule.\n\nBest regards,\nTrackMate Assistant",
    "status": "pending_approval"
  },
  "guardrail_flags": []
}
```

### Trace Excerpt (`GET /trace/a5a6149b2b714dc9b6ef8eea4659754b`)
```json
{
  "run_id": "a5a6149b2b714dc9b6ef8eea4659754b",
  "input": {
    "tracking_id": "TM1006",
    "question": "Why is this so late?"
  },
  "steps": [
    {
      "index": 1,
      "action": "call_tool",
      "tool": "get_shipment",
      "tool_args": {"tracking_id": "TM1006"},
      "tool_result": "{\"found\": true, \"shipment\": {\"tracking_id\": \"TM1006\", ...}, \"derived\": {\"days_past_estimate\": 5, \"days_since_last_scan\": 2}}"
    },
    {
      "index": 2,
      "action": "call_tool",
      "tool": "search_policies",
      "tool_args": {"query": "delayed in transit 5 days past estimate courier delivery policy"},
      "tool_result": "{\"results\": [{\"doc\": \"courier_delivery_policy\", \"clause_id\": \"1.3\", \"title\": \"Significant delay\", ...}]}"
    },
    {
      "index": 3,
      "action": "final",
      "tool": null
    }
  ],
  "retrieved_clauses": [
    ["courier_delivery_policy", "1.3"],
    ["escalation_policy", "1.1"]
  ]
}
```

---

## 5. Evaluation

The evaluation suite consists of 30 hand-written test scenarios (`evals/scenarios.json`) covering standard inquiries, customs issues, missing records, damaged goods, and delivery delays.

| Metric | Score | Details |
|---|---|---|
| **Decision Accuracy** | TBD (from evals/results.md) | TBD (from evals/results.md) |
| **Escalate Recall** | **TBD (from evals/results.md)** | TBD (from evals/results.md) |
| **Update Recall** | TBD (from evals/results.md) | TBD (from evals/results.md) |
| **Ask Info Recall** | TBD (from evals/results.md) | TBD (from evals/results.md) |
| **Citation Validity** | TBD (from evals/results.md) | TBD (from evals/results.md) |
| **Citation Relevance** | TBD (from evals/results.md) | TBD (from evals/results.md) |
| **Missing-Data Handling** | TBD (from evals/results.md) | TBD (from evals/results.md) |
| **Average Latency** | TBD (from evals/results.md) | TBD (from evals/results.md) |

To run the evaluation:
```bash
python evals/run_eval.py
```

---

## 6. Limitations
- **Simulated Test Data:** All tracking numbers, courier statuses, and timestamps originate from static mock JSON rather than live logistics webhooks.
- **Prompt Refinement:** The system prompt was adjusted once after early test runs to enforce grounded, specific queries when retrieving policy clauses.
- **Evaluation Set Size:** The 30 evaluation scenarios were authored specifically for this project and reflect hand-written test conditions.
- **Heuristic Rule Dependence:** Agent decisions follow explicit, hand-written policy rules in the prompt and guardrails rather than a learned classifier.
- **Single Model:** The evaluation runs on a single model; development runs earlier used other Gemini models.
- **Citation Support:** Citation checks verify that a cited clause was retrieved, not that the clause supports the claim.
