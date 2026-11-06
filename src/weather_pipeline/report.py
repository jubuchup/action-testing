"""Report: render the clean table into a single static HTML page (ready for GitHub Pages)."""

from __future__ import annotations

import html
import os
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 760px; margin: 2rem auto;
         padding: 0 1rem; color: #1f2328; }}
  h1 {{ margin-bottom: .2rem; }}
  .meta {{ color: #656d76; font-size: .9rem; }}
  .kpis {{ display: flex; gap: 1rem; margin: 1.5rem 0; flex-wrap: wrap; }}
  .kpi {{ border: 1px solid #d0d7de; border-radius: 8px; padding: .8rem 1rem; min-width: 140px; }}
  .kpi b {{ display: block; font-size: 1.4rem; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border-bottom: 1px solid #d0d7de; padding: .4rem .6rem; text-align: right; }}
  th:first-child, td:first-child {{ text-align: left; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p class="meta">City: <b>{city}</b> &middot; {start} to {end}
  &middot; generated {generated}{build}</p>
<div class="kpis">
  <div class="kpi">Mean temp<b>{mean_temp:.1f} &deg;C</b></div>
  <div class="kpi">Warmest day<b>{max_temp:.1f} &deg;C</b></div>
  <div class="kpi">Total rain<b>{rain:.1f} mm</b></div>
  <div class="kpi">Rainy days<b>{rainy_days} / {n_days}</b></div>
</div>
{table}
</body>
</html>
"""


def render(df: pd.DataFrame, title: str = "Weather report") -> str:
    sha = os.environ.get("GITHUB_SHA", "")
    build = f" &middot; commit <code>{html.escape(sha[:7])}</code>" if sha else ""
    table_df = df.copy()
    table_df["date"] = pd.to_datetime(table_df["date"]).dt.strftime("%a %d %b")
    table_html = table_df.drop(columns=["city"]).to_html(index=False, border=0)
    return TEMPLATE.format(
        title=html.escape(title),
        city=html.escape(str(df["city"].iloc[0]).title()),
        start=pd.to_datetime(df["date"]).min().date(),
        end=pd.to_datetime(df["date"]).max().date(),
        generated=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        build=build,
        mean_temp=df["temp_mean_c"].mean(),
        max_temp=df["temp_max_c"].max(),
        rain=df["precipitation_mm"].sum(),
        rainy_days=int(df["is_rainy_day"].sum()),
        n_days=len(df),
        table=table_html,
    )


def write(df: pd.DataFrame, out: Path, title: str = "Weather report") -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(df, title), encoding="utf-8")
    return out
