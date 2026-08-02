# Capability Index — 能力索引

> lifecycle: permanent
>
> 本文档是可扫描的 current-state 能力索引，不是"唯一权威"；每行尽量短，
> 权威细节指向 README canonical 表、代码合同与 current-state 文档。
> 首次建立：2026-08-01（PROJECT_KNOWLEDGE_ENTRY_AND_DOCUMENTATION_SAFETY 任务）。

## 状态词（固定词汇）

| 状态 | 含义 |
|---|---|
| CANONICAL | 正式入口存在，新工作默认使用 |
| SUPPORTED_COMPATIBILITY | 保留兼容路径，不是默认入口 |
| LEGACY | 历史遗留，不得成为新依赖 |
| BLOCKED | 入口存在或计划中，但当前未授权 / 被禁止执行 |
| NOT_ESTABLISHED | 尚未建立（设计评审完成或未开始，均未实现） |
| DOCUMENTED_ONLY | 无正式受控 canonical 入口；可能已实现并有历史执行证据（行内说明给出实现与入口），也可能仅为文档 / 审计描述 |

状态可用斜杠组合（如 CANONICAL/BLOCKED）：入口已定义但执行未授权。

## 如何使用本索引

1. 按 Domain 找到目标能力行。
2. 看 Status：CANONICAL 可复用；LEGACY 不得作为新依赖；
   BLOCKED / NOT_ESTABLISHED 不得自行实现，先确认授权。
3. 看 Canonical entrypoint / Core implementation：用入口，不要绕行。
4. 看 Authorization & side effects：执行前确认是否已获授权。
5. 看 Legacy or forbidden alternatives：避免重复造轮子或依赖历史脚本。
6. 每行状态与授权可能变化；以 README canonical 表和 current-state 文档为准。

## Domain: 历史赔率（M3 odds staging / import foundation）

