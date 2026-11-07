import datetime
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import GEMINI_MODEL
from app.prompts import SYSTEM_PROMPT
from app.agent import run_agent
from app.trace import load_trace

EVALS_DIR = PROJECT_ROOT / "evals"
SCENARIOS_FILE = EVALS_DIR / "scenarios.json"
TRACES_DIR = EVALS_DIR / "traces"
RESULTS_FILE = EVALS_DIR / "results.md"
RUN_META_FILE = TRACES_DIR / "_run_meta.json"

AVAILABLE_TOOLS = ["get_shipment", "search_policies", "get_weather"]


def compute_fingerprint() -> tuple[str, str]:
    """Compute deterministic fingerprint from GEMINI_MODEL, SYSTEM_PROMPT, tool list, and code files."""
    prompt_hash = hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()
    agent_hash = hashlib.sha256((PROJECT_ROOT / "app" / "agent.py").read_bytes()).hexdigest()
    tools_code_hash = hashlib.sha256((PROJECT_ROOT / "app" / "tools.py").read_bytes()).hexdigest()
    tools_list_str = ",".join(sorted(AVAILABLE_TOOLS))

    raw = f"{GEMINI_MODEL}|{prompt_hash}|{tools_list_str}|{agent_hash}|{tools_code_hash}"
    full_fp = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    short_fp = full_fp[:12]
    return full_fp, short_fp


def is_daily_quota_error(err_str: str) -> bool:
    err_lower = err_str.lower()
    return "requests per day" in err_lower or "perday" in err_lower


def is_per_minute_error(err_str: str) -> bool:
    err_lower = err_str.lower()
    return "requests per minute" in err_lower or "perminute" in err_lower or "rpm" in err_lower


def evaluate_trace_data(s: dict[str, Any], trace: dict[str, Any], latency: float) -> dict[str, Any]:
    s_id = s["id"]
    t_id = s.get("tracking_id")
    q = s["question"]
    expected = s["expected_decision"]
    must_cite = s.get("must_cite")

    got = trace["final"]["decision"]
    citations = trace["final"].get("citations", [])
    flags = trace.get("guardrail_flags", [])
    step_count = len(trace.get("steps", []))

    # Citation relevance check
    must_cite_matched = None
    if must_cite:
        req_doc, req_clause = must_cite.split(":")
        must_cite_matched = any(
            c.get("doc") == req_doc and c.get("clause_id") == req_clause for c in citations
        )

    # Citation validity check (from trace's retrieved_clauses)
    retrieved_clauses = set((doc, cid) for doc, cid in trace.get("retrieved_clauses", []))
    valid_citations_count = sum(
        1 for c in citations if (c.get("doc"), c.get("clause_id")) in retrieved_clauses
    )
    total_citations_count = len(citations)

    return {
        "id": s_id,
        "tracking_id": t_id,
        "question": q,
        "expected": expected,
        "got": got,
        "latency": latency,
        "citations": citations,
        "must_cite": must_cite,
        "must_cite_matched": must_cite_matched,
        "valid_citations_count": valid_citations_count,
        "total_citations_count": total_citations_count,
        "guardrail_flags": flags,
        "step_count": step_count,
        "error": None,
        "trace_file": f"evals/traces/{s_id}.json",
    }


