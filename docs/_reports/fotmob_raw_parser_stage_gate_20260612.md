# FotMob Raw/Parser Stage Gate

lifecycle: phase-artifact

- Date: `2026-06-12`
- Branch: `docs/fotmob-raw-parser-stage-gate`
- Main reference commit: `cc8d071bb0ca33ed9b46c790316de798acdd646d` (`#1500`)
- Scope: summary only; consolidate merged FotMob raw/parser stage evidence up to `#1500`
- Safety: no live fetch; no DB write; no parser/test/feature/model change; no full raw JSON/pageProps/body saved or printed

## Current Stage Completed

- `#1485/#1486`: established and preserved retained FotMob raw storage path into `raw_match_data` for `data_version='fotmob_live_v1'`
- `#1496`: fixed parser policy for `null-id`, `synthetic_event_key`, and `marker_event`
- `#1499`: expanded retained real FotMob raw sample from `4` to `24`
- `#1500`: reran latest `main` `FotMobRawParser` on all retained rows and closed the retained-sample parser dry-run gate

## Verified Data Scope

- Verified range: `24` retained `raw_match_data` rows with `data_version='fotmob_live_v1'`
- Evidence basis:
  - `docs/_reports/fotmob_retain_more_raw_sample_20260612.md`
  - `docs/_reports/fotmob_parser_24_retained_dry_run_20260612.md`

## Parser Verification Result

- Parse success: `24/24`
- Events parity: `446/446`
- `Substitution` synthetic key pass: `197/197`
- `AddedTime` `marker_event` pass: `45/45`
- `Half` `marker_event` pass: `46/46`
- New null-id `real_event`: `0`

## What This Stage Proves

- Current retained `fotmob_live_v1` raw sample can be parsed end-to-end by `FotMobRawParser`
- Current null-id / synthetic key / marker-event policy holds on the retained 24-row sample
- Expanded retained sample preserves event-level parity without introducing new null-id `real_event`

## What This Stage Does Not Yet Prove

- It does not prove all FotMob payloads are stable across leagues, seasons, or future payload variants
- It does not prove standardized parsed/intermediate storage is complete
- It does not prove feature engineering is complete
- It does not prove model training is authorized, safe, or ready

## Gate Decision

- `GO`: parsed/intermediate storage design
- `NO-GO`: direct transition to feature engineering or model training

## Next Recommended Phase

- Design parsed/intermediate persistence first
- Keep raw retention plus parser contract as the current boundary
- Do not jump directly to feature/model work until parsed storage boundaries and downstream data contract are explicit

## Out Of Scope

- No new data fetch
- No DB write
- No parser change
- No test change
- No feature work
- No model training
- No extra task creation
- No raw JSON committed
