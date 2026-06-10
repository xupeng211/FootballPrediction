# FotMob Retained Raw Stage Status

- lifecycle: current-state
- owner: data / ingestion workflow
- update rule: update when retained raw count, audit results, data_version, or next step changes

## Current retained raw state

- **Table**: `raw_match_data`
- **data_version**: `fotmob_live_v1`
- **Retained raw rows**: 4
- **Source PRs**: #1485 (single), #1486 (N=3), #1487 (audit), #1488 (AI Workflow Gate)
- **Last audit date**: 2026-06-11

## Audit results (#1487)

| Check | Result |
|---|---|
| Rows audited | 4 |
| Parseable | 4/4 |
| SHA valid | 4/4 |
| Inner matchId OK | 4/4 |
| Errors | 0 |
| Warnings | 0 |

## What this stage proves

- Retained raw storage pipeline (`raw_match_data` + `fotmob_live_v1`) is functional.
- 4 real FotMob raw payloads have been fetched, stored, and verified.
- Audit tooling exists and confirms: parseable JSON, sha integrity, correct inner matchId.

## What this stage does NOT prove

- **Parser contract**: raw payload structure has not been validated against any parser schema.
- **Feature extraction**: no features have been extracted from these rows.
- **Model training**: no models have been trained on this data.
- **Scalability**: N=4 does not demonstrate N=50 or N=100 throughput.
- **Cross-league coverage**: only Ligue 1 seeded targets in scope.

## Relation to legacy ADG60 / 32-sample state

- The old `raw_write_ready_count=0` and "ADG60 blocked" state is **superseded** for the
  purpose of retained raw storage. Raw write has been authorized and executed for exactly
  4 targets under controlled conditions.
- The legacy 32-target ADG inventory and corrected-source discovery pipeline is a
  **separate concern** — it was about identity correction and canonical URL discovery,
  not about retained raw storage.
- The 32-sample state remains relevant for Ligue 1 corrected-source inventory but does
  **not** describe the current retained raw storage reality.

## Active safety rules (unchanged)

- No DB write beyond the already-authorized 4 retained raw rows.
- No live fetch, network request, or browser automation without explicit authorization.
- No parser implementation, feature extraction, training, or prediction.
- No schema migration without explicit authorization.
- No bulk raw acquisition (N=5, N=10, N=50) without separate preflight + authorization.

## Recommended next step

1. **Parser contract / raw payload structure validation** — confirm that the 4 retained
   `fotmob_live_v1` payloads conform to expected parser schema before scaling up.
2. After parser validation passes, consider **N=5 or N=10 controlled expansion** with
   fresh authorization, preflight, and hash-gated write.

Do not start automatically.
Recommended next task only after user confirmation.
