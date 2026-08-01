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
| DOCUMENTED_ONLY | 仅有文档描述 / 审计结论，无实现或未验证 |

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
| Odds | 离线 source inventory | CANONICAL | `npm run odds:staging:dry-run` | `src/infrastructure/odds_staging/sourceManifest.js` | tests/unit/odds_staging_pipeline.test.js | no-write 默认；读本地 CSV + manifest | 历史 CSV 直接入库脚本 | M3-D4A 已合并（Issue #1793） |
| Odds | 离线 staging pipeline | CANONICAL | `npm run odds:staging:dry-run` | `src/infrastructure/odds_staging/pipeline.js` | tests/unit/odds_staging_pipeline.test.js、tests/unit/odds_staging_cli.test.js、tests/integration/odds_staging/ | no-write 默认（dry-run）；写文件需显式授权 | — | football-data-csv@1.2.0 + E0/Premier League + three-season + exact-alias + Europe/London 合同（docs/M3_D4F_READINESS_REVIEW.md） |
| Odds | dry-run importer | CANONICAL | `npm run odds:staging:dry-run` | 同上（CLI 默认 dry-run） | tests/unit/odds_staging_cli.test.js | 不写 DB、不写文件 | — | 唯一离线导入入口，默认 fail-closed/no-write |
| Odds | semantic identity | CANONICAL | 同上（pipeline 内） | `src/infrastructure/odds_staging/footballDataIdentity.js` | tests/unit/odds_staging_match_identity.test.js | 纯计算 | — | — |
| Odds | match linking | CANONICAL | 同上 | `src/infrastructure/odds_staging/matchLinker.js` | 见 odds_staging 测试族 | 只读比对 | 人工 / 历史模糊匹配脚本 | 888 exact / 4 kickoff conflicts / 248 canonical-only / 252 无 exact link（docs/data/FOTMOB_CURRENT_STATE.md） |
| Odds | idempotency | CANONICAL | 同上 | `src/infrastructure/odds_staging/deduplication.js` | tests/unit/odds_staging_historical.test.js | 只读 | — | D4E 稳定重放 0 accepted / 0 quarantine / 9 duplicates 零表差（docs/PROJECT_STATUS.md） |
| Odds | duplicate policy | CANONICAL | 同上 | `src/infrastructure/odds_staging/deduplication.js` | tests/unit/odds_staging_historical.test.js | 只读 | — | 重复向量检测与 quarantine 决策 |
| Odds | quarantine 分类 | CANONICAL | 同上 | `src/infrastructure/odds_staging/persistenceRepository.js` / `persistenceContracts.js` | tests/unit/odds_staging_persistence_contract.test.js | 只读；写库仅限授权 sandbox | — | D4B 冻结合同：38,616 accepted / 216 quarantined（docs/PROJECT_STATUS.md） |
| Odds | kickoff conflict 处理 | CANONICAL | 同上（match linking 结果） | `matchLinker.js` + `deduplication.js` | 见 odds_staging 测试族 | 只读 | — | 4 个冲突（3×15min + 1×30min），linkage-quarantine 分离（docs/data/FOTMOB_CURRENT_STATE.md、docs/M3_D4F_READINESS_REVIEW.md） |
| Odds | initial-closing 语义 | DOCUMENTED_ONLY | 无 | 无（policy 未实现） | — | 只读审计结论 | — | adapter 不从 ordinary/C 列或行序推断 opening/closing；显式 closing 策略需单独设计（docs/M3_D4F_READINESS_REVIEW.md） |
| Odds | staging schema | CANONICAL | `make data-schema-*` 门禁 | `database/migrations/V26.8__create_odds_historical_staging_contract.sql`、`V26.9__add_odds_historical_observation_fingerprint.sql` | tests/integration/odds_staging/ephemeral_postgres.test.js 等 | 迁移执行需门禁 + 授权；M3 迁移仅在 disposable tmpfs 库执行过 | 直接执行 migration apply（禁止） | M3 合同迁移（docs/PROJECT_STATUS.md） |
| Odds | controlled synthetic write（D4E） | CANONICAL（sandbox 范围） | `make data-schema-m3-canonical-inventory-disposable-*`（preview/authorize/preflight/execute 链） | `src/infrastructure/odds_staging/persistenceRepository.js` | tests/unit/odds_staging_d4e_controlled_write.test.js | 只接受确定性 synthetic 输入；专用 disposable 数据库；需单独 schema/proof 授权 | — | D4E = 1 run / 1 source / 6 accepted / 3 quarantine；无真实历史赔率读写（docs/PROJECT_STATUS.md） |
| Odds | production import schema | NOT_ESTABLISHED | 无 | 无（writer 未实现） | — | 无 | 历史 import 脚本 | 设计评审完成（PR #1810）；fail-closed writer 与隔离 schema/lineage 迁移计划均未实现（docs/PROJECT_STATUS.md） |
| Odds | 真实历史赔率 import | BLOCKED | 无 | 无 | — | 未授权、未执行 | — | 真实历史赔率从未读 / 写（docs/PROJECT_STATUS.md）；需后续单独授权 |

