# FotMob Identity / Anti-Bot Differential Diagnosis Result ADG2

> Date: 2026-05-27
> Phase: Phase 5.21-ADG2
> Scope: bounded read-only diagnosis execution

## 1. Execution Boundary

ADG2 executed only the bounded diagnosis authorized after PR #1335 merged and main Production Gate passed.

- adg2_execution_performed=true
- live_fetch_performed=true
- network_request_performed=true
- browser_automation_performed=false
- db_write_performed=false
- raw_write_execution_performed=false
- raw_match_data_insert_performed=false
- re_acceptance_execution_performed=false
- suspension_reversal_performed=false
- rollback_execution_performed=false
- full_payload_saved=false
- full_payload_printed=false
- uncontrolled_retry_performed=false
- captcha_bypass_performed=false
- proxy_bypass_performed=false
- bulk_fetch_performed=false
- raw_write_execution_ready=false

No full HTML, JSON, pageProps, raw_data, or source body was saved or printed. The network step produced only status, content-type, redirect summary, hashes, byte counts, marker booleans, and blocker tags.

## 2. Positive Sample URL Parsing

Positive sample:

`https://www.fotmob.com/zh-Hans/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813735`

Parsed result:

- parsed_url_path_slug=`2feiv3`
- parsed_url_hash_id=`4813735`
- hash_id_numeric=true
- hash_id_available_before_http_request=true
- URL fragment is not sent to the server by normal HTTP requests, so the hash id must be parsed from the href/string before request.

## 3. Discovery Chain Diagnosis

Inspected code paths:

- `FotMobSourceInventoryAdapter.parseSourcePageUrl`
- `FotMobSourceInventoryAdapter.deriveSourceInventoryIdentityEvidence`
- `pageprops_v2_source_inventory_enrichment_apply.parseSourcePageUrl`
- `pageprops_v2_controlled_source_inventory_acquisition_execute.safeSourceRecord`

Findings:

- discovery_extracts_hash_id=true
- discovery_persists_hash_id=true
- source_url_fragment_external_id_supported=true
- source inventory artifact has `source_page_url`, `source_page_url_base`, `source_url_fragment_external_id`, and record keys for all 50 candidate records.
- current active proposal candidate targets sampled in ADG2 do not carry `source_page_url` or `source_url_fragment_external_id`.

This means the problem is not that the repository lacks hash parsing support. The gap is that source inventory hash evidence is not propagated into the active candidate manifest/recapture decision path as canonical detail identity evidence.

## 4. Recapture Identity Usage Diagnosis

Inspected code paths:

- `FotMobRouteIdentityReconciler.resolveRecaptureIdentityContract`
- `pageprops_v2_no_write_payload_recapture_execute`
- `pageprops_v2_recapture_runner_identity_input_contract_fix_implementation_aw.test`
- prior blocker artifact `phase521l2v3ap`

Current behavior:

- recapture_uses_detail_identity_candidate=true when a re-accepted `accepted_detail_external_id` exists.
- recapture_falls_back_to_schedule_external_id=false in the current guarded path.
- fallback_blocked_when_not_reaccepted=true.
- blind_schedule_route_blocked=true.

Prior artifact evidence still matters: the older AO runner path used a schedule match route for `4830466`, and that was correctly recorded as a runner input contract issue. The current L2V3AW guard fixes the unsafe fallback by blocking recapture until a re-accepted detail identity exists.

## 5. Positive Sample Network Diagnosis

Only two bounded public requests were made for the positive sample:

1. Page route without URL fragment:
   `https://www.fotmob.com/zh-Hans/matches/manchester-city-vs-afc-bournemouth/2feiv3`
2. Known direct API route:
   `https://www.fotmob.com/api/data/matchDetails?matchId=4813735`

Safe summary:

| Route      | HTTP | content-type               | redirects | marker / blocker                                 |
| ---------- | ---: | -------------------------- | --------: | ------------------------------------------------ |
| page route |  200 | `text/html; charset=utf-8` |         0 | hydration marker present; expected teams present |
| direct API |  403 | `application/json`         |         0 | blocked/access marker; no observed payload id    |

Additional safe page route summary:

- page_body_sha256=`1d65dd396c47e9528f1e474d0c884cfa069ede9384c25e59b3759d93d57c7984`
- page_body_byte_length=1005956
- next_data_marker_present=true
- hydration_marker_present=true
- expected_hash_id_occurrences=21
- expected team markers present=true
- page_anti_bot_signs=[]

Direct API summary:

- direct_api_http_status=403
- direct_api_body_sha256=`9f36e31930368263ca03ccd40f8ad36ddc178b25211d7b4bf0cbc2c1f6fa7558`
- direct_api_body_byte_length=61
- direct_api_parse_ok=true
- observed_payload_match_id=null
- direct_api_anti_bot_signs=`403`, `block_or_captcha_marker`

Browser automation was not used. Because direct API returned 403, browser/page-route vs direct API identity could not be compared; the route-level result is `page_route_available_but_direct_api_blocked_identity_not_comparable`.

## 6. Suspended Sample Diagnosis

ADG2 inspected three suspended targets from source-controlled artifacts only:

| schedule_external_id | observed_detail_external_id | source URL fragment | route code | classification                                                                                                           |
| -------------------- | --------------------------- | ------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------ |
| 4830461              | 4830758                     | 4830461             | 2s3gtg     | url_hash_id_persisted_but_not_used; reverse_fixture_or_home_away_inversion; source_inventory_candidate_generation_defect |
| 4830463              | 4830622                     | 4830463             | 362v61     | url_hash_id_persisted_but_not_used; reverse_fixture_or_home_away_inversion; source_inventory_candidate_generation_defect |
| 4830465              | 4830619                     | 4830465             | 38dxtn     | url_hash_id_persisted_but_not_used; reverse_fixture_or_home_away_inversion; source_inventory_candidate_generation_defect |

All three have complete source inventory hash evidence, but prior bounded review classified them as reverse fixture / large date gap identity mismatches. The schedule-side URL hash is not enough to re-accept or raw write.

## 7. Needs-New-Evidence Sample Diagnosis

ADG2 inspected three `needs_new_evidence` targets from source-controlled artifacts only:

| schedule_external_id | source URL fragment | route code | observed_detail_external_id | classification                                                    |
| -------------------- | ------------------- | ---------- | --------------------------- | ----------------------------------------------------------------- |
| 4830460              | 4830460             | 2fo2ub     | null                        | url_hash_id_persisted_but_not_used; unknown_insufficient_evidence |
| 4830458              | 4830458             | 1qlitv     | null                        | url_hash_id_persisted_but_not_used; unknown_insufficient_evidence |
| 4830459              | 4830459             | 2gteq5     | null                        | url_hash_id_persisted_but_not_used; unknown_insufficient_evidence |

These targets have source inventory URL hash evidence, but source-controlled review artifacts do not contain observed detail identity evidence sufficient for raw write or re-acceptance.

## 8. Classification Summary

- url_hash_id_not_extracted=0
- url_hash_id_extracted_but_not_persisted=0
- url_hash_id_persisted_but_not_used=6
- schedule_external_id_incorrectly_used_as_detail_id=0 for current guarded recapture path
- missing_request_contract_headers_session_locale_region=1
- anti_bot_or_access_block=1
- reverse_fixture_or_home_away_inversion=3
- source_inventory_candidate_generation_defect=3
- unknown_insufficient_evidence=3

## 9. Likely Root Cause

Likely root causes:

1. Source inventory hash identity exists, but it is not propagated into the active candidate manifest / recapture decision path as usable detail identity evidence.
2. Current raw write route was correctly paused because accepted detail identity is not established for mismatched targets.
3. Public page route can return hydration for the positive sample, while direct `matchDetails` API returns 403 without a usable request contract.
4. Suspended samples show reverse fixture evidence, so schedule-side hash/slug alone is insufficient for raw write or re-acceptance.

## 10. Recommended Next Step

Plan runtime implementation for a URL-hash/detail-external-id identity pipeline:

- propagate `source_url_fragment_external_id` from source inventory into active candidates;
- treat URL hash id as detail identity evidence requiring validation, not as automatic acceptance;
- keep recapture blocked unless a validated detail identity is bound by the current identity contract;
- review the direct `matchDetails` API request contract because the positive sample returned 403;
- do not raw write, do not re-accept, and do not bulk recapture.
