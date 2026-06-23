# Claude Code Project Instructions

- lifecycle: permanent / agent-entrypoint

## Read order

Before working on this repository, treat the following files as the authoritative workflow sources:

1. AGENTS.md
2. docs/AGENT_WORKFLOW.md
3. .github/pull_request_template.md
4. docs/data/FOTMOB_CURRENT_STATE.md

Do not rely on historical ADG reports as the primary current truth. Use docs/data/FOTMOB_CURRENT_STATE.md for the latest FotMob ingestion state.

## Container-first

All Node.js / Python commands run inside the dev container: `docker compose -f docker-compose.dev.yml exec dev <command>`. Never run business logic directly on the host. Use `make dev-up` / `make dev-shell` for environment setup. See AGENTS.md §4 for details.

## Core rules

- Implementation PRs must include real runtime behavior change.
- Planning / governance PRs must not pretend to be implementation.
- Data / ingestion work is no-write by default.
- Do not perform live fetch, network request, DB write, raw write, re-acceptance, suspension reversal, source inventory production mutation, or candidate production mutation unless explicitly authorized.
- Do not save or print full HTML, pageProps, raw_data, or source body.
- Every PR must include Repository Hygiene / Debt Impact.
- Every new file must have a lifecycle.
- One-shot helpers are cleanup candidates unless future reuse is documented.
- Prefer current-state updates over creating long historical reports.
- Keep reports and manifests minimal.

## FotMob current state

Read docs/data/FOTMOB_CURRENT_STATE.md before any FotMob ingestion task.

Current high-level status:

- raw_write_ready_count is 0.
- Existing source-controlled artifacts cannot generate corrected Ligue 1 source inventory records.
- The next data step is bounded corrected-source discovery, only after workflow hygiene is merged and explicitly authorized.

## MCP permissions

| Server | Permission | Allowed |
|--------|-----------|---------|
| postgres | READ-ONLY | SELECT / DESCRIBE / EXPLAIN |
| filesystem | PROJECT ROOT | read / diff / controlled write |
| git | READ-ONLY | commit history / diff / blame |
| pytest | RESTRICTED | run pytest / list tests |

MCP does not own production control. No irreversible or high-risk automation via MCP.

## Claude Skills

Project has 12+ dedicated Skills (see `.claude/README.md`). Use Skill tool for specialized tasks (football-prediction, data-collection, code-quality, etc.).

## Agent Workflow Hardening

These rules are non-negotiable. They exist so AI agents working in this repo do not need repeated long-form prompts to enforce basic discipline. Detailed reference: `AGENTS.md`.

### 1. Branch discipline

- **Never work directly on main.** Always create a feature branch from clean latest `origin/main`.
- Always start from clean latest `origin/main`. Verify `HEAD == origin/main` before branching.
- **If main is red** (Production Gate failure), stop all feature work and fix main first. Do not start new branches from a red main.
- Delete remote branch after merge.

### 2. Scope discipline

- **Prefer minimal diffs.** Do not expand scope without explicit user instruction.
- Do not rewrite existing modules unless explicitly requested.
- **Do not create V2 / FINAL / rewritten / replacement / backup duplicates** to replace old code. This applies to file naming patterns: `*_v2.py`, `*_v2.js`, `*_new.py`, `*_new.js`, `*_final.py`, `*_final.js`, `*_rewritten.py`, `*_rewritten.js`, `*_replacement.py`, `*_replacement.js`, `*_backup.py`, `*_backup.js`.
- Do not delete or move historical code without an explicit cleanup task with declared scope.
- Do not perform mass refactoring or large-scale code movement without explicit authorization.

### 3. Safety discipline

- **Do not run DB write scripts.** Do not execute INSERT/UPDATE/DELETE/TRUNCATE/CREATE/DROP/ALTER.
- **Do not run SQL / migrations.** No `ALTER TABLE`, no `flyway`, no `alembic upgrade`, no schema changes.
- **Do not connect to DB** for write operations. SELECT-only MCP access is permitted for auditing.
- **Do not run scraper / browser / Playwright.** No live HTTP fetch, no headless browser, no network data collection.
- **Do not train or expand data.** No model training, no data expansion, no raw data acquisition.
- Do not execute `DRY_RUN=false` or `FINAL_DB_WRITE_CONFIRMATION=yes` target scripts unless explicitly authorized by the user with clear scope and confirmation.

### 4. SC-002 discipline

- **SC-002 is partial mitigation only.** It is not complete until all closure criteria in `docs/SC002_CLOSURE_PLAN.md` are satisfied.
- **Do not claim SC-002 is complete** or fully fixed.
- **Do not claim training / data expansion / real DB write are unblocked.** They remain blocked.
- **Allowlist is historical baseline, not safety approval.** Being in an allowlist does not authorize execution.
- **Guarded means gated, not authorized to execute.** A guard script blocks by default; it does not grant permission.
- Remaining: 11 confirmed Python write paths, 8 indirect write paths, 5 manual review candidates are **NOT addressed** by this hardening task.

### 5. PR discipline

- Every PR must include these sections in the body:
  - `## Summary`
  - `## Scope`
  - `## Files Changed`
  - `## Safety Impact`
  - `## Validation`
  - `## CI Gate Scope`
  - `## No deletion / no move / no rename confirmation`
  - `## SC-002 status`
  - `## Remaining risks`
  - `## Next Recommended Task`
- Every PR must state whether DB / migration / scraper / browser / training was executed.
- `## Next Recommended Task` must contain: "Do not start automatically." and "Recommended next task only after user confirmation:".
- **Post-merge main Production Gate must be green** before the task is considered complete.
- If post-merge main Gate fails, open a minimal hotfix immediately. Do not start new feature work until main is green.

### 6. Task type discipline

| Task type | Allowed | Forbidden |
|---|---|---|
| **design phase** | planning, static analysis, docs, SELECT-only audit | runtime code change, DB write, training, live fetch |
| **scanner phase** | static scanning, allowlist management, CI enforcement | runtime guard implementation, DB write, live fetch |
| **guard phase** | guard integration, test updates, allowlist updates | new feature code, schema migration, training, data expansion |
| **hotfix phase** | minimal fix for gate/test failure | scope expansion, new features, refactoring |
| **cleanup phase** | explicit delete/move/rename within declared scope only | mass delete without explicit authorization, expanding beyond declared targets |
| **documentation-only phase** | docs, templates, manifests, governance files | runtime code, DB, scraper, browser, training, data |

### 7. Post-merge discipline

- Verify post-merge main Production Gate is green.
- If main Gate is red, open minimal hotfix immediately.
- Do not start new feature work until main is green again.
- Delete remote branch after merge is confirmed.

## Validation expectations

Before proposing completion:

- run relevant targeted tests;
- run lint / formatting checks when reasonable;
- run hidden/bidi and payload marker checks if touched files require them;
- report failures honestly;
- do not fake passing tests.
