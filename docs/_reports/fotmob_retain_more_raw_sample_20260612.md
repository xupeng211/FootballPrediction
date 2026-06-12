# FotMob Retain More Raw Sample

lifecycle: phase-artifact

- Date: 2026-06-12
- Base main commit: `196c9c8ea9df596c8eb19e0c28dbe5d0996434c0`
- Branch: `data/fotmob-retain-more-raw-sample`
- Goal: retain up to 20 additional real FotMob match detail raw payloads into `raw_match_data` with `data_version=fotmob_live_v1`
- Existing mechanisms used: `scripts/ops/n3_live_fotmob_raw_retain.js` and `scripts/ops/single_live_fotmob_raw_ingest_smoke.js`
- Safety: low-frequency serial execution; no browser; no proxy bypass; no full raw JSON saved to repo or printed; no parser/test/feature/training changes

## Execution Summary

- Starting retained `fotmob_live_v1` rows: `4`
- Attempted additional raw retains: `20`
- Actual additional raw retains: `20`
- Final retained `fotmob_live_v1` rows: `24`
- Duplicate skips: `0`
- Failures: `0`
- Writes performed: `yes`, `raw_match_data` only
- Writes not performed: `matches=no`, `features=no`, `odds=no`
- Raw payload files committed to repo: `no`
- Parser changed: `no`
- Model training run: `no`

## Candidate Scope

- Existing retained rows explicitly avoided:
  `4830507`, `4830466`, `4830461`, `4830464`
- Candidate source: existing `matches` rows with non-null `external_id`, missing `fotmob_live_v1` raw, limited to 20 targets
- Execution pattern:
  6 sequential `N=3` retain batches + 2 sequential single retains

## Added External IDs

`4830494`, `4830495`, `4830496`, `4830497`, `4830499`, `4830500`, `4830501`,
`4830502`, `4830505`, `4830508`, `4830510`, `4830511`, `4830746`, `4830747`,
`4830748`, `4830750`, `4830751`, `4830752`, `4830753`, `4830754`

## Read-only Validation

- `raw_match_data` `data_version='fotmob_live_v1'` total count after write: `24`
- Inserted target rows present: `20/20`
- JSON structural check passed: `20/20`

Validation rule for each new row:

- `raw_data` is valid `jsonb` object
- top-level `matchId` present
- top-level `general` present
- top-level `header` present
- top-level `content` present
- `content.matchFacts` or `content.stats` has valid object structure

Result:

- `jsonb object`: `20/20`
- `matchId`: `20/20`
- `general`: `20/20`
- `header`: `20/20`
- `content`: `20/20`
- `content.matchFacts/content.stats`: `20/20`

## Notes

- Retention used the same guarded live-retain path introduced by `#1485` and extended by `#1486`; no new collection architecture was added.
- Each target completed live fetch, FK check, UPSERT, read-back verification, and idempotent re-UPSERT verification before proceeding.
- No parser dry-run, feature generation, training, or non-raw table mutation was performed.

## Conclusion

- Additional retained FotMob raw storage is now expanded from `4` to `24` rows for `data_version=fotmob_live_v1`.
- All 20 new retained rows were written successfully into `raw_match_data` and passed the requested lightweight structural checks.
- This PR only expands the retained raw sample set; it does not validate parser behavior on the new rows and does not authorize any next task.