def generate_markdown_report(
    run_results: list[dict[str, Any]],
    total_scenarios: int,
    total_api_calls: int,
    short_fp: str,
    reused_count: int,
    stale_count: int,
) -> str:
    completed_cases = [r for r in run_results if r["error"] is None]
    errored_cases = [r for r in run_results if r["error"] is not None]

    completed_count = len(completed_cases)
    error_count = len(errored_cases)

    # Decision accuracy (denominator = completed_count)
    correct_decisions = sum(1 for r in completed_cases if r["got"] == r["expected"])
    decision_accuracy_str = f"{(correct_decisions / completed_count):.2%}" if completed_count > 0 else "N/A"

    # Per-class recall (denominator = completed expected)
    recall_by_class = {}
    for cls_name in ["update", "ask_info", "escalate"]:
        exp_count = sum(1 for r in completed_cases if r["expected"] == cls_name)
        got_count = sum(1 for r in completed_cases if r["expected"] == cls_name and r["got"] == cls_name)
        if exp_count > 0:
            rec_str = f"{(got_count / exp_count):.2%}"
            details = f"{got_count} / {exp_count}"
        else:
            rec_str = "N/A"
            details = f"0 / 0"
        recall_by_class[cls_name] = (rec_str, details)

    # Citation validity (from completed runs)
    total_valid_cites = sum(r["valid_citations_count"] for r in completed_cases)
    total_cites = sum(r["total_citations_count"] for r in completed_cases)
    citation_validity_str = f"{(total_valid_cites / total_cites):.2%}" if total_cites > 0 else "N/A"

    # Citation relevance (among completed scenarios where must_cite is not null)
    must_cite_cases = [r for r in completed_cases if r["must_cite"] is not None]
    matched_must_cite_cases = [r for r in must_cite_cases if r["must_cite_matched"] is True]
    citation_relevance_str = (
        f"{(len(matched_must_cite_cases) / len(must_cite_cases)):.2%}"
        if must_cite_cases else "N/A"
    )

    # Missing-data handling (scenarios 21, 22, 23 among completed)
    missing_data_cases = [r for r in completed_cases if r["id"] in [21, 22, 23]]
    correct_missing_data = sum(1 for r in missing_data_cases if r["got"] == "ask_info")
    missing_data_accuracy_str = (
        f"{(correct_missing_data / len(missing_data_cases)):.2%}"
        if missing_data_cases else "N/A"
    )

    # Guardrail activations (completed cases)
    flag_counts: dict[str, int] = {}
    for r in completed_cases:
        for fl in r["guardrail_flags"]:
            flag_counts[fl] = flag_counts.get(fl, 0) + 1

    # Average latency
    avg_latency = (
        sum(r["latency"] for r in completed_cases) / completed_count
        if completed_count > 0 else 0.0
    )

    # Failed cases (completed mismatches + errored cases)
    failed_cases = [r for r in run_results if r["got"] != r["expected"]]

    timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    run_title = "## Run 1 (Aborted - Invalid)" if error_count > 0 or completed_count < total_scenarios else "## Run 1"

    reused_desc = f"{reused_count} traces reused"
    if stale_count > 0:
        reused_desc += f" ({stale_count} stale traces ignored)"
    elif reused_count == 0:
        reused_desc = "None (fresh run)"

    markdown_report = f"""# Evaluation Results

{run_title}
- **Timestamp:** {timestamp_str}
- **Model:** `{GEMINI_MODEL}`
- **Fingerprint:** `{short_fp}`
- **Trace Reuse:** {reused_desc}
- **Status:** Completed {completed_count} of {total_scenarios}, Errors {error_count}
- **Total LLM API Calls Recorded:** {total_api_calls}
"""
    if error_count > 0 or completed_count < total_scenarios:
        markdown_report += f"\n> [!WARNING]\n> Aborted due to API quota limits. Denominators below reflect only the {completed_count} completed cases.\n"

    markdown_report += f"""
### Metrics

| Metric | Score | Details |
|---|---|---|
| **Decision Accuracy** | {decision_accuracy_str} | {correct_decisions} / {completed_count} completed |
| **Escalate Recall** | **{recall_by_class['escalate'][0]}** | {recall_by_class['escalate'][1]} |
| **Update Recall** | {recall_by_class['update'][0]} | {recall_by_class['update'][1]} |
| **Ask Info Recall** | {recall_by_class['ask_info'][0]} | {recall_by_class['ask_info'][1]} |
| **Citation Validity** | {citation_validity_str} | {total_valid_cites} / {total_cites} cited clauses |
| **Citation Relevance** | {citation_relevance_str} | {len(matched_must_cite_cases)} / {len(must_cite_cases)} required clauses |
| **Missing-Data Handling** | {missing_data_accuracy_str} | {correct_missing_data} / {len(missing_data_cases)} (cases 21, 22, 23) |
| **Average Latency** | {avg_latency:.2f}s | per completed scenario |

### Guardrail Activations

| Guardrail Flag | Count |
|---|---|
"""
    if flag_counts:
        for fl, cnt in sorted(flag_counts.items()):
            markdown_report += f"| `{fl}` | {cnt} |\n"
    else:
        markdown_report += "| None | 0 |\n"

    markdown_report += "\n### Failed Cases\n\n"
    if failed_cases:
        markdown_report += "| ID | Tracking ID | Question | Expected | Got | Trace File |\n"
        markdown_report += "|---|---|---|---|---|---|\n"
        for fc in failed_cases:
            markdown_report += f"| {fc['id']} | {fc['tracking_id']} | {fc['question']} | `{fc['expected']}` | `{fc['got']}` | `{fc['trace_file']}` |\n"
    else:
        markdown_report += "No failed cases.\n"

    return markdown_report


