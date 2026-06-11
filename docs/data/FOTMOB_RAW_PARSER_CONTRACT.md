<!-- markdownlint-disable MD013 -->

# FotMob Raw Parser Contract

- lifecycle: current-state
- owner: data / ingestion workflow
- based on: PR #1490 structure validation (merge commit 52cbac5)
- data_version: `fotmob_live_v1`
- sample size: N=4 (external IDs 4830507, 4830466, 4830461, 4830464)
- last updated: 2026-06-11

## 1. Purpose

This document defines the canonical parser contract for `raw_match_data` rows with
`data_version=fotmob_live_v1`. It is derived from the #1490 structure validation of 4
retained raw payloads. Every parser implementation MUST conform to this contract.

This contract does NOT define feature extraction, training labels, or prediction
pipelines. Those remain deferred per Phase 5.21L2P.

## 2. Source Payload Shape

### 2.1 Top-Level Keys (all required, 4/4 consistent)

| Key | Type | Description |
|-----|------|-------------|
| `_meta` | object | Fetch/parse metadata; excluded from feature extraction |
| `matchId` | string (numeric) | Inner FotMob match ID from `general.matchId` |
| `general` | object | Match identity and league context |
| `header` | object | Teams, status, score summary |
| `content` | object | Stats, lineup, events, and auxiliary data |

### 2.2 `general` — Match Identity (18 fields, 4/4 consistent)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `matchId` | number | yes | Inner FotMob match ID |
| `homeTeam` | object | yes | `{ id, name, shortName }` |
| `awayTeam` | object | yes | `{ id, name, shortName }` |
| `leagueId` | number | yes | FotMob league ID |
| `leagueName` | string | yes | Human-readable league name |
| `leagueRoundName` | string | no | Long round name (may be empty) |
| `matchRound` | string | no | Short round label (e.g. "Round 1") |
| `matchTimeUTC` | string | yes | ISO-8601 kickoff time |
| `matchTimeUTCDate` | string | no | Date-only string |
| `matchName` | string | no | Match display name |
| `started` | boolean | yes | Whether match has started |
| `finished` | boolean | yes | Whether match has finished |
| `coverageLevel` | number | no | FotMob coverage tier |
| `countryCode` | string | no | ISO country code |
| `parentLeagueId` | number | no | Parent competition ID |
| `gender` | string | no | "male" / "female" |
| `teamColors` | object | no | `{ home, away }` color info |

### 2.3 `header` — Teams / Score / Status (3 keys, 4/4 consistent)

#### `header.teams` — array[2]

| Index | Field | Type | Description |
|-------|-------|------|-------------|
| [0] | `id` | number | Home team FotMob ID |
| [0] | `name` | string | Home team name |
| [0] | `score` | number \| null | Home team score |
| [0] | `imageUrl` | string | Home team badge URL |
| [0] | `pageUrl` | string | Home team page URL |
| [1] | *(same fields)* | | Away team |

#### `header.status` — object

| Field | Type | Description |
|-------|------|-------------|
| `started` | boolean | Match started |
| `finished` | boolean | Match finished |
| `cancelled` | boolean | Match cancelled |
| `scoreStr` | string | Display score (e.g. "2-1") |
| `utcTime` | string | Kickoff time |
| `halfs` | object | Half-level score detail |
| `reason` | object | Match end reason (if applicable) |

#### `header.events` — score summary object

| Field | Type | Description |
|-------|------|-------------|
| `homeTeamGoals` | number | Home team total goals |
| `awayTeamGoals` | number | Away team total goals |
| `homeTeamRedCards` | number | Home red cards |
| `awayTeamRedCards` | number | Away red cards |

**Note**: This is a SCORE SUMMARY, NOT the match events timeline. The timeline is at
`content.matchFacts.events.events[]`. Do not confuse the two.

### 2.4 `content` — Match Detail (15 keys, 4/4 consistent with 1 minor variance)