## Domain: FotMob

| Domain | Capability | Status | Canonical entrypoint | Core implementation | Primary tests | Authorization & side effects | Legacy or forbidden alternatives | Current notes |
|---|---|---|---|---|---|---|---|---|
| FotMob | candidate exporter | CANONICAL | `npm run fotmob:candidates:export`；`make data-fotmob-candidates-network-export`（需 NETWORK_AUTHORIZATION=yes） | `scripts/ops/fotmob_candidates_export.js` → `src/infrastructure/fotmob/FotMobCandidateExporter.js` | tests/unit/fotmob_candidate_exporter.test.js | no-write 默认（本地导出）；网络导出需显式授权 | `n3_live_fotmob_raw_retain.js`、`pageprops_v2_*`、`adg60_*`、`titan_discovery.js` 及其它 Phase/ADG 历史采集脚本 | 唯一正式路径；PR #1813 后支持 canonical-v2 |
| FotMob | status mapping | CANONICAL | 同上（CLI 内） | `src/infrastructure/fotmob/FotMobStatusContract.js` | tests/unit/fotmob_candidate_exporter.test.js | 纯映射 | 历史脚本各自硬编码状态 | unknown / started fail closed（PR #1813） |
| FotMob | raw retention | CANONICAL | 同上（`--retain-raw-responses`） | `FotMobCandidateExporter.js` | tests/unit/fotmob_candidate_exporter.test.js | 本地文件写盘；both-or-neither 语义；git revision 绑定 | `n3_live_fotmob_raw_retain.js`（网络/UPSERT 路径，LEGACY） | 不得保存 / 打印完整 HTML body 到对话（AGENTS.md） |
| FotMob | capture manifest | CANONICAL | 同上（与 raw 配对落盘） | `FotMobCandidateExporter.js`（SHA-256 manifest） | tests/unit/fotmob_candidate_exporter.test.js | 本地文件写盘；both-or-neither 语义 | — | raw + manifest 必须同生共灭（PR #1813） |
| FotMob | identity projection hash | CANONICAL | 同上（canonical-v2 双哈希） | `FotMobCandidateExporter.js` + `CanonicalInventoryContract.js` | tests/unit/fotmob_candidate_exporter.test.js | 纯计算 | — | 稳定 payload hash，不含 volatile fetch metadata（AGENTS.md） |
| FotMob | business hash | CANONICAL | 同上 | 同上（full business hash） | tests/unit/fotmob_candidate_exporter.test.js、tests/unit/canonical_inventory_contract.test.js | 纯计算 | — | 与 identity projection hash 双哈希并存 |
| FotMob | canonical inventory contract | CANONICAL | 同上（写盘前强制校验） | `src/infrastructure/canonical/CanonicalInventoryContract.js` | tests/unit/canonical_inventory_contract.test.js | 校验失败即 fail closed | — | `validateArtifactDocument()` 合同执行点（PR #1813） |
| FotMob | canonical writer proof | CANONICAL（proof 范围） | `make data-m3-canonical-inventory-preflight` / `make data-m3-canonical-inventory-disposable-proof` | `src/infrastructure/canonical/CanonicalInventoryWriter.js` | tests/unit/canonical_inventory_writer.test.js、canonical_inventory_authorization.test.js、canonical_inventory_operator.test.js | preflight 只读；disposable proof 仅确定性 synthetic 输入 + 专用 tmpfs 库 | — | persistent canonical write 仍 blocked（README canonical 表） |
| FotMob | v1 compatibility | SUPPORTED_COMPATIBILITY | `--output-schema=identity-v1`（输出路径不变） | `FotMobCandidateExporter.js` | tests/unit/fotmob_candidate_exporter.test.js | 无副作用 | — | P3-3 v1 paired-write 弱点未修复、不属于阶段A（PR #1813 Debt Impact） |
| FotMob | production acquisition | NOT_ESTABLISHED | 无 | 无 | — | 无 | 上述 legacy 采集脚本 | README canonical 表：Not yet established for production acquisition |
| FotMob | real capture | BLOCKED | 无 | 无 | — | 未授权；FOTMOB_REAL_CAPTURE_READINESS 为 planning milestone（Issue #1793 / PR #1813） | — | 网络 probe、三赛季采集、条款审查、单页面 shape probe 均未授权（详见 docs/ACTIVE_MILESTONE.md） |

