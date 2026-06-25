# GitHub Actions Workflow Inventory — Phase 1

- lifecycle: permanent
- owner: project governance
- created: 2026-06-25
- updated: 2026-06-25 (permissions hardening applied)
- task: github_actions_workflow_inventory_phase1
- audit_type: static inventory / documentation / low-risk audit
- sc002_status: enforcement infrastructure complete

## Permissions Hardening Status

**✅ Applied (2026-06-25):** `production-gate.yml` now has an explicit least-privilege
`permissions:` block at the workflow level.

```yaml
permissions:
  contents: read        # for actions/checkout@v4
  actions: write        # for actions/cache@v4 (cache save)
  pull-requests: read   # for gh pr view on PR events
```

**No write scopes granted beyond what is operationally required.** Specifically:
- No `contents: write`
- No `pull-requests: write`
- No `issues: write`
- No `deployments: write`
- No `packages: write`
- No `id-token: write`

This change reduces the default `GITHUB_TOKEN` scope from permissive to minimal,
following the principle of least privilege. Workflow behavior, triggers, job steps,
and logic are unchanged.

See PR [#1626](https://github.com/xupeng211/FootballPrediction/pull/1626)
(`github_actions_workflow_permissions_hardening`) for implementation details.

---

This document is a **low-risk static inventory** of all GitHub Actions workflow files
in `.github/workflows/`. It catalogs each workflow's triggers, jobs, security surface,
and risk profile — without modifying any workflow behavior, triggers, permissions,
secrets, or Docker logic.

**This task did NOT:**
- Change workflow behavior
- Delete or rename any workflow
- Modify triggers, secrets, permissions, or runners
- Continue staging deployment
- Connect to any database
- Execute any SQL
- Run scraper / browser / Playwright
- Train or expand data
- Perform real DB write

SC-002 enforcement infrastructure remains complete.
Training / data expansion / real DB write remain blocked.

---

## 1. Workflow 总览表 (Workflow Summary Table)

**Total workflow files: 1**

| # | 文件名 | Workflow Name | 触发方式 | PR Gate | Production / Main Gate | Category | 关键 Job | Uses Secrets | Uses Docker | Runs Tests | May Connect DB | May Execute SQL | May Run Scraper/Browser | May Train/Expand Data | Risk Level | Recommended Action |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `production-gate.yml` | Production Gate | `push` (main), `pull_request` | **Yes** | **Yes** | CI Gate (dual-role) | `production-gate` (Environment / Proxy / Static / Unit Gate), `docker-build` (Docker Build Validation) | Yes (`github.token` for `gh pr view`) | Yes (Docker Buildx, dev container image) | Yes (via gatekeeper.sh) | Yes (gatekeeper cold-start probes via `docker compose up -d dev db redis`) | Yes (gatekeeper `runColdStartBlueprintCheck` executes CREATE DATABASE / DROP DATABASE / INSERT probes) | No | No | **Medium** | keep |

### Detailed workflow analysis

#### `production-gate.yml` — Production Gate

**Trigger:** `push` on `main` + `pull_request` (all branches).

**Concurrency:** Group `production-gate-${{ github.workflow }}-${{ github.ref }}`, cancel-in-progress enabled.

**Job 1: `production-gate`** (Environment / Proxy / Static / Unit Gate)
- Timeout: 30 minutes
- Steps:
  1. Checkout code (`actions/checkout@v4`, fetch-depth: 0)
  2. Prepare CI cache directories
  3. Restore dependency cache (`actions/cache@v4`)
  4. Restore Docker layer cache (`actions/cache@v4`)
  5. Set up Docker Buildx (`docker/setup-buildx-action@v3`)
  6. Warm dev image cache (`docker buildx build` of `.devcontainer/Dockerfile`)
  7. Rotate Docker layer cache
  8. Print resolved dev environment (docker compose config)
  9. CI Environment Diagnostics (`docker compose up -d dev db redis` + network probe)
  10. Install project dependencies (`npm ci` + verify critical deps including playwright, pg, nock)
  11. Run Gatekeeper (`bash scripts/devops/gatekeeper.sh --mode=${GATEKEEPER_CI_MODE}`)
  12. AI Workflow Gate (P0) — fetches PR body via `gh pr view`, runs `scripts/ops/ai_workflow_gate.py`

**Job 2: `docker-build`** (Docker Build Validation)
- Timeout: 30 minutes
- Depends on: `production-gate`
- Steps:
  1. Checkout code
  2. Set up Docker Buildx
  3. Build production image (`docker buildx build --file Dockerfile`)

**Secrets used:** `${{ github.token }}` (for `gh pr view` in AI Workflow Gate step).

**Docker surface:** Dev container image build + production image build. DB and Redis services started via `docker compose` for CI diagnostics and gatekeeper probes.

**DB connection:** Yes — gatekeeper cold-start blueprint probes connect to the dev DB container and execute CREATE DATABASE, DROP DATABASE, INSERT on `matches`, `raw_match_data`, `matches_oddsportal_mapping`.

**SQL execution:** Yes — gatekeeper `runColdStartBlueprintCheck` executes DDL (CREATE DATABASE, DROP DATABASE) and DML (INSERT) as CI health probes against the ephemeral CI DB container.

**Scraper/browser:** No. Playwright is installed as a dependency (verified in step "Install project dependencies") but is NOT executed during CI. The gatekeeper does not trigger browser automation.

**Training/data expansion:** No. The gatekeeper runs static checks, linting, unit tests, and CI health probes only. No training scripts or data expansion pipelines are invoked.

**Risk assessment — Medium:**
- **Rationale:** The workflow starts real DB containers and executes SQL DDL/DML as part of CI health probes. While these are against ephemeral CI containers (not production), the CREATE DATABASE / DROP DATABASE operations mean this workflow is not purely read-only.
- **Mitigations:** All guard scripts (gatekeeper.js, gatekeeper.sh) have `assertDbWriteAllowed()` guards. CI DB is ephemeral and destroyed after the run. Production-like hosts are hard-blocked by the guard.
- **Why not High:** No scraper/browser, no training, no data expansion. DB operations are scoped to CI health probes only.
- **Why not Low:** Real Docker containers with real PostgreSQL are spun up; SQL DDL/DML is executed; this is not a purely static/read-only CI pipeline.

---

## 2. Gate 边界说明 (Gate Boundary Clarification)

### What is the PR Gate?

The PR Gate is the CI check that runs on every pull request. It is the **same** `production-gate.yml` workflow triggered by `pull_request`. For PR events:
- `GATEKEEPER_CI_MODE` = `pr`
- The gatekeeper runs PR-mode validation (linting, tests, static analysis)
- The AI Workflow Gate fetches the PR body via `gh pr view` and validates it against required sections, forbidden patterns, and safety claims

### What is the Production Gate / Main Gate?

The Production Gate is the CI check that runs on every push to `main`. It is the **same** `production-gate.yml` workflow triggered by `push` on `main`. For push events:
- `GATEKEEPER_CI_MODE` = `push`
- The gatekeeper runs full-mode validation
- The AI Workflow Gate runs git-diff-based checks only (no PR body)

### One workflow, dual role

The single `production-gate.yml` workflow serves **both** the PR Gate and the Production (main) Gate. The behavioral difference is controlled by `GATEKEEPER_CI_MODE` (set from `github.event_name`):
- `pull_request` → `pr` mode
- `push` (on main) → `push` mode

### Blocking vs. auxiliary

| Workflow | Blocking Gate? | Notes |
|---|---|---|
| `production-gate.yml` (job: `production-gate`) | **Yes** | Required check for PR merge. Must pass before merge. |
| `production-gate.yml` (job: `docker-build`) | **Yes** | Required check for PR merge. Depends on `production-gate`. |

There are **no auxiliary or non-blocking workflows** in this repository. The single workflow is the sole CI gate.

### Which workflows should NOT be treated as the main Gate by Claude Code?

All checks in this repo run through `production-gate.yml`. There is no ambiguity — Claude Code should treat this single workflow as both the PR Gate and the main Gate.

---

## 3. 重复/重叠检查 (Overlap/Duplication Check)

### Multiple workflows doing the same check?

**No.** There is only 1 workflow file. No duplication exists.

### Duplicate dependency installation?

**No.** Dependencies are installed once in the `production-gate` job (Step 10: `npm ci`). The `docker-build` job only builds the production Docker image and does not install dependencies separately.

### Duplicate Docker build?

The workflow builds **two different Docker images**, which is not duplication:
1. **Dev container image** (`production-gate` job): `.devcontainer/Dockerfile` — used for running gatekeeper checks inside the dev environment
2. **Production image** (`docker-build` job): `Dockerfile` — validates that the production image can be built

Both are necessary and serve different purposes.

### Duplicate lint/test?

**No.** Linting and testing run once through the gatekeeper in the `production-gate` job.

### Ambiguous job names?

**No.** Job names are clear:
- `production-gate`: The main CI gate (environment validation, static analysis, unit tests, AI workflow gate)
- `docker-build`: Docker production image build validation

---

## 4. 过时/历史遗留检查 (Stale/Legacy Check)

### Possibly unused workflows?

**None.** The single workflow is actively used and is the sole CI gate for all PRs and main-branch pushes.

### Inconsistencies with Makefile / CLAUDE.md / AI workflow hardening?

**No inconsistencies detected:**

| Source | Reference | Consistency |
|---|---|---|
| CLAUDE.md (§CI Watch Command) | `make watch-pr PR=<number>` watches `production-gate.yml` checks | Consistent |
| CLAUDE.md (§Local PR Gate Preflight) | `make pr-gate-local` simulates `production-gate.yml` validation locally | Consistent |
| Makefile (`ci-local`, `pr-gate-local`) | Gatekeeper integration matches workflow | Consistent |
| `docs/AI_AGENT_WORKFLOW_HARDENING.md` | PR lifecycle references remote CI via `make watch-pr` | Consistent |
| `.github/pull_request_template.md` | Required sections match AI Workflow Gate validation | Consistent |

### Name vs. actual responsibility mismatch?

**No.** "Production Gate" accurately describes the workflow's role: it gates both PRs and pushes to `main` (production branch).

### Schedule review?

**No scheduled workflows exist.** The only trigger types are `push` (main) and `pull_request`. There are no `schedule` (cron), `workflow_dispatch`, or other trigger events.

**Note:** The absence of scheduled maintenance workflows (e.g., nightly dependency audit, stale branch cleanup, cache warming) is a gap — see Follow-ups §6.4.

---

## 5. 安全边界检查 (Security Boundary Check)

### Workflow-level security surface

| Check | `production-gate.yml` | Notes |
|---|---|---|
| Uses secrets? | Yes | `${{ github.token }}` for `gh pr view` only |
| Connects to DB? | Yes | CI ephemeral DB container (PostgreSQL via docker compose) |
| Executes SQL? | Yes | Gatekeeper cold-start probes: CREATE DATABASE, DROP DATABASE, INSERT |
| Runs docker compose? | Yes | `docker compose -f docker-compose.dev.yml up -d dev db redis` |
| Runs scraper/browser/Playwright? | No | Playwright is installed as dep but not executed |
| Executes training/data expansion? | No | No training or data pipeline scripts invoked |
| Has write access to main? | Indirect | Push to main triggers the workflow; workflow does not push code |
| Uploads artifacts? | No | No `actions/upload-artifact` steps |
| Publishes images or deploys? | No | Production image is built but not pushed or deployed |
| Uses third-party actions? | Yes | `actions/checkout@v4`, `actions/cache@v4`, `docker/setup-buildx-action@v3` — all from trusted GitHub/ Docker organizations |

### Detailed security assessment

**Secrets exposure risk: Low**
- Only `${{ github.token }}` is used, and only for `gh pr view` (read-only PR metadata)
- No custom secrets, no deployment keys, no cloud credentials
- Token is auto-generated by GitHub Actions per-run

**DB connection risk: Low**
- DB connection is to an ephemeral CI PostgreSQL container (`db` service in docker-compose.dev.yml)
- Container is destroyed after the CI run
- The `football_gatekeeper` role (POC) has SELECT-only + CREATEDB for temp probes
- Production-like DB hosts are hard-blocked by guard scripts

**SQL execution risk: Low**
- All executed SQL is via guarded entrypoints (`gatekeeper.js`, `gatekeeper.sh` have `assertDbWriteAllowed()`)
- SQL is scoped to CI health probes only
- No migration execution, no schema changes to persistent databases
- CI ephemeral DB is isolated from staging/production

**Docker compose risk: Low**
- Only dev compose file is used (`docker-compose.dev.yml`)
- No production compose, no staging compose
- Containers are ephemeral and scoped to the CI run

**Scraper/browser risk: None**
- Playwright is installed as a dependency verification step only
- No browser automation is triggered by the workflow
- No network data collection is performed

**Training/data expansion risk: None**
- No training scripts are invoked
- No data pipelines are triggered
- No `ALLOW_TRAINING_WRITE` or data expansion env vars are set

---

## 6. 推荐 Follow-ups (Recommended Follow-ups)

These are **recommendations only**. None are executed by this task.
Each requires separate authorization and should not be started automatically.

### 6.1 `github_actions_workflow_cleanup_phase2`

**Not applicable** — there is only 1 workflow with no duplication or staleness to clean up.
However, if future workflows are added, this task should be re-run to maintain the inventory.

### 6.2 `ci_gate_naming_standardization`

**Low priority.** The single workflow uses the name "Production Gate" for a workflow that serves both PR and Production Gate roles. While functional, the naming could be clarified:
- Option A: Rename to "CI Gate" or "PR & Production Gate" to reflect the dual role
- Option B: Split into separate `pr-gate.yml` and `production-gate.yml` workflows (higher effort, more maintenance)
- **Recommendation:** Keep current naming. It accurately reflects the gate's primary role (protecting `main`). The fact that it also serves as PR Gate is implicit in the `pull_request` trigger.

### 6.3 `workflow_permissions_hardening`

**Medium priority.** The workflow does not set explicit `permissions:` at the top level. GitHub Actions defaults to permissive permissions. Recommendation:
- Add explicit `permissions:` block to limit the `GITHUB_TOKEN` scope:
  ```yaml
  permissions:
    contents: read
    pull-requests: read
  ```
- The `docker-build` job needs no token permissions at all
- This follows the principle of least privilege for CI tokens

### 6.4 `scheduled_workflow_review`

**Medium priority.** There are no scheduled (cron) workflows. Consider adding:
- **Nightly dependency audit:** `npm audit` + `pip audit` to detect vulnerable dependencies
- **Weekly stale branch cleanup:** Identify and report stale branches
- **Cache warming:** Periodic cache refresh to keep CI fast
- None of these should modify code, delete branches, or write to DB automatically

### 6.5 `legacy_workflow_deprecation_plan`

**Not applicable** — there are no legacy workflows to deprecate.

### 6.6 `workflow_runtime_cost_reduction`

**Low priority.** The single workflow has a 30-minute timeout per job (60 minutes total worst case). Observations:
- Docker image build (both dev and production) dominates runtime
- Cache restoration is already implemented (`actions/cache@v4` for deps + Docker layers)
- If CI runtime consistently exceeds 15-20 minutes, consider:
  - Slimmer dev container image
  - Pre-built CI runner images with cached layers
  - Splitting static checks (fast) from Docker build validation (slow)

---

## 7. 当前结论 (Current Conclusions)

1. **This task did NOT change CI behavior.** No workflow YAML was modified.
2. **This task did NOT continue staging deployment.** Staging deployment remains paused.
3. **This task did NOT connect to any database.** All analysis is static / file-read only.
4. **This task did NOT execute any SQL.** No `psql`, no migration, no Alembic, no DB interaction.
5. **This task did NOT train, expand data, or write to any database.** Training and data expansion remain blocked.
6. **SC-002 enforcement infrastructure remains complete.** No guard or enforcement was modified.
7. **Training / data expansion / real DB write remain blocked.** No gates were opened.
8. **The repository has exactly 1 GitHub Actions workflow** (`production-gate.yml`) serving dual PR Gate + Production Gate roles.
9. **The workflow is well-structured** with no duplication, no staleness, and clear job separation.
10. **Risk level is Medium** due to real DB container startup and SQL execution (CI health probes). All DB operations are scoped to ephemeral CI containers and guarded.
11. **No scheduled, legacy, or auxiliary workflows exist.** The CI surface is minimal and well-defined.

---

## Appendix A: Files Analyzed

| File | Purpose |
|---|---|
| `.github/workflows/production-gate.yml` | Sole CI workflow — full deep read |
| `scripts/devops/gatekeeper.sh` | Gatekeeper orchestration script — partial read (first 300 lines) |
| `CLAUDE.md` | Agent workflow rules — full read |
| `AGENTS.md` | AI assistant handbook — partial read (first 100 lines) |
| `Makefile` | Build orchestration — partial read (CI section) |
| `docs/AI_AGENT_WORKFLOW_HARDENING.md` | CI discipline rules — full read |
| `docs/PROJECT_STATUS.md` | Current project state — full read |
| `docs/SC002_FINAL_CLOSURE_CHECK.md` | SC-002 closure verification — full read |
| `docs/SC002_CLOSURE_PLAN.md` | SC-002 closure criteria — full read |
| `tests/unit/test_ai_workflow_gate.py` | Gate test reference — partial read |
| `tests/unit/test_agent_workflow_hardening.py` | Hardening test reference — partial read |
| `tests/unit/test_agent_workflow_hardening_phase1_ci_rules.py` | CI rules test reference — partial read |

## Appendix B: Verification Commands

```bash
# Verify workflow file count
ls .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null | wc -l

# Verify gatekeeper integration
grep -n "gatekeeper.sh" .github/workflows/production-gate.yml

# Verify AI Workflow Gate integration
grep -n "ai_workflow_gate.py" .github/workflows/production-gate.yml

# Verify no schedule/cron triggers
grep -r "schedule:" .github/workflows/ || echo "No scheduled workflows"

# Verify no workflow_dispatch triggers
grep -r "workflow_dispatch:" .github/workflows/ || echo "No manual dispatch workflows"
```
