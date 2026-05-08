# FOOTBALL_DATA_PACKET_FILE_AUTH_REVIEW_PHASE4_72C

## 1. 当前 HEAD / branch

- base HEAD: `f16d969d0ea36db3f00b222df1966460c2d4f56a`
- 工作分支: `feat/football-data-packet-file-auth-review-phase472c`
- 阶段: `PHASE4.72C_FOOTBALL_DATA_PACKET_FILE_AUTH_REVIEW`

## 2. 为什么这次做稍大主题 PR 是合理的

本阶段不是单点脚本补丁，而是把 Phase 4.71C 的 packet file creation authorization template
推进到下一层治理能力：

- 需要新增独立 review gate
- 需要把 auth form validator、packet file preflight 和 packet preview 串起来
- 需要把“ready / authorized 仍为 false”的 dry-run review 结果标准化输出
- 需要新增 blocked commit 入口、unit tests、AGENTS 规则和阶段报告

这些改动属于单一安全主题，集中在同一个 PR 内更容易审计。

## 3. 新增文件

- `scripts/ops/football_data_packet_file_auth_review.js`
- `tests/unit/football_data_packet_file_auth_review.test.js`
- `docs/_reports/FOOTBALL_DATA_PACKET_FILE_AUTH_REVIEW_PHASE4_72C.md`

同时更新：

- `Makefile`
- `AGENTS.md`

## 4. authorization review 设计

Phase 4.72C review script 只做 dry-run authorization review，不授予权限，不执行写动作。

输入：

- packet file creation auth form
- source manifest
- local CSV
- approval form
- runbook template

复用：

- Phase 4.71C `football_data_packet_file_auth_validate.js`
- Phase 4.70C `football_data_packet_file_preflight.js`
- Phase 4.69C `football_data_small_write_packet_assembly.js`

额外行为：

- 输出 review summary 到 stdout
- 显式给出 `packet_file_creation_ready=false`
- 显式给出 `packet_file_creation_authorized=false`
- 显式给出 `approval_granted=false`
- 显式列出缺失的人类授权条件
- 显式列出 human-only fields
- 显式列出 permission separation
- 只做 SELECT-only DB row count inspection

## 5. missing_authorization_requirements

review 输出固定检查并报告以下缺口：

- `authorization_status must be authorized_for_packet_file_creation`
- `final_packet_creation_confirmation must be true`
- `operator must be filled`
- `reviewer must be filled`
- `packet_directory must be explicit`
- `packet_file must be explicit`
- `packet_manifest_file must be explicit`
- `source_manifest must match reviewed source`
- `local_csv must match reviewed CSV`
- `approved_candidate_match_ids must be reviewed`
- `manual_review_candidate_match_ids must be excluded or resolved`
- `human_approval_note must be present`

当前模板默认 `not_authorized`，因此本阶段 review 预期仍然输出未满足状态。

## 6. human_only_fields

review 输出固定标记以下字段只能由人类在未来真实授权阶段填写或修改：

- `authorization_status`
- `final_packet_creation_confirmation`
- `operator`
- `reviewer`
- `human_approval_note`
- `approved_candidate_match_ids`
- `excluded_candidate_match_ids`
- `manual_review_candidate_match_ids`
- `packet_creation_reason`

## 7. permission_separation

review 输出固定声明：

- packet file creation does not authorize DB write
- packet file creation does not authorize `pg_dump`
- packet file creation does not authorize `pg_restore`
- packet file creation does not authorize training
- packet file creation does not authorize prediction

这保证 packet file authorization 不会被误解为下游链路总授权。

## 8. 为什么本阶段不创建 packet 文件

因为 Phase 4.72C 的目标是 authorization review，不是 authorization grant，也不是 packet file creation phase。

本阶段只允许：

- 读取本地文件
- 复用 dry-run gate
- 输出 stdout summary
- 做 SELECT-only DB row count inspection

本阶段不允许：

- packet 文件写入
- packet manifest 写入
- backup 写入

## 9. 为什么本阶段不创建目录

packet directory 仍属于未来真实 packet file creation 行为的一部分。

当前 review 只判断“未来是否可能被授权”，不触发任何 filesystem side effect，
因此不得创建输出目录，也不得生成 staging / packet 路径实体。

## 10. 为什么本阶段不写 DB

本阶段的 DB 访问范围仅限 SELECT-only row count inspection。

review 结果不会触发：

- `INSERT`
- `UPDATE`
- `DELETE`
- 任何 schema 变更

