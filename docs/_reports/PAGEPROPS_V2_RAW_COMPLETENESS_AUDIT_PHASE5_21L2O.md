# PageProps V2 Raw Completeness Audit - Phase 5.21L2O

## 1. Executive summary

Phase 5.21L2N confirmed that all eight seeded Ligue 1 matches now canonical-select
`fotmob_pageprops_v2`.

This phase adds a local pageProps v2 raw inventory and completeness audit for
those same eight seeded matches. The audit is strictly SELECT-only, reads local
`raw_match_data` only, does not access FotMob or any network path, and does not
implement parser/features/training/prediction.

The goal is to determine whether the stored `fotmob_pageprops_v2` payloads are
complete and structurally consistent enough to justify a later parser planning
phase, while still keeping parser implementation deferred.

## 2. Current DB baseline

Expected and verified baseline before and after the audit:

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |   10 |
| `raw_match_data`          |   18 |
| `bookmaker_odds_history`  |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

Protected tables with current rows: `bookmaker_odds_history=2`, `predictions=2`.

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

## 3. Per-target inventory

The script reads only the stored v2 rows and derives team names from
`pageProps.general.homeTeam.name` / `awayTeam.name`. It does not print full
`raw_data` or full `pageProps`.

Shared top-level `pageProps` keys across all eight rows:

- `content`
- `fallback`
- `fetchingLeagueData`
- `general`
- `hasPendingVAR`
- `header`
- `nav`
- `ongoing`
- `seo`
- `ssr`
- `translations`

Per-target inventory:

| external_id | match_id              | home_team             | away_team    | data_hash                                                          | json_byte_length | path_count | leaf_path_count | max_depth | coverage_tier                       |
| ----------- | --------------------- | --------------------- | ------------ | ------------------------------------------------------------------ | ---------------: | ---------: | --------------: | --------: | ----------------------------------- |
| `4830746`   | `53_20252026_4830746` | `Angers`              | `Strasbourg` | `7953562593a2ab57ed59741667ccf2fa628adf22eff76fdc7a499f559b3ac440` |          335,469 |      9,550 |           7,175 |        10 | `seeded_pageprops_v2_high_coverage` |
| `4830747`   | `53_20252026_4830747` | `Auxerre`             | `Nice`       | `f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc` |          320,963 |      9,635 |           7,238 |        10 | `seeded_pageprops_v2_high_coverage` |
| `4830748`   | `53_20252026_4830748` | `Le Havre`            | `Marseille`  | `fe664ebe76d4e0e9fda088d4d642fe98fe25c03b920f4f3d83531e6ea4c4ad04` |          301,621 |      9,284 |           6,981 |        10 | `seeded_pageprops_v2_high_coverage` |
| `4830750`   | `53_20252026_4830750` | `Metz`                | `Lorient`    | `e5cada280a0b8d351181defd5605ded7ced091e86be3039439559aed1247b762` |          332,451 |      9,827 |           7,405 |        10 | `seeded_pageprops_v2_high_coverage` |
| `4830751`   | `53_20252026_4830751` | `Monaco`              | `Lille`      | `de78dc67d69ffc22739e4cf648788fd6f50a6dfccae8518a9c1fa8def0eb16a5` |          309,990 |      9,564 |           7,156 |        10 | `seeded_pageprops_v2_high_coverage` |
| `4830752`   | `53_20252026_4830752` | `Paris Saint-Germain` | `Brest`      | `65564219fcb25c6369822a0082f43e96f59675f434208d45cb16ef6395f08c32` |          344,660 |      9,376 |           7,066 |        10 | `seeded_pageprops_v2_high_coverage` |
| `4830753`   | `53_20252026_4830753` | `Rennes`              | `Paris FC`   | `4ab9fcb73465d00cc8bab7a6cb1a61b1b3370d466b15c2ace0092c8357ead413` |          325,116 |      9,788 |           7,354 |        10 | `seeded_pageprops_v2_high_coverage` |
| `4830754`   | `53_20252026_4830754` | `Toulouse`            | `Lyon`       | `29be450e84a55fb56a8db4f1bf7a672adcd6c85e34a8cf06c98e99ac179532c6` |          363,127 |      9,844 |           7,411 |        10 | `seeded_pageprops_v2_high_coverage` |

Observed size/path envelope:

- `json_byte_length_min=301621`
- `json_byte_length_max=363127`
- `json_byte_length_median=328783.5`
- `path_count_min=9284`
- `path_count_max=9844`
- `path_count_median=9599.5`

## 4. Module coverage

The audit tracks coverage across all eight rows for:

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
- `seo.eventJSONLD`
- `seo.breadcrumbJSONLD`
- `fallback`
- `translations`
- `header`
- `general`
- `nav`
- `ongoing`
- `ssr`
- `fetchingLeagueData`
- `hasPendingVAR`

Actual module coverage across the eight seeded v2 rows:

