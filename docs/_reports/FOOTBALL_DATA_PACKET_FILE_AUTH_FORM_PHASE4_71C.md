# Football-Data Packet File Creation Authorization Form - Phase 4.71C

## 1. 当前 HEAD / branch

- 起始 HEAD: `ec41c82d18540fd0a02c56eaeea7c9405bf29626`
- 工作分支: `docs/football-data-packet-file-auth-phase471c`
- 报告整理时本地分支仍未提交，HEAD 仍指向 `ec41c82d18540fd0a02c56eaeea7c9405bf29626`

## 2. 为什么这次做稍大主题 PR 是合理的

Phase 4.71C 增加的是一个完整但仍然不执行写入的安全层：packet file creation authorization form template、validator、Makefile validate / blocked commit gate、unit tests、AGENTS 规则和阶段报告共同定义了同一个边界。把这些内容放在一个 PR 里，审计对象更集中，也更容易确认“只新增授权模板与校验，不新增任何真实写入能力”。

## 3. 新增 / 修改文件

- `docs/runbooks/FOOTBALL_DATA_PACKET_FILE_CREATION_AUTH_FORM_TEMPLATE.md`
- `scripts/ops/football_data_packet_file_auth_validate.js`
- `tests/unit/football_data_packet_file_auth_validate.test.js`
- `Makefile`
- `AGENTS.md`
- `docs/_reports/FOOTBALL_DATA_PACKET_FILE_AUTH_FORM_PHASE4_71C.md`

## 4. packet file creation auth form 设计

新的模板文件是：

```text
docs/runbooks/FOOTBALL_DATA_PACKET_FILE_CREATION_AUTH_FORM_TEMPLATE.md
```

模板内含 machine-readable YAML fenced block，覆盖：

- source manifest / local CSV / approval form / runbook template 引用
- future packet directory / packet file / packet manifest file 字段
- source sha256 / row_count
- `approved_output_root`
- `approved_packet_sections`
- candidate / excluded / manual review match_id 列表
- packet creation reason / human note
- `final_packet_creation_confirmation`

该模板默认保留人工审批状态，不提供真实 packet file write、packet manifest write、DB write、`pg_dump`、`pg_restore`、training 或 prediction 权限。

## 5. 默认 not_authorized 的原因

本阶段只是在 future packet file creation 之前补一个单独的授权层。只要真实 packet 文件还没有被单独授权，模板就必须保持：

- `authorization_status=not_authorized`
- `final_packet_creation_confirmation=false`

这样可以明确区分：

- packet file preflight / preview
- packet file creation authorization review
- future real packet file creation

Codex 不得自行把 `authorization_status` 改成 `authorized_for_packet_file_creation`，也不得把 `final_packet_creation_confirmation` 改成 `true`。

## 6. validator 设计

新脚本：

```bash
node scripts/ops/football_data_packet_file_auth_validate.js \
  --auth-form docs/runbooks/FOOTBALL_DATA_PACKET_FILE_CREATION_AUTH_FORM_TEMPLATE.md
```

validator 只做本地 markdown 读取与 YAML block 校验，不访问外网、不读 DB、不写 DB、不写文件、不创建目录、不执行 `pg_dump`、不执行 `pg_restore`、不 spawn child process。

校验点包括：

- required fields 是否齐全
- `phase` 是否保持模板值
- `authorization_status=not_authorized`
- packet / DB / network / training / prediction 相关布尔字段是否全部为 `false`
- `final_packet_creation_confirmation=false`
- `approved_output_root` 是否保持在 `docs/_packets/football_data/small_write`
- `approved_packet_sections` 是否包含 Phase 4.69C 要求的全部 sections

`--commit` 分支仍然 blocked：

```text
BLOCKED: football-data packet file creation authorization commit is not wired in Phase 4.71C.
```

## 7. approved_output_root 规则

`approved_output_root` 必须保持在：

```text
docs/_packets/football_data/small_write
```

原因是 packet file 的 future 输出根目录需要在审计范围内固定，不能在 Phase 4.71C 允许自由漂移到其他路径。当前模板默认写死这个安全根目录，validator 也会拒绝任何越界路径。

## 8. approved_packet_sections 规则

`approved_packet_sections` 必须覆盖 Phase 4.69C packet preview 已经定义的全部 section：

- `source_manifest_summary`
- `local_csv_summary`
- `csv_dry_run_summary`
- `db_write_preflight_summary`
- `duplicate_precheck_summary`
- `insert_policy_summary`
- `small_write_auth_preview_summary`
- `runbook_template_summary`
- `approval_form_summary`
- `proposed_match_ids`
- `insert_candidate_table`
- `blocked_candidate_table`
- `manual_review_table`
- `pg_dump_command_preview`
- `post_write_validation_checklist`
- `rollback_restore_preview`
- `final_human_approval_required`

这样未来即使进入单独授权评审，也不会遗漏 preflight / preview 阶段已经要求过的核心材料。

## 9. 为什么本阶段不创建 packet 文件

Phase 4.71C 只新增授权模板和 validator，没有进入真实 packet file creation。validator 输出和 Makefile gate 都保持：

- `authorization_granted=false`
- `would_write_packet_file=false`
- `would_write_packet_manifest=false`

真实 packet file write 仍需未来单独阶段和用户明确授权。

## 10. 为什么本阶段不创建目录

packet 目录创建本身就是实际文件系统变更。本阶段模板和 validator 只允许预先定义未来授权边界，不允许落地创建：

