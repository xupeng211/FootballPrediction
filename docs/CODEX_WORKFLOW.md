# Codex Workflow

- lifecycle: permanent
- owner: Codex workflow governance

## Core Rules

- Never develop directly on `main`.
- Use one branch per task.
- Use one PR per task.
- One task must not combine feature work with cleanup, audit with repair, merge
  with new work, or documentation governance with business code.
- Read current source-of-truth docs before starting a task.
- Before finishing a task, decide whether active conclusions need to be
  reflected in source-of-truth docs.
- Default to adding no documents.
- Default to adding no manifests.
- Default to adding no review reports.
- Default to adding no next-plan reports.
- Prefer updating existing source-of-truth docs.
- Include Documentation Impact in every PR.
- Include Safety Impact in every PR.
- Include Validation in every PR.
- Keep `git status` clean after commit.
- Do not continue a paused feature stream when the task is governance-only.
- Do not treat adding a report as task completion unless the source-of-truth
  backflow decision is also handled.
- Do not start the next recommended task automatically. Every final report must
  say "Do not start automatically" and that the recommended next task requires
  user confirmation.

## Task Types

### 1. Feature Task

Default maximum budget:

- 0-1 doc
- 0 manifest
- 1 test file

Feature tasks should focus on runtime behavior and behavior tests. Documentation
should explain the change, not replace it.

### 2. Research / Discovery Task

Default maximum budget:

- 1 report
- 1 manifest
- 1 checker
- 1 test file

Discovery tasks must state no-write and no-network boundaries when applicable.
The report should summarize findings instead of copying full raw evidence.

### 3. Governance Task

Default maximum budget:

- 2 docs
- 1 report
- 1 checker
- 1 test file

Governance tasks may define rules, templates, and checkers. They must not claim
business progress unless runtime behavior also changed.

### 4. Cleanup Task

Cleanup tasks must:

- start with a no-deletion plan
- update source-of-truth summaries first
- archive only after review
- not directly delete evidence by default

## Mandatory PR Body Sections

Every PR body must include:

- Summary
- Scope
- Files Changed
- Documentation Impact
- Safety Impact
- Validation
- CI Gate Scope
- No deletion / no move / no rename confirmation
- Rollback Plan
- Next Recommended Task

When a PR adds or modifies `docs/_reports/*.md`, the PR body must also state:

- whether a `docs/_reports` artifact was added or modified
- whether source-of-truth docs were updated
- which authoritative docs were updated
- if not updated, a concrete no-update reason
- whether active conclusions were reflected in `docs/PROJECT_STATUS.md`

The CI Gate Scope section must state what validation proves and does not prove.
Production Gate success does not prove full-system coverage, model/data quality,
or safety for unscoped runtime, DB, browser, scraper, or network work. Host
validation that is unavailable must be reported separately from container
validation.

## Documentation Creation Decision Tree

Before Codex creates a document, answer:

1. Is there an existing source-of-truth document that should be updated instead?
2. Is there an existing report that can be extended instead?
3. Will this document still be useful 30 days from now?
4. Is it only being created to prove process activity?
5. Will it duplicate an existing conclusion?
6. Does it need an explicit lifecycle status?
7. Should the conclusion be written into a source-of-truth doc instead?

Only create the document when the answers justify a new file.

## Prohibited Habits

Codex must not:

- create report/review/decision/next-plan bundles for every phase
- pair every script with a manifest by default
- add reports without lifecycle status
- repeat the same conclusion across multiple new files
- treat a machine manifest as a human status document
- put temporary exploration files in the main docs tree
- skip source-of-truth updates while adding more reports
- use a new report as a substitute for updating `docs/PROJECT_STATUS.md`
- use PR body reports as the only durable documentation
- create `PROJECT_STATUS_V2.md`, `NEW_WORKFLOW.md`, `NEW_RULES.md`, or similar
  new authority entrypoints to avoid maintaining existing docs
- use broad report allowlists such as `docs/_reports/*.md`,
  `docs/_reports/*AUDIT*.md`, `docs/_reports/*NEXT_PLAN*.md`,
  `docs/_reports/*REVIEW*.md`, or `docs/_reports/*DECISION*.md`
- create reports, manifests, next-plan files, review reports, or decision
  reports unless the task explicitly allows the exact path

## Current Project Source of Truth

Recommended source-of-truth docs:

| Path | Status | Codex action |
|---|---|---|
| docs/PROJECT_STATUS.md | active | Read before status-sensitive tasks; update when active blockers change. |
| docs/DATA_SOURCE_STRATEGY.md | active | Read before data-source strategy tasks. |
| docs/FOTMOB_CURRENT_STATE.md | planned | Prefer root-level state after cleanup. |
| docs/data/FOTMOB_CURRENT_STATE.md | exists/needs_update | Read for current FotMob state. |
| docs/CANONICAL_MATCH_SCHEMA.md | planned | Create after schema direction is approved. |
| docs/DOCUMENTATION_GOVERNANCE.md | exists | Read before documentation-heavy tasks. |
| docs/CODEX_WORKFLOW.md | exists | Read before every Codex task. |
| docs/DEVELOPMENT_WORKFLOW.md | planned | Create only when explicitly scoped. |

