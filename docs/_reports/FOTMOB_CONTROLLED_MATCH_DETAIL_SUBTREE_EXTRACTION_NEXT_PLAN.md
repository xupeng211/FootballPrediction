<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->
# FotMob Controlled Match Detail Subtree Extraction — Next Plan

## Why Subtree Extraction Is Needed

- #1445 proved NEXT_DATA parses but target match_id not found at pageProps level.
- pageProps contains Next.js framework config (fallback, fetchingLeagueData, ssr, translations).
- Real match detail data is likely nested under fallback cache entries.
- This phase does in-memory subtree scan WITHOUT persisting values.

## Route and Samples

- route: `https://www.fotmob.com/matches/{route_code}/{match_id}`
- match IDs: 4813722, 4813492
- route codes: 2ygkcb, 2ynv4k

## Constraints

- max_samples: 2
- max_network_requests: 2
- max_body_bytes: 524288
- max_subtree_scan_depth: 8
- max_key_paths_recorded: 200

## Allowed Metadata

- key path metadata
- data type metadata
- key presence booleans
- candidate subtree path
- candidate score
- estimated subtree size
- value fingerprints: length, type, numeric equality, string contains match_id

## Forbidden Persistence

- full HTML body
- full __NEXT_DATA__ JSON
- full pageProps
- full match detail subtree value
- raw JSON file
- DB write
- raw response body
- scheduler enable
- feature parse
- browser automation
- captcha bypass
- proxy rotation

## Scoring Rules

- target match_id found in subtree: +5
- key path or name contains matchId/id and value matches target: +4
- subtree contains 'header' key: +3
- subtree contains 'general' key: +3
- subtree contains 'content' key: +3
- subtree contains 'matchFacts' key: +2
- subtree contains 'stats' key: +2
- subtree contains 'lineup' key: +2

## Success/Failure Criteria

**Success:**
- find at least one subtree with score >= 6
- detect target match_id in subtree
- identify viable path for match detail extraction
**Failure:**
- max depth reached without finding any candidate with score > 0
- all subtrees are generic config/translations

## Stop Conditions

- HTTP 403 on any route → stop all
- HTTP 429 on any route → stop all
- captcha/bot page detected → stop all
- body exceeds max_body_bytes without finding NEXT_DATA → stop

## After Success

- Next: **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-SUBTREE-VALIDATION-NO-WRITE**
- Still not raw JSON write
- L2 raw harvesting remains blocked

## After Failure

- Fallback: hydration structure review followup no-write

## Safety Reminder

- 不保存 full HTML
- 不保存 full NEXT_DATA
- 不保存 raw JSON
- 不写 DB
- 不启用 scheduler
- 不使用 browser automation
- 不绕过反爬