| Domain | Capability | Status | Canonical entrypoint | Core implementation | Primary tests | Authorization & side effects | Legacy or forbidden alternatives | Current notes |
|---|---|---|---|---|---|---|---|---|
| Odds | 离线 source inventory | DOCUMENTED_ONLY | `npm run odds:staging:dry-run`（internal 执行：node `scripts/ops/odds_staging_dry_run.js`；未登记 README canonical 表、无 make `data-*` wrapper） | `src/infrastructure/odds_staging/sourceManifest.js` | tests/unit/odds_staging_pipeline.test.js | no-write 默认；读本地 CSV + manifest | 历史 CSV 直接入库脚本 | 离线 source inventory 已合并（M3 里程碑，Issue #1793）；入口未登记正式 canonical 表面 |
| Odds | 离线 staging pipeline | DOCUMENTED_ONLY | `npm run odds:staging:dry-run`（internal 执行，同上） | `src/infrastructure/odds_staging/pipeline.js` | tests/unit/odds_staging_pipeline.test.js、tests/unit/odds_staging_cli.test.js、tests/integration/odds_staging/ | no-write 默认（dry-run）；写文件需显式授权 | — | football-data-csv@1.2.0 + E0/Premier League + three-season + exact-alias + Europe/London 合同（docs/M3_D4F_READINESS_REVIEW.md）；入口未登记正式 canonical 表面 |
| Odds | dry-run importer | DOCUMENTED_ONLY | `npm run odds:staging:dry-run`（internal 执行，同上） | 同上（CLI 默认 dry-run） | tests/unit/odds_staging_cli.test.js | 不写 DB、不写文件 | — | 唯一离线导入入口，默认 fail-closed/no-write；入口未登记正式 canonical 表面 |
| Odds | semantic identity | DOCUMENTED_ONLY | pipeline 内（经 odds:staging:dry-run 执行，无独立入口） | `src/infrastructure/odds_staging/footballDataIdentity.js` | tests/unit/odds_staging_match_identity.test.js | 纯计算 | — | 实现与测试存在（M3 交付），随未登记入口执行 |
| Odds | match linking | DOCUMENTED_ONLY | pipeline 内（同上） | `src/infrastructure/odds_staging/matchLinker.js` | 见 odds_staging 测试族 | 只读比对 | 人工 / 历史模糊匹配脚本 | 888 exact / 4 kickoff conflicts / 248 canonical-only / 252 无 exact link（docs/data/FOTMOB_CURRENT_STATE.md） |
| Odds | idempotency | DOCUMENTED_ONLY | pipeline 内（同上） | `src/infrastructure/odds_staging/deduplication.js` | tests/unit/odds_staging_historical.test.js | 只读 | — | D4E 稳定重放 0 accepted / 0 quarantine / 9 duplicates 零表差（docs/PROJECT_STATUS.md） |
| Odds | duplicate policy | DOCUMENTED_ONLY | pipeline 内（同上） | `src/infrastructure/odds_staging/deduplication.js` | tests/unit/odds_staging_historical.test.js | 只读 | — | 重复向量检测与 quarantine 决策 |
| Odds | quarantine 分类 | DOCUMENTED_ONLY | pipeline 内（同上） | `src/infrastructure/odds_staging/persistenceRepository.js` / `persistenceContracts.js` | tests/unit/odds_staging_persistence_contract.test.js | 只读；写库仅限授权 sandbox | — | D4B 冻结合同：38,616 accepted / 216 quarantined（docs/PROJECT_STATUS.md） |
| Odds | kickoff conflict 处理 | DOCUMENTED_ONLY | pipeline 内（同上） | `matchLinker.js` + `deduplication.js` | 见 odds_staging 测试族 | 只读 | — | 4 个冲突（3×15min + 1×30min），linkage-quarantine 分离（docs/data/FOTMOB_CURRENT_STATE.md、docs/M3_D4F_READINESS_REVIEW.md） |
| Odds | snapshot_type 合同 / 显式 opening-current-closing 映射 | DOCUMENTED_ONLY | pipeline 内（同上） | `src/infrastructure/odds_staging/contracts.js` + `adapters.js` | tests/unit/odds_staging_pipeline.test.js、tests/unit/odds_staging_historical.test.js | 纯计算 | — | `ALLOWED_SNAPSHOT_TYPES = opening / current / closing / unknown`；只有来源显式提供 opening/current/closing 字段时才使用对应类型，否则保持 unknown |
| Odds | 普通列 / C 列推断 opening-closing | BLOCKED | 无 | 无（禁止实现） | tests/unit/odds_staging_historical.test.js（断言保持 unknown） | 禁止推断 | 按行序、列顺序或普通/C 列命名推断的旧思路 | 来源没有时间证据必须保持 unknown；禁止把普通列解释为 opening、把 C 列解释为 closing（contracts.js、adapters.js 注释与测试） |
| Odds | staging schema | DOCUMENTED_ONLY | 无（唯一应用路径 = `make m3-odds-sandbox-migrate`，固定 M3-D4D-B1 sandbox 范围，需 `ALLOW_M3_PERSISTENT_SANDBOX_MIGRATION=1` + 精确授权短语） | `database/migrations/V26.8__create_odds_historical_staging_contract.sql`、`V26.9__add_odds_historical_observation_fingerprint.sql` | tests/integration/odds_staging/ephemeral_postgres.test.js 等 | 需双授权 + 单独授权；M3 迁移仅在授权 sandbox / disposable tmpfs 库应用过 | 直接执行 migration apply（禁止）；`make data-schema-*` 不覆盖 V26.8/V26.9（`data-schema-plan` 仅列到 V26.4，`data-schema-migrate` 未接通执行） | M3 合同迁移（docs/PROJECT_STATUS.md、docs/M3_ODDS_STAGING_PERSISTENT_SANDBOX_RUNBOOK.md） |
| Odds | controlled synthetic write（D4E） | DOCUMENTED_ONLY | 无（历史执行证据：`make m3-odds-sandbox-d4e-preflight/-write/-replay/-conflict-probe/-quarantine-conflict-probe`，需 `ALLOW_M3_D4E_PERSISTENT_SANDBOX_WRITE=1` + 精确授权短语） | `src/infrastructure/odds_staging/persistenceRepository.js` | tests/unit/odds_staging_d4e_controlled_write.test.js | 只接受确定性 synthetic 输入；持久 sandbox（M3-D4D-B1）范围；未经新授权不得执行 | 不得指向 `data-schema-m3-canonical-inventory-disposable-*`（那是 canonical inventory proof：迁移 V26.10 + CanonicalInventoryWriter，不运行 D4E 的 V26.8/V26.9 赔率 staging 写入） | D4E = 1 run / 1 source / 6 accepted / 3 quarantine，已结案（docs/PROJECT_STATUS.md、docs/M3_ODDS_STAGING_PERSISTENT_SANDBOX_RUNBOOK.md） |
| Odds | production import schema | NOT_ESTABLISHED | 无 | 无（historical odds → production 表的 import 集成未实现） | — | 无 | 历史 import 脚本 | 与 canonical inventory writer 分开：writer/V26.10 合同/disposable proof 已存在（PR #1811），本行仅指 historical odds staging → production bookmaker odds / matches 表的正式 import 集成、授权表面与执行流程，仍 NOT_ESTABLISHED；真实持久化/生产写入仍 BLOCKED（docs/PROJECT_STATUS.md） |
| Odds | 真实历史赔率 import | BLOCKED | 无 | 无 | — | 未授权、未执行 | — | 三份 Git 审计输入已离线读取（docs/M3_D4F_READINESS_REVIEW.md L549-551 / L631-634）：`raw_odds_2223.csv`（380 行 / 13,680 obs）、`raw_odds_2324.csv`（380 行 / 12,546 obs）、`real_odds_raw.csv`（420 行 / 12,606 obs），合计 1,180 行 / 38,832 obs；D4B 的 38,616 accepted / 216 quarantined 是历史合同证据，不是 D4F 审计人口。从未正式 import 或写入任何数据库 / 生产；真实导入需后续单独授权，勿只恢复单份文件却按总量规划 |

