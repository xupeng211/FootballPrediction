# Data Source Strategy

- lifecycle: current-state
- owner: data / ingestion governance

Last updated: 2026-06-07

## Current source priority

1. FotMob is the primary near-term football data source.
2. OddsPortal / NowGoal / BetExplorer are not current implementation targets.
3. Paid odds data remains a future option, not a current task.

## Current FotMob posture

- FotMob work may resume only after explicit user confirmation.
- Initial FotMob work must be read-only / no-write.
- Do not run real browser automation unless explicitly authorized.
- Do not write `raw_match_data` or any database table unless explicitly authorized.
- Do not change DB schema in FotMob tasks.
- `docs/data/FOTMOB_CURRENT_STATE.md` is the active FotMob current-state doc.
- Historical ADG reports in `docs/_reports/` are evidence, not current truth.

## Current data safety status

- `raw_write_ready_count`: 0.
- DB write: blocked.
- Raw data write: blocked.
- Schema migration: blocked.
- Browser automation: blocked.
- Scraper/proxy-bypass: blocked.
- Network data collection: blocked unless explicitly authorized with exact scope.

## Allowed next data tasks (after user confirmation)

- Read current FotMob state docs.
- Inspect existing parser/collector code without running real scraping.
- Design small parser or schema-reuse plans (no-write).
- Add tests using fixtures/mocks only.
- Document exact evidence needed before enabling ingestion.
- Small read-only source inventory audits.

## Blocked data tasks

- DB write and schema migration.
- Raw data write (`raw_match_data`, `matches`).
- Real scraping and browser automation.
- Proxy-bypass experiments.
- Bulk historical data collection.
- Odds source implementation.
- Training and prediction.
- Feature extraction from live data.

## Active runtime guards

- `validateStrictFixtureIdentity()` — strict home/away/date/competition validation.
- `classifyDetailCandidateIdentity()` — generation-time candidate classification.
- `selectOrientedFixtureRecord()` — oriented fixture selection from ambiguous records.

## Safe assets (offline reference only)

From PR #1454:
- Parser, schema, fixture, and validation assets are safe to reuse as offline references.
- Do not use them to justify live fetch, DB write, or browser automation.

## Cross-source principles

- Synthetic/legacy rows in `raw_match_data` must not be used for FotMob source fidelity
  assessment unless explicitly identified.
- Parser/features/training must branch by `data_version` and source/provenance.
- Odds data is a separate market-pricing source with independent ingestion lifecycle.
- Do not cross-contaminate FotMob source decisions with odds source decisions.

## Validation rules for data tasks

- Use branch + PR with the mandatory PR template.
- Use `make ci-local-pr` as a local pre-push helper.
- Remote GitHub Actions `production-gate.yml` is the final authority.
- PR body must state what was and was not validated.
- CI Gate Scope must state what validation proves and does not prove.
- Data ingestion PRs must fill the Ingestion Convergence Gate section in the PR template.
- Do not start automatically. Recommended next task only after user confirmation.

## Open questions before ingestion resumes

- What is the latest verified FotMob endpoint status?
- Which existing fixtures are safe to use for testing?
- Is `raw_write` authorization phrase mechanism still wired and effective?
- Are current DB write guards (gatekeeper.sh, ai_workflow_gate.py) still active?
- What exact no-write test should be run first?
