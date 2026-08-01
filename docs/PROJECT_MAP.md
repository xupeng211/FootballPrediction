# Project Map — 仓库结构与知识入口

> lifecycle: permanent
>
> 本文档是 current-state 索引，不是"唯一权威"；它指向权威文档而不是替代它们。
> 首次建立：2026-08-01（PROJECT_KNOWLEDGE_ENTRY_AND_DOCUMENTATION_SAFETY 任务）。

## 本文档回答什么 / 不回答什么

回答：

- 仓库有哪些主要目录，各自职责是什么。
- 新 Agent / 新成员应该按什么顺序阅读文档、在哪里找能力。
- 正式、兼容、历史遗留代码大致分布在哪里。
- 两套 migration 树、config 多目录、scripts/ops 与 docs/_reports 的已知边界与风险。

不回答：

- 不回答具体命令的授权状态 —— 见 README "Canonical Business Entrypoints" 表。
- 不逐条罗列能力 —— 见 docs/CAPABILITY_INDEX.md。
- 不回答当前里程碑进度 —— 见 docs/ACTIVE_MILESTONE.md。
- 不回答 FotMob 摄取当前状态 —— 见 docs/data/FOTMOB_CURRENT_STATE.md。
- 不替代代码本身、数据合同（V*.sql / contract 模块）或任何 current-state 文档。

## 当前可信阅读顺序

按 CLAUDE.md 定义，新 Agent 从以下顺序开始：

1. `AGENTS.md` —— 仓库级安全与工作流规则的权威。
2. README "Canonical Business Entrypoints" —— 业务命令正式入口的权威。
3. `docs/AGENT_WORKFLOW.md` 与 `docs/engineering/AI_AGENT_WORKFLOW.md` —— 详细工作流。
4. `docs/AI_AGENT_WORKFLOW_HARDENING.md` —— CI 监控、分支安全、完成证据规则。
5. `docs/data/FOTMOB_CURRENT_STATE.md` —— FotMob 摄取最新状态。
6. 本文档（`docs/PROJECT_MAP.md`）—— 仓库结构与找能力路径。
7. `docs/CAPABILITY_INDEX.md` —— 可扫描能力表。
8. `docs/ACTIVE_MILESTONE.md` —— 当前里程碑与授权边界。

注意：canonical 表定义"正式入口"，但 **canonical ≠ 已获得执行授权**。
网络、DB 写入、migration、artifact、训练与生产操作仍需逐项明确授权
（AGENTS.md §2.4、CLAUDE.md）。

## 技术栈摘要

- 双语言仓库：Node.js（收割 / 编排 / 基础设施）+ Python（ML 训练 / 推理 / 特征）。
- PostgreSQL 15+（开发 / 生产数据库）、Redis（缓存）、Docker Compose（dev 容器）。
- 数据链路：L1 Discovery → L2 Harvest → L3 Smelt → ELO → Predict（见 README 数据流向图）。
- 详细架构见 docs/ARCHITECTURE.md；本文件不复制大段架构内容。

## 主要目录职责

| 目录 | 职责 | 说明 |
|---|---|---|
| `scripts/ops/` | 生产与运维脚本入口；canonical CLI（`fotmob_candidates_export.js`、`odds_staging_dry_run.js`、`canonical_inventory_writer.js` 等） | 同时保留大量历史 / legacy 脚本（见下）；`scripts/ops/helpers/` 承载 DB write guard 与治理检查 |
| `src/infrastructure/` | 抓取、网络、侦察、监控基础设施 | 含 M3 模块：`odds_staging/`（12 个模块）、`canonical/`（Authorization/Contract/Writer）、`fotmob/`（CandidateExporter/StatusContract） |
| `src/ml/` | 训练、特征、推理 | 训练 / 预测需显式授权 |
| `src/feature_engine/` | Node 侧特征工程 | |
| `src/config/` | Python 侧配置 | 与 `config/`、`src/config_unified/` 多目录并存（见 config 风险提示） |
| `config/` | 业务配置 | AGENTS.md §6.2 列出的优先配置源 |
| `database/migrations/` | M3 正式 SQL migration 树（16 个 V*.sql） | V26.8 / V26.9 / V26.10 为 M3 合同；执行必须走 `make data-schema-*` 门禁 |
| `src/database/migrations/` | Alembic migration 树（alembic.ini / env.py / versions/ 3 个版本） | 职责划分 UNCLEAR（见下） |
| `tests/` | 单元、集成、夹具 | 含 `tests/unit/odds_staging_*`、`tests/unit/canonical_inventory_*`、`tests/integration/odds_staging/` 等 |
| `docs/` | 架构与运维文档 | `docs/_reports`、`docs/_manifests` 为历史治理资产，新任务默认不得创建 |

## 正式 / 兼容 / 历史代码分布

