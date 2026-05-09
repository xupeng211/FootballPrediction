# Football-Data Packet File Creation Authorization Packet Draft Template

> 模板用途：未来提交给人类审核的 packet file creation authorization packet 草案模板。
>
> 本文件在 Phase 4.74C 只是草案模板，不是授权；不允许据此创建目录、写 packet 文件、写 packet manifest、写 DB、执行 `pg_dump` / `pg_restore`、训练或预测。

```yaml
phase: PHASE4_PACKET_FILE_CREATION_AUTH_PACKET_DRAFT
draft_status: draft_only
packet_file_creation_authorized: false
packet_file_creation_ready: false
readiness_status: not_ready
authorization_status: not_authorized
final_packet_creation_confirmation: false

operator:
reviewer:
source_manifest:
local_csv:
approval_form:
runbook_template:
packet_auth_form:
readiness_checklist:
packet_directory:
packet_file:
packet_manifest_file:
approved_output_root: docs/_packets/football_data/small_write

draft_inputs:
    source_manifest_summary_required: true
    local_csv_summary_required: true
    packet_preview_required: true
    packet_file_preflight_required: true
    auth_form_validation_required: true
    auth_review_required: true
    readiness_review_required: true

required_human_fields:
    - operator
    - reviewer
    - human_approval_note
    - packet_creation_reason
    - packet_directory
    - packet_file
    - packet_manifest_file
    - approved_candidate_match_ids
    - excluded_candidate_match_ids
    - manual_review_candidate_match_ids

permission_separation:
    packet_file_creation_authorizes_db_write: false
    packet_file_creation_authorizes_pg_dump: false
    packet_file_creation_authorizes_pg_restore: false
    packet_file_creation_authorizes_training: false
    packet_file_creation_authorizes_prediction: false

safety_defaults:
    allow_packet_directory_creation: false
    allow_packet_file_write: false
    allow_packet_manifest_write: false
    allow_db_write: false
    allow_pg_dump: false
    allow_pg_restore: false
    allow_external_network: false
    allow_training: false
    allow_prediction: false

final_decision:
    ready_for_human_review: false
    ready_for_packet_file_creation: false
    authorized_for_packet_file_creation: false
```

## 说明

- 默认 `draft_status=draft_only`，不可在未经人工审批的情况下改为 `approved`。
- 默认 `packet_file_creation_authorized=false`，不允许创建 packet 文件。
- 默认 `packet_file_creation_ready=false`，不允许创建 packet 文件。
- 默认 `readiness_status=not_ready`。
- 默认 `authorization_status=not_authorized`。
- 默认 `final_packet_creation_confirmation=false`。
- 默认所有 `permission_separation` 标志均为 false。
- 默认所有 `safety_defaults` 标志均为 false。
- 本模板不是授权。
- 本模板不是 packet 文件。
- 本模板不等于 packet file creation authorization。
- Codex 不得自行把 `draft_status` 改成 `approved`。
- Codex 不得自行把 `ready_for_human_review` 改成 `true`。
- Codex 不得自行把 `ready_for_packet_file_creation` 改成 `true`。
- Codex 不得自行把 `authorized_for_packet_file_creation` 改成 `true`。
- 真实 packet 文件创建必须单独阶段、用户明确授权、真实 auth form、显式路径。
