# TITAN Football Prediction Platform

> 工业级足球数据采集与预测平台 | Production-Ready Data Harvesting System
>
> **Version**: V4.51.2-TOTAL-WAR | **Status**: Production-Ready | **Coverage**: 80%+ Threshold

---

## 📐 Architecture

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TITAN 四层流水线架构                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐    │
│  │   L1 Discovery   │────▶│  C++ Fuzzy Match │────▶│  L2/L3 Harvest   │    │
│  │   (Node.js)      │     │  Bridge (Python) │     │  (Node.js)       │    │
│  └──────────────────┘     └──────────────────┘     └──────────────────┘    │
│         │                                                   │               │
│         ▼                                                   ▼               │
│  ┌──────────────────┐                              ┌──────────────────┐    │
│  │   FotMob API     │                              │   ML Prediction  │    │
│  │   Match Seeding  │                              │   (Python)       │    │
│  └──────────────────┘                              └──────────────────┘    │
│                                                             │               │
│                                                             ▼               │
│                                                    ┌──────────────────┐    │
│                                                    │   XGBoost 3-Model │    │
│                                                    │   Consensus       │    │
│                                                    └──────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 技术栈 | 职责 |
|------|--------|------|
| **L1 Discovery** | Node.js + Playwright | 自动发现未来7天比赛 |
| **L2 Harvest** | Node.js + 22节点代理池 | 赔率数据采集（开盘/收盘/亚洲盘） |
| **L3 Smelt** | FeatureSmelter | 12061维特征向量生成 |
| **ML Engine** | Python + XGBoost | 3-Model共识预测（67.2%准确率） |
| **Network Shield** | Custom Proxy Pool | 熔断保护与会话管理 |

### V11.0 Clean Sweep 架构 (Recon 侦察引擎)

V11.0 引入了工业级 Recon 侦察系统，实现从 OddsPortal 高效采集历史数据：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      V11.0 RECON 侦察引擎架构                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐    │
│  │  ReconNavigator  │────▶│   ReconParser    │────▶│  ReconStitcher   │    │
│  │   (页面导航)      │     │   (数据解析)      │     │   (数据缝合)      │    │
│  └──────────────────┘     └──────────────────┘     └──────────────────┘    │
│           │                       │                       │                 │
│           ▼                       ▼                       ▼                 │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐    │
│  │ReconDistributed  │     │ ReconResilience  │     │  ReconMetrics    │    │
│  │    (分布式锁)     │     │   (错误恢复)      │     │   (指标监控)      │    │
│  └──────────────────┘     └──────────────────┘     └──────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### V11.0 核心特性

| 特性 | 实现 | 说明 |
|------|------|------|
| **TraceID 追踪** | 每笔请求唯一编号 | 全链路可观测性 |
| **全局异常捕获** | 单点失败不影响整体 | 任务级容错 |
| **协议解密** | ReconDecryptor | 自动处理加密响应 |
| **熔断保护** | ReconCircuitBreaker | 连续失败自动熔断 |
| **配置解耦** | `config/recon_config.json` | Recon 配置唯一源 |
| **真事务映射保存** | `FixtureRepository` 单 Client 事务 | 避免批量写入伪事务 |
| **Fallback 加固** | `smartScan()` + DOM fallback | API 失败后不再因赛季变量缺失崩溃 |

#### V11.0 Release Note

**新特性**

- Recon TraceID 已从扫描入口显式贯穿到 Navigator、Engine、Parser、Repository
- 新增 Recon 鲁棒性回归测试，覆盖 API 失败后自动进入 fallback 链路

**Bug 修复**

- 修复 `smartScan()` fallback 路径 `dbSeason` 未定义崩溃
- 修复 `FixtureRepository` 批量映射保存的伪事务问题，改为单 `client` 真事务
- 修复 ajax / raw / nested 赔率结构解析回归

**破坏性变更**

- 真实网络与浏览器型验证用例迁移至 `tests/integration/`，`npm test` 仅保留单元测试基线

**已知技术债**

- `AbstractHarvester.js` 当前仍为高耦合大类，已登记到根目录 `TECH_DEBT.md`，计划在 V12.0 或全量收割完成后重构

#### V11.0 启动指令

