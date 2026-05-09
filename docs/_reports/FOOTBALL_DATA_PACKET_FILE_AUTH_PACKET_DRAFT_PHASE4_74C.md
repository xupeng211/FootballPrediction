# Phase 4.74C：Football-Data Packet File Creation Authorization Packet Draft

**日期**: 2026-05-09
**分支**: feat/football-data-packet-file-auth-packet-draft-phase474c
**起始 HEAD**: f82af575ae1c1392117d235e7fcc19368ccc5e5a

---

## 1. 概述

Phase 4.74C 准备"未来创建真实 packet 文件前，提交给人类审核的授权材料包草案模板和 dry-run draft review"。

本阶段不创建 `docs/_packets` 目录、不写真实 packet 文件、不写 packet manifest、不写 DB、不执行 pg_dump / pg_restore。

---

## 2. 为什么做稍大主题 PR 是合理的

Phase 4.74C 需要同时交付以下内容才能形成完整的 authorization packet draft 体系：

- Authorization packet draft template（定义草案格式）
- Draft review script（生成 draft review，复用 5 个已有 gates）
- Makefile entries（review + blocked commit）
- Unit tests（26 个测试用例，保证安全边界）
- AGENTS.md updates（规则文档化）
- Phase report（可追溯性）

这 6 个交付物互相依赖，拆分会导致中间态的 PR 无法独立验证。作为一个 consolidation PR 一次性交付是最合理的方式。

---

## 3. 新增文件

| 文件                                                                             | 用途                            |
| -------------------------------------------------------------------------------- | ------------------------------- |
| `docs/runbooks/FOOTBALL_DATA_PACKET_FILE_CREATION_AUTH_PACKET_DRAFT_TEMPLATE.md` | Authorization packet draft 模板 |
| `scripts/ops/football_data_packet_file_auth_packet_draft.js`                     | Draft review 脚本               |
| `tests/unit/football_data_packet_file_auth_packet_draft.test.js`                 | Unit tests (26 个)              |

## 4. 修改文件

| 文件        | 变更                                                                                                                      |
| ----------- | ------------------------------------------------------------------------------------------------------------------------- |
| `Makefile`  | 新增 `data-football-data-packet-file-auth-packet-draft` 和 `data-football-data-packet-file-auth-packet-draft-commit` 入口 |
| `AGENTS.md` | 新增 Phase 4.74C 规则                                                                                                     |

---

## 5. Authorization Packet Draft Template 设计

模板包含 machine-readable YAML block，覆盖以下部分：

- **draft status**: `draft_status=draft_only`
- **authorization**: `packet_file_creation_authorized=false`, `readiness_status=not_ready`
- **draft_inputs**: 7 个必需输入项
- **required_human_fields**: 10 个人工填写字段
- **permission_separation**: 5 个权限分离声明
- **safety_defaults**: 9 个安全默认值（全 false）
- **final_decision**: `ready_for_human_review=false`, `ready_for_packet_file_creation=false`, `authorized_for_packet_file_creation=false`

### 5.1 Draft Review Script

`football_data_packet_file_auth_packet_draft.js` 复用已有 gates：

- Phase 4.73C `runReadinessReview`
- Phase 4.72C `runAuthorizationReview`
- Phase 4.71C `runValidation` (auth form)
- Phase 4.70C `runPacketFilePreflight`
- Phase 4.69C `runPacketAssembly` (packet preview)
- SELECT-only DB row count inspection

### 5.2 依赖注入

支持 `dependencies` 参数注入：`existsSync`, `readFileSync`, `dbClient`, `createPool`，允许 unit test 不连接真实 DB。

---

## 6. draft_status=draft_only 的原因

当前所有检查项的默认值都是不满足状态：

- `draft_status=draft_only`
- `ready_for_human_review=false`
- `ready_for_packet_file_creation=false`
- `authorized_for_packet_file_creation=false`
- `packet_file_creation_authorized=false`
- `readiness_status=not_ready`
- `authorization_status=not_authorized`
- `final_packet_creation_confirmation=false`

这些只有在用户手动填写 draft、提供真实参数、完成所有 gates 并经过人类审核后才能变为 approved。

---

## 7. Authorization Packet Draft Sections

```
- packet_creation_scope
- source_inputs_summary
- gate_results_summary
- readiness_review_summary
- authorization_review_summary
- proposed_packet_paths
- proposed_packet_metadata
- proposed_candidate_match_ids
- blocked_candidate_summary
- manual_review_summary
- human_only_fields
- missing_readiness_items
- permission_separation
- final_human_decision_required
```

---

## 8. Missing Draft Requirements