#### Required content sections

| Section | Path | Type | Description |
|---------|------|------|-------------|
| Stats | `content.stats` | object | Periods-aware stats (see §3) |
| Lineup | `content.lineup` | object | `{ homeTeam, awayTeam }` (see §4) |
| Match Facts | `content.matchFacts` | object | Events, insights, top players (see §5) |
| Shotmap | `content.shotmap` | object | `{ shots[], Periods }` |
| Player Stats | `content.playerStats` | object | Player IDs as keys → stat objects |
| Table | `content.table` | object | League table snapshot |
| H2H | `content.h2h` | object | `{ matches[], summary }` |

#### Optional / auxiliary sections

| Section | Path | Type | Notes |
|---------|------|------|-------|
| Momentum | `content.momentum` | object | Match momentum graph data |
| Liveticker | `content.liveticker` | object | Live text commentary |
| Superlive | `content.superlive` | object | Superlive scoring data |
| Weather | `content.weather` | — | May be null or absent |
| Buzz | `content.buzz` | null | Null in all 4 samples; handle gracefully |
| Highlight Stories | `content.highlightStories` | — | May be absent |
| Heatmap URL | `content.heatmapUrl` | string | URL string |
| Has Playoff | `content.hasPlayoff` | boolean | Playoff indicator |

#### Minor variance (record 39)

Record 39 (external_id=4830464) has 2 extra keys in `content.matchFacts`:
`preReview` and `postReview`. Records 33/35/37 have 14 matchFacts keys; record 39 has
16. This is match-state dependent. Parser MUST handle missing preReview/postReview
gracefully.

## 3. Stats: Periods-Aware Traversal

### 3.1 Canonical Path

```
content.stats.Periods.All.stats[]
content.stats.Periods.FirstHalf.stats[]
content.stats.Periods.SecondHalf.stats[]
```

### 3.2 Traversal Rules

1. Parse `content.stats` as object.
2. Descend into `content.stats.Periods`.
3. For each period (`All`, `FirstHalf`, `SecondHalf`), extract `period.<period>.stats[]`.
4. Each stats array entry has structure:

```json
{ "key": "<stat_name>", "title": "<display_name>", "stats": [{ "key": "homeValue", "value": <n> }, { "key": "awayValue", "value": <n> }] }
```

5. If `Periods` is missing, parser MUST return empty stats (not throw).
6. If a period key is missing, skip that period.
7. Stats key names are FotMob-idiomatic (e.g. "expected_goals", "possession_percentage").
   Parser MUST NOT hardcode a stat-name allowlist at this layer; normalization is the
   responsibility of the feature engineering layer.

### 3.3 Periods-Aware Flattening

The parser SHOULD produce a flat array of stat entries with an added `period` field:

```json
[
  { "period": "All", "key": "expected_goals", "homeValue": 1.2, "awayValue": 0.8 },
  { "period": "FirstHalf", "key": "expected_goals", "homeValue": 0.6, "awayValue": 0.3 },
  { "period": "SecondHalf", "key": "expected_goals", "homeValue": 0.6, "awayValue": 0.5 }
]
```

## 4. Lineup

### 4.1 Canonical Path

```
content.lineup.homeTeam
content.lineup.awayTeam
```

### 4.2 Structure

Each team object:

| Field | Type | Description |
|-------|------|-------------|
| `id` | number | Team FotMob ID |
| `name` | string | Team name |
| `formation` | string | Formation (e.g. "4-3-3") |
| `starters` | array | Starting XI players |
| `subs` | array | Substitutes |
| `coach` | object | `{ id, name }` |
| `rating` | number | Team average rating |
| `averageStarterAge` | number | Average age of starters |
| `totalStarterMarketValue` | string | Total market value |
| `unavailable` | array | Unavailable players |

### 4.3 Player Structure (starters[] / subs[] entries)