```bash
# 启动 Recon 扫描器 (单赛季单联赛)
docker-compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/recon_scanner.js --season 2025-2026 --league BUNDESLIGA

# 启动 DOM Surgical Harvest (按月分段清缴)
docker-compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/dom_surgical_harvest.js

# 启动 L1 发现引擎
docker-compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/seed_fixtures.js --season 2025/2026 --league 54
```

Recon 当前默认走直连模式，代理为显式开启：

```bash
docker-compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/recon_scanner.js --season 2025-2026 --league EPL --use-proxy
```

L2 状态机约定：
- `pending`: 等待 Detail Harvester 领取
- `harvested`: `raw_match_data` 已落库，等待 Recon 建立映射
- `RECON_LINKED`: `matches_oddsportal_mapping` 已建立，且主表状态已原子推进
- `RECON_MISMATCH`: 当前批次未达到对齐阈值，等待后续人工或规则修复

---

### 🧩 模块化架构 (V4.52+)

TITAN V4.52 引入了三大高内聚组件，实现真正的模块化设计：

```
┌─────────────────────────────────────────────────────────────────┐
│                    ProductionHarvester                          │
│                    (轻量级调度中心 ~547行)                        │
└──────────────┬─────────────────┬────────────────┬───────────────┘
               │                 │                │
       ┌───────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
       │ Dispatcher   │  │Persistence  │  │ErrorHandler │
       │ 任务分派器    │  │数据持久化器  │  │错误审计器   │
       │ 231行 100%   │  │219行 核心   │  │289行 100%   │
       └──────────────┘  └─────────────┘  └─────────────┘
```

#### 组件职责

| 组件 | 行数 | 覆盖率 | 核心功能 |
|------|------|--------|----------|
| **Dispatcher** | 231 | 100% | Worker ID计算、统计报告、CLI解析、批次调度 |
| **Persistence** | 219 | 60%+ | 数据库保存、文件保存、双保险模式、错误分类 |
| **ErrorHandler** | 289 | 100% | 错误分类、可重试性判断、审计报告、模式匹配 |

#### 使用示例

```javascript
// Dispatcher - 任务分派
const workerId = this.dispatcher.calculateWorkerId(index);
const delay = this.dispatcher.calculateDelay(isRetry, minDelay, maxDelay);
this.dispatcher.printReport();

// Persistence - 数据持久化
await this.persistence.dualSave(pool, matchId, rawData, metadata);
await this.persistence.saveToFile(matchId, rawData, metadata);

// ErrorHandler - 错误审计
const type = this.errorHandler.classify(error);
const retryable = this.errorHandler.isRetryable(error, attempt);
this.errorHandler.audit(error, { matchId, workerId });
```

### 数据流向

```
FotMob API → matches (L1) → raw_match_data (L2) → l3_features (L3) → predictions
     │              │                │                   │                │
     ▼              ▼                ▼                   ▼                ▼
  比赛发现      基础信息        赔率数据(JSONB)      12061维特征      预测结果+EV
```

---

## Canonical Business Entrypoints

The table below is the **single source of truth** for business commands in this repository.
New human work and agent work must use these entries. `AGENTS.md` and `CLAUDE.md` reference
this section rather than maintaining duplicate command lists.

