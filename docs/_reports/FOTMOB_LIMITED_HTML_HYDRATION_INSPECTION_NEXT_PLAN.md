<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 -->

# FotMob Limited HTML Hydration Inspection — Next Plan

## Why Limited Inspection

- HTML routes are confirmed viable (6/6 HTTP 200).
- Before extracting full pageProps, we must verify __NEXT_DATA__ markers exist in first 256KB.
- Limited inspection confirms structural viability without full body capture.

## Selected Routes

- `https://www.fotmob.com/match/{match_id}` — match_id=4813722, pair=Liverpool vs Manchester United
- `https://www.fotmob.com/matches/{route_code}/{match_id}` — match_id=4813722, pair=Liverpool vs Manchester United

## Probe Parameters

- **phase**: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIMITED-HTML-HYDRATION-INSPECTION-NO-WRITE
- **max_samples**: 2
- **max_route_templates**: 2
- **max_network_requests**: 4
- **max_body_bytes**: 524288
- **allowed_markers**:
  - __NEXT_DATA__
  - pageProps
  - matchId
  - header
  - general
- **forbidden_persistence**:
  - full HTML body save
  - raw JSON file write
  - DB write (any table)
  - raw response body persistence
  - pageProps full extraction save
- **success_criteria**:
  - __NEXT_DATA__ script tag found in first 256KB
  - pageProps marker found
  - match_id confirmed in hydrated data
- **stop_conditions**:
  - 403 on any route → stop all
  - 429 on any route → stop all
  - captcha/bot page detected → stop all
  - body exceeds 512KB without marker → stop that route
- **next_phase_after_success**: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-EXTRACTION-VALIDATION-NO-WRITE
- **next_phase_after_failure**: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-ROUTE-REVIEW-FOLLOWUP-NO-WRITE
- **notes**: Even if markers are found, next phase is extraction validation no-write, not raw JSON write. Full body extraction requires separate planning. L2 raw harvesting remains blocked until json_validated.

## Success Criteria

- __NEXT_DATA__ script tag found in first 256KB
- pageProps marker found
- match_id confirmed in hydrated data

## Stop Conditions

- 403 on any route → stop all
- 429 on any route → stop all
- captcha/bot page detected → stop all
- body exceeds 512KB without marker → stop that route

## What Must NOT Be Persisted

- Full HTML body
- Raw JSON
- DB write
- pageProps full extraction
- __NEXT_DATA__ full dump
- Any raw response body

## After Success

- Next phase: **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-EXTRACTION-VALIDATION-NO-WRITE**
- Still not raw JSON write
- L2 raw harvesting remains blocked

## After Failure

- Fallback: **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-ROUTE-REVIEW-FOLLOWUP-NO-WRITE**