If a source-of-truth doc is missing, mark it planned. Do not create it as a side
effect of an unrelated task.

## Active Workflow After Phase1

After Phase1, Codex must treat documentation governance as the active blocker
before restarting FotMob payload work.

Current order:

1. Keep source-of-truth summaries current.
2. Prepare a no-deletion, no-move archive candidate marking phase.
3. Only after governance summaries and archive candidate marking are reviewed,
   resume FotMob payload reconstruction.

Codex must not restart HISTORICAL-FOTMOB-PAYLOAD-SHAPE-RECONSTRUCTION-READONLY
until documentation cleanup Phase1 is merged and the next governance task has
confirmed which reports are evidence, superseded, or archive candidates.

## Document Lifecycle Usage

At task start, Codex must read active source-of-truth docs first. Evidence docs
can support historical claims, but they cannot be used alone as current truth.
`superseded`, `archive_candidate`, and `archived` docs must not be cited as the
current project state.

When Codex cites an old report, it must say whether the report is evidence. If a
report conflicts with an active doc, the active doc wins and the PR body should
describe the conflict. If no active doc exists for a long-lived conclusion,
Codex should create or update a source-of-truth doc in a scoped task instead of
continuing a report chain.

## Task Completion Standard

Before finalizing a task, Codex must check whether the task changed active
project status, blockers, workflow rules, safety posture, or next-step priority.
If it did, update the relevant source-of-truth doc in the same PR unless the user
explicitly scoped the task away from that update. When `docs/_reports/*.md` is
added or modified without a source-of-truth update, the PR body must provide a
specific no-update reason; hollow placeholders such as `n/a`, `none`, `not
needed`, `no`, `无`, or `无需` are not valid.

Completion is not "a new report exists". Completion means the implementation,
validation, safety boundary, and current-state backflow decision are all handled
within the authorized scope.

## Archive Move Planning Rules

Archive move plans are not authorization to move files. During Phase3A, Codex
may only document proposed source and destination paths. It must not delete,
move, rename, archive, or create `docs/_archive/` content.

Before any future move, Codex must require owner review, list every moved file in
the PR body, preserve the original relative path or mapping table, and provide a
rollback plan. If a candidate has uncertain current value, mark it do-not-move
until the source-of-truth replacement is confirmed.

Archive moves must not be based on filename patterns alone. Broad patterns such
as `FOTMOB_*`, `*_REVIEW*`, `*_DECISION*`, and `*_NEXT_PLAN*` are planning
signals only. A future archive move task requires an exact owner-approved file
list, explicit destructive flag, rollback plan, and no broad destination pattern.

## Merge-Only Task Rules

Merge-only tasks are zero-change tasks. They may only verify repository and PR
state, merge the approved PR, sync local `main`, delete the local task branch,
and report final state. They must not modify files, create commits, create new
branches, create new PRs, or start follow-up work.

## High-Risk Work Restrictions

Codex must not run or modify FotMob reconstruction, scraper, browser automation,
Playwright, Chromium, cookie/session code, captcha code, proxy rotation, DB
writes, raw data writes, or network data collection unless a future task
explicitly authorizes the exact scope.

Real DB writes, schema migrations, live data collection, raw writes, and formal
model training still require explicit user authorization before execution.

Any script that performs INSERT / UPDATE / DELETE / TRUNCATE / DROP on the
database must integrate the unified DB write guard (`scripts/ops/helpers/db_write_guard.js`)
before executing the write operation. New write entrypoints must not bypass this
guard. The guard enforces universal gates (`ALLOW_DB_WRITE`, `FINAL_DB_WRITE_CONFIRMATION`),
table-level gates (`ALLOW_RAW_MATCH_DATA_WRITE`, `ALLOW_MATCHES_WRITE`,
`ALLOW_ODDS_WRITE`, `ALLOW_TRAINING_WRITE`), and schema-level gates
(`ALLOW_SCHEMA_WRITE`). DRY_RUN defaults to `true`. Production environment
(`NODE_ENV=production` / `APP_ENV=production`) blocks write by default.
Production-like DB hosts (RDS, Cloud SQL, Supabase, Railway, Render, Heroku, etc.)
are blocked by default with no override. New env vars that bypass the production
host block must not be introduced without explicit user authorization and separate
audit.

Test-debt work must be handled in a separate audit or repair task. Do not fix
tests as part of workflow hardening unless the task explicitly scopes governance
checker tests.

## Codex Final Report Format

Codex final replies should include:

- Branch
- PR URL
- Commit SHA
- Files changed count
- Docs added count
- Docs modified count
- Source-of-truth docs touched
- Validation result
- Next task

For safety-sensitive tasks, also include whether network, DB, browser automation,
scraper, raw write, or scheduler paths were used.