| Domain | Canonical status | Primary entrypoint / surface | Safety & authorization |
|---|---|---|---|
| **Data collection** | Controlled canonical surface | `data-l1-*` and `data-l2-*` Makefile targets (use `make data-help` to list) | Preview/read-only stages first; commit/execute/write stages require explicit authorization per target |
| **Odds** | Primary canonical | `npm run odds:harvest` | May access network and write DB. Confirm authorization, environment, and credentials before execution |
| **DB schema evolution** | Canonical definition surface (execution blocked by default) | Add the next reviewed versioned `V*.sql` file under `database/migrations/` | The location is canonical; execution is not authorized by location. Use the existing `make data-schema-*` / specialized gate and obtain separate authorization. Application startup never auto-applies schema changes |
| **FotMob** | Not yet established for production acquisition | Controlled preview/gated `data-*` workflows only | New code must not depend on legacy acquisition scripts. A unified FotMob entrypoint belongs to a future business milestone |
| **FotMob detail capture** | Controlled canonical surface (make data-*) | `make data-fotmob-detail-capture-{help,plan,preflight,execute,replay}` are the canonical entrypoints. PLAN / PREFLIGHT / REPLAY run fully offline (zero network, zero DB writes). The direct Node CLI (`scripts/ops/fotmob_detail_capture.js`) is the internal engine / specialized implementation detail, not the canonical interface | EXECUTE is the only real-network entry and fails in make before Node unless every variable is explicit (`PLAN`, `EXPECTED_PLAN_SHA256`, `AUTHORIZATION_ID`, `MAX_REQUESTS`, `DELAY_MS`, `OUTPUT_ROOT`, `RUN_ID`, `CONFIRM_REAL_FOTMOB_DETAIL_CAPTURE=1`, `CONFIRM_MAX_FOTMOB_REQUESTS == MAX_REQUESTS`, `NETWORK_AUTHORIZATION=yes`; the `DELAY_MS >= 60000` value check is enforced in Node before any fetch); the plan hash is recomputed from business fields before any fetch; retention is a stable allowlisted payload + manifest (no raw HTML persisted); replay is offline validation/materialization of the stable payload. The frozen 888-population acquisition (GDI1C, 2026-08-10/11) was executed under explicit Owner authorization (14 formal batches / 812 unique targets / 888 raw frozen; ACQUISITION_NETWORK_PHASE=CLOSED — see docs/data/FOTMOB_CURRENT_STATE.md closeout block); any NEW capture beyond the frozen population still requires explicit authorization and all tests are mocked |
| **FotMob detail staging (offline)** | Controlled canonical surface (make data-*) | `make data-fotmob-detail-staging-{help,receipt,build,validate}` are the canonical entrypoints. Fully offline converter/validator of archived capture payload+manifest pairs into immutable `fotmob-detail-staging-artifact/v1` snapshots. The direct Node CLI (`scripts/ops/fotmob_detail_staging.js`) is the internal engine / specialized implementation detail, not the canonical interface. `receipt`/`build` accept an optional `LIMITS_FILE=<absolute repository-external JSON>` overriding archive resource limits (member count/sizes, compressed/decompressed bytes) within hard caps — the limits file is repository-external by rule and strictly validated | OFFLINE ONLY by construction: ZERO NETWORK (no fetcher import), ZERO DATABASE (no DB client, no migration, no canonical/staging/odds write), NO CAPTURE, no wall-clock in business fields. Output is repository-external only; append-only file snapshots + numbered `store-state-<seq>.json` ledger versions; per-file atomic writes (O_EXCL tmp + fsync + same-fs rename) under an exclusive per-store lock; fail-closed on divergent content; committed by the LOGICAL_COMMIT_MARKER protocol (commit marker = only commit point, residue reported); re-validated by `-validate` (MODE_1_UNANCHORED or MODE_2_EXTERNALLY_ANCHORED; `EXPECTED_LATEST_MARKER_SHA256` and `ANCHOR_CHECKPOINT` are mutually exclusive anchor variables). 16 archived matches validated twice byte-identically (derived outputs removed; no real payload/manifest committed). PR #1817 remediation (merged 2026-08-06, squash merge commit `fd60117d2…`; post-merge main Production Gate run 31075669344 success): 8 blocker findings + 13 Codex closed-loop findings (review 4863122944) fixed — live archive↔receipt re-verification, REPEAT_EQUIVALENT write-back + three-way validator cross-checks, ACTUAL 16-field double-binding, TOCTOU mitigation (no-follow fd reads, controlled private dirs, store lock), anchored validation modes, strict tar parsing, container-first make targets |
| **M3 canonical inventory** | Controlled implementation surface | `make data-m3-canonical-inventory-preflight` and `make data-m3-canonical-inventory-disposable-proof` | Preflight validates a hash-bound artifact without writing. The proof accepts only deterministic synthetic input, requires separate exact schema and proof authorizations, and reaches its V26.10 migration through the disposable-only `data-schema-*` gate; persistent canonical writes remain blocked pending separate provenance review and authorization |
| **GD-A01 file-first assembly** | Specialized / internal offline surface | `npm run gd:a01 -- {build,validate}` with every input/output path explicit | Builds only the GD-A01 spine+historical-odds assembly outside the repository after validating frozen source identities, M3 receipt/output, exact linkage, and provider semantics; zero DB, zero network, zero raw mutation, zero features/training. This is not the completed Golden Dataset |
| **GD-A02 file-first facts assembly** | Specialized / internal offline surface | `npm run gd:a02 -- {build,validate}` with every input/output path explicit | Projects the validated GD-A01 admitted population onto the frozen FotMob capture/staging facts contract (five sections, result label, xG coverage) with exact provenance, deterministic ordering, population conservation, and postmatch-only semantics; zero DB, zero network, zero raw mutation, zero features/training. This does not complete the Golden Dataset |
| **GD-A03 prior-state feature view** | Specialized / internal offline surface | `npm run gd:a03 -- {build,validate}` with every input/output path explicit | Derives strict target-kickoff-exclusive prior-state features from GD-A01 identity, GD-A02 facts, and the canonical 1,140-fixture schedule; records feature-level numeric lineage and availability without defaults/proxies; zero DB, zero network, zero raw mutation, zero training/backtest. This does not prove decision-time readiness or complete the Golden Dataset |
| **Feature build** | Primary canonical | `npm run l3:stitch` | Schema must already be provisioned from the selected `database/migrations/` authority; the main stitch pipeline checks the L3 precondition and its Elo child checks the pre-provisioned `team_elo_ratings` relation before writing data. Neither path performs runtime schema creation. The raw SQL tree currently has no canonical `team_elo_ratings` definition; that provisioning gap is carried forward and is not repaired by A4-F1. Execution remains separately authorized. Confirm input/write scope; `npm run smelt` is a specialized internal alternative |
| **Training** | Primary canonical | `npm run train -- --input <offline-feature-frame> --output <candidate-path>` | **Only with explicit training authorization.** The canonical producer consumes an explicit pre-match frame, writes only a non-production candidate, uses the exact API contract, and never activates the tracked manifest. `train:fast` and `train:deep` are variants |
| **Prediction** | Primary canonical | `npm run predict -- --input <json-file>` (or JSON stdin) | HTTP and default CLI share `src/ml/inference/prediction_runtime.py`; the CLI does not perform legacy DB-batch discovery, fetch network data, or write artifacts. The canonical API artifact is currently pending, so prediction fails closed; execution still requires explicit prediction authorization |
| **Backtest** | Not yet established | None — must be implemented and accepted in a future business milestone | Historical scripts (`recon_scanner.js`, `gold_pilot_50.js`, `titan_marathon.js`) are not canonical backtest entrypoints |
| **Offline probability benchmark (Value MVP-1)** | Research evaluation (DOCUMENTED_ONLY) | Internal research-evaluation entrypoint: `scripts/model_training/value_mvp_baseline_vs_closing.py` (not a README canonical entrypoint; see Entry classification below) | Strictly offline probability benchmark evaluation: zero DB, zero network, zero new data, no odds as model features, walk-forward by season, protocol frozen before OOS. This is NOT an executable betting backtest and makes no ROI / profitability / CLV claim — the **Backtest** row above remains Not yet established |

