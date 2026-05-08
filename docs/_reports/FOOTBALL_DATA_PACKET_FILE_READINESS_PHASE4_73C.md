# Phase 4.73C：Football-Data Packet File Creation Readiness Checklist Consolidation

**日期**: 2026-05-09
**分支**: feat/football-data-packet-file-readiness-phase473c
**起始 HEAD**: edfa46e9f21193a8d8f599773b3956d129abcb23

---

## 1. 概述

Phase 4.73C 将未来"真正创建 packet 文件"之前必须满足的 readiness checklist 汇总为一个清晰、可验证、可审计的 consolidated checklist。

本阶段不创建 packet 文件、不创建目录、不写 DB、不执行 pg_dump / pg_restore。

---

## 2. 为什么做稍大主题 PR 是合理的

Phase 4.73C 需要同时交付以下内容才能形成完整的 consolidation 体系：

- Readiness checklist template（定义格式）
- Review script（读取/验证 checklist）
- Makefile entries（入口和 blocked commit）
- Unit tests（保证正确性）
- AGENTS.md updates（规则文档化）
- Phase report（可追溯性）

这 6 个交付物互相依赖，拆分会导致中间态的 PR 无法独立验证。作为一个 consolidation PR 一次性交付是最合理的方式。

---

## 3. 新增文件

| 文件                                                                               | 用途                       |
| ---------------------------------------------------------------------------------- | -------------------------- |
| `docs/runbooks/FOOTBALL_DATA_PACKET_FILE_CREATION_READINESS_CHECKLIST_TEMPLATE.md` | Readiness checklist 模板   |
| `scripts/ops/football_data_packet_file_readiness_review.js`                        | Readiness 合并 review 脚本 |
| `tests/unit/football_data_packet_file_readiness_review.test.js`                    | Unit tests (26 个)         |

## 4. 修改文件

| 文件        | 变更                                                                                                             |
| ----------- | ---------------------------------------------------------------------------------------------------------------- |
| `Makefile`  | 新增 `data-football-data-packet-file-readiness-review` 和 `data-football-data-packet-file-readiness-commit` 入口 |
| `AGENTS.md` | 新增 Phase 4.73C 规则                                                                                            |

---

## 5. Readiness Checklist Consolidation 设计

### 5.1 Checklist Template

模板包含 machine-readable YAML block，覆盖以下检查类别：

- **source_checks**: source manifest / local CSV / sha256 / row_count
- **gate_checks**: 10 个 pipeline gate 的通过状态
- **authorization_checks**: authorization_status / final_packet_creation_confirmation / human approval
- **safety_checks**: 9 个 禁止/允许 标志（目录创建、文件写入、DB 写入、pg_dump 等）
- **candidate_checks**: match ID 候选集审核状态
- **final_readiness**: 最终 readiness 状态（全 false）

### 5.2 Review Script

`football_data_packet_file_readiness_review.js` 复用已有的 gate 逻辑：

- packet file auth review (Phase 4.72C)
- packet file auth validator (Phase 4.71C)
- packet file preflight (Phase 4.70C)
- packet preview (Phase 4.69C)
- SELECT-only DB row count inspection

输出 consolidated readiness review，包含：

- missing_readiness_items
- permission_separation
- human_only_fields
- non_execution_confirmations

### 5.3 依赖注入设计

Review 脚本支持 `dependencies` 参数注入：

- `existsSync` / `readFileSync` — 文件系统 mock
- `dbClient` — DB client mock
- `createPool` — pg Pool factory mock

这使得 unit test 不需要连接真实 DB。

---

## 6. readiness_status=not_ready 的原因

当前所有检查项的默认值都是不满足状态：

- `readiness_status=not_ready`
- `packet_file_creation_ready=false`
- `packet_file_creation_authorized=false`
- `authorization_status=not_authorized`
- `final_packet_creation_confirmation=false`
- 所有 `safety_checks` 标志均为 false

这些只有在用户手动填写 checklist、提供真实参数、完成所有 gates 后才能变为 ready。

---

## 7. Missing Readiness Items

```
- readiness_status must be ready
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
- packet file creation must be separately authorized by human
```

---

## 8. Human-Only Fields

以下字段只能由人工填写和审核，Codex 不得自行修改：

```
- readiness_status
- authorization_status
- final_packet_creation_confirmation
- operator
- reviewer
- human_approval_note
- packet_creation_reason
- approved_candidate_match_ids
- excluded_candidate_match_ids
- manual_review_candidate_match_ids
- packet_directory
- packet_file
- packet_manifest_file
```

---

## 9. Permission Separation

```
- readiness does not authorize packet file creation
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
2. 真实 auth form（非模板）
3. 显式输出目录和文件路径
4. 所有 readiness items 满足
5. 单独阶段执行

当前 readiness_status=not_ready，这些条件均不满足。

### 为什么不创建目录？

目录创建是 packet 文件创建的前置操作，同样需要用户明确授权。

### 为什么不写 DB？

DB write 是与 packet 文件创建独立的操作，需要单独授权、真实 pg_dump、非空备份验证。

### 为什么不执行 pg_dump？

pg_dump 是 DB write 前的前置保护操作，需要用户明确授权。不创建 packet 文件时不需要 pg_dump。

---

## 11. Commit Gate Blocked

`make data-football-data-packet-file-readiness-commit` 即使在 `CONFIRM_FOOTBALL_DATA_PACKET_FILE_READINESS=1` 时也 block：

```
BLOCKED: football-data packet file readiness commit is not wired in Phase 4.73C.
```

---

## 12. Existing Gates Re-verification

所有已有 gates 复验通过：

| Gate                       | 状态 |
| -------------------------- | ---- |
| packet file auth review    | OK   |
| packet file auth validate  | OK   |
| packet file preflight      | OK   |
| small write packet preview | OK   |
| CSV dry-run                | OK   |
| DB write preflight         | OK   |
| duplicate precheck         | OK   |
| insert policy precheck     | OK   |
| small write auth preview   | OK   |
| runbook validate           | OK   |

---

## 13. Test Results

| Command                                              | Result                                                 |
| ---------------------------------------------------- | ------------------------------------------------------ |
| `football_data_packet_file_readiness_review.test.js` | 26/26 pass                                             |
| All football-data tests (13 files)                   | 288/288 pass                                           |
| `npm test`                                           | 48/48 pass                                             |
| `npm run test:coverage`                              | PASS (lines=88.59%, branches=80.08%, functions=81.23%) |

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

### Option A: Phase 4.74C — packet file creation authorization packet draft

在 Phase 4.74C 中：

- 准备真实的 packet file creation authorization form
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

- DB writes (INSERT / UPDATE / DELETE / CREATE / ALTER / DROP / TRUNCATE / COPY)
- non-SELECT DB SQL
- pg_dump execution
- pg_restore execution
- backup file writes
- packet file writes
- packet manifest writes
- packet directory creation
- file writes from readiness review runtime
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
