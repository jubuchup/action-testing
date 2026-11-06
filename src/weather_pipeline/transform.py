"""Transform: raw Open-Meteo JSON -> tidy, typed table."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

RAINY_DAY_THRESHOLD_MM = 1.0

COLUMNS = [
    "date",
    "city",
    "temp_min_c",
    "temp_max_c",
    "temp_mean_c",
    "precipitation_mm",
    "is_rainy_day",
]


def to_frame(payload: dict) -> pd.DataFrame:
    daily = payload["response"]["daily"]
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]).date,
            "temp_max_c": daily["temperature_2m_max"],
            "temp_min_c": daily["temperature_2m_min"],
            "precipitation_mm": daily["precipitation_sum"],
        }
    )
    df["city"] = payload["city"]
    df["temp_mean_c"] = ((df["temp_max_c"] + df["temp_min_c"]) / 2).round(1)
    df["is_rainy_day"] = df["precipitation_mm"] >= RAINY_DAY_THRESHOLD_MM
    return df[COLUMNS].sort_values("date").reset_index(drop=True)


def run(raw_path: Path, out_path: Path) -> pd.DataFrame:
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    df = to_frame(payload)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return df


def load(clean_path: Path) -> pd.DataFrame:
    return pd.read_csv(clean_path, parse_dates=["date"])
