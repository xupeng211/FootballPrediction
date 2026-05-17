# Single-League Small-Batch Target Manifest Planning - Phase 5.21L2S

## 1. Executive summary

Phase 5.21L2R 已确认 short-term acquisition target inventory 应使用
docs/source-controlled manifest 或 generated report 表达，不应把 `matches` 表当作
workflow queue。

本阶段选择 `Ligue 1 / 2025/2026` 作为第一个 profile batch scope，生成
source-controlled manifest proposal：

- `docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json`

本阶段严格保持 planning-only：

- 不触网
- 不采集
- 不写库
- 不做 schema migration
- 不 invent target IDs / external IDs / teams / kickoff_time
- 不实现 parser / features / training

由于当前本地 DB 只有 8 个 `Ligue 1 / 2025/2026` seeded matches，且全部已有
`fotmob_pageprops_v2`，本阶段不能生成 20-50 个真实新 targets。manifest 因此标记：

- `target_population_status=blocked_pending_authorized_target_discovery`
- `required_next_step=authorized_target_discovery_or_source_inventory`

## 2. Current DB baseline

只读确认当前 DB baseline：

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |   10 |
| `raw_match_data`          |   18 |
| `bookmaker_odds_history`  |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

Protected tables:

- `bookmaker_odds_history=2`
- `predictions=2`

Current `raw_match_data` distribution:

| data_version          | rows |
| --------------------- | ---: |
| `PHASE4.23`           |    1 |
| `PHASE4.43_SYNTHETIC` |    1 |
| `fotmob_html_hyd_v1`  |    8 |
| `fotmob_pageprops_v2` |    8 |

Current `fotmob_pageprops_v2` count:

- `fotmob_pageprops_v2=8`

Important schema note:

- `matches` currently has `league_name`, not a dedicated `league_id` column.
- The manifest preserves source-native `league_id=53` as manifest metadata, not as a DB write.

## 3. Batch metadata

| field               | value                                              |
| ------------------- | -------------------------------------------------- |
| `batch_id`          | `fotmob-pageprops-v2-ligue1-2025-2026-profile-001` |
| `source`            | `fotmob`                                           |
| `route`             | `html_hydration`                                   |
| `raw_data_version`  | `fotmob_pageprops_v2`                              |
| `hash_strategy`     | `stable_pageprops_payload_v1`                      |
| `league_id`         | `53`                                               |
| `league_name`       | `Ligue 1`                                          |
| `season`            | `2025/2026`                                        |
| `batch_type`        | `profile_batch`                                    |
| `batch_size_policy` | `20-50`                                            |
| `write_policy`      | `no write in this phase`                           |
| `network_policy`    | `no network in this phase`                         |
| `status`            | `blocked_pending_authorized_target_discovery`      |

## 4. Known completed targets

The current local DB has 8 `Ligue 1 / 2025/2026` seeded targets with
`fotmob_pageprops_v2`. They are marked `already_completed` and excluded from the
new profile batch.

| match_id              | external_id | home_team             | away_team    | match_date             | status     | existing_versions                           | target_status       | exclude_from_new_profile_batch |
| --------------------- | ----------- | --------------------- | ------------ | ---------------------- | ---------- | ------------------------------------------- | ------------------- | ------------------------------ |
| `53_20252026_4830746` | `4830746`   | `Angers`              | `Strasbourg` | `2026-05-10T19:00:00Z` | `finished` | `fotmob_html_hyd_v1`, `fotmob_pageprops_v2` | `already_completed` | `true`                         |
| `53_20252026_4830747` | `4830747`   | `Auxerre`             | `Nice`       | `2026-05-10T19:00:00Z` | `finished` | `fotmob_html_hyd_v1`, `fotmob_pageprops_v2` | `already_completed` | `true`                         |
| `53_20252026_4830748` | `4830748`   | `Le Havre`            | `Marseille`  | `2026-05-10T19:00:00Z` | `finished` | `fotmob_html_hyd_v1`, `fotmob_pageprops_v2` | `already_completed` | `true`                         |
| `53_20252026_4830750` | `4830750`   | `Metz`                | `Lorient`    | `2026-05-10T19:00:00Z` | `finished` | `fotmob_html_hyd_v1`, `fotmob_pageprops_v2` | `already_completed` | `true`                         |
| `53_20252026_4830751` | `4830751`   | `Monaco`              | `Lille`      | `2026-05-10T19:00:00Z` | `finished` | `fotmob_html_hyd_v1`, `fotmob_pageprops_v2` | `already_completed` | `true`                         |
| `53_20252026_4830752` | `4830752`   | `Paris Saint-Germain` | `Brest`      | `2026-05-10T19:00:00Z` | `finished` | `fotmob_html_hyd_v1`, `fotmob_pageprops_v2` | `already_completed` | `true`                         |
| `53_20252026_4830753` | `4830753`   | `Rennes`              | `Paris FC`   | `2026-05-10T19:00:00Z` | `finished` | `fotmob_html_hyd_v1`, `fotmob_pageprops_v2` | `already_completed` | `true`                         |
| `53_20252026_4830754` | `4830754`   | `Toulouse`            | `Lyon`       | `2026-05-10T19:00:00Z` | `finished` | `fotmob_html_hyd_v1`, `fotmob_pageprops_v2` | `already_completed` | `true`                         |

These targets must not be placed in the new acquisition target list.

## 5. Candidate target result

Current result:

