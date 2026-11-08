from app.tools import get_route_disruptions


def test_route_disruption_feed_is_explicitly_simulated_and_matches_route():
    result = get_route_disruptions("Mumbai", "Pune")

    assert result["source"] == "simulated"
    assert result["disruptions"]
    assert all(item["active"] for item in result["disruptions"])


def test_route_disruption_feed_returns_empty_for_unknown_route():
    result = get_route_disruptions("Pune", "Mumbai")

    assert result["source"] == "simulated"
    assert result["disruptions"] == []
