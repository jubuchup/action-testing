"""Data-quality checks. The CLI exits with code 1 if any check fails, which fails the CI job."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from weather_pipeline.transform import COLUMNS


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


def run_checks(df: pd.DataFrame, min_rows: int = 3) -> list[CheckResult]:
    results: list[CheckResult] = []

    def add(name: str, passed: bool, detail: str = "") -> None:
        results.append(CheckResult(name, bool(passed), detail))

    add("expected columns", list(df.columns) == COLUMNS, f"got {list(df.columns)}")
    add("enough rows", len(df) >= min_rows, f"{len(df)} rows, need >= {min_rows}")
    add("no nulls", not df.isna().any().any(), f"{int(df.isna().sum().sum())} null values")
    add("unique dates", df["date"].is_unique, "duplicate dates found")

    if len(df) and "temp_max_c" in df and "temp_min_c" in df:
        add(
            "max >= min temperature",
            (df["temp_max_c"] >= df["temp_min_c"]).all(),
            "some days have temp_max_c < temp_min_c",
        )
        add(
            "plausible temperatures",
            df[["temp_min_c", "temp_max_c"]].stack().between(-50, 50).all(),
            "values outside [-50, 50] degrees C",
        )
    if len(df) and "precipitation_mm" in df:
        add(
            "non-negative precipitation",
            (df["precipitation_mm"] >= 0).all(),
            "negative precipitation",
        )
    return results


def format_results(results: list[CheckResult]) -> str:
    lines = []
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        suffix = "" if r.passed else f"  ({r.detail})"
        lines.append(f"[{mark}] {r.name}{suffix}")
    return "\n".join(lines)
