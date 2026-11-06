# GitHub Actions in 2 days: project plan

**Goal:** Learn the core of GitHub Actions hands-on, coming from GitLab CI/CD.
**Vehicle:** `weather-pipeline`, a small Python data pipeline (Open-Meteo API → clean → quality checks → HTML report).
**Split:** The Python app is already written. **You write every workflow file yourself.** Each step below explains *what* to build, *why*, and *what you learn*, plus the GitLab equivalent.

Total effort: about 12–14 hours. Each step ends with a **Done when** checkpoint. Commit after every step (`git commit -m "step N: ..."`), so your git history becomes your learning log.

---

## The app in one minute

```
src/weather_pipeline/
  extract.py    # calls Open-Meteo, saves raw JSON
  transform.py  # raw JSON -> tidy CSV (pandas)
  checks.py     # data-quality checks, exit code 1 on failure
  report.py     # CSV -> static HTML report
  cli.py        # `weather-pipeline <extract|transform|check|report|run>`
tests/          # pytest, no network needed (uses a fixture)
```

Local commands you'll reuse in the workflows:

```bash
uv sync                                   # install deps + dev deps into .venv
uv run ruff check .                       # lint
uv run ruff format --check .              # formatting check
uv run pytest                             # tests
uv run weather-pipeline run --city berlin --days 7   # full pipeline -> data/ and site/
```

The CLI is split into sub-commands on purpose. In Step 5 each stage becomes its own job, and the files are handed from job to job.

---

## Cheat sheet: GitLab → GitHub

| GitLab CI/CD | GitHub Actions |
|---|---|
| `.gitlab-ci.yml` (one file) | `.github/workflows/*.yml` (any number of independent workflows) |
| pipeline | workflow run |
| `stages:` | none; jobs are parallel by default, ordered via `needs:` |
| job `script:` | job `steps:`, each a `run:` (shell) or a `uses:` (reusable action) |
| `image:` | `runs-on: ubuntu-latest` (full VM) + setup actions; `container:` is optional |
| automatic repo clone | **none**; you must use `actions/checkout` |
| `rules:` / `only:` / `except:` | `on:` (triggers) + `if:` (job/step conditions) |
| `parallel: matrix:` | `strategy: matrix:` |
| `artifacts:` | `actions/upload-artifact` / `actions/download-artifact` |
| `cache:` | `actions/cache` or built into setup actions (`setup-uv` has `enable-cache`) |
| CI/CD variables (masked/protected) | `secrets.*`, `vars.*`, environment-scoped secrets |
| `environment:` + protected envs | `environment:` + required reviewers / branch rules |
| `when: manual` | `workflow_dispatch` or environment approval |
| pipeline schedules (UI) | `on: schedule: - cron:` (in YAML, **UTC**) |
| `include:` / `extends:` / templates | reusable workflows (`workflow_call`) + composite actions |
| `CI_COMMIT_SHA`, `CI_COMMIT_REF_NAME` | `github.sha`, `github.ref_name` (or env `GITHUB_SHA`, `GITHUB_REF_NAME`) |
| `CI_JOB_TOKEN` | `GITHUB_TOKEN` (permissions set with `permissions:`) |
| GitLab Pages (`pages` job) | GitHub Pages via `actions/deploy-pages` |

---

# Day 1: Foundations and CI

## Step 0: Setup and baseline (30 min)

**Do**
1. Install uv locally (`brew install uv`) and run `uv sync`, then the four local commands above.
2. Commit the app (`git add . && git commit -m "step 0: add weather pipeline app"`) and push.
3. Open the repo on GitHub and look at the **Actions** tab. It's empty, because there are no workflows yet.

**Why:** CI should only automate things that already work locally. If a command fails locally, debugging it in CI wastes time.
**Learn:** The exact commands your workflows will run. CI is "your terminal, but reproducible".
**Done when:** Tests pass locally, `site/index.html` opens in a browser, and the code is on GitHub.

---

## Step 1: Hello workflow, anatomy and contexts (45 min)

**File:** `.github/workflows/hello.yml` (you already created it)

**Build**
- Name the workflow (`name:`).
- Trigger it on `push` **and** `workflow_dispatch` (adds a "Run workflow" button in the UI).
- One job `hello` on `ubuntu-latest` with steps that:
  - print a greeting,
  - print `${{ github.actor }}`, `${{ github.ref_name }}`, `${{ github.sha }}`, `${{ github.event_name }}`,
  - print the same values via shell env vars (`$GITHUB_ACTOR`, `$GITHUB_REF_NAME`, …),
  - run `ls -la` **without** checking out, then add `actions/checkout@v4` and run `ls -la` again,
  - write a line of Markdown to `$GITHUB_STEP_SUMMARY`.

