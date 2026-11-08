# TrackMate

TrackMate is a delivery investigation assistant with three coordinated roles: a shipment investigator, a policy researcher, and a resolution specialist. It can investigate a tracking ID from the local demo shipment dataset or a forwarded `.eml` order email, retrieve applicable courier and retailer policies, and check weather and route context. It then recommends an update, a request for information, or escalation. Follow-up messages and courier-support requests remain drafts until a human approves them.

---

## 1. Honest Scope
- **Simulated Shipment Data:** All shipment records and tracking scan events are mock data loaded from local JSON (`data/mock_shipments.json`). All shipments operate relative to a simulated anchor date of `2026-11-02`.
- **Human-Approved Delivery:** Dispatch defaults to dry-run and never sends without an explicit approval action. SMTP email and Twilio WhatsApp delivery can be enabled by configuring credentials and `DELIVERY_MODE=live`; WhatsApp approval also requires an explicit opt-in confirmation. Provider outcomes are recorded in the draft and `outbox.jsonl`.
- **Email Intake:** Forward an order email by saving it as `.eml` and uploading it from the tracking page. TrackMate processes the plain-text body and does not retain the uploaded file.
- **Shipment and Route Data:** Shipment records are local mock data. Route advisories are also explicitly simulated; neither source represents live carrier or road conditions.
- **Live Weather via Open-Meteo:** Historical weather queries call the live Open-Meteo API. If dates are unavailable or external requests fail, the agent marks weather data as unavailable and proceeds without affecting the decision logic.

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
     Coordinated Agent Roles
   ┌───────────┴───────────┐
   │ Shipment Investigator │
   │ - mock shipment data  │
   │ - weather + route     │
   └───────────┬───────────┘
               ▼
      Policy Researcher
      - policy retrieval
               ▼
     Resolution Specialist
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
  SMTP / Twilio (live only when configured)
  or outbox.jsonl (dry-run default)
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
GEMINI_MODEL=models/gemini-3.8-flash
GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001

# Default: approvals are recorded but nothing is sent.
DELIVERY_MODE=dry_run
COURIER_SUPPORT_EMAIL=
APPROVAL_TOKEN=

# Optional SMTP delivery; used only after human approval in live mode.
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_STARTTLS=true
SMTP_USE_SSL=false

# Optional Twilio WhatsApp delivery; used only after human approval in live mode.
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=
```

To enable live dispatch, configure the matching provider settings, set a strong `APPROVAL_TOKEN`, and change `DELIVERY_MODE` to `live`. Keep `.env` private. The approval screen requires the token; WhatsApp dispatch additionally requires confirming recipient opt-in. Email intake extracts the sender address for an information-request draft, while escalation drafts go to `COURIER_SUPPORT_EMAIL` when configured. Without live credentials, approved drafts remain in dry-run mode.

### Build Knowledge Base & Run Server
```bash
# 1. Build ChromaDB policy index (28 clauses)
python -m app.rag build

# 2. Start the FastAPI server
uvicorn app.main:app --reload
```
Navigate to `http://127.0.0.1:8000/docs` in your browser for interactive API documentation and endpoint testing.

### Deploy on Render (Free)
1. Push this repository to GitHub and open [Render](https://render.com/).
2. Choose **New > Blueprint**, connect `Gurjit11/TrackMate`, and select the `main` branch. Render will use the checked-in `render.yaml`.
3. Enter your Gemini API key when prompted for `GOOGLE_API_KEY`, then deploy. The policy index is built during deployment, so the key is needed at build time as well as runtime.
4. Open the deployed service URL and confirm `https://<your-service>.onrender.com/health` returns `{"status":"ok"}`.

The Blueprint uses Render's free web-service plan and keeps delivery in `dry_run`; no email or WhatsApp messages will be sent. Free services can sleep when idle and their local filesystem is ephemeral, so traces, drafts, and other runtime-generated local files are not durable and may be cleared on restart or redeploy. The app is intended as a demo on this plan, not for production or sensitive customer data.

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

The latest recorded run completed 6 of 30 scenarios; the remaining 24 ended in errors. The figures below describe only the completed cases and are not full-suite results.

| Metric | Score | Details |
|---|---|---|
| **Decision Accuracy** | 100.00% | 6 / 6 completed scenarios |
| **Escalate Recall** | **100.00%** | 1 / 1 completed escalate scenarios |
| **Update Recall** | 100.00% | 5 / 5 completed update scenarios |
| **Ask Info Recall** | N/A | No ask-info scenarios completed |
| **Citation Validity** | 100.00% | 8 / 8 cited clauses in completed scenarios |
| **Citation Relevance** | 100.00% | 4 / 4 completed scenarios with a required clause |
| **Missing-Data Handling** | N/A | 0 / 3 applicable scenarios completed |
| **Average Latency** | 10.25s | Per completed scenario (6 scenarios) |

These are partial-run measurements; see [`evals/results.md`](evals/results.md) for the run status and per-case details.

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