- `candidate_targets_count=0`
- `candidate_targets=[]`
- `candidate_targets` is not enough for a `20-50` target profile batch.
- `target_population_status=blocked_pending_authorized_target_discovery`

Reason:

- The local DB has no additional real `Ligue 1 / 2025/2026` matches without
  `fotmob_pageprops_v2`.
- The existing 8 seeded matches are completed v2 targets and are excluded.

Explicit anti-fabrication statement:

- no invented `external_id`
- no invented `match_id`
- no invented teams
- no invented kickoff_time / match_date
- no fabricated candidate target rows

Required next step:

- `authorized_target_discovery_or_source_inventory`

## 6. Manifest proposal

New source-controlled proposal manifest:

- `docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json`

Manifest summary:

- `schema_version=target_manifest_proposal_v1`
- batch metadata:
    - `source=fotmob`
    - `route=html_hydration`
    - `raw_data_version=fotmob_pageprops_v2`
    - `hash_strategy=stable_pageprops_payload_v1`
    - `league_id=53`
    - `league_name=Ligue 1`
    - `season=2025/2026`
- `known_completed_targets=8`
- `candidate_targets=0`
- `target_population_status=blocked_pending_authorized_target_discovery`
- `required_next_step=authorized_target_discovery_or_source_inventory`

The manifest is source-controlled documentation, not runtime staging. It does
not contain full raw_data, full pageProps, live response data, or invented IDs.

## 7. Target manifest schema

Future target fields:

- `target_id`
- `batch_id`
- `source`
- `route`
- `raw_data_version`
- `hash_strategy`
- `match_id`
- `external_id`
- `league_id`
- `league_name`
- `season`
- `home_team`
- `away_team`
- `kickoff_time`
- `match_date`
- `status`
- `target_status`
- `priority`
- `expected_coverage_tier`
- `existing_versions`
- `preflight_status`
- `baseline_hash`
- `last_preflight_at`
- `write_status`
- `write_attempt_count`
- `failure_reason`
- `source_fidelity_notes`
- `odds_alignment_ready`
- `created_at`
- `updated_at`

## 8. Selection policy

Selection policy for the first profile batch:

- same league/season first: `Ligue 1 / 2025/2026`
- exclude completed v2 targets
- prefer finished matches first for stable pageProps profile
- scheduled matches stay deferred unless prediction-time raw policy exists
- cancelled/postponed/abandoned matches stay excluded unless explicitly profiled
- require stable `external_id` and `match_id`
- require `kickoff_time` / `match_date` for odds alignment readiness
- require duplicate detection before preflight
- do not use `matches` as an uncontrolled acquisition workflow queue

## 9. Readiness gates

Before any real acquisition:

- manifest reviewed
- target identities verified
- no invented IDs
- duplicate detection passed
- no existing `fotmob_pageprops_v2` for new targets
- explicit network authorization before discovery/preflight
- no-write preflight before write
- baseline hash before write
- separate final DB write confirmation before write

## 10. Verification results

Verification scope for this phase:

- new manifest planning tests:
    - `tests/unit/single_league_small_batch_target_manifest_plan.test.js`
- schema-readiness tests:
    - `tests/unit/large_scale_target_inventory_schema_readiness_audit.test.js`
- large-scale acquisition strategy tests:
    - `tests/unit/large_scale_pageprops_v2_acquisition_strategy_plan.test.js`
- parser boundary planning tests:
    - `tests/unit/pageprops_v2_parser_boundary_leakage_plan.test.js`
- raw completeness tests:
    - `tests/unit/pageprops_v2_raw_completeness_audit.test.js`
- canonical read tests:
    - `tests/unit/all_seeded_pageprops_v2_canonical_read_verification.test.js`
    - `tests/unit/RawMatchDataVersionSelector.test.js`
- Makefile planning target:
    - `make data-single-league-small-batch-target-manifest-plan ...`
- full gates:
    - `npm test`
    - `npm run test:coverage`
- quality:
    - `eslint`
    - `prettier --check`
    - `git diff --check`
- safety:
    - DB row counts unchanged
    - `tests/fixtures/l1-config-*` residue absent
    - `docs/_staging_preview` absent
    - PR CI green before merge
    - main push CI green after merge

## 11. Recommended next phases

Because `candidate_targets_count=0`, the next recommended phase is:

### Phase 5.21L2T0

`authorized single-league target discovery / source inventory preflight`

Requirements:

- explicit network authorization required
- no DB write
- no `raw_match_data` write
- discover / validate 20-50 real FotMob external IDs for `Ligue 1 / 2025/2026`
- update manifest proposal
- no parser/features/training

Then:

### Phase 5.21L2T

`single-league small-batch no-write pageProps v2 preflight`

Requirements:

- only after explicit network authorization
- no DB write
- limited 20-50 targets
- capture `stable_pageprops_payload_v1` baseline hashes

Parallel planning track:

### Phase 5.22L2A

`odds raw schema / source / leakage policy planning and existing module audit`

Requirements:

- no odds access
- no DB write
- inspect existing odds modules only

## 12. Explicit non-execution

This phase confirms:

- no DB writes
- no `raw_match_data` writes
- no `bookmaker_odds_history` writes
- no network / FotMob access
- no odds access
- no raw acquisition
- no schema migration
- no `matches` writes
- no parser implementation
- no feature extraction
- no `l3_features` write
- no `match_features_training` write
- no training / prediction
- no browser / proxy
- no full raw_data print / save
- no full pageProps print / save
- no file deletion
- no invented `external_id` / fake target data
