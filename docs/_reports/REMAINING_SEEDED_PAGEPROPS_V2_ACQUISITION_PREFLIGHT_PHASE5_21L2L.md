# Remaining Seeded PageProps V2 Acquisition Preflight - Phase 5.21L2L

## 1. Executive summary

Phase 5.21L2K verified canonical reads after the first `fotmob_pageprops_v2`
insert for `4830747`. The selector now picks v2 for that target, falls back to
`fotmob_html_hyd_v1` for seeded matches without v2, and excludes synthetic /
legacy / unknown versions by default.

This phase adds planning and preflight support for the remaining seven seeded
matches. It is no-write: the script performs SELECT-only DB checks, authorized
sequential HTML hydration recapture, in-memory `fotmob_pageprops_v2` candidate
construction, and `stable_pageprops_payload_v1` hash reporting.

Parser/features/training/prediction remain deferred.

## 2. Current DB baseline

Expected baseline before and after this phase:

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

## 3. Target inventory

The script must derive teams and metadata from `matches`, not hard-coded report
text. Current read-only inventory:

| match_id              | external_id | home_team           | away_team  | existing_versions    | v2 status |
| --------------------- | ----------- | ------------------- | ---------- | -------------------- | --------- |
| `53_20252026_4830746` | `4830746`   | Angers              | Strasbourg | `fotmob_html_hyd_v1` | absent    |
| `53_20252026_4830748` | `4830748`   | Le Havre            | Marseille  | `fotmob_html_hyd_v1` | absent    |
| `53_20252026_4830750` | `4830750`   | Metz                | Lorient    | `fotmob_html_hyd_v1` | absent    |
| `53_20252026_4830751` | `4830751`   | Monaco              | Lille      | `fotmob_html_hyd_v1` | absent    |
| `53_20252026_4830752` | `4830752`   | Paris Saint-Germain | Brest      | `fotmob_html_hyd_v1` | absent    |
| `53_20252026_4830753` | `4830753`   | Rennes              | Paris FC   | `fotmob_html_hyd_v1` | absent    |
| `53_20252026_4830754` | `4830754`   | Toulouse            | Lyon       | `fotmob_html_hyd_v1` | absent    |

`4830747` is intentionally excluded because Phase 5.21L2J already inserted its
`fotmob_pageprops_v2` row.

## 4. Live preflight result

The post-merge live no-write preflight must run only after PR CI and main push CI
are green. It must use:

```bash
make data-remaining-seeded-pageprops-v2-acquisition-preflight \
  SOURCE=fotmob \
  ROUTE=html_hydration \
  TARGET_EXTERNAL_IDS=4830746,4830748,4830750,4830751,4830752,4830753,4830754 \
  CANDIDATE_VERSION=fotmob_pageprops_v2 \
  HASH_STRATEGY=stable_pageprops_payload_v1 \
  NETWORK_AUTHORIZATION=yes \
  PAGEPROPS_V2_REMAINING_PREFLIGHT_AUTHORIZATION=yes \
  ALLOW_DB_WRITE=no \
  ALLOW_RAW_MATCH_DATA_WRITE=no \
  ALLOW_MATCHES_WRITE=no \
  ALLOW_PARSER_FEATURES=no \
  ALLOW_TRAINING=no \
  ALLOW_PREDICTION=no \
  CONCURRENCY=1 \
  RETRY=0 \
  PRINT_BODY=no \
  SAVE_BODY=no \
  PRINT_FULL_JSON=no \
  SAVE_FULL_JSON=no
```

Post-merge execution records per target:

- `request_url`
- `final_url`
- `http_status`
- `content_type`
- `body_byte_length`
- `body_sha256`
- `stable_pageprops_hash`
- pageProps top-level keys
- path counts and content path counts
- v1/v2 comparison counts
- `decision`

## 5. Baseline hashes for next controlled write

To be filled from the post-merge no-write preflight output:

| external_id | stable_pageprops_payload_v1 hash |
| ----------- | -------------------------------- |
| `4830746`   | post-merge preflight output      |
| `4830748`   | post-merge preflight output      |
| `4830750`   | post-merge preflight output      |
| `4830751`   | post-merge preflight output      |
| `4830752`   | post-merge preflight output      |
| `4830753`   | post-merge preflight output      |
| `4830754`   | post-merge preflight output      |

## 6. Write decision

Expected preflight decision:

- `attempted_target_count=7`
- `would_insert_count=7`
- `would_update_count=0`
- `would_skip_count=0`
- conflict target for next phase: `(match_id,data_version)`
- expected `raw_match_data` after future controlled write: `11 -> 18`

No write is executed in this phase.

## 7. Safety verification

Required safety checks:

- no DB write
- `raw_match_data` remains 11
- protected tables remain unchanged
- no browser/proxy
- no retry
- no full HTML body print/save
- no full pageProps JSON print/save
- no parser/features/training/prediction

## 8. Next phase recommendation

Recommended next phase:

`Phase 5.21L2M: remaining seeded matches pageProps v2 controlled write`

Requirements:

- explicit final DB-write confirmation
- use Phase 5.21L2L hashes as baselines
- recapture each target sequentially before write
- each recaptured hash must match the baseline
- insert exactly seven `fotmob_pageprops_v2` rows
- `raw_match_data` moves from `11 -> 18`
- keep existing v1 rows
- no parser/features/training

If any target hash drifts or recapture fails, the recommended default is to block
the whole write. A reduced target set should require separate user authorization.

## 9. Explicit non-execution

This phase does not perform:

- DB writes
- `raw_match_data` writes
- `matches` writes
- schema migration
- parser/features
- harvest/ingest/backfill
- training/prediction
- browser/proxy
- retry
- full body save/print
- full JSON save/print
- file deletion
