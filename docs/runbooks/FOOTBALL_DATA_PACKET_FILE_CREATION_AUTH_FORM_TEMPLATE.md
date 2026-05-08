# Football-Data Packet File Creation Authorization Form Template

> 模板用途：未来如需真正创建 packet 文件，先由人工填写和审批这个授权表。
>
> 本文件在 Phase 4.71C 只是模板，不是真实授权；不允许据此创建目录、写 packet 文件、写 packet manifest、写 DB、执行 `pg_dump` / `pg_restore`、训练或预测。

```yaml
phase: PHASE4_PACKET_FILE_CREATION_AUTH
authorization_status: not_authorized
operator:
reviewer:
source_manifest:
local_csv:
approval_form:
runbook_template:
packet_directory:
packet_file:
packet_manifest_file:
packet_version:
source_name:
source_sha256:
row_count:
allow_packet_directory_creation: false
allow_packet_file_write: false
allow_packet_manifest_write: false
allow_db_write: false
allow_pg_dump: false
allow_pg_restore: false
allow_external_network: false
allow_training: false
allow_prediction: false
approved_packet_sections:
    - source_manifest_summary
    - local_csv_summary
    - csv_dry_run_summary
    - db_write_preflight_summary
    - duplicate_precheck_summary
    - insert_policy_summary
    - small_write_auth_preview_summary
    - runbook_template_summary
    - approval_form_summary
    - proposed_match_ids
    - insert_candidate_table
    - blocked_candidate_table
    - manual_review_table
    - pg_dump_command_preview
    - post_write_validation_checklist
    - rollback_restore_preview
    - final_human_approval_required
approved_output_root: docs/_packets/football_data/small_write
approved_candidate_match_ids: []
excluded_candidate_match_ids: []
manual_review_candidate_match_ids: []
packet_creation_reason:
human_approval_note:
final_packet_creation_confirmation: false
```

## 说明

- 默认 `authorization_status=not_authorized`。
- 默认 `allow_packet_directory_creation=false`，不允许创建目录。
- 默认 `allow_packet_file_write=false`，不允许写 packet 文件。
- 默认 `allow_packet_manifest_write=false`，不允许写 packet manifest。
- 默认 `allow_db_write=false`，不允许写 DB。
- 默认 `allow_pg_dump=false`、`allow_pg_restore=false`。
- 默认 `allow_external_network=false`、`allow_training=false`、`allow_prediction=false`。
- Codex 不得自行把 `authorization_status` 改成 `authorized_for_packet_file_creation`。
- Codex 不得自行把 `final_packet_creation_confirmation` 改成 `true`。
- 本阶段只提供模板和校验 gate，不是真实授权，也不会真正创建 packet 文件。
