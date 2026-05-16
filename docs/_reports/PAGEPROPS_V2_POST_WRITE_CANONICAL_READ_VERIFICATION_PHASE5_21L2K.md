# PageProps V2 Post-Write Canonical Read Verification - Phase 5.21L2K

## 1. Executive summary

Phase 5.21L2J inserted the first `fotmob_pageprops_v2` row for target
`4830747` (`53_20252026_4830747`, Auxerre vs Nice). The existing
`fotmob_html_hyd_v1` row was retained and parser/features/training stayed
deferred.

This phase adds SELECT-only post-write canonical read verification. It confirms
that `RawMatchDataVersionSelector` chooses pageProps v2 for the target with both
versions, falls back to v1 for seeded matches without v2, and keeps
synthetic/legacy/unknown versions excluded by default.

This phase performs no DB write, no FotMob access, no parser/features, and no
training/prediction.

## 2. Current DB baseline

Expected and verified baseline after Phase 5.21L2J:

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |   10 |
| `raw_match_data`          |   11 |
| `bookmaker_odds_history`  |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

Schema:

- `raw_match_data_match_id_key`: absent
- `raw_match_data_match_id_data_version_key`: present
- unique constraint: `UNIQUE(match_id, data_version)`

Data version distribution:

| data_version          | rows |
| --------------------- | ---: |
| `PHASE4.23`           |    1 |
| `PHASE4.43_SYNTHETIC` |    1 |
| `fotmob_html_hyd_v1`  |    8 |
| `fotmob_pageprops_v2` |    1 |

## 3. Target canonical verification

Target:

- `match_id=53_20252026_4830747`
- `external_id=4830747`

Available versions:

- `fotmob_html_hyd_v1`
- `fotmob_pageprops_v2`

Expected canonical result:

| field                      | value                                                              |
| -------------------------- | ------------------------------------------------------------------ |
| selected canonical version | `fotmob_pageprops_v2`                                              |
| selected hash              | `f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc` |
| hash_matches_expected      | `true`                                                             |
| has `_meta`                | `true`                                                             |
| has top-level `matchId`    | `true`                                                             |
| has `pageProps`            | `true`                                                             |

## 4. Fallback verification for remaining seeded matches

Expected canonical fallback results:

| external_id | match_id              | selected canonical version |
| ----------- | --------------------- | -------------------------- |
| `4830746`   | `53_20252026_4830746` | `fotmob_html_hyd_v1`       |
| `4830748`   | `53_20252026_4830748` | `fotmob_html_hyd_v1`       |
| `4830750`   | `53_20252026_4830750` | `fotmob_html_hyd_v1`       |
| `4830751`   | `53_20252026_4830751` | `fotmob_html_hyd_v1`       |
| `4830752`   | `53_20252026_4830752` | `fotmob_html_hyd_v1`       |
| `4830753`   | `53_20252026_4830753` | `fotmob_html_hyd_v1`       |
| `4830754`   | `53_20252026_4830754` | `fotmob_html_hyd_v1`       |

Expected summary:

- `seeded_matches_checked=7`
- `fallback_to_v1_count=7`
- `unexpected_missing_count=0`
- `unexpected_v2_count=0`

## 5. Synthetic / unknown exclusion

Default selector behavior must continue to exclude:

- `PHASE4.43_SYNTHETIC`
- `PHASE4.23`
- unknown/untracked versions

The post-write verification checks legacy/synthetic rows independently and
requires canonical selection to return `null` when no allowed FotMob version is
present.

## 6. Duplicate / schema checks

Required checks:

- duplicate `(match_id,data_version)=0`
- `raw_match_data_match_id_data_version_key` present
- `raw_match_data_match_id_key` absent

The script blocks verification success if the versioned unique constraint is
missing, if the legacy `match_id` unique constraint reappears, or if duplicate
version rows are found.

## 7. Verification results

Required local validation for this phase:

- `tests/unit/pageprops_v2_post_write_canonical_read_verification.test.js`
- `tests/unit/RawMatchDataVersionSelector.test.js`
- `tests/unit/raw_match_data_version_compatibility_audit.test.js`
- `make data-pageprops-v2-post-write-canonical-read-verification ...`
- `npm test`
- `npm run test:coverage`
- `eslint`
- `prettier --check`
- `git diff --check`

Safety verification:

- DB row counts remain unchanged at `10 / 11 / 2 / 2 / 2 / 2`
- `tests/fixtures/l1-config-*` residue absent
- `docs/_staging_preview` absent
- PR CI and main push CI pass before post-merge SELECT-only verification

## 8. Next phase recommendation

Recommended next phase:

`Phase 5.21L2L: remaining seeded matches pageProps v2 acquisition planning/preflight`

Use two steps rather than direct bulk write:

1. Planning / target inventory for the remaining seven seeded matches.
2. No-write live preflight for the remaining seven only if explicitly authorized.

Suggested future preflight scope:

- no DB write first
- sequential live recapture only if authorized
- compute `stable_pageprops_payload_v1` hashes
- SELECT existing versions
- report `would_insert` seven v2 rows
- no parser/features/training

## 9. Explicit non-execution

This phase does not perform:

- DB writes
- `raw_match_data` writes
- network / FotMob access
- schema migration
- `matches` writes
- parser/features
- harvest/ingest/backfill
- training/prediction
- browser/proxy
- full raw_data print/save
- file deletion
