<!-- markdownlint-disable MD013 -->

# FotMob Ligue 1 ADG60 Payload Acquisition Live Fetch One Target No Write

- lifecycle: phase-artifact
- phase: ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-ONE-TARGET-NO-WRITE
- scope: one target live fetch, no write
- based_on: ADG60 preflight no-write; ADG60 raw payload source inventory; ADG60 payload acquisition plan; ADG60 authorization gate; ADG60 dry-run no-write; ADG60 live-fetch authorization
- target_count: 32
- selected_target_count: 1
- no response body persisted
- no DB write
- no raw write
- no raw_match_data insert
- no schema migration
- no ADG60 write

## Selected Target

- target_index: 1
- target_match_id: 53_20252026_4830473
- expected_home: Paris Saint-Germain
- expected_away: Angers
- expected_date: 2025-08-22
- competition: Ligue 1
- corrected_hash_id: 4830473
- corrected_route_hash_pair: 2o4ahb#4830473
- selected_reason: Default first target (smallest target_index=1) from dry-run matrix
- preflight_identity_status: accepted_suspension_resolved
- preflight_route_status: route_hash_pair_available

## Preflight Result

- preflight_passed: true
- execute_live_fetch_requested: true

| Check | Pass | Note |
| --- | --- | --- |
| exactly_one_target_selected | true |  |
| target_count_total_32 | true |  |
| expected_home_exists | true |  |
| expected_away_exists | true |  |
| expected_date_exists | true |  |
| competition_exists | true |  |
| corrected_hash_id_exists | true |  |
| corrected_route_hash_pair_exists | true |  |
| url_constructed | true |  |
| browser_automation_allowed | false | browser automation not allowed in this PR |
| payload_body_persistence_allowed | false | body persistence not allowed in this PR |
| db_write_allowed | false | DB write not allowed |
| raw_write_allowed | false | raw write not allowed |
| raw_match_data_insert_allowed | false | raw_match_data insert not allowed |
| adg60_write_allowed | false | ADG60 write not allowed |

## Request Policy

- method: GET
- url: <https://www.fotmob.com/matches/2o4ahb/4830473>
- route_hash: 2o4ahb
- match_id: undefined
- max_network_requests: 1
- timeout_ms: 20000
- redirect: manual
- browser_automation: false
- retry: false
- parallelism: false
- body_persistence: false

## Execution Result

- request_performed: true
- request_count: 1
- http_status: 200
- final_url: <https://www.fotmob.com/matches/2o4ahb/4830473>
- redirected: false
- content_type: text/html; charset=utf-8
- byte_size: 281623
- sha256: d8081fc11823e5c0de014b71bb00fc14ee43cfdf1a286d10a86920abb74cab5a
- payload_like: true

### Minimal Schema Flags

- hasNextDataMarker: true
- hasPagePropsMarker: true
- hasPropsMarker: true
- looksLikeJson: false
- looksLikeHtml: true
- hasMatchDetails: true
- hasGeneral: false
- hasContent: false
- hasTeamColorsPageProps: false
- body_persisted: false
- body_logged: false
- body_committed: false

## Safety

- live_fetch_performed: true
- network_fetch_performed: true
- browser_automation_performed: false
- payload_saved: false
- response_body_saved: false
- acquisition_execution_performed: true
- db_write_performed: false
- raw_write_performed: false
- raw_match_data_insert_performed: false
- schema_migration_performed: false
- adg60_write_performed: false
- raw_write_ready_marked: false

## Stop Conditions

- target identity mismatch
- home/away orientation mismatch
- expected date mismatch
- competition mismatch
- missing corrected_hash_id
- missing route hash
- selected target count exceeded 1
- network request count would exceed 1
- output directory not clean
- body would be persisted
- DB write attempted
- raw_match_data insert attempted
- browser automation attempted in this PR
- 403 / 429 / captcha / anti-bot / blocked response
- unexpected redirect
- unexpected schema / payload structure
- payload too large (> 5 MB)
- more targets than authorized batch
- any retry loop

## Recommended Next Phase

- recommended next phase: ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-ONE-TARGET-NO-WRITE-REVIEW
- Review the one-target live fetch result before any further target.
- No automatic progression to next target.
- DB/raw/raw_match_data writes remain prohibited.
- If body was not persisted, next phase still requires separate body persistence authorization.
