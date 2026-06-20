# Technical Debt & Workflow Audit — Dry Run Report

**Date:** 2026-06-20
**Branch:** `chore/technical-debt-workflow-audit-dry-run`
**Script:** `scripts/ops/technical_debt_workflow_audit_dry_run.js`
**Phase:** `TECHNICAL_DEBT_WORKFLOW_AUDIT_DRY_RUN`
**Type:** READ-ONLY — no network, no DB write, no file modification

---

## Executive Summary

对 FootballPrediction 仓库的 8 个审计领域进行了只读静态扫描，共发现 **38 个技术债务项**。

**总体债务评级：极高（EXTREMELY_HIGH）**
**Workflow 健康度：中等（MEDIUM）**

### 关键数字

| 指标 | 数量 |
|------|------|
| P0 — 必须立即处理 | 8 |
| P1 — 数据扩容前处理 | 17 |
| P2 — 可排期 | 13 |
| Write risk（缺少安全闸门） | 2 |
| Structural debt（结构性问题） | 24 |
| Stale（过期/僵死） | 11 |
| Dry-run safe | 1 |

### 核心结论

**不能进入 multi_league_multi_season_expansion_plan_dry_run。** 4 个扩张阻断项未解决：

- BM-002: 无 GitHub 分支保护
- DG-001: 训练管线绕过所有治理标签
- DG-002: `init_db.sql` 落后迁移链 7+ 列
- DG-006: 特征泄漏防护策略（cutoff time）未定义

**正式训练被阻断。** 4 个训练阻断项：
- DG-001, DG-002, DG-006（同上）
- DS-002: ELO 算法在 Python 和 JS 中重复实现

---

## 审计范围

1. GitHub Workflows — `.github/workflows/*`, `gatekeeper.sh`, AI Workflow Gate
2. 分支与合并流程 — branch patterns, main 保护, post-merge 验证
3. 测试技术债 — 规模、分布、跳过的测试、模拟、边界
4. 脚本技术债 — `scripts/ops/*`, `scripts/devops/*`, 重复、孤儿、安全闸门
5. 报告和文档债务 — `docs/_reports/*`, 过期、矛盾、缺失
6. 数据治理债务 — governance 字段, training eligibility, raw_match_data, odds
7. Python/JS 双栈债务 — 职责、重复、类型安全、配置一致性
8. 仓库噪音和资产债务 — 大文件、临时文件、gitignore gap

---

## P0 发现（必须立即处理）

### WF-001: 单个 workflow 文件承担所有 CI 职责
- **风险类别:** structural_debt
- **详情:** 仅 1 个 workflow 文件 (`production-gate.yml`)。一个 job (`production-gate`) 串行运行所有检查。无 matrix、无并行、无备用 workflow。
- **影响:** 此文件任何配置错误都会瘫痪整个 CI 管线。
- **建议:** 拆分为独立 workflow：lint, test, security, build。添加 `workflow_dispatch` 触发器。

### BM-001: Gatekeeper 仅识别 `security/*` 和 `feat/*` 为合法工作分支
- **风险类别:** structural_debt
- **详情:** `git_branch_is_preferred_workspace()` 仅接受 `security/*` 和 `feat/*`。实际 `data/*` 分支占远程分支的 82%、合并活动的 73%。
- **影响:** 每次 push 到 `data/*` 都触发 workspace 警告，噪音降低对真实 gate 失败的关注。
- **建议:** 将 `data/*`, `docs/*`, `chore/*` 加入 preferred workspace，或移除 preferred-branch 概念。

### BM-002: 无 GitHub 分支保护规则
- **风险类别:** structural_debt
- **详情:** 无 CODEOWNERS、无必需状态检查、无 merge queue。main 分支保护完全依赖客户端 git hooks（可被 `--no-verify` 绕过）。
- **影响:** 开发者可绕过保护直接推送到 main。
- **建议:** 配置 GitHub 分支保护：要求 PR、要求状态检查、阻止 force push、要求线性历史。

### SC-002: 34 个脚本执行 DB 写入但无环境变量安全闸门
- **风险类别:** write_risk_no_safety_gate
- **详情:** 包含 `INSERT INTO raw_match_data`、`INSERT INTO matches`、`DELETE FROM` 等 SQL 操作，但未检查 `ALLOW_DB_WRITE` / `FINAL_DB_WRITE_CONFIRMATION` / `ALLOW_RAW_MATCH_DATA_WRITE`。
- **影响:** 意外对生产数据库执行写入的可能性很高。这是仓库中风险最高的文件类别。
- **建议:** 为所有 DB 写入脚本添加 `ALLOW_DB_WRITE` 和 `FINAL_DB_WRITE_CONFIRMATION` 门禁。未经明确授权阻止执行。