**Why:** Before building real pipelines you need the skeleton (workflow → jobs → steps) and how to read the run logs.
**Learn**
- Two ways to access values: **expressions** `${{ … }}` are replaced *before* the shell runs, while **env vars** are read *by* the shell. This matters for security later: never put untrusted input like PR titles directly into `${{ }}` inside `run:`.
- The workspace is empty until you check out. This is the #1 surprise for GitLab users.
- Job summaries are a nicer replacement for scrolling through logs.

**GitLab equivalent:** a single job with `script: echo $CI_COMMIT_SHA`.
**Done when:** The run is green, you've triggered it once by push and once manually, and the summary shows on the run page.

---

## Step 2: CI with lint and test jobs (1.5 h)

**File:** `.github/workflows/ci.yml`

**Build**
- Triggers: `push` to `main`, and `pull_request`.
- Job `lint`: checkout → `astral-sh/setup-uv@v6` (with `enable-cache: true`) → `uv sync --locked` → `uv run ruff check .` → `uv run ruff format --check .`
- Job `test`: same setup → `uv run pytest`
- Add `concurrency:` so a new push cancels the still-running old run of the same branch.
- Add `timeout-minutes: 10` to each job.

**Why:** This is the bread and butter of CI: every change is checked automatically. Two parallel jobs give faster feedback and clearer signals ("lint failed" vs "tests failed").
**Learn**
- Using marketplace actions (`uses:` + `with:`) instead of writing everything in shell.
- Jobs run **in parallel on separate VMs** and share nothing by default.
- Caching: compare the duration of run #1 (cold) with run #2 (cache hit), and find the cache line in the logs.
- `--locked` makes CI fail if `uv.lock` is out of date. Reproducibility is a data-engineering virtue.

**GitLab equivalent:** a `lint` and a `test` job in the same stage, `cache:` keyed on the lockfile, `interruptible: true`.
**Try breaking it:** Add an unused import in `cli.py`, push, watch `lint` fail and `test` stay green, then fix it.
**Done when:** Both jobs are green and the second run shows a cache hit.

---

## Step 3: Matrix builds (30 min)

**File:** extend `ci.yml` → `test` job

**Build**
- `strategy: matrix: python-version: ["3.11", "3.12", "3.13"]`
- Pass it to setup-uv (`python-version: ${{ matrix.python-version }}`).
- Experiment with `fail-fast: false`, and add an `include:` entry, e.g. one extra run on `macos-latest`.

**Why:** Libraries and pipelines often have to run on several Python versions or OSes. A matrix gives you N jobs from one definition.
**Learn:** The `matrix` context, how job names are generated, `fail-fast` behavior, `include`/`exclude`.
**GitLab equivalent:** `parallel: matrix:`.
**Done when:** You see 3+ test jobs in the run graph.

---

## Step 4: Protect `main` with PR gating (45 min)

**Do (GitHub UI, no YAML)**
1. Settings → Rules → Rulesets → New branch ruleset for `main`: require a pull request and require the status checks `lint` and `test (3.12)` etc.
2. Create a branch `feature/break-a-test`, change an expected value in `tests/test_transform.py`, push and open a PR.
3. Watch the PR get blocked, then fix it and merge.

**Why:** CI is only useful if it can **stop** bad changes. This is where workflows become a team process.
**Learn**
- The difference between `push` and `pull_request` events (PR runs test the *merge result*, `github.ref` is `refs/pull/N/merge`).
- Required checks are matched **by job name**. If you rename a job, the check silently goes missing ("Expected — Waiting for status"). A classic pitfall.
- Bonus: add `paths-ignore: ["**.md"]` to CI and think about why that can block PRs that only change docs when checks are required.

**GitLab equivalent:** protected branches + "Pipelines must succeed" in MR settings.
**Done when:** A red PR could not be merged, and a green one was merged.

---

## Step 5: A real multi-job pipeline with artifacts and outputs (1.5 h)

**File:** `.github/workflows/pipeline.yml`

**Build:** four jobs chained with `needs:`

```
extract ──► transform ──► check ──► report
```

