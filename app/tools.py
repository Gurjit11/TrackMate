from typing import Any
import httpx
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


def get_weather(city: str, start_date: str, end_date: str) -> dict[str, Any]:
    """Retrieve historical daily weather data from Open-Meteo for a given city and date range."""
    if not city or not start_date or not end_date:
        return {"available": False, "reason": "Missing city or date range"}

    try:
        # Step 1: Geocoding lookup
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        with httpx.Client(timeout=10.0) as client:
            geo_res = client.get(geo_url, params={"name": city, "count": 1, "format": "json"})
            if geo_res.status_code != 200:
                return {"available": False, "reason": f"Geocoding API returned HTTP {geo_res.status_code}"}
            
            geo_data = geo_res.json()
            results = geo_data.get("results")
            if not results:
                return {"available": False, "reason": f"City '{city}' not found in geocoding"}
            
            lat = results[0]["latitude"]
            lon = results[0]["longitude"]

            # Step 2: Historical archive weather lookup
            weather_url = "https://archive-api.open-meteo.com/v1/archive"
            weather_params = {
                "latitude": lat,
                "longitude": lon,
                "start_date": start_date,
                "end_date": end_date,
                "daily": "precipitation_sum,wind_speed_10m_max",
                "timezone": "auto",
            }
            weather_res = client.get(weather_url, params=weather_params)
            if weather_res.status_code != 200:
                return {"available": False, "reason": f"Weather archive API returned HTTP {weather_res.status_code}"}

            weather_data = weather_res.json()
            daily = weather_data.get("daily", {})
            times = daily.get("time", [])
            precips = daily.get("precipitation_sum", [])
            winds = daily.get("wind_speed_10m_max", [])

            if not times:
                return {"available": False, "reason": "No daily weather data returned for date range"}

            days = []
            heavy_rain_days = []
            strong_wind_days = []

            for i, date_str in enumerate(times):
                prec = precips[i] if i < len(precips) and precips[i] is not None else 0.0
                wind = winds[i] if i < len(winds) and winds[i] is not None else 0.0
                flags = []
                if prec >= 50.0:
                    flags.append("heavy_rain")
                    heavy_rain_days.append(date_str)
                if wind >= 60.0:
                    flags.append("strong_wind")
                    strong_wind_days.append(date_str)
                days.append({
                    "date": date_str,
                    "precipitation_mm": prec,
                    "wind_max_kmh": wind,
                    "flags": flags,
                })

            if heavy_rain_days and strong_wind_days:
                summary = f"Heavy rain recorded on {', '.join(heavy_rain_days)} and strong winds on {', '.join(strong_wind_days)} in {city}."
            elif heavy_rain_days:
                summary = f"Heavy rain (>=50mm) recorded in {city} on {', '.join(heavy_rain_days)}."
            elif strong_wind_days:
                summary = f"Strong winds (>=60km/h) recorded in {city} on {', '.join(strong_wind_days)}."
            else:
                summary = f"No severe weather conditions (heavy rain or strong winds) recorded in {city} between {start_date} and {end_date}."

            return {
                "available": True,
                "city": city,
                "days": days,
                "summary": summary,
            }

    except Exception as e:
        return {"available": False, "reason": str(e)}