因此 `packet_file_creation_ready` 和 `packet_file_creation_authorized` 都保持 false。

## 11. 为什么本阶段不执行 pg_dump

`pg_dump` 仍属于未来真实 DB write 之前的独立授权事项。

即使未来允许 packet file creation，也不代表同时允许：

- `pg_dump`
- `pg_restore`
- DB write

因此本阶段只保留 preview / separation 声明，不执行真实备份命令。

## 12. commit gate blocked 结果

新增：

- `make data-football-data-packet-file-auth-review`
- `make data-football-data-packet-file-auth-review-commit`

其中 commit 入口保持 blocked：

- 默认 blocked
- 即使提供 `CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH_REVIEW=1` 仍 blocked

blocked message:

`BLOCKED: football-data packet file authorization review commit is not wired in Phase 4.72C.`

本地验证结果：

- 缺参数时 `make data-football-data-packet-file-auth-review` 按预期失败
- 正确参数下 review 成功
- 输出确认：
    - `authorization_review_completed=true`
    - `packet_file_creation_ready=false`
    - `packet_file_creation_authorized=false`
    - `authorization_status=not_authorized`
    - `final_packet_creation_confirmation=false`
    - `approval_granted=false`
- `make data-football-data-packet-file-auth-review-commit` 在无确认参数和有确认参数两种情况下都保持 blocked

## 13. 现有 gates 复验结果

要求复验的既有 gate 继续成功：

- packet file auth validation
- packet file preflight
- small write packet preview
- CSV dry-run
- DB write preflight
- duplicate precheck
- insert policy precheck
- small write auth preview
- runbook validation

并保持：

- no DB write
- no packet file write
- no packet directory creation
- no `pg_dump`
- no `pg_restore`

本地复验结果：以上 gate 全部成功，并保持 dry-run / preview-only 行为。

## 14. unit tests 结果

新增 `tests/unit/football_data_packet_file_auth_review.test.js`，覆盖：

- 缺参数失败
- 正确 template review 成功
- summary 字段正确
- missing authorization requirements
- human-only fields
- permission separation
- authorized-looking form 仍不得触发写动作
- `--commit` blocked
- sha256 mismatch 失败且不查 DB
- auth / approval failure path
- no network / no file write / no mkdir / no child process
- SQL 只允许 `BEGIN READ ONLY` / `SELECT` / `ROLLBACK`

执行结果：

- `tests/unit/football_data_packet_file_auth_review.test.js` 通过
- 相关既有 Football-Data unit tests 全部通过

## 15. npm test / test:coverage 结果

本阶段要求：

- `npm test` 通过
- `npm run test:coverage` 通过
- coverage 阈值保持不变：
    - lines >= 80
    - functions >= 80
    - branches >= 80

实际结果：

- `npm test` 通过
- `npm run test:coverage` 通过
- coverage:
    - lines `88.68`
    - functions `81.10`
    - branches `80.03`

## 16. DB 前后统计

本阶段前后期望保持：

- `matches=2`
- `bookmaker_odds_history=2`
- `raw_match_data=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

review 脚本只允许 SELECT-only DB row count inspection，不得修改这些计数。

本地前后核对结果保持不变：

- `matches=2`
- `bookmaker_odds_history=2`
- `raw_match_data=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

## 17. 下一步建议

建议二选一：

- `Phase 4.73C`：packet file creation readiness checklist consolidation  
  继续不写 packet 文件、不写 DB、不执行 `pg_dump`

- `Phase 4.56A`：用户给齐真实 network dry-run 参数后才做 runbook  
  仍需单独授权，且不绕过现有 gate

## 18. 明确未执行事项

本阶段明确未执行：

- DB writes
- non-SELECT DB SQL
- `pg_dump` execution
- `pg_restore` execution
- backup file writes
- packet file writes
- packet manifest writes
- packet directory creation
- auth review runtime file writes
- 将 `authorization_status` 改成 `authorized_for_packet_file_creation`
- 将 `final_packet_creation_confirmation` 改成 `true`
- 将 `approval_status` 改成 `approved_for_db_write`
- 将 `final_human_confirmation` 改成 `true`
- external download
- `curl` / `wget` / `git clone`
- 外部足球数据源访问
- 外部赔率数据源访问
- scraping / browser automation
- harvest / ingest
- batch backfill
- network dry-run 真执行
- bulk harvest
- adapted CSV / staging 数据写入
- model training
- real prediction execution
- model artifact loading
- Docker volume 清理
- force push
- `git fetch --all`
- `git pull`
- 删除已有报告
- 删除文件
