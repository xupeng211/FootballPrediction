<!-- markdownlint-disable MD013 -->

# FotMob Ligue 1 ADG60 Payload Acquisition Plan

- lifecycle: phase-artifact
- phase: ADG60-PAYLOAD-ACQUISITION-PLAN
- scope: plan only
- based_on: ADG60 preflight no-write
- based_on: ADG60 raw payload source inventory
- target_count: 32
- current blocker: blocked_missing_payload=32
- no live fetch
- no network fetch
- no browser automation
- no payload save
- no DB write
- no raw write
- no raw_match_data insert
- no schema migration
- no ADG60 write

This PR does not acquire raw payload. It only plans an authorization-gated acquisition workflow.

## Target Scope

- Scope is exactly the 32 ADG59B accepted Ligue 1 targets.
- Do not add matches, discover new targets, or widen the batch.
- Required target fields: target_match_id, corrected_hash_id, corrected_route_hash_pair, expected_home, expected_away, expected_date, competition, canonical_detail_route_or_url_if_available.

## Reusable Reference Paths

- scripts/ops/pageprops_v2_no_write_payload_recapture_plan.js (pageProps v2 planning; reusable_with_guardrails)
- scripts/ops/single_league_pageprops_v2_controlled_write_plan.js (pageProps v2 controlled-write planning reference; reference_only)
- scripts/ops/l2_remaining_raw_match_data_acquisition_preflight.js (raw payload acquisition preflight reference; reusable_with_guardrails)
- scripts/ops/l2_raw_match_data_ingest_plan.js (raw ingest planning reference; reusable_with_guardrails)
- scripts/ops/raw_match_data_completeness_fidelity_audit.js (completeness/source fidelity audit reference; reusable_with_guardrails)
- scripts/ops/fotmob_ligue1_canonical_detail_url_discovery_adg39.js (detail URL / route-hash reference; reusable_with_guardrails)
- scripts/ops/pageprops_v2_continued_detail_endpoint_investigation.js (detail endpoint investigation reference; reusable_with_guardrails)
- scripts/ops/pageprops_v2_detail_api_endpoint_feasibility.js (legacy API feasibility reference; reusable_with_guardrails)

## Dangerous Paths Not To Execute

- scripts/ops/pageprops_v2_no_write_payload_recapture_execute.js: live recapture capable; reference-only until separate authorization
- scripts/ops/pageprops_v2_no_write_preview.js: live preview capable; do not run in this plan phase
- scripts/ops/single_league_small_batch_pageprops_v2_preflight.js: network/detail preflight capable; needs future authorization gate
- scripts/ops/single_league_pageprops_v2_controlled_write_execute.js: controlled raw write execution path; do not use
- scripts/ops/renewed_pageprops_v2_raw_write_execute.js: raw write execution path; do not use
- scripts/ops/l2_raw_match_data_write.js: raw table write path; do not use
- scripts/ops/l2_remaining_raw_match_data_write.js: raw table write path; do not use
- scripts/ops/backfill_historical_raw_match_data.js: historical backfill write-capable path; do not use
- scripts/ops/html_hydration_source_fidelity_live_compare.js: live source compare path; not authorized here
- scripts/ops/fotmob_ligue1_ssr_pageprops_bounded_probe_adg46.js: SSR probe/live page path; not authorized here
- scripts/ops/fotmob_ligue1_ssr_pageprops_discovery_gate_adg46.js: SSR discovery/live page path; not authorized here
- src/infrastructure/services/BrowserProvider.js: browser-capable runtime service; not part of this plan execution

## Proposed Acquisition Strategy

- Preferred path: pageProps v2 planning/preflight references.
- Not preferred: legacy API routes.
- Forbidden in this PR: live recapture, controlled write, raw write execution.

## Authorization Gate Checklist

- exact 32 ADG59B accepted Ligue 1 target scope
- explicit live/network access permission
- explicit browser automation permission or prohibition
- explicit payload persistence permission or prohibition
- allowed storage location
- maximum batch size
- rate limit and delay policy
- separate DB write authorization if ever needed
- separate raw_match_data write authorization if ever needed

## Pre-Execution Checklist

- 32 target identities still match target_match_id, corrected_hash_id, and corrected_route_hash_pair
- no duplicate raw_match_data rows for the 32 targets
- DB invariant unchanged before execution
- output directory clean and explicitly approved
- no full HTML persistence unless separately authorized
- no full pageProps dump unless separately authorized
- payload minimization policy selected
- stable hash generation policy selected
- rollback and cleanup policy documented

## Storage Policy Recommendation

- Do not store full raw payload in docs/_manifests.
- Prefer metadata and stable hashes in source-controlled manifests.
- Use a dedicated non-source-controlled raw external location only if explicitly authorized.
- Add or verify gitignore coverage before any local payload persistence.
- Use external storage for large payloads if retention is required.
- Do not commit full raw payload, full HTML, pageProps, or source body to git.

## Risk Controls

- anti-bot risk: require explicit live access authorization, low batch size, and delay policy
- stale route/hash risk: verify route/hash identity immediately before any future acquisition
- wrong orientation risk: re-check expected home/away/date/competition for all targets
- duplicate raw row risk: SELECT-only duplicate audit before any write authorization
- full HTML persistence risk: default to metadata/hash-only outputs
- DB write risk: keep acquisition and raw write phases separate
- dangerous historical script risk: use only reference paths; do not run write-capable scripts

## Recommended Next Step

- recommended next phase: ADG60-PAYLOAD-ACQUISITION-AUTHORIZATION-GATE
- Next phase should be authorization gate only, not acquisition execution.
