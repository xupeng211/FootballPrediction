<!-- markdownlint-disable MD013 -->

# FotMob Match ID Discovery Route Candidate No Write

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-ROUTE-CANDIDATE-NO-WRITE
- run_id: fotmob_match_id_discovery_route_candidate_v1
- mode: offline
- 本阶段仍然不是 L2 raw harvesting；不写 DB、不写 raw JSON、不保存 response body。

## Current Stage Background

- 从 #1436 source review 进入 route candidate no-write validation。
- 即使解析出 FotMob match_id，也只是 route_candidate，不代表可入库。
- controlled JSON probe no-write 通过前，不考虑 controlled raw JSON dev write。

## #1436 Source Review Inheritance

- input_target_count: 14
- discovery_candidate_count: 76
- reviewed_sources: 6
- bootstrap/primary/secondary/fallback: manual_seed, known_match_page, team_calendar, competition_fixtures
- deferred_sources: date_fixtures, historical_backfill

## Sample Selection Summary

- max_samples: 3
- selected_sample_count: 3
- selected_sources: manual_seed, known_match_page, team_calendar
- selected_targets: [63, 69, 68]

## Route Candidate Construction Summary

| route_candidate_id | source | target_id | team | state | route_code | match_id | stop_reason |
|--------------------|--------|-----------|------|-------|------------|----------|-------------|
| route-01-3ffb0eb6 | manual_seed | 63 | England | route_blocked | null | null | manual_seed_missing_verified_match_id |
| route-02-bfe0912c | known_match_page | 69 | Manchester United | route_blocked | null | null | known_match_page_missing_real_url_fragment |
| route-03-7c00d668 | team_calendar | 68 | Manchester United | route_blocked | null | null | team_calendar_missing_fotmob_team_id |

## Known Page URL Parsing Summary

- known_match_page parser supports `/matches/.../{route_code}#{match_id}` and short `/matches/{route_code}/{match_id}`.
- current selected known_match_page input is redacted, so no current-target real match_id was parsed.

## Manual Seed Parsing Summary

- current manual_seed input lacks a verified match_id/url; it remains route_blocked until a real seed is supplied.

## Team Calendar Route Candidate Summary

- team_calendar is still a suitable long-term primary discovery route, but current candidates lack real FotMob team IDs.

## Network Probe Summary

- network_probe: not performed
- network_requests_attempted: 0
- status_code_summary: {}
- html_detected_count: 0
- json_parse_attempted_count: 0
- json_parse_ok_count: 0

## Route Status Summary

- route_candidate_count: 0
- route_probe_observed_count: 0
- route_blocked_count: 3
- route_invalid_count: 0
- route_validated_count: 0
- json_validated_count: 0

## Raw Write Readiness Gate

- raw_write_eligible_count: 0
- raw_write_blocked_until_json_validated: true
- 必须等 controlled JSON probe no-write 通过后，才考虑 controlled raw JSON dev write。

## No-Write Safety Review

- db_write_performed: false
- raw_json_write_performed: false
- raw_response_body_saved: false
- scheduler_enabled: false
- feature_parse_performed: false

## Remaining Blockers

- 当前 target 仍缺少真实 known_match_page URL fragment 或 verified manual_seed match_id。
- team_calendar 仍缺少真实 FotMob team ID/source identity。
- raw JSON write 仍未授权且仍被 json validation gate 阻断。

## Recommended Next Phase

- FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-KNOWN-MATCH-PAGE-PARSE-NO-WRITE-FOLLOWUP
