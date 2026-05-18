# Data Entrypoint Governance - Phase 5.21 L2V3B

## A. Current worktree state

- branch=data/post-seed-matches-identity-raw-write-execution-phase521l2v3
- start_head=e3177e6b90721e5a0dc3778d441cae9a8d6f4d92
- phase=hash drift review / renewed baseline readiness planning
- mode=no-write review
- current L2V3 worktree changes were preserved.

Changed / new files at review start:

- AGENTS.md
- Makefile
- docs/\_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json
- docs/\_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3.md
- scripts/ops/renewed_pageprops_v2_raw_write_execute.js
- tests/unit/renewed_pageprops_v2_raw_write_execute.test.js

## B. Protected L2V3 uncommitted changes

- Local patch backup created at `/tmp/footballprediction_l2v3_worktree_backup_20260518T105638Z.patch`.
- No reset, clean, deletion, or baseline overwrite was performed.

## C. 4830466 Hash Drift Fact

- match_id=53_20252026_4830466
- external_id=4830466
- identity=Rennes vs Marseille, 2025-08-15T18:45:00.000Z, status=finished
- baseline_hash=c0365494bedfad7f49c59db649dc52d45bd364e7991f518261085349bebd530b
- L2V3 recaptured_hash=34f7ba2a692b03c4e5d2e0df4eef544569eb9773ba568a8d96a93c78f3962087
- L2V3 result=RECAPTURE_HASH_GATE_BLOCKED
- transaction_began=false
- raw_match_data_inserted=0

## D. Baseline Hash Source Analysis

- Baseline source phase: Phase 5.21L2T single-league small-batch pageProps v2 no-write preflight.
- Baseline report: `docs/_reports/SINGLE_LEAGUE_SMALL_BATCH_PAGEPROPS_V2_PREFLIGHT_PHASE5_21L2T.md`.
- Baseline script: `scripts/ops/single_league_small_batch_pageprops_v2_preflight.js`.
- Baseline function path:
    - `buildSuccessfulTargetSummary()`
    - `buildPagePropsV2Candidate()`
    - `computeStablePagePropsHash(pageProps)`
- Baseline for 4830466 was recorded as `hash_baseline_ready`.
- Baseline payload summary for 4830466:
    - http_status=200
    - parse_status=pageprops_v2_parsed
    - pageProps_path_count=2916
    - pageProps_content_path_count=365
    - block_markers=[]

## E. Recaptured Hash Generation Path Analysis

- L2V3 runner: `scripts/ops/renewed_pageprops_v2_raw_write_execute.js`.
- L2V3 recapture helper reused: `scripts/ops/single_league_pageprops_v2_controlled_write_execute.js`.
- Fetch path: direct `https://www.fotmob.com/match/<external_id>` HTML hydration fetch.
- Parser path:
    - `extractNextDataJsonFromHtml()`
    - `getPageProps()`
    - `buildRawDataForTarget()`
    - `computeStablePagePropsHash(pageProps)`
- No browser/proxy/captcha bypass was used.
- No full body, full JSON, raw_data, or pageProps was printed or saved.

## F. Canonicalization / stable_pageprops_payload_v1 Consistency Check

- Shared hash function: `scripts/ops/pageprops_v2_no_write_preview.js`.
- `computeStablePagePropsHash(pagePropsOrCandidate)` hashes canonical JSON after extracting `pageProps` when a candidate wrapper is provided.
- `canonicalizeJson()` recursively sorts object keys and preserves array order.
- `_meta`, fetch URL, body hash, generated_at, and collected_at are excluded when hashing a candidate wrapper.
- Unit coverage exists for:
    - stable hash excludes `_meta`
    - stable hash changes when pageProps content changes
    - stable hash is 64 hex
    - controlled writer data_hash equals baseline hash
- Review conclusion: baseline and L2V3 recapture use the same hash algorithm. The mismatch is not explained by a known implementation split.

## G. No-Write Recapture Stability Result

Repeated no-write recapture for 4830466:

