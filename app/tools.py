from typing import Any
from app.data_access import get_shipment_with_derived, normalize_tracking_id
from app.rag import search

def get_shipment(tracking_id: str) -> dict[str, Any]:
    normalized = normalize_tracking_id(tracking_id)
    record = get_shipment_with_derived(normalized)
    if not record:
        return {"found": False, "tracking_id": normalized}
    derived = record.pop("derived", {})
    return {
        "found": True,
        "shipment": record,
        "derived": derived,
    }

def search_policies(query: str) -> dict[str, Any]:
    results = search(query)
    return {"results": results}