## Domain: FotMob

| Domain | Capability | Status | Canonical entrypoint | Core implementation | Primary tests | Authorization & side effects | Legacy or forbidden alternatives | Current notes |
|---|---|---|---|---|---|---|---|---|
| FotMob | candidate exporter | CANONICAL/BLOCKED | 仅 `make data-fotmob-candidates-network-export`（需 NETWORK_AUTHORIZATION=yes） | `scripts/ops/fotmob_candidates_export.js` → `src/infrastructure/fotmob/FotMobCandidateExporter.js` | tests/unit/fotmob_candidate_exporter.test.js | 每次实际执行都会访问 FotMob 网络（CLI 对非 --help 调用强制 `--network-preview=true` + `--network-authorization=yes`，普通直接调用被 CLI 阻止）；`OUTPUT=<dir>` 经 Makefile 转发为 `--output`，写入候选 artifact（identity-v1：`candidate-match-identity.v1.json` + `.summary.json`，要求仓库外已存在的绝对目录）——文件写盘与网络授权相互独立、需另行授权（ACTIVE_MILESTONE 停止边界禁止 artifact 写盘）；`--retain-raw-responses` 落盘是另一项可选行为；不写数据库；当前未获得真实网络执行授权 | `n3_live_fotmob_raw_retain.js`、`pageprops_v2_*`、`adg60_*`、`titan_discovery.js` 及其它 Phase/ADG 历史采集脚本 | 唯一正式路径；不存在"本地无网络导出"模式；PR #1813 后支持 canonical-v2 |
| FotMob | status mapping | CANONICAL | 同上（CLI 内） | `src/infrastructure/fotmob/FotMobStatusContract.js` | tests/unit/fotmob_candidate_exporter.test.js | 纯映射 | 历史脚本各自硬编码状态 | unknown / started fail closed（PR #1813） |
| FotMob | raw retention | DOCUMENTED_ONLY | 无受控入口（`make data-fotmob-candidates-network-export` 默认 identity-v1，不转发 `--output-schema` / `--retain-raw-responses`；canonical-v2 参数仅可经直接 CLI 调用且 `--retain-raw-responses` 为 REQUIRED） | `FotMobCandidateExporter.js` | tests/unit/fotmob_candidate_exporter.test.js | 实现存在（PR #1813）；本地文件写盘；both-or-neither 语义；git revision 绑定；执行仍需网络授权 | `n3_live_fotmob_raw_retain.js`（网络/UPSERT 路径，LEGACY） | 不得保存 / 打印完整 HTML body 到对话（AGENTS.md）；当前无受控执行表面触发该能力 |
| FotMob | capture manifest | DOCUMENTED_ONLY | 无受控入口（依赖 canonical-v2，同 raw retention 行） | `FotMobCandidateExporter.js`（SHA-256 manifest） | tests/unit/fotmob_candidate_exporter.test.js | 实现存在（PR #1813）；本地文件写盘；both-or-neither 语义 | — | raw + manifest 必须同生共灭（PR #1813）；当前无受控执行表面触发该能力 |
| FotMob | identity projection hash | DOCUMENTED_ONLY | 无受控入口（依赖 canonical-v2，同 raw retention 行） | `FotMobCandidateExporter.js` + `CanonicalInventoryContract.js` | tests/unit/fotmob_candidate_exporter.test.js | 实现存在（PR #1813）；纯计算 | — | 稳定 payload hash，不含 volatile fetch metadata（AGENTS.md）；当前无受控执行表面触发该能力 |
| FotMob | business hash | DOCUMENTED_ONLY | 无受控入口（依赖 canonical-v2，同 raw retention 行） | 同上（full business hash） | tests/unit/fotmob_candidate_exporter.test.js、tests/unit/canonical_inventory_contract.test.js | 实现存在（PR #1813）；纯计算 | — | 与 identity projection hash 双哈希并存；当前无受控执行表面触发该能力 |
| FotMob | canonical inventory contract | CANONICAL | `make data-m3-canonical-inventory-preflight ARTIFACT=<path> ARTIFACT_SHA256=<sha256>`（no-write 合同验证，不依赖网络导出） | `src/infrastructure/canonical/CanonicalInventoryContract.js`（`readOrdinaryArtifact()` → `validateArtifactDocument()`，经 `scripts/ops/canonical_inventory_writer.js`） | tests/unit/canonical_inventory_contract.test.js | 校验失败即 fail closed；只验证外部提供的 hash-bound artifact，无网络 / DB 副作用 | — | 与"生成 v2 artifact"（raw retention 等，仍无受控入口）分开：验证 v2 artifact 有受控 preflight（PR #1813 / README canonical 表） |
| FotMob | canonical writer proof | CANONICAL（proof 范围） | `make data-m3-canonical-inventory-preflight` / `make data-m3-canonical-inventory-disposable-proof` | `src/infrastructure/canonical/CanonicalInventoryWriter.js` | tests/unit/canonical_inventory_writer.test.js、canonical_inventory_authorization.test.js、canonical_inventory_operator.test.js | preflight 只读；disposable proof 仅确定性 synthetic 输入 + 专用 tmpfs 库 | — | persistent canonical write 仍 blocked（README canonical 表） |
| FotMob | v1 compatibility | SUPPORTED_COMPATIBILITY | `make data-fotmob-candidates-network-export` 默认输出（identity-v1，输出路径不变） | `FotMobCandidateExporter.js` | tests/unit/fotmob_candidate_exporter.test.js | 受控入口默认行为；执行仍需网络授权 | — | P3-3 v1 paired-write 弱点未修复、不属于阶段A（PR #1813 Debt Impact） |
| FotMob | production acquisition | NOT_ESTABLISHED | 无 | 无 | — | 无 | 上述 legacy 采集脚本 | README canonical 表：Not yet established for production acquisition |
| FotMob | real capture | BLOCKED | 无 | 无 | — | 未授权；FOTMOB_REAL_CAPTURE_READINESS 为 planning milestone（Issue #1793 / PR #1813） | — | 网络 probe、三赛季采集、条款审查、单页面 shape probe 均未授权（详见 docs/ACTIVE_MILESTONE.md） |