- `extract`: `uv run weather-pipeline extract --city berlin --days 7` → upload `data/raw.json` as artifact `raw`.
  - Also write the row count to a **job output**: `echo "rows=…" >> "$GITHUB_OUTPUT"` (the CLI prints `rows=<n>`), and expose it under `jobs.extract.outputs`.
- `transform`: download `raw` → `uv run weather-pipeline transform` → upload `clean` (`data/clean.csv`).
- `check`: download `clean` → `uv run weather-pipeline check`. A failing check fails the job and stops `report`.
- `report`: download `clean` → `uv run weather-pipeline report` → upload `site/` as artifact `report`. Print `needs.extract.outputs.rows` in the summary.
- Trigger for now: `workflow_dispatch` and `push` to `main`.

**Why:** This is the classic shape of a data pipeline: stages with explicit hand-offs. It forces you to understand that jobs are isolated machines.
**Learn**
- `needs:` creates a DAG (like GitLab's `needs:`, but there are **no stages**).
- Artifacts are the only way to pass *files* between jobs. Job outputs pass small *values*.
- `if: always()` / `if: failure()`: add a `notify` job that runs only when something failed.
- Download the final `report` artifact from the run page and open it.

**GitLab equivalent:** stages + `artifacts:` + `dependencies:`/`needs:`, and `dotenv` reports for passing variables.
**Try breaking it:** Run `extract` with `--days 1`. The `check` job fails ("enough rows: 1 rows, need >= 3") and the DAG stops before `report`.
**Done when:** The graph shows 4 chained jobs and you've downloaded the report.

---

# Day 2: Triggers, secrets, deployment, reuse

## Step 6: Schedules and manual inputs (1 h)

**File:** extend `pipeline.yml`

**Build**
- `on: schedule: - cron: "0 6 * * *"` (06:00 **UTC**, i.e. 07:00/08:00 Berlin).
- `workflow_dispatch:` with inputs:
  - `city`: `type: choice`, options `berlin`, `hamburg`, `munich`, `cologne`
  - `days`: `type: number`, default `7`
- Use `${{ inputs.city || 'berlin' }}`, because on scheduled runs `inputs` is empty, so you need a fallback.
- Use `run-name:` to make runs readable, e.g. `Pipeline – ${{ inputs.city || 'berlin' }}`.

**Why:** Data pipelines run on time *and* on demand (backfills, other parameters).
**Learn**
- Cron is UTC, runs only on the **default branch**, may be delayed under load, and is **disabled after 60 days of repo inactivity**.
- The same workflow behaves differently per `github.event_name`. Use `if:` to branch on it.
- Inputs are strings in shell; `type:` only affects the UI.

**GitLab equivalent:** pipeline schedules + "Run pipeline" with variables / `spec:inputs`.
**Done when:** A manual run for `hamburg` worked and the schedule appears in the workflow page.

---

## Step 7: Secrets, variables and environments (1 h)

**Do**
1. Settings → Secrets and variables → Actions:
   - **Variable** `REPORT_TITLE` = `My Weather Report`
   - **Secret** `DUMMY_API_TOKEN` = anything
2. Settings → Environments → create `production` with **yourself as required reviewer**.
3. In `pipeline.yml`:
   - Pass `${{ vars.REPORT_TITLE }}` to `report --title`.
   - In a step, map the secret into an env var and `echo` it. Notice it's masked as `***`.
   - Make the `report` job use `environment: production` and approve the run manually.

**Why:** Real pipelines need credentials and controlled promotion to production.
**Learn**
- `vars` (plain config) vs `secrets` (encrypted, masked, never shown again).
- Repository vs environment scope: the same secret name can have different values per environment.
- Secrets are **not** passed to workflows triggered from forks. Think about why that's a security feature.
- Pass secrets via `env:`, not inline `${{ secrets.X }}` inside shell commands.

**GitLab equivalent:** masked/protected CI/CD variables, protected environments with approvals.
**Done when:** A run waited for your approval and the secret appears only as `***`.

---

## Step 8: Publish the report to GitHub Pages (1 h)

**File:** extend `pipeline.yml` (or a new `deploy.yml`)

**Do:** Settings → Pages → Source: **GitHub Actions**.

**Build**
- In `report`: replace the plain artifact upload with `actions/upload-pages-artifact@v3` (path `site/`).
- New job `deploy`: `needs: report`, `environment: { name: github-pages, url: ${{ steps.deployment.outputs.page_url }} }`, and step `actions/deploy-pages@v4` with `id: deployment`.
- Add `permissions:` → `pages: write`, `id-token: write`, `contents: read`.
- Only deploy from `main` (`if: github.ref == 'refs/heads/main'`).

**Why:** It's a real deployment with a visible result, and it forces you to deal with token permissions.
**Learn**
- `GITHUB_TOKEN` gets **minimal permissions**. You declare what each workflow or job needs (least privilege).
- `id-token: write` = OIDC, the same mechanism you'd use to deploy to AWS without stored keys.
- Step `id:` + `steps.<id>.outputs` for using outputs within a job.

**GitLab equivalent:** the `pages` job with `artifacts: paths: [public]`.
**Done when:** Your daily weather report is live at `https://<user>.github.io/action-testing/`.

---

## Step 9: Don't repeat yourself, composite actions and reusable workflows (1.5 h)

By now "checkout → setup-uv → uv sync" appears in many jobs.

**Build A: composite action** `.github/actions/setup-project/action.yml`
- `runs: using: composite`, with steps for setup-uv and `uv sync --locked`, and an input `python-version`.
- Replace the repeated steps everywhere with `uses: ./.github/actions/setup-project` (after checkout).

**Build B: reusable workflow** `.github/workflows/_quality.yml`
- `on: workflow_call` with an input `python-versions` (JSON string → `fromJSON()` in the matrix).
- Move lint + test into it, and make `ci.yml` just `uses: ./.github/workflows/_quality.yml`.

**Why:** In real organizations, CI logic is shared across many repos. Knowing which tool to use for which level of reuse is key.
**Learn**
- **Composite action** = reusable *steps* (runs inside the caller's job).
- **Reusable workflow** = reusable *jobs* (own runners, own matrix, can take secrets via `secrets: inherit`).
- Rule of thumb: steps → composite action, entire pipelines → reusable workflow.

**GitLab equivalent:** composite action ≈ YAML anchors / `extends:`; reusable workflow ≈ `include:` of a template or CI/CD component.
**Done when:** `ci.yml` is under 15 lines and everything is still green.

---

## Step 10: Hardening and housekeeping (45 min)

**Build**
- Top-level `permissions: contents: read` in every workflow (least privilege by default).
- `.github/dependabot.yml` with the `github-actions` ecosystem (weekly). Dependabot opens PRs to bump your actions.
- Pin one third-party action to a full commit SHA (`uses: astral-sh/setup-uv@<sha> # v6.x`) and understand why: tags can be moved, SHAs can't.
- Add a CI status badge to `README.md`.

**Why:** Workflows run code from the internet with access to your repo. Supply-chain hygiene is part of doing CI properly.
**Learn:** Security model of actions, Dependabot, why `pull_request_target` is dangerous.
**Done when:** The badge is green and Dependabot has been configured.

---

## Stretch goals (if time is left)

- **Run locally with [`act`](https://github.com/nektos/act):** a fast feedback loop without pushing.
- **Matrix over cities** in the pipeline, plus combining the results into one report.
- **Release on tag:** `on: push: tags: ["v*"]` → build a wheel with `uv build` → create a GitHub Release with the wheel attached.
- **Docker image to GHCR:** `docker/build-push-action` with `packages: write`.
- **Debugging:** re-run a job with "Enable debug logging", and learn about `ACTIONS_STEP_DEBUG`.

---

## Suggested schedule

| Time | Day 1 | Day 2 |
|---|---|---|
| 09:00 | Step 0 + Step 1 | Step 6 (schedules & inputs) |
| 10:30 | Step 2 (CI) | Step 7 (secrets & environments) |
| 12:00 | *lunch* | *lunch* |
| 13:00 | Step 3 (matrix) + Step 4 (PR gating) | Step 8 (Pages) |
| 14:30 | Step 5 (multi-job pipeline) | Step 9 (reuse) |
| 16:30 | Recap: write down 3 GitLab↔GitHub differences | Step 10 + stretch goals |

## Useful docs

- Workflow syntax: https://docs.github.com/actions/writing-workflows/workflow-syntax-for-github-actions
- Contexts (`github`, `inputs`, `needs`, …): https://docs.github.com/actions/writing-workflows/choosing-what-your-workflow-does/accessing-contextual-information-about-workflow-runs
- Events that trigger workflows: https://docs.github.com/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows
- Migrating from GitLab: https://docs.github.com/actions/migrating-to-github-actions/manually-migrating-to-github-actions/migrating-from-gitlab-cicd-to-github-actions
- setup-uv: https://github.com/astral-sh/setup-uv