| Field | Type | Description |
|-------|------|-------------|
| `id` | number | Player FotMob ID |
| `name` | object | `{ fullName, firstName, lastName }` |
| `position` | string | Playing position |
| `shirtNumber` | number | Jersey number |
| `rating` | number \| null | Match rating |
| `stats` | object | Player-level stats |

## 5. Events: Match Events Timeline

### 5.1 Canonical Path

```
content.matchFacts.events.events[]
```

This is the CORRECTED path from the original canonical schema expectation of
`content.events`. The actual 4 retained raw payloads have events at
`content.matchFacts.events.events[]`.

### 5.2 Container Structure

```
content.matchFacts.events
├── events[]          ← the actual timeline (array of event objects)
├── ongoing           ← ongoing event (if any)
├── eventTypes[]      ← event type definitions
└── penaltyShootoutEvents[]
```

### 5.3 Event Entry Structure (from events[] array)

Each event entry is expected to have:

| Field | Type | Description |
|-------|------|-------------|
| `id` | number | Event ID |
| `type` | string | Event type (e.g. "Goal", "Card", "substitution") |
| `minute` | number \| string | Match minute |
| `teamId` | number | Team FotMob ID |
| `playerId` | number \| null | Primary player |
| `playerName` | string \| null | Player display name |
| `assistPlayerId` | number \| null | Assist player (goals) |
| `outcome` | string \| null | Event outcome |

### 5.4 Score Summary (separate from timeline)

```
header.events.homeTeamGoals
header.events.awayTeamGoals
header.events.homeTeamRedCards
header.events.awayTeamRedCards
```

### 5.5 Events Extraction Rules

1. Primary events source: `content.matchFacts.events.events[]`.
2. If `content.matchFacts.events.events` is missing or empty, parser returns empty
   events array (not throw).
3. Score summary at `header.events` is an AGGREGATE, not a timeline. Use it only for
   final score verification.
4. Do not confuse `header.events` (score summary object with homeTeamGoals/awayTeamGoals)
   with `content.matchFacts.events.events[]` (timeline array).

## 6. Parser Output Structure (Draft)

The parser MUST produce a flat, deterministic output structure. The following is the
contract for the parser output — every field below MUST be present in the parsed result.

```json
{
  "match": {
    "matchId": "<inner_numeric_id>",
    "externalId": "<external_id_from_input>",
    "leagueId": "<number>",
    "leagueName": "<string>",
    "matchRound": "<string_or_null>",
    "matchTimeUTC": "<ISO-8601>",
    "started": "<boolean>",
    "finished": "<boolean>",
    "cancelled": "<boolean>"
  },
  "homeTeam": {
    "id": "<number>",
    "name": "<string>",
    "score": "<number_or_null>",
    "formation": "<string_or_null>"
  },
  "awayTeam": {
    "id": "<number>",
    "name": "<string>",
    "score": "<number_or_null>",
    "formation": "<string_or_null>"
  },
  "stats": [
    { "period": "<All|FirstHalf|SecondHalf>", "key": "<stat_name>", "homeValue": "<number_or_null>", "awayValue": "<number_or_null>" }
  ],
  "lineup": {
    "home": { "starters": [], "subs": [], "coach": {} },
    "away": { "starters": [], "subs": [], "coach": {} }
  },
  "events": [
    { "id": "<number>", "type": "<string>", "minute": "<number_or_string>", "teamId": "<number>", "playerId": "<number_or_null>", "playerName": "<string_or_null>" }
  ],
  "shotmap": {
    "shots": []
  },
  "playerStats": {},
  "meta": {
    "dataVersion": "fotmob_live_v1",
    "hashStrategy": "stable_raw_payload_v1",
    "parserVersion": "<semver>",
    "parsedAt": "<ISO-8601>"
  }
}
```

## 7. Missing-Field Behavior

