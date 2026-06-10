<!-- markdownlint-disable MD013 -->

# FotMob Raw Payload Structure Validation Report

- lifecycle: phase-artifact
- owner: data / ingestion workflow
- phase: #1490 — fotmob-raw-structure-validation
- date: 2026-06-11

## Summary

SELECT-only validation of 4 retained `raw_match_data` rows with `data_version=fotmob_live_v1`.
Confirms top-level structure conformance and identifies path-level gaps between actual raw payloads
and the canonical parser schema defined in `docs/_manifests/fotmob_safe_parser_schema_reuse_plan_no_write_manifest.json`.

## Scope

| Parameter | Value |
|-----------|-------|
| Table | `raw_match_data` |
| data_version | `fotmob_live_v1` |
| Records checked | 4 |
| External IDs | 4830507, 4830466, 4830461, 4830464 |
| Match IDs | 53_20252026_4830507, 53_20252026_4830466, 53_20252026_4830461, 53_20252026_4830464 |
| Source | fotmob |
| Route | html_hydration |
| Hash strategy | stable_raw_payload_v1 |
| Network fetch | none |
| DB write | none |

## Top-Level Structure (4/4 identical)

All 4 records share identical top-level keys:

| Key | Type | Present (4/4) |
|-----|------|---------------|
| `_meta` | object | ✓ |
| `matchId` | string (numeric) | ✓ |
| `general` | object | ✓ |
| `header` | object | ✓ |
| `content` | object | ✓ |

### General (18 fields, 4/4 identical keys)

`gender`, `matchId`, `started`, `awayTeam`, `finished`, `homeTeam`, `leagueId`,
`matchName`, `leagueName`, `matchRound`, `teamColors`, `countryCode`, `matchTimeUTC`,
`coverageLevel`, `parentLeagueId`, `leagueRoundName`, `matchTimeUTCDate`

### Header (3 top-level keys, 4/4 identical)

| Key | Type | Sub-keys |
|-----|------|----------|
| `teams` | array[2] | `id`, `name`, `score`, `pageUrl`, `imageUrl` |
| `status` | object | `halfs`, `reason`, `awarded`, `started`, `utcTime`, `finished`, `scoreStr`, `timezone`, `cancelled`, `whoLostOnPenalties`, `whoLostOnAggregated`, `numberOfAwayRedCards`, `numberOfHomeRedCards` |
| `events` | object | `homeTeamGoals`, `awayTeamGoals`, `homeTeamRedCards`, `awayTeamRedCards` |

### Content (15 top-level keys, 4/4 identical except matchFacts variance)

| Key | Type | Notes |
|-----|------|-------|
| `stats` | object | Periods → All / FirstHalf / SecondHalf → stats[] |
| `lineup` | object | homeTeam + awayTeam (starters, subs, coach, formation, rating) |
| `shotmap` | object | shots[] + Periods |
| `table` | object | league table with teams[] |
| `h2h` | object | matches[] + summary |
| `matchFacts` | object | events, infoBox, insights, topPlayers, etc. |
| `playerStats` | object | player IDs as keys → stats objects |
| `liveticker` | object | live text commentary |
| `momentum` | object | momentum data |
| `superlive` | object | superlive scoring data |
| `weather` | — | present |
| `highlightStories` | — | present |
| `heatmapUrl` | — | present |
| `hasPlayoff` | — | present |
| `buzz` | null | null in all 4 records |

**Minor variance**: Record 39 (4830464) has `matchFacts` with 16 keys (includes `preReview` +
`postReview`); records 33/35/37 have 14 keys (no review content). All other keys are identical
across 4 records. This variance is match-state dependent (pre/post-review content).

## validateCanonicalRawDataShape Check

As defined in `FotMobRawDetailFetcher.js` line 357:

| Rule | Result (4/4) |
|------|-------------|
| `_meta` key present | ✓ |
| `content` key present | ✓ |
| `general` key present | ✓ |
| `header` key present | ✓ |
| `matchId` key present and numeric | ✓ |
| `_meta.full_html_body_stored` = false | ✓ |
| `_meta.http_response_string_stored` = false | ✓ |

**Result**: 4/4 pass `validateCanonicalRawDataShape`.

## Parser Contract Comparison

Against `fotmob_safe_parser_schema_reuse_plan_no_write_manifest.json` canonical payload shape:

### Required sections

| Section | Expected path | Actual path | Status |
|---------|--------------|-------------|--------|
| general | `general` | `general` | ✓ Exact match |
| header | `header` | `header` | ✓ Exact match |
| content.stats | `content.stats` | `content.stats.Periods.All.stats[]` | ⚠ Path adjusted — stats are nested under Periods/All; StatsParser would need Periods-aware navigation |
| content.lineup | `content.lineup` | `content.lineup.homeTeam` / `content.lineup.awayTeam` | ✓ Exact match |
| content.events | `content.events` | `content.matchFacts.events.events[]` (timeline) + `header.events` (score summary) | ⚠ Path mismatch — match events timeline is at `content.matchFacts.events.events[]`, not `content.events` |

### Optional sections

| Section | Available | Path |
|---------|-----------|------|
| content.shotmap | ✓ | `content.shotmap.shots[]` + `content.shotmap.Periods` |
| xG/expectedGoals | ✓ | Available via `content.shotmap` and `content.stats.Periods.All.stats[]` stat entries |
| tournament/venue | ✓ | `general.leagueName`, `general.leagueRoundName`, `header.status` |

### Validation rules