- **CANONICAL（正式入口指向的实现）**：`src/infrastructure/odds_staging/`、
  `src/infrastructure/canonical/`（CanonicalInventoryContract.js 等）、
  `src/infrastructure/fotmob/FotMobCandidateExporter.js`、
  `src/infrastructure/fotmob/FotMobStatusContract.js`。
- **SUPPORTED_COMPATIBILITY（保留兼容路径，非默认入口）**：v1 identity 输出路径
  （`--output-schema=identity-v1`，与 canonical-v2 并存，PR #1813 保留）。
- **LEGACY / admin-only（保留但不得成为新代码依赖）**：`scripts/ops/titan_discovery.js`、
  `run_production.js`、`total_war_pipeline.js`、`batch_historical_backfill.js`、
  `n3_live_fotmob_raw_retain.js`、`pageprops_v2_*`（historical acquisition scripts，
  不属于 M3 FotMob 路径）、Phase/ADG 编号脚本整体类别
  （AGENTS.md §5.1、README "Entry classification"）。

## 新 Agent 找能力推荐顺序

1. 读本文档 + `docs/CAPABILITY_INDEX.md`，确认目标能力是否已存在。
2. 在 CAPABILITY_INDEX 中按 Domain 找对应行：状态词、canonical 入口、核心实现、
   测试、legacy 替代。
3. 读状态为 current-state 的对应文档（FotMob → `docs/data/FOTMOB_CURRENT_STATE.md`；
   M3 总体 → `docs/PROJECT_STATUS.md`）。
4. 若能力已存在且状态为 CANONICAL：复用，不重复创建（AGENTS.md §2.1 防重复开发规则）。
5. 若状态为 BLOCKED / NOT_ESTABLISHED：不自行实现，先向 Issue / 用户确认授权范围。

## 两套 migration 目录的已知边界

- `database/migrations/`：16 个 V*.sql（V6.x / V26.x）。V26.8（odds historical staging
  contract）、V26.9（observation fingerprint）、V26.10（M3 canonical inventory contract）
  为 M3 合同。执行必须走 `make data-schema-*` 门禁；M3 相关迁移仅在 disposable
  PostgreSQL 15 tmpfs 容器中执行过（docs/PROJECT_STATUS.md）。
- `src/database/migrations/`：Alembic 树（alembic.ini / env.py / versions/，3 个版本）。
- **UNCLEAR — requires dedicated documentation**：两套树的职责划分（谁负责哪个 schema、
  何时用 SQL 树、何时用 Alembic 树）在仓库文档中无明确说明。本文档不自行断言划分依据。

## config 多目录风险提示

`config/`、`src/config/`、`src/config_unified/` 多目录并存（历史上还存在更多变体，
与仓库历史清理计划相关）。多目录并存可能导致同一参数多处定义。修改配置前先搜索
所有目录中的同名符号，不要只按一个目录的现状下结论。AGENTS.md §6.2 列出优先查看的
配置源清单。

## scripts/ops 与 docs/_reports 历史资产提示

- `scripts/ops/` 同时承载 canonical CLI 与大量历史 / legacy 脚本。执行前先确认目标脚本
  是否在 README canonical 表 / CAPABILITY_INDEX 中注册；未注册的脚本不得当作正式入口。
- `docs/_reports`、`docs/_manifests` 属于历史治理资产分类：新任务默认不得创建，
  只有 Issue 明确授权且通过 M2 增长冻结门禁才允许最小必要记录（AGENTS.md §2.4）。
- 现存历史资产不得替代 runtime 实现（AGENTS.md §2.3）。

## canonical ≠ 授权

README canonical 表只定义"正式入口"，不授予执行权。所有含副作用的命令
（网络、DB 写入、migration、artifact 写盘、训练、预测、生产操作）仍需逐项明确授权。
授权现状见 `docs/CAPABILITY_INDEX.md` 的 Authorization 列与 `docs/ACTIVE_MILESTONE.md`。

## 本文档不替代什么

- 不替代 README canonical 表（业务命令入口的权威）。
- 不替代 AGENTS.md / CLAUDE.md（安全与工作流规则的权威）。
- 不替代代码、数据合同（V*.sql、contract 模块）与 current-state 文档
  （`docs/data/FOTMOB_CURRENT_STATE.md`、`docs/PROJECT_STATUS.md`）。
- 不替代 docs/DOCUMENTATION_GOVERNANCE.md 的 Source of Truth 注册表。

## 文档维护触发条件

- 目录结构发生结构性变化（新增 / 移除顶层业务目录、migration 树职责明确化）。
- README canonical 表入口集合变化时，同步检查本文档目录职责表。
- 两套 migration 树职责得到官方说明（届时把 UNCLEAR 替换为结论并更新 CAPABILITY_INDEX）。
- 新 Agent 反馈按本文档找不到能力时，立即修正。
