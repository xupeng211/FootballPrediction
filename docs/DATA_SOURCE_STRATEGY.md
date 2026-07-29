# Data Source Strategy

- lifecycle: current-state
- owner: data / ingestion governance

Last updated: 2026-07-29

## Current source priority

1. FotMob is the primary football fixture, canonical-match-identity and retained
   match-detail/raw-asset source.
2. Football-Data is the historical results/odds candidate source for M3. Its
   current identity contract permits `E0` / `Premier League` only for seasons
   `2022/2023`, `2023/2024` and `2024/2025`; it does not yet have retained
   real-ingest proof in the development inventory. The D4F cross-source audit
   reverified three historical Git inputs and produced 892 reproducible source
   semantic candidates against a recovered 1,140-candidate FotMob Premier
   League artifact. It isolated 888 unique exact matches and four kickoff
   conflicts with no identity-policy expansion. The completed 2026-07-29
   design review selects all 1,140 FotMob candidates for future canonical
   inventory; 888 is linkage-only, four remain linkage quarantine, and the
   remaining 248 are canonical-only/unlinked. The four plus 248 are the 252
   candidates without an exact Football-Data link. The recovered v1 artifact
   lacks status for all 1,140, so it is identity evidence rather than a
   write-ready input; real import is blocked.
3. OddsPortal / NowGoal / BetExplorer are not current implementation targets.
   OddsPortal has no retained execution evidence and its legacy route remains
   blocked.
4. Paid odds data remains a future option, not a current task.

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
- **Current retained FotMob raw inventory**: 58 `fotmob_live_v1` rows and 32
  retained full raw-payload records. The payload table stores complete unparsed
  `__NEXT_DATA__` JSON in non-null `next_data_json`, with file locators,
  SHA-256 values, byte sizes and capture/ingestion metadata. `page_props_json`
  is nullable and retained when present.
- **Historical fully audited milestone**: four retained rows only—4/4
  parseable, 4/4 SHA-valid, 4/4 inner-`matchId`-valid, zero errors and zero
  warnings. This 4/4 result does not extend to all 58 retained rows.
- The 32 payload assets establish match-level `match_id` overlap only;
  record-level lineage to a specific `raw_match_data` row, 32/32
  parser/schema/pageProps validation and exact writer provenance for all 58
  rows are not proven.
- FotMob retained assets and its independent 50-target Ligue 1 mapping
  chronology do not define the M3 Football-Data candidate population.
- **M3 D4F status**:
  `READY_FOR_CANONICAL_INVENTORY_PROVENANCE_REVIEW` with
  `REAL_WRITE_BLOCKED_PROVENANCE_POLICY`.
  The historical Git inputs remain reverified (1,180 raw rows, 38,832 odds
  observations, 892 semantic candidates; source hash `07e579…98b8b`). Two
  recovered, validated FotMob `candidate-match-identity/v1` artifacts each
  contain 1,140 Premier League candidates (380 per target season; business
  hash `eff881…bc9d3f`). Existing exact-alias, Europe/London and ordered
  home/away rules yielded 888 exact unique matches and four isolated kickoff
  conflicts (3 × 15 minutes, 1 × 30 minutes); no unmatched, ambiguity, team,
  competition/season, incomplete or invalid-source terminal occurred. The
  development `matches` inventory itself remains zero for this scope, but it
  was not used as the cross-source candidate side. A separate insert-only
  writer, v2 status-complete input contract and additive V26.10 schema/lineage
  migration now passed only a synthetic PostgreSQL 15 disposable proof. No
  real v2 artifact/provenance, business/persistent schema write, canonical
  linkage or odds import occurred; real inventory remains
  `BLOCKED_PROVENANCE_POLICY`.
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
- After separate authorization, review real FotMob provenance for a
  status-complete artifact. The implemented writer has only a disposable
  synthetic proof; inventory is 1,140 candidates, canonical creation remains
  separate from 888 exact linkage, four conflicts and historical odds. This
  does not authorize a business write.

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
- The 32 `clean_candidate`, 10 `needs_new_evidence` and 8
  `remain_suspended` Ligue 1 FotMob mapping states are ingestion-governance
  evidence only. They must not be used as the candidate set for an M3
  Football-Data compatibility audit.
- Repository Git-history location and SHA-256 identity are verified for the
  bounded D4F input package. Original upstream capture/provider/license
  provenance remains unverified; recovered FotMob candidate business identity
  proves candidate compatibility, not historical-odds provenance or an import
  authorization.

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
- Can implementation establish a status-complete, hash-bound FotMob artifact
  without expanding provider scope?
- Can the isolated migration prove provider-scoped uniqueness and immutable
  import lineage on a disposable target before a persistent write?
- What evidence is sufficient to resolve each isolated kickoff conflict without
  changing aliases, timezone interpretation or tolerance?
- Is `raw_write` authorization phrase mechanism still wired and effective?
- Are current DB write guards (gatekeeper.sh, ai_workflow_gate.py) still active?
- What exact no-write test should be run first?