## Domain: 数据库与迁移

| Domain | Capability | Status | Canonical entrypoint | Core implementation | Primary tests | Authorization & side effects | Legacy or forbidden alternatives | Current notes |
|---|---|---|---|---|---|---|---|---|
| DB | M3 正式 SQL migration 树 | CANONICAL | `make data-schema-*` 门禁（`data-schema-help` 起步） | `database/migrations/V*.sql`（V26.8 / V26.9 / V26.10 为 M3 合同） | tests/integration/canonical_inventory/disposable_postgres.test.js 等 | 执行迁移需门禁 + 单独授权；M3 迁移仅在 disposable tmpfs 库执行过 | 直接 psql 执行 migration apply（禁止） | AGENTS.md §2.1 规则 10 |
| DB | Alembic migration 树 | CANONICAL（树存在） | 未明确（无文档化 canonical 入口） | `src/database/migrations/`（alembic.ini / env.py / versions/ 3 个版本） | — | 未授权不得执行 | — | **UNCLEAR**：两套树职责划分无文档说明（见 docs/PROJECT_MAP.md） |
| DB | DB write guard | CANONICAL | 所有写路径强制经过 | `scripts/ops/helpers/db_write_guard.js` | 见 guard 相关测试 | fail-closed；无 guard 通过不得写 | — | 写路径强制检查（AGENTS.md §5.3） |
| DB | controlled write（sandbox） | CANONICAL（sandbox 范围） | D4E disposable 门禁链 | `src/infrastructure/odds_staging/persistenceRepository.js` | tests/unit/odds_staging_d4e_controlled_write.test.js | 仅专用 disposable 库 + 单独授权 | — | 保留证据 1/1/6/3（docs/PROJECT_STATUS.md） |
| DB | production DB write | BLOCKED | 无 | 无 | — | 未授权 | — | 任何写库命令默认 blocked（AGENTS.md §5.3） |

## Domain: 训练 / 预测 / 回测

| Domain | Capability | Status | Canonical entrypoint | Core implementation | Primary tests | Authorization & side effects | Legacy or forbidden alternatives | Current notes |
|---|---|---|---|---|---|---|---|---|
| ML | training | CANONICAL/BLOCKED | `npm run train`（train:fast / train:deep 变体） | `src/ml/` | ML 测试 | 写模型 artifact；仅显式训练授权后可执行 | 任何未经授权的训练脚本 | 当前无训练授权 |
| ML | prediction | CANONICAL/BLOCKED | `npm run predict`（predict:dry / predict:json 变体） | `src/ml/inference/predictor.py` | ML 测试 | 读 DB；需确认环境 / 模型 / 授权 | — | 未授权不执行 |
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
