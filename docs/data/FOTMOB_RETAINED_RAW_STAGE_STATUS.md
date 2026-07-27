# FotMob Retained Raw Stage Status

- lifecycle: current-state
- owner: data / ingestion workflow
- update rule: update when retained raw count, audit results, data_version, or next step changes

## Current retained raw inventory

- **Table**: `raw_match_data`
- **Inventory date**: 2026-07-27
- **Inventory method**: authorized local Docker PostgreSQL read-only inventory
- **Current `fotmob_live_v1` retained rows**: 58
- **Current total `raw_match_data` rows**: 76
- **Composition**: `fotmob_live_v1=58`, hydration=8, page-props=8, synthetic=2
- **Current linkage**: 76/76 rows FK-linked to `matches`; 60 distinct `match_id`; 0 raw orphans
- **Full raw-payload assets**: `fotmob_raw_match_payloads=32`. V26.5 requires
  complete, unparsed `__NEXT_DATA__` JSON in non-null `next_data_json`, with
  raw-file locators, SHA-256 values, byte sizes, capture timestamps and
  ingestion metadata; complete `page_props_json` is retained when present but
  is nullable. The assets have match-level `match_id` overlap only;
  record-level payload-to-raw lineage is not proven.
- **Separate mapping-target state**: retained rows are not mapping-target
  classifications. Exact historical reconciliation yields 32 `clean_candidate`,
  10 `needs_new_evidence` and 8 `remain_suspended` targets; row existence does
  not make all 50 historical targets clean.

## Historical controlled audit milestone

The #1487 audit explicitly covered four retained rows from the #1485/#1486
controlled milestone. It remains a historical full-audit result, not a claim
that all 58 current `fotmob_live_v1` rows received identical validation.

| Check | Historical #1487 result |
|---|---|
| Rows audited | 4 |
| Parseable | 4/4 |
| SHA valid | 4/4 |
| Inner matchId OK | 4/4 |
| Errors | 0 |
| Warnings | 0 |

## What this stage proves

- Current retained storage contains 58 `fotmob_live_v1` rows.
- Retained FotMob match identity/raw-storage outcome exists; all current
  `raw_match_data` rows have the enforced `matches` FK.
- The 32 retained payload rows are offline full raw-payload assets, which may
  support a future separately authorized no-write parser/schema verification.
- The historical four-row audit proves full validation only for those four rows.

## What this stage does NOT prove

- Full parser/audit validation for all 58 rows.
- 32/32 parser validation, schema validation, inner-`matchId` validation or
  pageProps presence for the retained full raw-payload assets.
- Unique writer/run provenance for all 58 rows.
- That the legacy N=3 script is canonical, reusable or a recovery dependency.
- Record-level payload-to-raw lineage.
- A clean state for every historical FotMob mapping target; eight remain
  suspended and ten need new evidence in the separate target chronology.
- Current external endpoint availability, production acquisition readiness or
  scalability of a future canonical pipeline.
- Network or database-write authorization, parser implementation, feature
  extraction, training or prediction.

## Active safety rules

- No additional network acquisition or database write is authorized by this
  current-state update; existing retained rows are inventory evidence only.
- Legacy acquisition scripts must not be reactivated or made new dependencies.
- Any future canonical FotMob writer requires a new `data-*`-gated milestone,
  tests and explicit network/write authorization.
- No schema migration, M3 candidate audit, parser implementation, feature
  extraction, training or prediction is authorized here.

## Recommended next step

Do not automatically start another governance review or compatibility audit. If
the user separately authorizes a bounded, read-only M3
candidate-to-existing-FotMob-identity compatibility audit, it must exclude the
ten `needs_new_evidence` and eight `remain_suspended` mapping targets. It
permits no network, database write, migration, new identity generation,
canonical-linkage persistence or legacy writer execution.

Do not start automatically.
Recommended next task only after user confirmation.