### Prediction authority (PR-A3 current state)

- HTTP `POST /predict` and `POST /predict/batch` delegate to the shared
  `src/ml/inference/prediction_runtime.py` owner. The owner always creates
  `v26_7_aligned` through `Predictor.create_v26_7_aligned()`, which remains
  bound to the verified loader, manifest, feature-contract registry, and
  readiness lifecycle.
- The default CLI is the thin `src/ml/inference/predict_cli.py` adapter:

  ```bash
  npm run predict -- --input payload.json
  cat payload.json | npm run predict
  npm run predict:json -- --input payload.json
  npm run predict:dry -- --input payload.json
  ```

  Input is an explicit JSON object or an array of JSON objects with the same
  outer shape accepted by the HTTP routes. The adapter does not recreate the
  legacy DB/Titan batch query. `predict:dry` validates input only;
  it does not load a model. With the tracked pending/null canonical artifact,
  normal prediction exits non-zero with `prediction model unavailable` and
  never falls back to Titan or `v26_mini`.
- `npm run predict:titan-legacy` is the explicit legacy compatibility command
  for `scripts/ops/predict_pipeline.py`. It retains the old DB-backed Titan
  feature path and is not a canonical prediction authority. Its Titan input
  contains an 11-feature legacy core plus default-filled Titan-specific
  extensions; it is not asserted to equal the canonical 20-feature contract.
  `scripts/ops/titan_cruise_control.py` remains a historical Titan caller for
  the same reason.

