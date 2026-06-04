<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->
# FotMob Endpoint Runtime Candidate Probe No Write

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-RUNTIME-CANDIDATE-PROBE-NO-WRITE
- run_id: fotmob_endpoint_runtime_candidate_probe_no_write_v1
- mode: controlled_endpoint_candidate_probe_no_write

## 当前阶段背景

- #1452 已完成 endpoint/runtime request discovery plan no-write。
- 本阶段对 ep-004/ep-005/ep-006 执行受控 bounded probe。
- bounded body read in memory，不保存 response body / raw JSON / DB write。

## #1452 Discovery Plan Inheritance

- endpoint_candidate_count: 10
- next_probe_candidate_count: 3
- selected: ep-004 (_next/data match), ep-005 (_next/data matches), ep-006 (api/matches)

## Skipped Candidates
- ep-004: skipped_missing_build_id
- ep-005: skipped_missing_build_id
- ep-006: skipped_missing_date

## Raw Write Readiness Gate

- json_validated_count: 0
- raw_write_eligible_count: 0
- raw_write_blocked_until_json_validated: true

## No-Write Safety Review

- 本阶段允许 bounded body read in memory，但不保存 response body。
- 本阶段不保存 raw JSON、不写 DB、不启用 scheduler、不使用 browser automation。
- 即使发现 strong candidate，也只是进入 response validation no-write。

## Recommended Next Phase

- **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-FOTMOB-RAW-DETAIL-DOWNGRADE-DECISION-NO-WRITE**