## Domain: 数据库与迁移

| Domain | Capability | Status | Canonical entrypoint | Core implementation | Primary tests | Authorization & side effects | Legacy or forbidden alternatives | Current notes |
|---|---|---|---|---|---|---|---|---|
| DB | M3 SQL migration 树（V26.8 / V26.9 / V26.10） | DOCUMENTED_ONLY | V26.10：`make data-schema-m3-canonical-inventory-disposable-*`（唯一接通路径）；V26.8 / V26.9：无（仅 `make m3-odds-sandbox-migrate` sandbox 路径，双授权） | `database/migrations/V*.sql`（V26.8 / V26.9 / V26.10 为 M3 合同） | tests/integration/canonical_inventory/disposable_postgres.test.js 等 | 执行迁移需门禁 + 单独授权；M3 迁移仅在 disposable tmpfs 库 / 授权 sandbox 应用过 | 直接 psql 执行 migration apply（禁止）；`make data-schema-plan` 止于 V26.4、`data-schema-migrate` 未接通（不覆盖 V26.8 / V26.9） | AGENTS.md §2.1 规则 10；两套树职责划分仍 UNCLEAR（见 docs/PROJECT_MAP.md） |
| DB | Alembic migration 树 | DOCUMENTED_ONLY | 无（无文档化 canonical 入口） | `src/database/migrations/`（alembic.ini / env.py / versions/ 3 个版本） | — | 未授权不得执行 | 直接执行 alembic 命令（禁止） | **UNCLEAR — 两套 migration 树职责未文档化**（见 docs/PROJECT_MAP.md）；目录存在不等于 canonical，在职责和门禁查清前，新 migration 不得选择该树 |
| DB | DB write guard | CANONICAL | 仅覆盖显式 import 并调用该 helper 的 scripts/ops JS 脚本（精确枚举：`grep -rlE "require\([^)]*db_write_guard|import[^;]*db_write_guard" scripts/ops --include="*.js" | grep -vE "helpers/db_write_guard\.js$|db_write_guard_static_enforcement_dry_run\.js$"`（排除已内嵌于命令，当前 53 个）；CI 侧由 AI Workflow Gate 的 db_write_guard enforcement check——`scripts/ops/helpers/db_write_guard_advisory_check.py` / `scripts/ops/db_write_guard_static_enforcement_dry_run.js`——对扫描器判定为直接写入风险且未被跳过的 new/modified 脚本强制接入；`read_only_or_false_positive`（无写风险关键字）与 `skipped_complex`（Phase1 跳过 / allowlist / browser 自动化）分类不报 violation） | `scripts/ops/helpers/db_write_guard.js`（fail-closed；guard 自述仅供 ops scripts 调用，不构成统一 writer 层、不替代脚本自身检查） | 见 guard 相关测试 | 显式调用者未通过 guard 时被阻止（需 `DRY_RUN=false`〔默认 true〕+ `ALLOW_DB_WRITE=yes` + `FINAL_DB_WRITE_CONFIRMATION=yes` + 表级门禁；CREATE / ALTER / DELETE / TRUNCATE / DROP 等高风险操作另需 `ALLOW_SCHEMA_WRITE=yes`） | 未导入该 guard 的写路径不受其约束、各有自身授权机制：`scripts/ops/run_production.js` → `ProductionHarvester.saveData` → `Persistence.dualSave`（INSERT/UPDATE raw_match_data）；src/ 内 CanonicalInventoryWriter、FixtureRepository 等 | 仅覆盖显式调用者，不是全局环境门禁；`grep -l` 类宽松查询会混入治理脚本 / helper 自身 / 扫描器，勿用于枚举；审计任意写路径时须逐路径确认授权（AGENTS.md §5.3） |
| DB | controlled write（sandbox） | DOCUMENTED_ONLY | 无（历史执行证据：`make m3-odds-sandbox-d4e-*` 固定表面） | `src/infrastructure/odds_staging/persistenceRepository.js` | tests/unit/odds_staging_d4e_controlled_write.test.js | 需双授权 + 单独授权；持久 sandbox（M3-D4D-B1）范围；未经新授权不得执行 | — | D4E 已结案，保留证据 1/1/6/3（docs/PROJECT_STATUS.md、docs/M3_ODDS_STAGING_PERSISTENT_SANDBOX_RUNBOOK.md） |
| DB | production DB write | BLOCKED | 无 | 无 | — | 未授权 | — | 任何写库命令默认 blocked（AGENTS.md §5.3） |