- `would_create_packet_directory=false`
- `no_packet_directory_create`

## 11. 为什么本阶段不写 DB

packet file creation authorization form 不是 DB write authorization。当前 validator 不读 DB，Makefile auth commit gate 也保持 blocked，因此本阶段没有 `INSERT / UPDATE / DELETE`，也没有任何真实写库行为。

## 12. 为什么本阶段不执行 pg_dump

packet file creation 不等于 DB write pre-write backup。真实 `pg_dump` 仍属于未来真实 DB write 之前的单独授权动作。本阶段 validator 和 blocked commit gate 都不会执行：

- `would_execute_pg_dump=false`
- `would_execute_pg_restore=false`

## 13. commit gate blocked 结果

以下两个命令都保持 blocked：

- `make data-football-data-packet-file-auth-commit || true`
- `make data-football-data-packet-file-auth-commit AUTH_FORM=... CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH=1 || true`

blocked message:

```text
BLOCKED: football-data packet file creation authorization commit is not wired in Phase 4.71C.
```

同时也验证了缺确认参数时的 blocked 分支：

```text
BLOCKED: football-data packet file creation authorization requires CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH=1 and is not wired in Phase 4.71C.
```

## 14. 现有 gates 复验结果

以下已有 gate 已全部继续通过，且未写 DB、未执行 `pg_dump`、未创建 packet 文件：

- `make data-football-data-packet-file-preflight`
- `make data-football-data-small-write-packet-preview`
- `make data-football-data-csv-dry-run`
- `make data-football-data-db-write-preflight`
- `make data-football-data-duplicate-precheck`
- `make data-football-data-insert-policy-precheck`
- `make data-football-data-small-write-auth-preview`
- `make data-football-data-small-write-runbook-validate`

观测结果：

- packet file preflight: passed
- small write packet preview: passed
- CSV dry-run: passed
- DB write preflight: passed
- duplicate precheck: passed
- insert policy precheck: passed
- small write auth preview: passed
- runbook validate: passed

## 15. unit tests 结果

本阶段已运行并通过：

- `tests/unit/football_data_packet_file_auth_validate.test.js`
- `tests/unit/football_data_packet_file_preflight.test.js`
- `tests/unit/football_data_small_write_packet_assembly.test.js`
- `tests/unit/football_data_small_write_runbook_validate.test.js`
- `tests/unit/football_data_small_write_auth_preview.test.js`
- `tests/unit/football_data_insert_policy_precheck.test.js`
- `tests/unit/football_data_duplicate_precheck.test.js`
- `tests/unit/football_data_db_write_preflight.test.js`
- `tests/unit/football_data_adapter_dry_run.test.js`
- `tests/unit/football_data_local_csv_parser.test.js`
- `tests/unit/acquisition_engine_gate.test.js`

其中 `tests/unit/football_data_packet_file_auth_validate.test.js` 为新文件，最终覆盖：

- 缺参数
- 正常模板 validation
- help / JSON / text output
- 未知参数
- YAML fenced block 缺失
- YAML 顶层 / nested / indentation 解析失败
- required field 缺失
- `phase` / `authorization_status` 错误
- packet / DB / network / training / prediction 布尔字段越权
- `approved_output_root` 错误
- `approved_packet_sections` 缺失
- blocked commit
- no-network / no-db / no-file-write / no-directory-create / no-`pg_dump` / no-`pg_restore` / no-child-process
- 真实 CLI `--help` 入口

## 16. npm test / test:coverage 结果

本阶段已运行并通过：

- `docker compose -f docker-compose.dev.yml exec -T dev npm test`
- `docker compose -f docker-compose.dev.yml exec -T dev npm run test:coverage`

coverage 阈值保持不变，最终结果为：

- lines >= 80
- functions >= 80
- branches >= 80

实际 summary：

- lines: `88.52`
- functions: `80.96`
- branches: `80.01`

说明：

- 首次全量 coverage 结果是 `branches=79.93`
- 在不调整阈值、不扩大改动面的前提下，只对新增 `football_data_packet_file_auth_validate` 补充分支测试
- 第二次结果是 `branches=79.96`
- 再补两条针对 text output 和真实 CLI 入口的最小测试后，最终达到 `branches=80.01`

## 17. DB 前后统计

本阶段开始和结束都保持：

- `matches=2`
- `bookmaker_odds_history=2`
- `raw_match_data=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

## 18. 下一步建议

- Phase 4.72C：packet file creation dry-run authorization review，不写 packet 文件、不写 DB、不执行 `pg_dump`
- 或 Phase 4.56A：用户给齐真实 network dry-run 参数后才做 runbook

## 19. 明确未执行事项

本阶段设计上明确不执行：

- DB writes
- non-SELECT DB SQL
- `pg_dump`
- `pg_restore`
- backup file writes
- packet file writes
- packet manifest writes
- packet directory creation
- external download
- 外部足球数据源访问
- 外部赔率数据源访问
- scraping / browser automation
- harvest / ingest
- network dry-run 真执行
- training
- prediction
- model artifact loading

另外本阶段实际也未执行：

- packet 目录创建
- packet manifest 文件写入
- auth validator runtime 文件写入
- `authorization_status` 改为 `authorized_for_packet_file_creation`
- `final_packet_creation_confirmation` 改为 `true`
- `approval_status` 改为 `approved_for_db_write`
- `final_human_confirmation` 改为 `true`
