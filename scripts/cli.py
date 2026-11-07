import argparse
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agent import run_agent

def main():
    parser = argparse.ArgumentParser(description="TrackMate CLI")
    parser.add_argument("--tracking-id", type=str, default=None, help="Tracking ID (optional)")
    parser.add_argument("--question", type=str, required=True, help="User question")
    args = parser.parse_args()

    result = run_agent(tracking_id=args.tracking_id, question=args.question)

    print(f"Run ID: {result.run_id}")
    print(f"Decision: {result.final.decision}")
    print(f"Reply: {result.final.reply_to_user}")
    print(f"Citations: {[f'{c.doc}:{c.clause_id}' for c in result.final.citations]}")
    print(f"Missing Info: {result.final.missing_info}")
    if result.final.draft_message:
        print(f"Draft ({result.final.draft_message.channel}):")
        if result.final.draft_message.subject:
            print(f"  Subject: {result.final.draft_message.subject}")
        print(f"  Body: {result.final.draft_message.body}")
    else:
        print("Draft: None")
    print(f"Guardrail Flags: {result.guardrail_flags}")

if __name__ == "__main__":
    main()

