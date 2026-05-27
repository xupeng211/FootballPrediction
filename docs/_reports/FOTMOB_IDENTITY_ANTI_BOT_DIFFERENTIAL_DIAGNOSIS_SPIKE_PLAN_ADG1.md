# FotMob Identity / Anti-Bot Differential Diagnosis Spike Plan ADG1

> Date: 2026-05-27
> Phase: Phase 5.21-ADG1
> Scope: spike planning only

## 1. Decision Gate Context

PR #1334 merged the Architecture Decision Gate after L2V3BC triggered the no-progress stop rule:

- clean_candidate_count=0
- rejected_mapping_count=0
- superseded_mapping_count=0
- eligible_for_re_acceptance_review_count=0
- needs_new_evidence_target_count=42
- suspended_target_count=8
- architecture_decision_gate_triggered=true
- no_progress_stop_rule_triggered=true
- current_raw_write_route_paused=true
- current_50_target_batch_not_raw_write_ready=true
- raw_write_execution_ready=false

ADG1 is not another ordinary L2V3BD review/planning phase. It only plans a bounded diagnostic spike to determine why schedule, URL, detail route, and observed payload identities do not line up reliably.

## 2. Planning Goal

ADG2, if separately authorized later, should answer these questions:

- How do `schedule_external_id`, URL path slug, URL hash match id, detail request id, and observed payload id correspond?
- Does discovery extract URL hash ids like `#4813735`?
- Does enrichment persist the URL hash id as `source_url_fragment_external_id`?
- Does the recapture runner incorrectly use `schedule_external_id` when a distinct detail/hash identity should be used?
- Do direct API and browser/page-route access return different identities?
- Do anti-bot, header, session, redirect, locale, or region differences change the returned payload?
- Is a second data source needed for canonical fixture identity?

## 3. Current Local Chain To Audit

Source-controlled code already contains URL evidence fields, but the current 50-target batch still needs new evidence:

- `FotMobSourceInventoryAdapter` parses `pageUrl`/`matchUrl`/`href`/`url` into `source_page_url`, `source_page_url_base`, `source_url_fragment_external_id`, `source_slug`, and `source_route_code` when those values exist.
- `source_inventory_enrichment` keeps `schedule_external_id` separate from URL fragment evidence.
- `FotMobRouteIdentityReconciler` treats `schedule_external_id` as a correlation key, not default detail route identity.
- The recapture path blocks without a re-accepted mapping/baseline and an accepted detail identity.

ADG2 must verify whether those intended contracts hold against real source inventory and detail page behavior, but ADG1 does not execute that verification.

## 4. Positive Sample

The spike must include the user-provided positive sample:

| Field                          | Value                                                                                                                                                                                         |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| name                           | AFC Bournemouth vs Manchester City                                                                                                                                                            |
| source_page_url                | `https://www.fotmob.com/zh-Hans/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813735`                                                                                                    |
| URL path slug / route fragment | `2feiv3`                                                                                                                                                                                      |
| URL hash id                    | `4813735`                                                                                                                                                                                     |
| expected teams                 | AFC Bournemouth vs Manchester City                                                                                                                                                            |
| purpose                        | Verify discovery can extract URL hash id `4813735` and that downstream recapture/identity logic considers it as a detail identity candidate rather than blindly using `schedule_external_id`. |

This sample is a diagnostic control for URL hash extraction. It is not authorization to fetch the URL in ADG1.

## 5. Planned Sample Groups

ADG2 should stay bounded:

- Positive URL-hash sample: 1 sample, the `#4813735` FotMob URL above.
- Suspended targets: exactly 8 known schedule -> observed mismatches:
    - 4830461 -> 4830758
    - 4830463 -> 4830622
    - 4830465 -> 4830619
    - 4830466 -> 4830759
    - 4830481 -> 4830763
    - 4830496 -> 4830757
    - 4830508 -> 4830620
    - 4830511 -> 4830760
- `needs_new_evidence` targets: sample 8 of 42:
    - 4830460, 4830458, 4830459, 4830462
    - 4830464, 4830473, 4830471, 4830472
- Old-good samples: unavailable as a user-described old-code evidence group. Repository search did not locate source-controlled evidence proving "old code fetched these correctly." Do not fabricate this group. Existing seeded `fotmob_pageprops_v2` rows may be used later as a separate known-good storage control, not as proof of the old-code claim.

## 6. Planned Diagnostic Fields

Each ADG2 sample should compare only safe summaries:

- `schedule_external_id`
- `source_inventory_record_key`
- `source_page_url`
- URL path slug / route fragment, for example `2feiv3`
- URL hash id, for example `4813735`
- `accepted_detail_external_id`, if any
- detail request id to be used
- observed payload match id
- observed detail external id
- home team
- away team
- match date/time
- league / season
- status / score
- content-type
- HTTP status
- redirect chain
- locale / language
- anti-bot signs: 401, 403, captcha, block page, HTML instead of expected data, missing hydration data, header/session requirement
- browser/page-route result vs direct API result, only if future execution is explicitly authorized

## 7. Planned Classification Output

ADG2 must classify each sample into one or more of:

- URL hash id not extracted
- URL hash id extracted but not persisted
- URL hash id persisted but not used by recapture runner
- schedule_external_id incorrectly used as detail id
- direct API identity differs from browser/page route identity
- missing headers/session/locale/region contract
- anti-bot/block/captcha/403/401 issue
- reverse fixture / home-away inversion
- current 50-target source inventory candidate generation defect
- second source required for canonical fixture identity
- unknown / insufficient evidence

## 8. ADG2 Execution Boundaries

ADG2 requires separate explicit authorization. Default execution constraints:

- no DB write
- no raw write
- no `raw_match_data` insert/update
- no `matches` write or `matches.external_id` change
- no parser/features/training/prediction
- no re-acceptance
- no rollback
- no full raw_data/pageProps/source body saved or printed
- no captcha bypass
- no proxy bypass
- no uncontrolled retry
- no large-scale fetch
- bounded sample count only

If ADG2 is authorized to use network/browser/API, it may store only safe summaries: identity fields, HTTP status, content-type, redirect count/hosts, hashes, counts, and blocker tags. Any sample that hits 401, 403, captcha, block page, or identity mismatch must record the blocker and stop that sample.

## 9. ADG1 Safety Status

- spike_execution_performed=false
- live_fetch_performed=false
- detail_fetch_performed=false
- network_request_performed=false
- browser_automation_performed=false
- db_write_performed=false
- raw_match_data_insert_performed=false
- raw_write_execution_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- re_acceptance_execution_performed=false
- suspension_reversal_performed=false
- rollback_execution_performed=false
- parser_features_training_prediction_performed=false

## 10. Recommended Next Step

Phase 5.21-ADG2 may execute the bounded FotMob identity / anti-bot differential diagnosis spike only after explicit separate authorization. ADG1 does not authorize ADG2.
