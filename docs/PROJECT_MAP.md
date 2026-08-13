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
- schema authority、两套 migration 树、config 多目录、scripts/ops 与 docs/_reports 的已知边界与风险。

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
- 数据链路：L1 Discovery → L2 Harvest → L3 Smelt → Predict（见 README 数据流向图）。
- 详细架构见 docs/ARCHITECTURE.md；本文件不复制大段架构内容。

## 主要目录职责

| 目录 | 职责 | 说明 |
|---|---|---|
| `scripts/ops/` | 生产与运维脚本入口；canonical CLI（`fotmob_candidates_export.js`、`canonical_inventory_writer.js` 等；`odds_staging_dry_run.js` 为 internal 执行入口，未登记 README canonical 表，见 docs/CAPABILITY_INDEX.md） | 同时保留大量历史 / legacy 脚本（见下）；`scripts/ops/helpers/` 承载 DB write guard 与治理检查；`scripts/ops/odds_staging/` 含 M3-R1/M3-R2 离线确定性重建入口 `historical_odds_rebuild.js` + 同级 canonical 模块 `historical_odds_rebuild_canonical.js`（`npm run odds:staging:rebuild`，同 dry-run 分类，未登记 README canonical 表，见 docs/CAPABILITY_INDEX.md） |
| `src/infrastructure/` | 抓取、网络、侦察、监控基础设施 | 含 M3 模块：`odds_staging/`（13 个模块，含 M3-R2 provider 合同 `footballDataProviderContract.js`）、`canonical/`（Authorization/Contract/Writer）、`fotmob/`（CandidateExporter/StatusContract） |
| `src/ml/` | 训练、特征、推理 | 训练 / 预测需显式授权；`value_mvp/`（离线概率基准 VALUE_MVP-1，lifecycle: permanent，纯离线只读，见 docs/PROJECT_STATUS.md VALUE_MVP-1 节） |
| `src/feature_engine/` | Node 侧特征工程 | |
| `src/config/` | Python 侧配置 | 与 `config/`、`src/config_unified/` 多目录并存（见 config 风险提示） |
| `config/` | 业务配置 | AGENTS.md §6.2 列出的优先配置源 |
| `database/migrations/` | 唯一 forward schema-definition authority（16 个 V*.sql） | 新 schema 变更只进入这里的 reviewed `V*.sql`；执行仍需既有 SC-002 / `make data-schema-*` 门禁与单独授权，不由应用启动自动执行 |
| `src/database/migrations/` | Alembic 历史树（alembic.ini / env.py / versions/ 3 个版本） | `LEGACY`（future revisions frozen）：保留历史兼容与静态检查，不接收未来 schema revision，不是当前 schema authority |
| `src/database/schema_manager.py` | 历史 Python schema helper | `LEGACY_NON_CANONICAL_RUNTIME_DDL`；`initialize_schema()` / `initialize_production_schema()` 已停用；读取/检查方法保留 |
| `deploy/docker/init_db.sql` | 本地 Docker 空卷 bootstrap | `DEV_BOOTSTRAP_NON_AUTHORITATIVE`；仅 `docker-compose.dev.yml` 的开发 DB bootstrap，不是 staging/production migration authority |
| `tests/` | 单元、集成、夹具 | 含 `tests/unit/odds_staging_*`、`tests/unit/canonical_inventory_*`、`tests/integration/odds_staging/` 等 |
| `docs/` | 架构与运维文档 | `docs/_reports`、`docs/_manifests` 为历史治理资产，新任务默认不得创建 |

## 正式 / 兼容 / 历史代码分布

- **CANONICAL（正式入口指向的实现）**：`src/infrastructure/canonical/`
  （CanonicalInventoryContract.js 等）、`src/infrastructure/fotmob/FotMobCandidateExporter.js`、
  `src/infrastructure/fotmob/FotMobStatusContract.js`。
- **已实现但入口未登记（DOCUMENTED_ONLY，见 docs/CAPABILITY_INDEX.md）**：
  `src/infrastructure/odds_staging/`（13 个模块，含 M3-R2 机器可读官方 provider 合同
  `footballDataProviderContract.js`；随 internal 入口 `npm run odds:staging:dry-run` 执行；
  M3-R1 起也可经 `npm run odds:staging:rebuild` 一次确定性重建，见 `scripts/ops/odds_staging/historical_odds_rebuild.js`）；
  `src/ml/value_mvp/` + `scripts/model_training/value_mvp_baseline_vs_closing.py`
  （VALUE_MVP-1 offline probability benchmark，internal research evaluation 入口，
  未登记 README canonical 表，见 docs/PROJECT_STATUS.md VALUE_MVP-1 节）。
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

## DB schema authority 与两套 migration 目录

机器可读的唯一契约是 `config/db_schema_authority.json`。新工程师对“下一项
schema change 放在哪里？”的唯一答案是：

> 在 `database/migrations/` 新增一个 reviewed、版本化的 `V*.sql` migration。

- `database/migrations/` 是唯一 forward schema-definition authority。它包含 V6.x、
  V12.x、V26.x 历史与现代合同；V26.8 / V26.9 的 odds staging 与 V26.10 的 M3
  canonical inventory 仍按各自现有受控 surface 执行，不能从 authority 位置推导执行授权。
- `src/database/migrations/` 的 Alembic head 是 `003_v145`，只有 3 个历史 revision，
  未覆盖 V26.4–V26.10 当前合同，因此生命周期为 `LEGACY` 且冻结 future revisions；不得新增未来 revision，
  不得由默认启动调用 `alembic upgrade`。
- `SchemaManager` 的 mutation entrypoints 是 `LEGACY_NON_CANONICAL_RUNTIME_DDL` 并已 fail-fast；
  只读/introspection 方法保留，`align_external_ids` 与 `bulk_insert_features` 是
  `LEGACY_NON_CANONICAL_RUNTIME_DML` 兼容方法，不是 schema authority。
- L3 主 pipeline 不再执行 schema DDL；其调用的
  `scripts/maintenance/recalculate_elo.js` 仍是 `SPECIALIZED_INTERNAL_RUNTIME_DDL` legacy
  子入口，仅作 Elo 数据维护，未来 schema change 不得写入其中，执行仍需单独授权。
- `deploy/docker/init_db.sql` 是 `DEV_BOOTSTRAP_NON_AUTHORITATIVE`，仅由
  `docker-compose.dev.yml` 的开发 DB 空卷 bootstrap 使用；unified/production-like Compose
  不再挂载它。它的表定义与 migration tree 的历史漂移是 carry-forward，不在 A4 修复。
- 应用启动不自动执行 migration；migration 的 canonical location 与 migration execution
  authorization 始终是两件事。现有 SC-002 allowlist、Python DB write guard、Alembic runtime
  guard 保持不变。

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
- 现存历史资产不得替代 runtime 实现（AGENTS.md §2.4）。

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
- `config/db_schema_authority.json` 的 authority、lifecycle 或 startup policy 发生变化时，
  同步更新 README、CAPABILITY_INDEX 与本节。
- 新 Agent 反馈按本文档找不到能力时，立即修正。
