"""Command line entry point.

Each pipeline stage is a separate sub-command so that it can run as its own CI job:

    weather-pipeline extract   --city berlin --days 7   -> data/raw.json   (prints rows=<n>)
    weather-pipeline transform                          -> data/clean.csv
    weather-pipeline check     --min-rows 3             -> exit 1 on failure
    weather-pipeline report    --title "..."            -> site/index.html
    weather-pipeline run       (all of the above)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from weather_pipeline import checks, extract, report, transform
from weather_pipeline.cities import CITIES

RAW = Path("data/raw.json")
CLEAN = Path("data/clean.csv")
SITE = Path("site/index.html")


def cmd_extract(args: argparse.Namespace) -> int:
    rows = extract.save(extract.fetch(args.city, args.days), args.out)
    # `key=value` on stdout is easy to append to $GITHUB_OUTPUT in a workflow
    print(f"rows={rows}")
    return 0


def cmd_transform(args: argparse.Namespace) -> int:
    df = transform.run(args.input, args.out)
    print(f"wrote {len(df)} rows to {args.out}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    results = checks.run_checks(transform.load(args.input), min_rows=args.min_rows)
    print(checks.format_results(results))
    failed = [r for r in results if not r.passed]
    if failed:
        print(f"{len(failed)} check(s) failed", file=sys.stderr)
        return 1
    print("all checks passed")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    path = report.write(transform.load(args.input), args.out, title=args.title)
    print(f"report written to {path}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    ns = argparse.Namespace
    steps = [
        (cmd_extract, ns(city=args.city, days=args.days, out=RAW)),
        (cmd_transform, ns(input=RAW, out=CLEAN)),
        (cmd_check, ns(input=CLEAN, min_rows=args.min_rows)),
        (cmd_report, ns(input=CLEAN, out=SITE, title=args.title)),
    ]
    for func, step_args in steps:
        code = func(step_args)
        if code != 0:
            return code
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="weather-pipeline", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def add_extract_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--city", default="berlin", choices=sorted(CITIES))
        p.add_argument("--days", type=int, default=7, help="number of past days to fetch")

    p = sub.add_parser("extract", help="fetch raw data from Open-Meteo")
    add_extract_args(p)
    p.add_argument("--out", type=Path, default=RAW)
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("transform", help="raw JSON -> clean CSV")
    p.add_argument("--input", type=Path, default=RAW)
    p.add_argument("--out", type=Path, default=CLEAN)
    p.set_defaults(func=cmd_transform)

    p = sub.add_parser("check", help="run data-quality checks (exit 1 on failure)")
    p.add_argument("--input", type=Path, default=CLEAN)
    p.add_argument("--min-rows", type=int, default=3)
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("report", help="clean CSV -> HTML report")
    p.add_argument("--input", type=Path, default=CLEAN)
    p.add_argument("--out", type=Path, default=SITE)
    p.add_argument("--title", default="Weather report")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("run", help="run the whole pipeline")
    add_extract_args(p)
    p.add_argument("--min-rows", type=int, default=3)
    p.add_argument("--title", default="Weather report")
    p.set_defaults(func=cmd_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