def main() -> None:
    TRACES_DIR.mkdir(parents=True, exist_ok=True)

    min_gap_seconds = float(os.getenv("EVAL_MIN_GAP_SECONDS", "13.0"))
    full_fp, short_fp = compute_fingerprint()

    # Save run metadata
    run_meta = {
        "fingerprint": full_fp,
        "short_fingerprint": short_fp,
        "model": GEMINI_MODEL,
        "tools": sorted(AVAILABLE_TOOLS),
        "min_gap_seconds": min_gap_seconds,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    with open(RUN_META_FILE, "w", encoding="utf-8") as rmf:
        json.dump(run_meta, rmf, indent=2)

    with open(SCENARIOS_FILE, "r", encoding="utf-8") as f:
        scenarios: list[dict[str, Any]] = json.load(f)

    run_results = []
    total_api_calls = 0
    reused_count = 0
    stale_count = 0

    print(f"Starting evaluation of {len(scenarios)} scenarios using model {GEMINI_MODEL} [Fingerprint: {short_fp}, Gap: {min_gap_seconds}s]...")

    for i, s in enumerate(scenarios, 1):
        s_id = s["id"]
        t_id = s.get("tracking_id")
        q = s["question"]
        expected = s["expected_decision"]
        trace_file = TRACES_DIR / f"{s_id}.json"

        # Check if saved successful trace exists and matches fingerprint
        if trace_file.exists():
            try:
                with open(trace_file, "r", encoding="utf-8") as tf:
                    saved_trace = json.load(tf)
                if "final" in saved_trace and "error" not in saved_trace:
                    saved_fp = saved_trace.get("fingerprint")
                    if saved_fp == full_fp:
                        latency = saved_trace.get("duration_ms", 0.0) / 1000.0
                        res_dict = evaluate_trace_data(s, saved_trace, latency)
                        run_results.append(res_dict)
                        total_api_calls += res_dict["step_count"]
                        reused_count += 1
                        status = "MATCH" if res_dict["got"] == expected else "MISMATCH"
                        print(f"[{i}/{len(scenarios)}] Resumed scenario {s_id} from trace (valid fingerprint): {status} (got={res_dict['got']}, expected={expected})")
                        continue
                    else:
                        stale_count += 1
                        print(f"[{i}/{len(scenarios)}] Scenario {s_id} trace is STALE (fp: {saved_fp[:8] if saved_fp else 'none'} != {short_fp[:8]}), re-running...")
            except Exception:
                pass  # If corrupt, re-run

        start_time = time.time()
        print(f"[{i}/{len(scenarios)}] Running scenario {s_id} (ID: {t_id})...", end=" ", flush=True)

        res = None
        error_msg = None

        # Attempt call with per-minute rate-limit retry
        for attempt in range(2):
            try:
                res = run_agent(tracking_id=t_id, question=q)
                break
            except Exception as e:
                err_text = str(e)
                error_msg = err_text

                # Stop immediately on daily quota error
                if is_daily_quota_error(err_text):
                    print(f"\nDAILY QUOTA LIMIT REACHED: {err_text}")
                    break

                # If per-minute error, wait 15s and retry once
                if is_per_minute_error(err_text) and attempt == 0:
                    print(f"[429 RPM limit - waiting 15s before retry]...", end=" ", flush=True)
                    time.sleep(15.0)
                    continue

                break

        latency = time.time() - start_time

        if res is not None:
            trace = load_trace(res.run_id)
            if trace:
                trace["fingerprint"] = full_fp
                with open(trace_file, "w", encoding="utf-8") as tf:
                    json.dump(trace, tf, indent=2)
            res_dict = evaluate_trace_data(s, trace, latency)
            run_results.append(res_dict)
            total_api_calls += res_dict["step_count"]
            status = "MATCH" if res_dict["got"] == expected else "MISMATCH"
            print(f"{status} (got={res_dict['got']}, expected={expected}, time={latency:.2f}s, steps={res_dict['step_count']})")
        else:
            print(f"ERROR: {error_msg} ({latency:.2f}s)")
            error_trace = {
                "scenario_id": s_id,
                "fingerprint": full_fp,
                "error": error_msg,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            with open(trace_file, "w", encoding="utf-8") as tf:
                json.dump(error_trace, tf, indent=2)

            run_results.append({
                "id": s_id,
                "tracking_id": t_id,
                "question": q,
                "expected": expected,
                "got": f"ERROR: {error_msg}",
                "latency": latency,
                "citations": [],
                "must_cite": s.get("must_cite"),
                "must_cite_matched": False if s.get("must_cite") else None,
                "valid_citations_count": 0,
                "total_citations_count": 0,
                "guardrail_flags": [],
                "step_count": 0,
                "error": error_msg,
                "trace_file": f"evals/traces/{s_id}.json",
            })

            # Stop immediately on daily quota error
            if error_msg and is_daily_quota_error(error_msg):
                print("Aborting further evaluation due to daily quota exhaustion.")
                break

    report = generate_markdown_report(
        run_results,
        len(scenarios),
        total_api_calls,
        short_fp,
        reused_count,
        stale_count,
    )
    with open(RESULTS_FILE, "w", encoding="utf-8") as rf:
        rf.write(report)

    print("\n" + "=" * 50)
    print(report)
    print("=" * 50)


if __name__ == "__main__":
    main()