### Entry classification

- **Canonical** — default entrypoint for new human work and agent work.
- **Specialized / Internal** — valid for specific use-cases but not the domain default (e.g.,
  `npm run seed`, `npm run odds:sniper`, `npm run smelt`, `predict:dry`,
  `predict:titan-legacy`, `train:fast`). M3 odds-staging offline entries belong here
  too: `npm run odds:staging:dry-run` (single-source offline import, fail-closed/no-write) and
  `npm run odds:staging:rebuild` (multi-source deterministic reconstruction, repo-external bundle/emit-dir only,
  no-write default; `--canonical-history` recovers the pinned sources from immutable git objects via a bounded
  read-only git child process; `--validate` recomputes every receipt fact from the emitted output). The
  GD-A01 file-first assembly (`npm run gd:a01 -- {build,validate}`) is likewise specialized/internal and
  requires explicit repository-external inputs/outputs; its spine+odds artifact is not the Golden Dataset.
  VALUE_MVP-1 offline probability benchmark (`scripts/model_training/value_mvp_baseline_vs_closing.py` +
  `src/ml/value_mvp/`) also belongs here: it is a research evaluation entrypoint, not a canonical backtest
  (see the **Offline probability benchmark** row above; Backtest remains Not yet established).
- **Legacy / Admin-only** — retained but **must not** become a new code dependency:
  `scripts/ops/run_production.js`, `scripts/ops/titan_discovery.js`,
  `scripts/ops/total_war_pipeline.js`, and Phase/ADG-numbered scripts as a category.

### Principles

1. New work must use the canonical entrypoint or surface listed above.
2. Specialized/internal scripts are not default entrypoints.
3. Legacy/admin-only scripts must not become new dependencies.
4. "Not yet established" means the corresponding business milestone must create and test a future entrypoint.
5. **Canonical does not mean automatically authorized.** Side-effectful commands (DB writes, network, browser,
   training, odds ingestion) still require explicit authorization per AGENTS.md.

### Project Knowledge Entry（当前可信知识入口）

- The table above defines the formal entrypoints, but **canonical ≠ 已获得执行授权**。
  含副作用的命令仍须按本表与 `AGENTS.md` 逐项明确授权。
- 新 Agent 应按 `CLAUDE.md` 定义的阅读顺序开始：`AGENTS.md` → 本表 →
  `docs/AGENT_WORKFLOW.md` / `docs/engineering/AI_AGENT_WORKFLOW.md` →
  `docs/AI_AGENT_WORKFLOW_HARDENING.md` → `docs/data/FOTMOB_CURRENT_STATE.md`。
- 项目地图 / 能力索引 / 活动里程碑（current-state 索引，不新增"唯一权威"声明）：
  - `docs/PROJECT_MAP.md` — 仓库结构、目录职责、阅读顺序、schema authority 与两套 migration 树生命周期。
  - `docs/CAPABILITY_INDEX.md` — 可扫描能力表（状态 / canonical 入口 / 授权 / legacy 替代）。
  - `docs/ACTIVE_MILESTONE.md` — 当前活动里程碑（M3）与授权边界。
- 历史 handover / merge-ready / command-center 类文档（`COMMAND_CENTER.md`、`HANDOVER.md`、
  `MERGE_READY.md`）仅保留历史背景与审计证据，**不得作为当前执行依据**。
- 真实网络、数据库写入、migration、artifact、训练与生产操作仍需单独授权，
  不因任何文档存在而自动放行。

### DB schema authority (PR-A4 current state)

The next schema change has exactly one location: add a reviewed, versioned
`V*.sql` migration under `database/migrations/`. The machine-readable contract is
`config/db_schema_authority.json`.

- `src/database/migrations/` is `LEGACY` historical Alembic compatibility with future revisions frozen;
  it has three revisions through `003_v145` and does not receive future schema changes.
- `src/database/schema_manager.py` mutation entrypoints are
  `LEGACY_NON_CANONICAL_RUNTIME_DDL` and fail fast; read-only helpers remain.
- `deploy/docker/init_db.sql` is `DEV_BOOTSTRAP_NON_AUTHORITATIVE`, limited to the
  development Compose DB empty-volume bootstrap. It is not a staging or production
  migration authority.
