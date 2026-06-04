<!-- markdownlint-disable MD013 -->

# FotMob Target Selection DB Dry-run

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-TARGET-SELECTION-DB-DRY-RUN
- run_id: fotmob_target_selection_db_dry_run_v1
- db_environment: docker_dev
- production_db_guard: pass
- db_read_performed: true
- db_write_performed: false

## Result

- input_target_count: 14
- selected_target_count: 10
- skipped_target_count: 4
- skip_reason_summary: blocked=1, budget_exhausted=2, stored=1
- sort_policy: priority_desc_match_date_asc_competition_team_source_match_id

## Selected Targets

| # | source_match_id | teams | competition | priority | target_state | raw_json_status |
|---|-----------------|-------|-------------|----------|--------------|-----------------|
| 1 | fixture-eng-friend-001 | England, Brazil | International Friendly | 20 | pending_raw_fetch | missing |
| 2 | fixture-champ-facup-001 | Leeds United, Sheffield Wednesday | FA Cup | 18 | pending_raw_fetch | missing |
| 3 | fixture-jpn-empcup-001 | Kashima Antlers, Urawa Red Diamonds | Emperor's Cup | 17 | pending_raw_fetch | missing |
| 4 | fixture-champ-001 | Leeds United, Sunderland | EFL Championship | 16 | pending_raw_fetch | missing |
| 5 | fixture-jpn-j1-001 | Kashima Antlers, Yokohama F. Marinos | J1 League | 15 | pending_raw_fetch | missing |
| 6 | fixture-mun-eflcup-001 | Newcastle United, Manchester United | EFL Cup | 14 | pending_raw_fetch | missing |
| 7 | fixture-eng-failed-001 | England, Italy | UEFA Nations League | 13 | pending_raw_fetch | failed |
| 8 | fixture-mun-facup-001 | Manchester United, Chelsea | FA Cup | 12 | pending_raw_fetch | missing |
| 9 | fixture-mun-uel-001 | Manchester United, AS Roma | UEFA Europa League | 11 | pending_raw_fetch | missing |
| 10 | fixture-mun-epl-001 | Manchester United, Liverpool | Premier League | 10 | pending_raw_fetch | missing |

## Skipped Targets

| # | source_match_id | teams | competition | priority | target_state | raw_json_status | skip_reason |
|---|-----------------|-------|-------------|----------|--------------|-----------------|-------------|
| 1 | fixture-mun-blocked-001 | Manchester United, Tottenham Hotspur | Premier League | 9 | blocked | missing | blocked |
| 2 | fixture-eng-unl-001 | Germany, England | UEFA Nations League | 8 | pending_raw_fetch | missing | budget_exhausted:request |
| 3 | fixture-mun-stored-001 | Manchester United, Everton | Premier League | 7 | raw_json_stored | stored | stored |
| 4 | fixture-eng-wcq-001 | England, Poland | FIFA World Cup Qualifier | 5 | pending_raw_fetch | missing | budget_exhausted:request |

## Budget Result

- request_budget: 10
- selected_count: 10
- per_team_budget: 5
- per_competition_budget: 4
- request_budget_respected: true
- per_team_budget_respected: true
- per_competition_budget_respected: true

## Source Identity Result

- all_selected_have_source_identity: true
- unsupported_source_selected: false

## Team Full-calendar Result

- Manchester United: 6
- England: 4
- Kashima Antlers: 2
- Leeds United: 2
- Manchester United competitions: Premier League, FA Cup, EFL Cup, UEFA Europa League
- England competitions: FIFA World Cup Qualifier, UEFA Nations League, Friendly
- Kashima Antlers competitions: J1 League, Emperor's Cup
- Leeds United competitions: EFL Championship, FA Cup

## Safety

- no live fetch
- no DB write
- no raw JSON write
- no fotmob_raw_match_payloads write
- no raw_match_data write
- no scheduler
- no feature parse
- raw_write_ready_marked=false

## Remaining Gaps

- 还没有 live fetch availability probe
- 还没有 raw JSON write authorization
- 还没有 collector scheduler
- 还没有 parser/features/training/prediction

## Recommended Next Phase

- FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ONE-DAY-LIVE-FETCH-NO-RAW-WRITE
- 仅建议极少量 selected targets 做 no-write live fetch availability probe
- 不推荐直接大规模入库、scheduler 或 production rollout