### DG-001: 训练管线绕过所有治理标签
- **风险类别:** write_risk_no_safety_gate
- **详情:** `train_model.py` 查询 `WHERE m.status = 'Harvested'`（大写 H，从不匹配小写约束），且不引用 `is_training_eligible`, `source_type`, `evidence_level`。
- **影响:** 治理层（V26.7: 6 列）对实际模型训练无任何效果。训练可能使用合成、未验证或泄漏污染的数据。
- **建议:** 修复 status filter 大小写不匹配。添加 `is_training_eligible=true`, `evidence_level IN ('strong','medium')` 检查。

### DG-002: `init_db.sql` 落后迁移链 7+ 列
- **风险类别:** structural_debt
- **详情:** 缺失: `pipeline_status`, `source_type`, `evidence_level`, `is_production_scope`, `is_reconciliation_eligible`, `is_training_eligible`, `pipeline_status_reason` 等。
- **影响:** 全新部署创建破损 schema。基于 `init_db.sql` 的测试使用错误 schema。
- **建议:** 更新 `init_db.sql` 匹配当前迁移状态，或从迁移自动生成。

### DG-006: 特征泄漏防护策略（Rule 3: cutoff time）未定义
- **风险类别:** structural_debt
- **详情:** Training eligibility Rule 3 要求 `prediction_cutoff_time` 策略，但目前不存在。没有它，赛后特征可能泄漏到训练中。
- **影响:** 在 cutoff time 策略定义并强制执行前，训练无法安全开始。
- **建议:** 定义 `prediction_cutoff_time` 策略。在 JS 和 Python 管线中实现时间门控特征提取。

### DS-002: ELO 评分算法在 Python 和 JS 中重复
- **风险类别:** structural_debt
- **详情:** Python: `src/ml/features/elo_rating_system.py` (643 行)。JS: `src/feature_engine/extractors/EloRatingExtractor.js` (356 行) + `EloAutoUpdater.js` (298 行)。无共享算法，无跨栈验证。
- **影响:** 如果 K-factors、起始评分或衰减函数在一个栈中更改，另一个栈会静默偏离。预测将使用过时的 ELO 值。
- **建议:** 将 ELO 算法提取到 `shared_constants.json` 配置中。两个栈从同一配置读取并交叉验证。

---

## P1 发现（数据扩容前必须处理）

### Workflow
- **WF-004:** Push 事件跳过 PR body 治理检查
- **WF-006:** Docker build 验证仅编译，无运行时检查
- **WF-007:** 8 个活跃集成测试文件存在但从不在 CI 中运行
- **WF-008:** 完整覆盖率门禁仅在 push to main 运行，不在 PR 运行

### 分支/合并
- **BM-003:** Post-merge 验证仅手动执行 (`make pr-post-merge-check`)

### 测试
- **TE-001:** 122 个测试文件超过 500 行
- **TE-002:** 严重测试金字塔失衡: ~99% unit, ~1% integration
- **TE-003:** 16 个禁用的测试文件

### 脚本
- **SC-001:** 93 个 dry-run/no-write 脚本 — 过量调查工件
- **SC-004:** `INSERT INTO raw_match_data` 在 14 个脚本中重复
- **SC-005:** `INSERT INTO matches` 在 10 个脚本中重复

### 报告
- **RP-001:** 431 个报告文件（56,536 行）— 过量历史工件
- **RP-002:** 缺失 `docs/DEBT_REGISTER.md`
- **RP-003:** 缺失 `docs/DATA_STATUS.md`
- **RP-005:** `FOTMOB_CURRENT_STATE.md` 携带已取代声明但仍作为主入口文档

### 数据治理
- **DG-003:** `raw_match_data` UNIQUE 约束冲突: `init_db.sql` 有 `UNIQUE(match_id)` 但脚本期望 `UNIQUE(match_id, data_version)`
- **DG-005:** V26.7 治理列存在但全部 NULL — backfill 尚未执行

---

## P2 发现（可排期）

| ID | 标题 | 领域 |
|----|------|------|
| WF-002 | 无 scheduled/cron workflow 触发器 | workflows |
| WF-003 | 无基于路径的 workflow 触发过滤 | workflows |
| WF-009 | 死代码: `scripts/ops/gatekeeper.js` 从未被调用 | workflows |
| BM-004 | 远程分支过多: 179 branches on origin | branches |
| BM-005 | 分支命名约定仅在 gatekeeper.sh 中编码，不在文档中 | branches |
| TE-005 | Python 和 JS 测试遵循根本不同的模式 | tests |
| SC-003 | 227 个脚本未被 Makefile/package.json/gatekeeper.sh 引用 | scripts |
| RP-004 | PROJECT_STATUS.md 报告计数过时（声称 363，实际 431） | reports |
| DS-004 | 380K 行 JavaScript 无类型系统 | dual-stack |
| RN-001 | `.codex-tmp/` 249 MB — 需清理 | repo noise |
| RN-002 | 3 个已跟踪文件匹配 .gitignore 模式但仍在索引中 | repo noise |
| RN-003 | `archive_vault_2026/` 包含 41 个已跟踪源文件 | repo noise |
| RN-005 | 2 个大型遗留测试夹具被 git 跟踪 | repo noise |

