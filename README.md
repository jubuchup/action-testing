# action-testing
trying out github actions and CI/CD

The vehicle is `weather-pipeline`, a tiny data pipeline:
Open-Meteo API → clean CSV → data-quality checks → static HTML report.
See [PROJECT_PLAN.md](PROJECT_PLAN.md) for the step-by-step learning path.

```bash
uv sync                                              # install
uv run ruff check . && uv run ruff format --check .  # lint
uv run pytest                                        # test (no network needed)
uv run weather-pipeline run --city berlin --days 7   # full run -> data/, site/index.html
```
