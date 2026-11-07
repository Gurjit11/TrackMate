import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.data_access import load_shipments, get_shipment_with_derived

EXPECTED = {
    "TM1001": (0, 1, None, None),
    "TM1002": (0, 0, None, None),
    "TM1003": (0, 1, 1, None),
    "TM1004": (2, 1, None, None),
    "TM1005": (3, 1, None, None),
    "TM1006": (5, 2, None, None),
    "TM1007": (3, 8, None, None),
    "TM1008": (3, 7, None, None),
    "TM1009": (0, 3, 3, None),
    "TM1010": (0, 1, 1, None),
    "TM1011": (3, 2, None, None),
    "TM1012": (1, 1, None, None),
    "TM1013": (0, 3, None, 3),
    "TM1014": (3, 7, None, 7),
    "TM1015": (0, 1, None, None),
    "TM1016": (0, 2, 2, None),
    "TM1017": (0, 3, None, None),
    "TM1018": (6, 1, None, None),
    "TM1019": (12, 3, None, None),
    "TM1020": (2, 1, None, None),
}

def main():
    shipments = load_shipments()
    assert len(shipments) == 20, f"Expected exactly 20 shipments, found {len(shipments)}"

    header = f"{'Tracking ID':<12} | {'Days Past Est':<13} | {'Since Last Scan':<15} | {'Since Delivered':<15} | {'Customs Hold':<12} | {'Match'}"
    print(header)
    print("-" * len(header))

    all_matched = True
    for tid, expected_tuple in EXPECTED.items():
        data = get_shipment_with_derived(tid)
        assert data is not None, f"Shipment {tid} not found"
        d = data["derived"]
        actual_tuple = (
            d["days_past_estimate"],
            d["days_since_last_scan"],
            d["days_since_delivered"],
            d["customs_hold_days"],
        )
        matched = actual_tuple == expected_tuple
        if not matched:
            all_matched = False
        match_str = "OK" if matched else f"MISMATCH (expected {expected_tuple})"
        
        v0 = str(actual_tuple[0]) if actual_tuple[0] is not None else "null"
        v1 = str(actual_tuple[1]) if actual_tuple[1] is not None else "null"
        v2 = str(actual_tuple[2]) if actual_tuple[2] is not None else "null"
        v3 = str(actual_tuple[3]) if actual_tuple[3] is not None else "null"

        print(f"{tid:<12} | {v0:<13} | {v1:<15} | {v2:<15} | {v3:<12} | {match_str}")

    assert all_matched, "Some derived values did not match expected values!"
    print(f"\nAll 20 shipments verified successfully.")

if __name__ == "__main__":
    main()
