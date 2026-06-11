# FotMob Null-id Event Shape Audit

lifecycle: phase-artifact

- Date: 2026-06-12
- Branch: `data/fotmob-null-id-event-shape-audit`
- Base main commit: `0448add0582c6367d5c40cf622c008d1e090ec0f`
- Scope: audit only; SELECT-only review of 4 retained `fotmob_live_v1` rows for `null-id` event shapes
- Safety: no live fetch, no browser, no external network, no DB write, no raw write, no parser/test changes, no full raw/pageProps/HTML/raw_data printed or saved

## Target Rows

| external_id | data_version | row_found |
|---|---|---:|
| `4830507` | `fotmob_live_v1` | 1 |
| `4830466` | `fotmob_live_v1` | 1 |
| `4830461` | `fotmob_live_v1` | 1 |
| `4830464` | `fotmob_live_v1` | 1 |

## Null-id Counts

- Audited `null-id` events: `51`
- `Substitution`: `35`
- `AddedTime`: `8`
- `Half`: `8`
- All 51 audited events truly lack both raw `eventId` and raw `id`.
- None of the 51 audited events contains `substitutionId` or `incidentId`.

## Shape Summary

### `Substitution` (35)

- Top-level keys: `awayScore`, `homeScore`, `injuredPlayerOut`, `isHome`, `overloadTime`, `overloadTimeStr`, `player`, `profileUrl`, `reactKey`, `swap`, `time`, `timeStr`, `type`
- Nested object keys: `player.{id, profileUrl}`
- Field presence:
  `time/timeStr/isHome/homeScore/awayScore/reactKey/swap` present on `35/35`
  `eventId/id/substitutionId/incidentId/playerId/assistId` present on `0/35`
  nested `player.id` key exists in shape, but observed value is absent on `35/35`
- Stability notes:
  `reactKey` present on `35/35`, unique on `35/35`
  `swap` present on `35/35`, but only `1` unique value across the sample, so it is not a usable identifier by itself
- Interpretation:
  no native event id exists in the retained source shape; if downstream requires a non-null identifier, the only strong candidate observed here is `reactKey`

### `AddedTime` (8)

- Top-level keys: `awayScore`, `homeScore`, `minutesAddedInput`, `minutesAddedKey`, `minutesAddedStr`, `overloadTime`, `player`, `reactKey`, `time`, `timeStr`, `type`
- Nested object keys: `player.{id, profileUrl}`
- Field presence:
  `time/timeStr/homeScore/awayScore/reactKey/minutesAddedKey` present on `8/8`
  `eventId/id/substitutionId/incidentId/isHome/playerId/assistId` present on `0/8`
- Interpretation:
  marker-style event, not a player incident; no native id in source

### `Half` (8)

- Top-level keys: `awayScore`, `halfStrKey`, `halfStrShort`, `homeScore`, `overloadTime`, `player`, `reactKey`, `time`, `timeStr`, `type`
- Nested object keys: `player.{id, profileUrl}`
- Field presence:
  `time/timeStr/homeScore/awayScore/reactKey/halfStrKey` present on `8/8`
  `eventId/id/substitutionId/incidentId/isHome/playerId/assistId` present on `0/8`
- Interpretation:
  marker-style event, not a player incident; no native id in source

## Audit Answers

1. These 51 `null-id` events really do not have raw `eventId`/`id`.
2. `Substitution` does not expose another native id field; the only stable candidate observed is `reactKey` (`35/35` present, `35/35` unique).
3. `AddedTime` and `Half` are marker-like events. Their shapes carry time/score/marker metadata, not player-incident ids.
4. Yes, some event types should be allowed to remain `id=null` if the system accepts source variance for marker events.
5. If a non-null identifier is still required, synthetic key design is preferable to continuing to search for nonexistent native ids.
6. Recommended synthetic key:
   preferred: `external_id + reactKey`
   fallback if `reactKey` is rejected:
   `AddedTime`: `external_id + type + time + minutesAddedKey + homeScore + awayScore`
   `Half`: `external_id + type + time + halfStrKey + homeScore + awayScore`
   `Substitution`: no reliable non-`reactKey` combination was demonstrated by this sample
7. No immediate parser fix is needed to map a “real” id for these shapes, because the retained source does not contain one. A future parser change is only justified if the product decides to emit a synthetic event key.

## Recommendation

- Treat this blocker as a source-shape/design question, not another `eventId/id` mapping bug.
- User decision needed next:
  accept source variance for marker events
  or design synthetic keys (prefer `external_id + reactKey`)
  or request a deliberate parser change to emit synthetic ids