| Rule | Result |
|------|--------|
| matchId present and numeric | ✓ 4/4 — inner matchId from `general.matchId` |
| content has stats OR lineup OR events | ✓ 4/4 — all three present |
| general.homeTeam + general.awayTeam present | ✓ 4/4 |
| header.tournament present | ⚠ — no explicit `header.tournament`; league context at `general.leagueName` + `general.leagueRoundName` |

## Required Parser Candidate Fields

For a minimal parser contract, the following fields MUST be mapped:

| # | Field | Source path | Present (4/4) |
|---|-------|-------------|---------------|
| 1 | match_id (inner) | `general.matchId` | ✓ |
| 2 | home_team_name | `general.homeTeam.name` | ✓ |
| 3 | away_team_name | `general.awayTeam.name` | ✓ |
| 4 | home_team_id | `general.homeTeam.id` | ✓ |
| 5 | away_team_id | `general.awayTeam.id` | ✓ |
| 6 | kickoff_time | `general.matchTimeUTC` | ✓ |
| 7 | match_status | `header.status.started` / `header.status.finished` | ✓ |
| 8 | home_score | `header.teams[0].score` | ✓ |
| 9 | away_score | `header.teams[1].score` | ✓ |
| 10 | league_id | `general.leagueId` | ✓ |
| 11 | league_name | `general.leagueName` | ✓ |
| 12 | match_round | `general.matchRound` | ✓ |

## Optional Parser Candidate Fields

| # | Field | Source path | Present (4/4) |
|---|-------|-------------|---------------|
| 1 | match_stats | `content.stats.Periods.All.stats[]` | ✓ |
| 2 | xG data | `content.shotmap` + stat entries | ✓ |
| 3 | lineup_home | `content.lineup.homeTeam.starters[]` | ✓ |
| 4 | lineup_away | `content.lineup.awayTeam.starters[]` | ✓ |
| 5 | subs_home | `content.lineup.homeTeam.subs[]` | ✓ |
| 6 | subs_away | `content.lineup.awayTeam.subs[]` | ✓ |
| 7 | events_timeline | `content.matchFacts.events.events[]` | ✓ |
| 8 | player_stats | `content.playerStats.<playerId>` | ✓ |
| 9 | match_insights | `content.matchFacts.insights` | ✓ |
| 10 | shotmap | `content.shotmap.shots[]` | ✓ |
| 11 | head_to_head | `content.h2h` | ✓ |
| 12 | league_table | `content.table` | ✓ |
| 13 | momentum | `content.momentum` | ✓ |
| 14 | weather | `content.weather` | ✓ |
| 15 | top_players | `content.matchFacts.topPlayers` | ✓ |
| 16 | player_of_match | `content.matchFacts.playerOfTheMatch` | ✓ (exception: record 39 also has preReview/postReview) |

## Missing / Gap Fields

Relative to canonical parser schema expectations:

| # | Expected | Actual | Severity | Resolution |
|---|----------|--------|----------|------------|
| 1 | `content.events` (array of match events) | `content.matchFacts.events.events[]` | **Medium** — path mismatch | Parser contract must specify `content.matchFacts.events.events` as the canonical events path, or adapter must remap |
| 2 | `content.stats` (direct array of stat groups) | `content.stats.Periods.All.stats[]` | **Low** — StatsParser already probes multiple paths (`rawData.content?.stats`) | Parser needs Periods-aware traversal or Periods-aware flattening |
| 3 | `header.tournament` | Tournament context at `general.leagueName` / `general.leagueRoundName` | **Low** — league metadata exists at different path | Parser should source tournament info from `general` instead of `header.tournament` |
| 4 | `content.buzz` | null in all 4 records | **Low** — optional field, may be populated for higher-coverage leagues | Parser should handle null buzz gracefully |

## Minimum Parser Contract Precondition

| Check | Status |
|-------|--------|
| All 4 records parseable JSONB | ✓ |
| Top-level structure identical (4/4) | ✓ |
| Required keys present | ✓ (5/5: _meta, content, general, header, matchId) |
| `validateCanonicalRawDataShape` passes | ✓ 4/4 |
| inner matchId numeric | ✓ 4/4 |
| Home/away team identity present | ✓ 4/4 |
| Stats present and structured | ✓ 4/4 |
| Lineup present | ✓ 4/4 |
| Events timeline present | ✓ 4/4 (at adjusted path) |
| Data hash integrity | ✓ 4/4 |

**Conclusion: 4/4 records satisfy minimum parser contract precondition.**

The raw payloads have a homogeneous, well-structured JSON schema that is sufficient to support
a parser contract. The parser contract must document 2 path adjustments:
`content.matchFacts.events.events` for events timeline and Periods-aware stats navigation.

## Next Steps

1. **Parser contract definition**: Formalize the parser contract with the 2 path adjustments
   identified above (`content.matchFacts.events.events` for events, Periods-aware stats).
   Reference: `docs/_manifests/fotmob_safe_parser_schema_reuse_plan_no_write_manifest.json`.
2. **Parser boundary / leakage-safe planning**: Before parser implementation, complete the
   parser boundary and feature leakage policy per Phase 5.21L2P.
3. **No parser implementation yet**: Do NOT implement parser or extract features. This is a
   structure-validation-only task.

## Safety

| Check | Status |
|-------|--------|
| Live fetch | No |
| Network request | No |
| DB write | No |
| Raw write | No |
| Retained rows modified | No |
| Full raw_data printed/saved | No |
| Parser implemented | No |
| Feature extraction | No |
| Training / prediction | No |