## Domain: 数据采集 / 赔率收割 / 特征构建（L1/L2 / odds:harvest / l3:stitch）

| Domain | Capability | Status | Canonical entrypoint | Core implementation | Primary tests | Authorization & side effects | Legacy or forbidden alternatives | Current notes |
|---|---|---|---|---|---|---|---|---|
| Data | L1 发现 / 种子写入（data-l1-*） | CANONICAL/BLOCKED | `make data-l1-*`（`make data-help` 列出；preview → plan → authorization → preflight → execute 多阶段） | Makefile Phase 5.05-5.07L1 目标 | — | preview / plan 阶段 no-write；authorization / execute 阶段需每目标显式授权（如 `USER_AUTHORIZED_MATCHES_SEED_COMMIT=yes` + `FINAL_HUMAN_CONFIRMATION=yes`） | `scripts/ops/titan_discovery.js`（legacy/admin-only，不得作为新依赖，AGENTS.md §6.1） | 未授权不执行（README canonical 表） |
| Data | L2 原始比赛数据（data-l2-*） | CANONICAL/BLOCKED | `make data-l2-*`（`make data-help` 列出；preview → plan → authorization → preflight → write 多阶段） | Makefile L2 目标 | — | ingest / write 阶段需逐目标显式授权（如 ALLOW_DB_WRITE 门禁）+ 最终人工确认 | 历史 raw 直写脚本 | 未授权不执行（README canonical 表） |
| Odds | 赔率收割（odds:harvest） | DOCUMENTED_ONLY | `npm run odds:harvest`（无 make `data-*` 受控门禁 wrapper；README canonical 表登记为 Primary canonical，但 npm script 直接宿主运行 Node，绕过容器化多阶段门禁） | `scripts/ops/odds_harvest_pipeline.js` | — | 默认 l3Enabled=true：收割后触发 `l3_stitch_pipeline.js`（L3_STITCH_FULL_RECALCULATE=true），其运行 `scripts/maintenance/recalculate_elo.js`，写 matches / l3_features / team_elo_ratings（默认跨域写入链）；赔率-only 需 `--skip-l3`；可能访问网络并写 DB；执行前确认授权 / 环境 / 凭据（README L198） | `npm run odds:sniper` 为 Specialized/Internal 替代 | 已实现（脚本存在）但无受控入口；README 登记 Primary canonical 与本索引 DOCUMENTED_ONLY 的差异即有无 make `data-*` 门禁；未授权不执行 |
| Data | L3 特征构建 | DOCUMENTED_ONLY | `npm run l3:stitch`（无 make `data-*` 受控门禁 wrapper；README canonical 表登记为 Primary canonical，但 npm script 直接宿主运行 Node，绕过容器化多阶段门禁；`make data-l3-*` 是另一套 fixture/local pipeline） | `scripts/ops/l3_stitch_pipeline.js` | — | 执行前确认输入数据与写入范围；可能触发 `scripts/maintenance/recalculate_elo.js`（写 l3_features / team_elo_ratings）（README L201） | `npm run smelt` 为 Specialized/Internal 替代 | 已实现（脚本存在）但无受控入口；未授权不执行 |

