# All Seeded PageProps V2 Canonical Read Verification - Phase 5.21L2N

## 1. Executive summary

Phase 5.21L2M inserted the remaining seven `fotmob_pageprops_v2` rows after
hash-gated controlled recapture. All eight seeded Ligue 1 matches now have both
`fotmob_html_hyd_v1` and `fotmob_pageprops_v2`.

This phase adds all-seeded canonical read verification. It is SELECT-only, does
not access FotMob, and does not run parser/features/training/prediction. The
goal is to confirm that `RawMatchDataVersionSelector` now canonical-selects
`fotmob_pageprops_v2` for all eight seeded matches and still excludes
synthetic/legacy/unknown versions by default.

## 2. Current DB baseline

Expected and verified baseline after Phase 5.21L2M:

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |   10 |
| `raw_match_data`          |   18 |
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
| `fotmob_pageprops_v2` |    8 |

## 3. All-seeded canonical verification

Expected canonical selection for all seeded matches:

- `4830746` -> `fotmob_pageprops_v2`, hash matches expected
- `4830747` -> `fotmob_pageprops_v2`, hash matches expected
- `4830748` -> `fotmob_pageprops_v2`, hash matches expected
- `4830750` -> `fotmob_pageprops_v2`, hash matches expected
- `4830751` -> `fotmob_pageprops_v2`, hash matches expected
- `4830752` -> `fotmob_pageprops_v2`, hash matches expected
- `4830753` -> `fotmob_pageprops_v2`, hash matches expected
- `4830754` -> `fotmob_pageprops_v2`, hash matches expected

Per-target verification fields:

- `match_id`
- `external_id`
- `available_versions`
- selected `data_hash`
- `has _meta`
- `has matchId`
- `has pageProps`

Expected hash baselines:

| external_id | match_id              | expected pageProps v2 hash                                         |
| ----------- | --------------------- | ------------------------------------------------------------------ |
| `4830746`   | `53_20252026_4830746` | `7953562593a2ab57ed59741667ccf2fa628adf22eff76fdc7a499f559b3ac440` |
| `4830747`   | `53_20252026_4830747` | `f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc` |
| `4830748`   | `53_20252026_4830748` | `fe664ebe76d4e0e9fda088d4d642fe98fe25c03b920f4f3d83531e6ea4c4ad04` |
| `4830750`   | `53_20252026_4830750` | `e5cada280a0b8d351181defd5605ded7ced091e86be3039439559aed1247b762` |
| `4830751`   | `53_20252026_4830751` | `de78dc67d69ffc22739e4cf648788fd6f50a6dfccae8518a9c1fa8def0eb16a5` |
| `4830752`   | `53_20252026_4830752` | `65564219fcb25c6369822a0082f43e96f59675f434208d45cb16ef6395f08c32` |
| `4830753`   | `53_20252026_4830753` | `4ab9fcb73465d00cc8bab7a6cb1a61b1b3370d466b15c2ace0092c8357ead413` |
| `4830754`   | `53_20252026_4830754` | `29be450e84a55fb56a8db4f1bf7a672adcd6c85e34a8cf06c98e99ac179532c6` |

## 4. Synthetic / unknown exclusion

Default canonical selector behavior must continue to exclude:

- `PHASE4.43_SYNTHETIC`
- `PHASE4.23`
- unknown/untracked versions

This phase verifies that:

- no canonical selection is taken from synthetic/legacy/unknown rows
- exclusion still applies even after all eight seeded matches now have pageProps
  v2
- no accidental fallback to synthetic/unknown occurs

## 5. Duplicate / schema checks

Required checks:

- duplicate `(match_id,data_version)=0`
- `raw_match_data_match_id_data_version_key` present
- `raw_match_data_match_id_key` absent

The script blocks verification success if:

- the versioned unique constraint is missing
- the legacy `UNIQUE(match_id)` constraint reappears
- duplicate `(match_id,data_version)` rows exist

## 6. Verification results

Required local validation for this phase:

- `tests/unit/all_seeded_pageprops_v2_canonical_read_verification.test.js`
- `tests/unit/RawMatchDataVersionSelector.test.js`
- `tests/unit/pageprops_v2_post_write_canonical_read_verification.test.js`
- `tests/unit/remaining_seeded_pageprops_v2_controlled_write.test.js`
- `make data-all-seeded-pageprops-v2-canonical-read-verification ...`
- `npm test`
- `npm run test:coverage`
- `eslint`
- `prettier --check`
- `git diff --check`

Safety verification:

- DB row counts remain unchanged at `10 / 18 / 2 / 2 / 2 / 2`
- `tests/fixtures/l1-config-*` residue absent
- `docs/_staging_preview` absent
- PR CI and main push CI pass before final SELECT-only verification

## 7. Next phase recommendation

Recommended next phase:

`Phase 5.21L2O: pageProps v2 raw inventory and completeness audit for all 8 seeded matches`

Scope:

- no DB write
- no FotMob access
- read local `raw_match_data` only
- compare v2 pageProps coverage across all eight
- inspect module availability:
    - `content`
    - `content.lineup`
    - `content.matchFacts`
    - `content.playerStats`
    - `content.shotmap`
    - `content.stats`
    - `content.h2h`
    - `content.table`
    - `content.momentum`
    - `seo`
    - `fallback`
    - `translations`
- summarize common / partial / missing paths
- no parser/features/training

Do not proceed directly to parser/features/training.

## 8. Explicit non-execution

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
