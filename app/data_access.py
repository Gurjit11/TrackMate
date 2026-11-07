import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "mock_shipments.json"

def normalize_tracking_id(s: str) -> str:
    return s.strip().upper()

def load_shipments() -> dict[str, dict[str, Any]]:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {
        normalize_tracking_id(shipment["tracking_id"]): shipment
        for shipment in data.get("shipments", [])
    }

def compute_derived_fields(shipment: dict[str, Any]) -> dict[str, Optional[int]]:
    as_of = date.fromisoformat(shipment["as_of_date"])
    est_delivery = date.fromisoformat(shipment["estimated_delivery"])
    status = shipment.get("status")

    # days_past_estimate
    if status == "delivered":
        days_past_estimate = 0
    else:
        days_past_estimate = max(0, (as_of - est_delivery).days)

    # days_since_last_scan
    events = shipment.get("events", [])
    if events:
        latest_event_dt = max(
            datetime.fromisoformat(ev["timestamp"]) for ev in events
        )
        days_since_last_scan = (as_of - latest_event_dt.date()).days
    else:
        days_since_last_scan = None

    # days_since_delivered
    if status == "delivered" and shipment.get("delivered_date"):
        delivered_d = date.fromisoformat(shipment["delivered_date"])
        days_since_delivered = (as_of - delivered_d).days
    else:
        days_since_delivered = None

    # customs_hold_days
    if shipment.get("exception") == "customs_hold" and shipment.get("customs_hold_started"):
        hold_started_d = date.fromisoformat(shipment["customs_hold_started"])
        customs_hold_days = (as_of - hold_started_d).days
    else:
        customs_hold_days = None

    return {
        "days_past_estimate": days_past_estimate,
        "days_since_last_scan": days_since_last_scan,
        "days_since_delivered": days_since_delivered,
        "customs_hold_days": customs_hold_days,
    }

def get_shipment_with_derived(tracking_id: str) -> Optional[dict[str, Any]]:
    shipments = load_shipments()
    normalized = normalize_tracking_id(tracking_id)
    shipment = shipments.get(normalized)
    if not shipment:
        return None
    record = dict(shipment)
    record["derived"] = compute_derived_fields(record)
    return record