## Domain: 训练 / 预测 / 回测

| Domain | Capability | Status | Canonical entrypoint | Core implementation | Primary tests | Authorization & side effects | Legacy or forbidden alternatives | Current notes |
|---|---|---|---|---|---|---|---|---|
| ML | training | CANONICAL/BLOCKED | `npm run train`（train:fast / train:deep 变体） | `src/ml/` | ML 测试 | 写模型 artifact；仅显式训练授权后可执行 | 任何未经授权的训练脚本 | 当前无训练授权 |
| ML | prediction | CANONICAL/BLOCKED | `npm run predict`（predict:dry / predict:json 变体） | `scripts/ops/predict_pipeline.py`（→ `src.ml.inference.titan_loader.get_titan_model` + `src/database/repositories/prediction_repo`） | ML 测试 | 读 DB；`scripts/ops/predict_pipeline.py` 模块加载即创建 `/app/logs` 并追加写 `/app/logs/predict_pipeline.log`（dev Compose 将仓库挂载到 `/app`，即使 predict:dry 也会写宿主工作区 `logs/`）；需确认环境 / 模型 / 授权 | — | 未授权不执行 |
| ML | backtest | NOT_ESTABLISHED | 无 | 无 | — | 无 | `recon_scanner.js`、`gold_pilot_50.js`、`titan_marathon.js` 不是 canonical 回测入口 | 需未来业务里程碑实现并验收（README canonical 表） |

## 本索引不回答什么

- 不回答具体命令的完整用法 —— 看 README canonical 表与各 CLI 的 `--help`。
- 不回答授权当前是否存在 —— 授权逐项确认；任何文档记录都不等于动态验证。
- 不回答里程碑进度 —— 看 docs/ACTIVE_MILESTONE.md。
- 不代替代码与数据合同 —— 合同以 `database/migrations/V*.sql` 与 contract 模块为准。
- 不把"存在 Makefile target"当作"已接通能力" —— 以 README canonical 表与 current-state 文档为准。

## 维护触发条件

- README canonical 表增删入口时同步本索引。
- 任何状态变化（NOT_ESTABLISHED → CANONICAL、BLOCKED 解除、新能力落地）时更新对应行。
- 新增能力前先查本索引；发现缺失即补行，同时声明新组件的生命周期（AGENTS.md §2.5）。
