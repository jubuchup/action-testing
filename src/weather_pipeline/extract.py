"""Extract: fetch daily weather for the last N completed days from Open-Meteo (no API key)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import requests

from weather_pipeline.cities import coordinates

API_URL = "https://api.open-meteo.com/v1/forecast"
DAILY_FIELDS = ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"]


def fetch(city: str, days: int, timeout: float = 15.0) -> dict:
    """Return the raw API payload wrapped with some metadata."""
    if days < 1:
        raise ValueError("days must be >= 1")
    lat, lon = coordinates(city)
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ",".join(DAILY_FIELDS),
        "timezone": "Europe/Berlin",
        "past_days": days,
        "forecast_days": 0,
    }
    response = requests.get(API_URL, params=params, timeout=timeout)
    response.raise_for_status()
    return {
        "city": city.lower(),
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "response": response.json(),
    }


def save(payload: dict, out: Path) -> int:
    """Write payload to disk and return the number of daily rows."""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return len(payload["response"]["daily"]["time"])