| module path            | coverage |
| ---------------------- | -------: |
| `content`              |      8/8 |
| `content.lineup`       |      8/8 |
| `content.matchFacts`   |      8/8 |
| `content.playerStats`  |      8/8 |
| `content.shotmap`      |      8/8 |
| `content.stats`        |      8/8 |
| `content.h2h`          |      8/8 |
| `content.table`        |      8/8 |
| `content.momentum`     |      8/8 |
| `seo`                  |      8/8 |
| `seo.eventJSONLD`      |      8/8 |
| `seo.breadcrumbJSONLD` |      8/8 |
| `fallback`             |      8/8 |
| `translations`         |      8/8 |
| `header`               |      8/8 |
| `general`              |      8/8 |
| `nav`                  |      8/8 |
| `ongoing`              |      8/8 |
| `ssr`                  |      8/8 |
| `fetchingLeagueData`   |      8/8 |
| `hasPendingVAR`        |      8/8 |

No module-level missing external IDs were found for the tracked set.

## 5. Path coverage

Actual path coverage:

- `common_paths_count=3483`
- `partial_paths_count=48762`
- `unique_paths_count=52245`

Common path examples (capped):

- `content`
- `content.attackingZones`
- `content.attackingZones.away`
- `content.attackingZones.away.firstHalf`
- `content.attackingZones.away.firstHalf.center`
- `content.attackingZones.away.firstHalf.left`
- `content.attackingZones.away.firstHalf.right`
- `content.attackingZones.away.secondHalf`
- `content.attackingZones.away.secondHalf.center`
- `content.attackingZones.away.secondHalf.left`

Partial path examples (capped):

- `content.h2h.matches[].status.reason.penalties` -> present `2/8`
- `content.h2h.matches[].status.reason.penalties[]` -> present `2/8`
- `content.lineup.awayTeam.coach.performance` -> present `1/8`
- `content.lineup.awayTeam.coach.performance.events` -> present `1/8`
- `content.lineup.awayTeam.coach.performance.events[]` -> present `1/8`
- `content.lineup.awayTeam.coach.performance.events[].time` -> present `1/8`
- `content.lineup.awayTeam.coach.performance.events[].type` -> present `1/8`
- `content.lineup.awayTeam.starters[].performance.events` -> present `7/8`
- `content.lineup.awayTeam.starters[].performance.events[]` -> present `7/8`
- `content.lineup.awayTeam.starters[].performance.events[].type` -> present `7/8`

Per-target missing path counts (capped samples only):

- `4830746`: `missing_path_count=42654`
- `4830747`: `missing_path_count=42567`
- `4830748`: `missing_path_count=42917`
- `4830750`: `missing_path_count=42379`
- `4830751`: `missing_path_count=42639`
- `4830752`: `missing_path_count=42826`
- `4830753`: `missing_path_count=42418`
- `4830754`: `missing_path_count=42363`

These are relative-to-union missing counts, not indications of broken payloads.
They mostly reflect optional or event-contingent branches across the eight
matches.

## 6. Suspicious payload checks

Actual suspicious payload results:

- suspicious small payloads: none
- payload size outliers: none
- missing core modules: none
- block/error/captcha/forbidden/placeholder markers: none

This means the current seeded Ligue 1 v2 sample does not show truncated,
blocked, placeholder-only, or obviously degraded payloads.

## 7. Completeness assessment

Assessment:

- `can_enter_parser_planning=true`
- overall coverage tier: `seeded_pageprops_v2_high_coverage`
- parser-candidate modules:
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
    - `header`
    - `general`
    - `nav`
- modules that should still be treated as optional in parser planning:
    - `seo.eventJSONLD`
    - `seo.breadcrumbJSONLD`
    - `ongoing`
    - `ssr`
    - `fetchingLeagueData`
    - `hasPendingVAR`
- `fields_not_safe_to_assume_all_leagues=[]` for this seeded Ligue 1 sample, but
  this must not be generalized to lower-tier or colder leagues

Judgment:

- yes, the current seeded Ligue 1 v2 sample is sufficient to enter parser
  planning
- no, it is not sufficient to jump directly into parser implementation,
  features, training, or prediction
- future lower-tier / colder league expansion should still assume optional
  handling for many deeper subpaths even when the seeded Ligue 1 sample looks
  complete

## 8. Verification results

Required validation for this phase:

- `tests/unit/pageprops_v2_raw_completeness_audit.test.js`
- `tests/unit/all_seeded_pageprops_v2_canonical_read_verification.test.js`
- `tests/unit/RawMatchDataVersionSelector.test.js`
- `make data-pageprops-v2-raw-completeness-audit ...`
- `npm test`
- `npm run test:coverage`
- `eslint`
- `prettier --check`
- `git diff --check`

Safety checks:

- DB row counts remain unchanged at `10 / 18 / 2 / 2 / 2 / 2`
- `tests/fixtures/l1-config-*` residue absent
- `docs/_staging_preview` absent
- PR CI and main push CI must pass before final post-merge audit

## 9. Next phase recommendation

Recommended next phase:

`Phase 5.21L2P: parser planning based on pageProps v2 inventory`

Required scope:

- no DB write
- no parser implementation
- no feature table write
- no training
- design parser modules based on completeness audit
- map raw modules to future feature groups
- define leakage-safe feature policy

Do not proceed directly to parser/features/training implementation.

## 10. Explicit non-execution

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
- full pageProps print/save
- file deletion