```
- draft_status must remain draft_only until human review
- readiness_status must be ready before creation
- authorization_status must be authorized_for_packet_file_creation
- final_packet_creation_confirmation must be true
- operator must be filled
- reviewer must be filled
- human_approval_note must be present
- packet_creation_reason must be present
- packet_directory must be explicit
- packet_file must be explicit
- packet_manifest_file must be explicit
- approved_candidate_match_ids must be reviewed
- manual_review_candidate_match_ids must be excluded or resolved
```

---

## 9. Permission Separation

```
- authorization packet draft does not authorize packet file creation
- packet file creation does not authorize DB write
- packet file creation does not authorize pg_dump
- packet file creation does not authorize pg_restore
- packet file creation does not authorize training
- packet file creation does not authorize prediction
```

---

## 10. Why No Actions Were Performed

### 为什么不创建 packet 文件？

Packet 文件创建需要：

1. 用户明确授权
2. 真实 auth form（非模板/草案）
3. 显式输出目录和文件路径
4. 所有 gates + readiness + human review 全部通过
5. 单独阶段执行

当前 `draft_status=draft_only`、`authorized_for_packet_file_creation=false`，这些条件均不满足。

### 为什么不创建目录？

目录创建是 packet 文件创建的前置操作，同样需要用户明确授权。

### 为什么不写 DB？

DB write 是与 packet 文件创建独立的操作，需要单独授权、真实 pg_dump、非空备份验证。

### 为什么不执行 pg_dump？

pg_dump 是 DB write 前的前置保护操作，需要用户明确授权。不写 DB 时不需要 pg_dump。

---

## 11. Commit Gate Blocked

`make data-football-data-packet-file-auth-packet-draft-commit` 双重 blocked：

- 无 `CONFIRM`: `BLOCKED: football-data auth packet draft requires CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH_PACKET_DRAFT=1 and is not wired in Phase 4.74C.`
- 有 `CONFIRM=1`: `BLOCKED: football-data auth packet draft commit is not wired in Phase 4.74C.`

---

## 12. Existing Gates Re-verification

| Gate                         | 状态                                  |
| ---------------------------- | ------------------------------------- |
| packet file readiness review | OK (`readiness_status=not_ready`)     |
| packet file auth review      | OK (`ok=true`, `commit_gate=blocked`) |
| packet file auth validate    | OK                                    |
| packet file preflight        | OK                                    |
| packet preview               | OK                                    |
| CSV dry-run                  | OK                                    |
| DB write preflight           | OK                                    |
| duplicate precheck           | OK                                    |
| insert policy precheck       | OK                                    |
| small write auth preview     | OK                                    |
| runbook validation           | OK                                    |

---

## 13. Test Results

| Command                                               | Result                                                 |
| ----------------------------------------------------- | ------------------------------------------------------ |
| `football_data_packet_file_auth_packet_draft.test.js` | 26/26 pass                                             |
| All football-data tests (14 files)                    | 314/314 pass                                           |
| `npm test`                                            | 48/48 pass                                             |
| `npm run test:coverage`                               | PASS (lines=88.48%, branches=80.06%, functions=81.28%) |

---

## 14. DB Row Counts (Before and After)

| Table                   | Before | After |
| ----------------------- | ------ | ----- |
| matches                 | 2      | 2     |
| bookmaker_odds_history  | 2      | 2     |
| raw_match_data          | 2      | 2     |
| l3_features             | 2      | 2     |
| match_features_training | 2      | 2     |
| predictions             | 2      | 2     |

DB 行数未变化。

---

## 15. Next Steps

### Option A: Phase 4.75C — packet file creation authorization packet review consolidation

- 将 draft review、readiness review、auth review 合并为统一的 final authorization packet review
- 不创建 packet 文件
- 不写 DB
- 不执行 pg_dump

### Option B: Phase 4.56A — 真实 network dry-run

用户给齐真实 network dry-run 参数后才做 runbook：

- 真实 ENGINE / TARGET_MATCH_ID / SOURCE_MANIFEST
- 不执行真实 network 请求
- 不写 DB

---

## 16. 明确未执行事项

以下操作均未执行：

- DB writes (INSERT/UPDATE/DELETE/CREATE/ALTER/DROP/TRUNCATE/COPY)
- non-SELECT DB SQL
- pg_dump execution
- pg_restore execution
- backup file writes
- packet file writes
- packet manifest writes
- packet directory creation (`docs/_packets/` 不存在)
- file writes from auth packet draft runtime
- draft_status 改为 approved
- readiness_status 改为 ready
- authorization_status 改为 authorized_for_packet_file_creation
- final_packet_creation_confirmation 改为 true
- approval_status 改为 approved_for_db_write
- final_human_confirmation 改为 true
- external download
- curl / wget / git clone
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
- git fetch --all
- git pull
- 删除文件