| attempt | http_status | parsed | hash                                                             | matches_baseline | body_bytes | candidate_json_bytes | pageProps_paths | content_paths | block_markers |
| ------- | ----------- | ------ | ---------------------------------------------------------------- | ---------------- | ---------- | -------------------- | --------------- | ------------- | ------------- |
| repeat1 | 200         | true   | 34f7ba2a692b03c4e5d2e0df4eef544569eb9773ba568a8d96a93c78f3962087 | false            | 1124805    | 435040               | 10224           | 7396          | []            |
| repeat2 | 200         | true   | 34f7ba2a692b03c4e5d2e0df4eef544569eb9773ba568a8d96a93c78f3962087 | false            | 1124805    | 435040               | 10224           | 7396          | []            |

Result:

- repeated_primary_hashes_identical=true
- current payload appears stable across repeated no-write recapture
- current structure is much larger than the L2T baseline summary for the same target

## H. Extended Target Check

Two additional manifest candidates were checked no-write:

| external_id | match_id            | baseline_paths | recaptured_paths | hash_match | recaptured_hash                                                  |
| ----------- | ------------------- | -------------- | ---------------- | ---------- | ---------------------------------------------------------------- |
| 4830461     | 53_20252026_4830461 | 2915           | 10071            | false      | f29ee7f91736e05d978cc55610ecf3328222e38a6d4ff6fdb33f1048cbdc4a37 |
| 4830463     | 53_20252026_4830463 | 9396           | 9396             | true       | 519a171d16190df970026046d067f8acf10e9489e3d57a1c269278799199ea83 |

Manifest baseline structure distribution:

- candidate_count=50
- low path-count baselines `<4000`=5
- high path-count baselines `>=8000`=45

## I. Drift Classification

- Classification: partial_systemic_stable_content_drift.
- Rationale:
    - 4830466 drift is stable across repeated recapture.
    - One additional low path-count baseline also drifted.
    - One high path-count baseline still matched exactly.
    - This does not look like random hash instability.
    - This suggests a subset of baselines may have captured smaller pageProps content than the current page serves.
- Current evidence is insufficient to safely refresh baseline or write raw rows in this phase.

## J. Need for New Baseline Planning

- New baseline planning is needed before any renewed raw write retry.
- Baseline hashes must not be edited in this phase.
- Recommended next phase:
    - Phase 5.21L2V3C: renewed baseline regeneration planning / no-write manifest proposal
    - no DB write
    - no raw_match_data insert
    - no parser/features/training
    - produce a reviewable proposal for handling the 5 low path-count baseline targets and any other detected drift

## K. Explicit Non-Execution

- no DB writes
- no raw_match_data inserts
- no matches writes
- no bookmaker_odds_history writes
- no l3_features writes
- no match_features_training writes
- no predictions writes
- no schema migration
- no parser implementation
- no feature extraction
- no training/prediction
- no browser/proxy/captcha bypass
- no full raw_data/pageProps/source body print/save
- no baseline_hash modification to pass a gate
- no hash gate bypass
- no file deletion
- no git reset or clean

## L. Recommended Next Step

Proceed to Phase 5.21L2V3C only after explicit authorization:

- no-write renewed baseline regeneration planning
- review low path-count targets as a distinct risk group
- define whether future raw write should use full new baselines for all 50 or a reduced/segmented target set
- require separate renewed final DB-write authorization before any raw_match_data write retry

## M. Validation and DB Safety Result

Validation completed after the no-write review:

- L2V3 execution tests: passed
- stable pageProps hash / no-write preview tests: passed
- L2T preflight tests: passed
- L2V controlled write execution tests: passed
- L2V2 readiness audit tests: passed
- L2U controlled write planning tests: passed
- FotMobRawDetailFetcher tests: passed
- RawMatchDataVersionSelector tests: passed
- npm test: passed
- npm run test:coverage: passed
- eslint: passed
- prettier: passed
- git diff --check: passed
- manifest JSON parse: passed
- full payload safety scan for changed docs/manifest: passed
- l1-config residue check: passed
- docs/\_staging_preview absence check: passed

SELECT-only DB safety check after L2V3B:

- matches=60
- raw_match_data=18
- bookmaker_odds_history=2
- l3_features=2
- match_features_training=2
- predictions=2
- candidate_targets=50
- candidate_matches_found=50
- candidate_fotmob_pageprops_v2_rows=0
- raw_match_data UNIQUE(match_id,data_version) present=true
- old UNIQUE(match_id) absent=true