---

## 不建议现在处理的内容

1. **大规模 JS → TypeScript 迁移** — 高成本，低优先级，在 P0/P1 解决前不宜启动
2. **完整测试重构** — 122 个超大测试文件的拆分应在建立测试策略后分批进行
3. **所有 431 个报告的归档** — 大规模文档重组应等到 current-state 入口文档就绪后
4. **跨栈统一** — ELO 算法提取后的其他统一工作应在 P0 写安全修复之后

---

## 推荐修复顺序

| 顺序 | 任务 | 优先度 | 预计影响 |
|------|------|--------|----------|
| 1 | 为 34 个 DB 写入脚本添加安全闸门 (SC-002) | P0 | 防止意外生产数据库写入 |
| 2 | 配置 GitHub 分支保护 (BM-002) | P0 | 防止绕过 main 保护 |
| 3 | 修复 `init_db.sql` 与迁移链对齐 (DG-002) | P0 | 确保冷启动 schema 正确 |
| 4 | 定义 cutoff time 策略 (DG-006) | P0 | 训练数据安全的先决条件 |
| 5 | 修复 `train_model.py` 的治理标签检查 (DG-001) | P0 | 防止训练使用不合格数据 |
| 6 | 提取 ELO 算法到共享配置 (DS-002) | P0 | 防止跨栈算法偏离 |
| 7 | 将 data/* 加入 preferred workspace (BM-001) | P0 | 减少 CI 噪音 |
| 8 | 拆分 CI workflow 文件 (WF-001) | P0 | CI 管线韧性 |
| 9 | 在 CI 中添加 Python 测试执行 | P1 | 覆盖 Python 业务逻辑 |
| 10 | 为 DB 写入操作创建集中抽象 | P1 | 消除重复 SQL 模式 |
| 11+ | 归档过期脚本和报告 | P1-P2 | 减少仓库噪音 |

---

## 影响分析

### 影响正式训练的债务
- **DG-001** (训练管线绕过治理) — 阻塞：当前训练数据查询不正确
- **DG-006** (cutoff time 未定义) — 阻塞：泄漏风险未缓解
- **DS-002** (ELO 重复) — 阻塞：特征值可能不一致

### 影响数据扩容的债务
- **DG-002** (`init_db.sql` 落后) — 阻塞：新数据库部署将破损
- **DG-003** (raw_match_data UNIQUE 冲突) — 阻塞：多版本 raw 存储无法在新部署上工作
- **SC-002** (34 个脚本缺少安全闸门) — 阻塞：无安全网无法安全大规模数据收割

### 仅仓库整洁问题的债务
- **RN-001** (`.codex-tmp/` 249 MB) — 磁盘浪费
- **RN-002** (tracked .gitignore 违规) — 微小膨胀
- **RP-004** (PROJECT_STATUS.md 计数过时) — 文档准确性
- **SC-003** (孤儿脚本) — 认知开销

---

## 结论

**是否可以进入 multi_league_multi_season_expansion_plan_dry_run：否（NO）**

扩张规划被 4 个 P0 问题阻塞：无 GitHub 分支保护、训练管线绕过治理标签、`init_db.sql` schema 漂移、特征泄漏策略缺失。

在解决 P0 阻断项（预计 1-2 个冲刺）之前：
- 不要启动多联赛数据收割
- 不要执行正式模型训练
- 不要扩大 raw_match_data 采集
- 不要创建新的数据管线阶段

建议下一步：
1. 执行此报告中列出的 P0 修复（SC-002, BM-002, DG-002, DG-006, DG-001, DS-002 优先）
2. 修复后重新运行此审计脚本以确认 P0 计数降至 0
3. 建立 `docs/DEBT_REGISTER.md` 来跟踪持续的技术债务
4. 然后在数据扩张规划前获得明确用户授权

---

## 附录：审计方法

- 纯静态扫描：读取文件、计算行数、模式匹配、git 命令
- 无网络请求、无数据库写入、无文件修改
- 所有发现均来自文件内容和 git 历史的证据
- 脚本可重复运行并产生确定性的发现集

## 报告元数据

- **脚本生命周期:** permanent
- **报告生命周期:** current-state（在下一次审计运行前保持权威）
- **审计工具:** `scripts/ops/technical_debt_workflow_audit_dry_run.js`（permanent）
- **测试覆盖:** `tests/unit/technical_debt_workflow_audit_dry_run.test.js`（42 个测试，全部通过）
