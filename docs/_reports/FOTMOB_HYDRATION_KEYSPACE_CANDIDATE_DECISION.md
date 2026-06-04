<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->
# FotMob Hydration Keyspace Candidate Decision

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-KEYSPACE-REVIEW-NO-WRITE decision
- run_id: fotmob_hydration_keyspace_review_no_write_v1
- mode: controlled

## Keyspace Scan Result

- __NEXT_DATA__ parse count: 2
- pageProps present count: 2
- fallback present count: 2
- total key paths recorded: (见每个 result entry)
- target match_id in key path: (见每个 result entry)
- route_code in key path: (见每个 result entry)
- strong_path_candidate_count: 0
- weak_path_candidate_count: 0
- partial_path_candidate_count: 698
- generic_or_irrelevant_path_count: 302

- best candidate path: props.pageProps.fetchingLeagueData
- best candidate score: 1
- best route variant: default

## Generic Paths Excluded

- notableMatches (score=-4 penalty + -5 generic-only, excludes from candidates)
- translations subtree (score=-4, generic config penalty)
- CountryCodes / Language / static config (score=-3 to -5)

## Per-Result Details

### keyspace-s01 — 4813722 (variant=default)

- validation_state: keyspace_review_completed
- next_data_parse_ok: True
- pageProps_present: True
- fallback_present: True
- key_paths_recorded: 500
- target_match_id_in_key_path: False
- positive_candidate_path_count: 465
- top candidates: props.pageProps.fetchingLeagueData, props.pageProps.fallback./api/translationmapping?locale=en.TournamentTemplates, props.pageProps.fallback./api/translationmapping?locale=en.TournamentTemplates.42, props.pageProps.fallback./api/translationmapping?locale=en.TournamentTemplates.50, props.pageProps.fallback./api/translationmapping?locale=en.TournamentTemplates.65
- top scores: [1, 1, 1, 1, 1]
- generic rejected: props.pageProps.fallback.notableMatches:en:USA, props.pageProps.fallback.notableMatches:en:USA.matches

### keyspace-s01 — 4813722 (variant=zh-Hans)

- validation_state: keyspace_review_completed
- next_data_parse_ok: True
- pageProps_present: True
- fallback_present: True
- key_paths_recorded: 500
- target_match_id_in_key_path: False
- positive_candidate_path_count: 233
- top candidates: props.pageProps.fetchingLeagueData, props.pageProps.fallback./api/translationmapping?locale=zh-Hans.TournamentTemplates, props.pageProps.fallback./api/translationmapping?locale=zh-Hans.TournamentPrefixes, props.pageProps.fallback./api/translationmapping?locale=zh-Hans.TournamentPrefixes.38, props.pageProps.fallback./api/translationmapping?locale=zh-Hans.TournamentPrefixes.40
- top scores: [1, 1, 1, 1, 1]
- generic rejected: props.pageProps.fallback.notableMatches:zh-Hans:USA, props.pageProps.fallback.notableMatches:zh-Hans:USA.matches

## Why Raw Write Is Still Blocked

- 本阶段只扫描 key path metadata，未验证任何 JSON value。
- json_validated_count=0。
- raw_write_eligible_count=0。
- 即使发现 strong candidate path，也需要先做 candidate path validation no-write。

## Recommended Next Phase

- **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-ROUTE-VARIANT-FOLLOWUP-NO-WRITE**