- Canonical location never implies execution authorization. Application startup does
  not auto-apply migrations; existing SC-002 guards remain in force.

---

## 🚀 Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose

### Installation

```bash
# 克隆项目
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction

# 配置环境变量
cp config/.env.example config/.env
# 编辑 config/.env 填入 DB_PASSWORD 和其他配置

# 启动基础设施
docker-compose -f docker-compose.dev.yml up -d

# 验证安装
npm run titan:check
```

### Start Harvesting

```bash
# 方式1: 哨兵自动监控模式（推荐）
npm run titan:start  # 终端1: 启动收割
npm run titan:watch  # 终端2: 启动哨兵

# 方式2: 手动模式
docker-compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/run_production.js --workers 12 --limit 12000
```

---

## 🛡️ Quality Gate

### 三位一体质检门禁

```
┌─────────────────────────────────────────────────────────────┐
│                    TITAN QUALITY GATE                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   ESLint     │  │    Jest      │  │  Coverage    │      │
│  │   0 Error    │  │   43+ Tests  │  │    80%+      │      │
│  │   Policy     │  │   Pass       │  │  Threshold   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                 │                │                │
│         ▼                 ▼                ▼                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              JSDoc Documentation                      │  │
│  │         (Code as Documentation)                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 质量标准

| 检查项 | 工具 | 阈值 | 命令 |
|--------|------|------|------|
| **静态分析** | ESLint | 0 Error | `npm run lint` |
| **单元测试** | Node.js --test | 100+ Pass | `node --test` |
| **代码覆盖** | c8 | 80%+ | `npx c8 --reporter=text node --test` |
| **文档规范** | JSDoc | Required | `npm run lint` |
| **代码格式** | Prettier | Enforced | `npm run format:check` |

### Pre-Commit Hook

所有提交必须通过本地质检门禁：

```bash
# .git/hooks/pre-commit 自动执行：
1. ESLint 检查 (src/, scripts/)
2. Node.js 单元测试 (100+ tests)
3. Line Coverage 验证 (≥80%)
4. Branch Coverage 验证 (≥80%)
5. components/ 目录扫描
```

**覆盖率阈值**:
- Line Coverage: **≥80%** (阻断)
- Branch Coverage: **≥80%** (阻断)

**执行结果：**

- ✅ 通过：准予提交
- ❌ 失败：阻断提交，需修复后重试

### 运行质检

```bash
# 全量质检流程
npm run qa

# 分项检查
npm run lint          # ESLint 检查
npm run lint:fix      # 自动修复
npm run test          # 单元测试 (Jest)
npm run test:coverage # 覆盖率报告
npm run format:check  # 格式检查

# Mini测试 (Node.js 内置测试，推荐)
node --max-old-space-size=256 tests/unit/Dispatcher.test.js
node --max-old-space-size=256 tests/unit/ErrorHandler.test.js
node --max-old-space-size=256 tests/unit/Persistence.test.js
```

---

## 📦 Deployment

### Docker 部署

```bash
# 开发环境
docker-compose -f docker-compose.dev.yml up -d

# 生产环境
docker-compose -f docker-compose.yml up -d

# 查看状态
docker-compose ps
```

### 环境配置

#### 数据库 (config/.env)

| 变量 | 默认值 | 必填 | 说明 |
|------|--------|------|------|
| `DB_HOST` | `host.docker.internal` | ✅ | 数据库主机 |
| `DB_PORT` | `5432` | ✅ | 数据库端口 |
| `DB_NAME` | `football_db` | ✅ | 数据库名 |
| `DB_USER` | `football_user` | ✅ | 数据库用户 |
| `DB_PASSWORD` | - | **必填** | 数据库密码 |

#### 收割配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MAX_WORKERS` | `12` | 并发Worker数量 |
| `MIN_DELAY_MS` | `10000` | 最小请求延迟 |
| `MAX_DELAY_MS` | `15000` | 最大请求延迟 |
| `PROXY_HOST` | `172.25.16.1` | 代理服务器 |
| `PROXY_PORT_RANGE` | `7891-7912` | 22节点代理池 |