| Scenario | Behavior |
|----------|----------|
| Required top-level key missing (`general`, `header`, `content`) | Parse error: return `{ ok: false, error: "MISSING_REQUIRED_SECTION:<key>" }` |
| `content.stats` missing | Return empty `stats[]`, continue |
| `content.stats.Periods` missing | Return empty `stats[]`, continue |
| `content.lineup` missing | Return `{ home: {starters:[],subs:[],coach:{}}, away: {starters:[],subs:[],coach:{}} }` |
| `content.matchFacts.events` missing | Return empty `events[]`, continue |
| `content.matchFacts.events.events` missing | Return empty `events[]`, continue |
| `general.homeTeam` / `general.awayTeam` missing | Parse error: return `{ ok: false, error: "MISSING_TEAM_IDENTITY" }` |
| `matchId` not numeric / missing | Parse error: return `{ ok: false, error: "INVALID_MATCH_ID" }` |
| Any optional section missing | Return `null` or empty container for that section |

Parser MUST NOT throw uncaught exceptions. All errors MUST be returned via the `{ ok: false,
error: "..." }` pattern.

## 8. Parser Implementation Acceptance Criteria

Before a parser implementation PR can be merged, it MUST satisfy all of the following:

1. **Pure function**: No network, no DB access, no file I/O (except reading fixtures in tests).
2. **Deterministic output**: Same input → same output. No `Date.now()`, `Math.random()`, or
   time-dependent logic in parser logic.
3. **All 4 retained raw rows parse successfully**: Parse all 4 `fotmob_live_v1` rows and
   produce valid output per §6.
4. **Missing-field resilience**: Tests demonstrate behavior for each scenario in §7.
5. **Events path confirmed**: Parser correctly reads events from
   `content.matchFacts.events.events[]`, NOT `content.events`.
6. **Periods-aware stats**: Parser traverses `content.stats.Periods.{All,FirstHalf,SecondHalf}`
   and produces flattened stats with `period` field.
7. **No full raw print**: Tests MUST NOT save or print complete `raw_data` payloads. Use
   only field-path-level assertions and structure checks.
8. **Schema validation**: Parser output validates against a defined JSON Schema (to be
   provided as a fixture alongside the parser).
9. **No feature extraction**: Parser output must be literal data transformation, not derived
   features, aggregations, or computed metrics.
10. **PR body states**: no DB write, no raw write, no live fetch, no model training.

## 9. Relationship to Existing Assets

| Asset | Relationship |
|-------|-------------|
| `docs/_manifests/fotmob_safe_parser_schema_reuse_plan_no_write_manifest.json` | Canonical shape plan — this contract refines it with actual `fotmob_live_v1` path evidence |
| `src/parsers/fotmob/MatchParser.js` | Legacy parser (pre-v1); reusable for `firstValue` cascade pattern, but paths must be updated |
| `src/parsers/fotmob/MatchStatsParser.js` | Legacy stats parser; `normalizeStat` is reusable; traversal must add Periods-awareness |
| `src/parsers/fotmob/NextDataParser.js` | HTML→apiFormat transform; NOT applicable to already-transformed `fotmob_live_v1` payloads |
| `src/infrastructure/services/FotMobRawDetailFetcher.js` | `validateCanonicalRawDataShape` — pre-parser shape gate; parser should validate against this before parsing |
| `docs/_reports/fotmob_raw_structure_validation_20260611.md` | Source evidence for this contract |

## 10. Safety Boundaries

- This contract defines WHAT to parse, not HOW to implement.
- No parser code is authorized by this document alone.
- Parser implementation must be a separate PR with its own authorization.
- No live fetch, no DB write, no raw write, no feature extraction, no training.

## 11. Next Steps

1. Authorize parser implementation PR (separate from this contract PR).
2. Implement parser per this contract, targeting `data_version=fotmob_live_v1`.
3. Write unit tests against the 4 retained raw rows (read-only, via fixtures).
4. After parser passes all acceptance criteria (§8), consider N=5 / N=10 controlled
   expansion.

Do not start automatically.
Recommended next task only after user confirmation.
