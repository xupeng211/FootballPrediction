# Football-Data Packet File Creation Readiness Checklist Template

> 模板用途：汇总未来真正创建 packet 文件之前必须满足的 readiness 条件。
>
> 本文件在 Phase 4.73C 只是 readiness checklist 模板，不是授权表；不允许据此创建目录、写 packet 文件、写 packet manifest、写 DB、执行 `pg_dump` / `pg_restore`、训练或预测。

```yaml
phase: PHASE4_PACKET_FILE_CREATION_READINESS
readiness_status: not_ready
operator:
reviewer:
source_manifest:
local_csv:
approval_form:
runbook_template:
packet_auth_form:
packet_directory:
packet_file:
packet_manifest_file:
approved_output_root: docs/_packets/football_data/small_write

source_checks:
    source_manifest_exists: false
    local_csv_exists: false
    sha256_match: false
    row_count_match: false

gate_checks:
    csv_dry_run_passed: false
    db_write_preflight_passed: false
    duplicate_precheck_passed: false
    insert_policy_precheck_passed: false
    small_write_auth_preview_passed: false
    runbook_validation_passed: false
    packet_preview_passed: false
    packet_file_preflight_passed: false
    packet_file_auth_validation_passed: false
    packet_file_auth_review_passed: false

authorization_checks:
    authorization_status: not_authorized
    final_packet_creation_confirmation: false
    human_approval_note_present: false
    operator_present: false
    reviewer_present: false
    packet_creation_reason_present: false

safety_checks:
    allow_packet_directory_creation: false
    allow_packet_file_write: false
    allow_packet_manifest_write: false
    allow_db_write: false
    allow_pg_dump: false
    allow_pg_restore: false
    allow_external_network: false
    allow_training: false
    allow_prediction: false

candidate_checks:
    proposed_match_ids_listed: false
    approved_candidate_match_ids_reviewed: false
    excluded_candidate_match_ids_reviewed: false
    manual_review_candidate_match_ids_resolved: false

final_readiness:
    packet_file_creation_ready: false
    packet_file_creation_authorized: false
    db_write_authorized: false
    pg_dump_authorized: false
    training_authorized: false
    prediction_authorized: false
```

## 说明

- 默认 `readiness_status=not_ready`，不可在未经人工审批的情况下改为 `ready`。
- 默认不允许创建 packet 目录 (`allow_packet_directory_creation=false`)。
- 默认不允许写 packet 文件 (`allow_packet_file_write=false`)。
- 默认不允许写 DB (`allow_db_write=false`)。
- 默认不允许执行 `pg_dump` / `pg_restore` (`allow_pg_dump=false`, `allow_pg_restore=false`)。
- 默认不允许外部网络访问 (`allow_external_network=false`)。
- 默认不允许训练 (`allow_training=false`)、预测 (`allow_prediction=false`)。
- 本模板不是授权表，不等于 packet file creation authorization。
- packet file creation authorization 不等于 DB write authorization。
- Codex 不得自行把 `readiness_status` 改成 `ready`。
- Codex 不得自行把 `packet_file_creation_ready` 改成 `true`。
- Codex 不得自行把 `packet_file_creation_authorized` 改成 `true`。
- Codex 不得自行把 `authorization_status` 改成 `authorized_for_packet_file_creation`。
- Codex 不得自行把 `final_packet_creation_confirmation` 改成 `true`。
- 真实 packet 文件创建必须单独阶段、用户明确授权、真实 auth form、显式路径。