#### 末端韧性模式 (Endgame)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RETRY_MAX_ATTEMPTS` | `5` | NO_DATA最大重试 |
| `CIRCUIT_THRESHOLD` | `10` | 熔断阈值 |
| `ENDGAME_SLOWDOWN` | `true` | 末端降速模式 |

### 运维指令集

| 指令 | 功能 | 场景 |
|------|------|------|
| `npm run titan:check` | 环境健康检查 | 启动前验证 |
| `npm run titan:start` | 启动12路收割 | 全量收割 |
| `npm run titan:watch` | 启动哨兵监控 | 无人值守 |
| `npm run titan:sync` | 存量数据同步 | 数据整理 |
| `npm run titan:audit` | 数据资产审计 | 质量检查 |
| `npm run status:db` | 查看数据库状态 | 监控 |

---

## 📊 Data Dictionary

### 数据库表结构

#### L1: matches (比赛发现层)

| 字段 | 类型 | 说明 |
|------|------|------|
| `match_id` | VARCHAR(50) PK | FotMob比赛ID |
| `home_team` | VARCHAR(100) | 主队名称 |
| `away_team` | VARCHAR(100) | 客队名称 |
| `match_time` | TIMESTAMP | 比赛时间 |
| `l2_harvested` | BOOLEAN | L2收割状态 |
| `is_finished` | BOOLEAN | 是否已完成 |

#### L2: raw_match_data (原始数据层)

| 字段 | 类型 | 说明 |
|------|------|------|
| `match_id` | VARCHAR(50) PK | 比赛ID |
| `collected_at` | TIMESTAMP | 采集时间 |
| `odds_data` | JSONB | 赔率数据(开盘/收盘/1X2/亚洲盘) |
| `xg_data` | JSONB | xG预期进球数据 |
| `source` | VARCHAR(50) | 数据来源 |

#### L3: l3_features (特征向量层)

| 字段 | 类型 | 说明 |
|------|------|------|
| `match_id` | VARCHAR(50) PK | 比赛ID |
| `feature_vector` | FLOAT[] | 12061维特征向量 |
| `feature_names` | TEXT[] | 特征名称列表 |
| `created_at` | TIMESTAMP | 生成时间 |

#### predictions (预测结果层)

| 字段 | 类型 | 说明 |
|------|------|------|
| `match_id` | VARCHAR(50) PK | 比赛ID |
| `home_win_prob` | FLOAT | 主胜概率 |
| `draw_prob` | FLOAT | 平局概率 |
| `away_win_prob` | FLOAT | 客胜概率 |
| `final_confidence` | FLOAT | 最终置信度 |
| `ev_value` | FLOAT | 期望值 |

### 物理文件结构

```
data/
├── matches/           # L2 JSON数据文件
│   ├── 12345.json
│   └── ...
├── sessions/          # 浏览器会话
│   └── manual_session.json
├── registry/          # 代理注册表
│   └── active_registry.json
└── debug/            # 调试输出
    └── screenshots/
```

### 数据质量指标

| 指标 | 目标 | 当前 |
|------|------|------|
| **L1覆盖率** | 100% | 12,000+/12,000 |
| **L2完整率** | ≥95% | 11,907/12,000 (99.2%) |
| **L3特征率** | ≥90% | 待处理 |
| **预测准确率** | ≥65% | 67.2% |

---

## 📁 Project Structure

```
FootballPrediction/
├── config/                    # 配置中心
│   ├── .env.example          # 环境变量模板
│   ├── factory_config.js     # 工厂级配置
│   └── database.js           # 数据库配置
├── scripts/                   # 运维脚本
│   ├── ops/                  # 核心操作
│   │   ├── run_production.js    # 生产收割
│   │   ├── check_health.js      # 健康检查
│   │   ├── sentinel_watch.js    # 哨兵监控
│   │   └── archive_legacy.sh    # 归档脚本
│   └── maintenance/          # 维护工具
├── src/                       # 源代码
│   ├── core/                 # 核心基础设施
│   ├── infrastructure/       # 基础设施层
│   │   ├── harvesters/      # 收割机系统
│   │   ├── network/         # 网络代理
│   │   └── browser/         # 浏览器工厂
│   ├── feature_engine/      # 特征工程
│   ├── ml/                  # 机器学习
│   └── parsers/             # 数据解析器
├── tests/                     # 测试套件
│   └── unit/                 # 单元测试
│       ├── Dispatcher.test.js      # 任务分派器测试 (38用例)
│       ├── ErrorHandler.test.js    # 错误审计器测试 (45用例)
│       ├── Persistence.test.js     # 持久化器测试 (17用例)
│       └── *_Mini.test.js          # 旧版Mini测试 (见下方)
├── docs/                      # 文档中心
├── data/                      # 数据存储
└── models/                    # ML模型仓库
```

