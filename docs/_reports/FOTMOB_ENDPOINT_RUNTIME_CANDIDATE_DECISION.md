<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->
# FotMob Endpoint Runtime Candidate Decision

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-RUNTIME-CANDIDATE-PROBE-NO-WRITE decision
- run_id: fotmob_endpoint_runtime_candidate_probe_no_write_v1
- mode: controlled

## Skipped
- ep-004: skipped_missing_build_id
- ep-005: skipped_missing_build_id
- ep-006: skipped_missing_date

## Why Raw Write Is Still Blocked

- json_validated_count=0
- raw_write_eligible_count=0
- 即使发现 strong candidate，也只是进入 response validation no-write

## Recommended Next Phase

- **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-FOTMOB-RAW-DETAIL-DOWNGRADE-DECISION-NO-WRITE**