---

## 🧪 Mini测试详解

TITAN 使用 Node.js 内置测试框架 (`node --test`) 进行单元测试，相比 Jest 更轻量、更快。

### 7个核心Mini测试

| 测试文件 | 测试目标 | 用例数 | 覆盖率 |
|----------|----------|--------|--------|
| `Dispatcher.test.js` | 任务分派器 | 38 | 100% |
| `ErrorHandler.test.js` | 错误审计器 | 45 | 100% |
| `Persistence.test.js` | 数据持久化器 | 17 | 60%+ |
| `ZK_Mini.test.js` | ZombieKiller | 3 | 核心 |
| `AA_Mini.test.js` | AutoAuthManager | 3 | 核心 |
| `DB_Mini.test.js` | PostgresClient | 5 | 85%+ |
| `FM_Mini.test.js` | FotMobStrategy | 5 | 核心 |

### 运行Mini测试

```bash
# 内存限制模式 (推荐，256MB)
node --max-old-space-size=256 tests/unit/Dispatcher.test.js
node --max-old-space-size=256 tests/unit/ErrorHandler.test.js
node --max-old-space-size=256 tests/unit/Persistence.test.js

# 批量运行
for f in tests/unit/*_Mini.test.js; do
  node --max-old-space-size=256 "$f"
done
```

### 测试覆盖重点

- **Dispatcher**: Worker ID计算、延迟计算、统计报告、CLI解析
- **ErrorHandler**: 8种错误类型分类、可重试性判断、审计报告
- **Persistence**: 数据库/文件错误分类、双保险保存模式

---

## 🔐 Authentication

### Cookie 更新

```bash
# 方法1: 手动导入
node scripts/import_manual_cookies.js

# 方法2: 自动采集
node scripts/capture_auth_v3.js
```

---

## 📈 Monitoring

### 实时监控

```bash
# 查看收割日志
docker-compose logs -f dev

# 数据库状态
npm run status:db

# 哨兵日志
tail -f logs/sentinel.log
```

### 胜利庆典

当 12,000 场目标达成时，哨兵系统将自动展示 ASCII Art 胜利庆典并安全停机。

---

## 🛠️ Troubleshooting

### 常见问题

| 问题 | 诊断 | 解决 |
|------|------|------|
| 代理熔断 | `curl -x http://proxy:port https://httpbin.org/ip` | 重启 docker-compose |
| 数据库连接失败 | `docker-compose exec db pg_isready` | 重启 db 服务 |
| NO_DATA 错误 | 检查 Cookie 是否过期 | 更新 manual_session.json |

### 故障排查手册

- 详见 `archive_vault_2026/docs_legacy/TROUBLESHOOTING.md`
- 运维 SOP: `docs/OPERATIONS_SOP.md`

---

## 📋 Version Information

- **Version**: V4.51.2-TOTAL-WAR
- **Node.js**: 18+
- **Python**: 3.11+
- **PostgreSQL**: 15+
- **Coverage**: 80%+ Threshold
- **License**: MIT
- **Last Updated**: 2026-03-13

---

## 🏆 Quality Badges

```
┌────────────────────────────────────────┐
│  ESLint    │  0 Error     │    ✅      │
├────────────────────────────────────────┤
│  Jest      │  43+ Pass    │    ✅      │
├────────────────────────────────────────┤
│  Coverage  │  80%+        │    ✅      │
├────────────────────────────────────────┤
│  JSDoc     │  Required    │    ✅      │
└────────────────────────────────────────┘
```

---

## 🆘 Support

- **Issues**: GitHub Issues
- **Docs**: `docs/` 目录
- **Team**: V174 Engineering Team

---

<p align="center">
  <strong>TITAN —— 工业级足球预测平台</strong><br>
  <em>Production-Ready. Zero Compromise.</em>
</p>
