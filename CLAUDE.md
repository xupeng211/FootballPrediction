# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**系统版本**: V4.47.0-BATTLE | **最后更新**: 2026-03-11

> 📋 **环境配置**: 复制 `.env.example` 到 `.env` 并填写 `DB_PASSWORD`。

---

## 工程铁律 (Engineering Constitution)

以下 5 条规则具有最高优先级：

### 1. 沟通协议

- 所有回复、注释、日志必须使用**中文**
- 变量名、函数名可使用英文

### 2. 容器化优先

- **禁止**在宿主机直接运行 Node/Python
- 所有操作在 Docker 容器内执行
- 日志写入 `/app/logs/`，数据写入 `/app/data/`

```bash
# ✓ 正确
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/run_production.js

# ✗ 错误
node scripts/ops/run_production.js
```

### 3. 分支管理

- 严禁在 `main` 分支开发
- 分支命名：`feat/<功能>` / `lab/<实验>` / `fix/<修复>`
- 提交遵循 Angular 规范

### 4. 数据完整性

- **零模拟原则**：严禁使用 `Math.random()` 伪造数据
- 数据缺失时报错中止，不生成假数据

### 5. 幂等性

- 所有收割任务支持重复执行
- 已存在的完整数据应跳过

---

## V4.46 架构规范

### 统一标准

- **配置唯一源**: `src/config_unified.py`
- **数学能力**: `src/core/math/` (finance, evaluator)
- **动态能力**: `src/core/` (Math, Database, Types)
- **预测大脑**: `src/ml/`
- **基础设施**: `src/infrastructure/`
- **唯一数据**: `src/database/`
- **唯一指环部**: `src/config/`

---

## V4.42 契约统一

### 政策统一

- **MatchStatus 唯一源头**: `src/constants/shared_constants.py`
- **禁止**在任何其他模块新建 MatchStatus 定义
- 所有模块都必须从 `shared_constants` 导入

### 契约统一

- **数据库模型**: `src/database/models.py` 是唯一真理
- **Pydantic Schema**: `src/schemas/match_features.py` 必须与数据库模型对齐
- **字段命名**: 全部使用下划线命名

### 服务加载标准

- **唯一标准**: `dependency_injection.py` 是唯一服务加载方式
- **向后兼容**: 使用 `MatchDataService` 替代原有 `MatchAligner` + `MatchLinker`

---

## MCP 服务器权限

| MCP 服务器 | 权限 | 允许行为 |
|-----------|------|----------|
| **postgres** | READ-ONLY | SELECT / DESCRIBE / EXPLAIN |
| **filesystem** | PROJECT ROOT | 读 / diff / 受控写 |
| **git** | READ-ONLY | commit history / diff / blame |
| **pytest** | RESTRICTED | 运行 pytest / 列出测试 |

> ⚠️ **MCP 不拥有生产环境控制权**，禁止任何不可逆或高风险自动化操作。

---

## Claude Skills 约束体系

项目已配置 12 个专用 Skills，详见 `.claude/README.md`。核心约束：

| 约束等级 | Skill | 用途 |
|----------|-------|------|
| 🔴 RED | `minimal_change` | 最小修改策略，防止过度重构 |
| 🔴 RED | `architecture_boundary` | 架构边界保护，维护层次结构 |
| 🔴 RED | `test_guard` | 测试质量保护 |
| 🔴 RED | `context_lock` | 核心模块冻结 |
| 🔴 RED | `change_impact` | 变更影响分析 |

**可用业务 Skills**:

- `football-prediction`: 比赛预测分析 (67.2% 准确率)
- `data-collection`: FotMob API 数据收集
- `report-generation`: PDF/Word/Excel 报告生成
- `machine-learning-engineering`: XGBoost 模型优化
- `code-quality`: 代码质量管理 (通过 Makefile)
- `database-operations`: PostgreSQL 运维

---

# ══════════════════════════════════════════════════════════════════════════════

# 常用命令 (Commands)

# ══════════════════════════════════════════════════════════════════════════════

## 开发环境

```bash
# === 启动/停止 ===
docker-compose -f docker-compose.dev.yml up -d              # 启动开发容器 (db + redis + dev)
docker-compose -f docker-compose.dev.yml exec dev bash      # 进入开发容器 Shell
docker-compose -f docker-compose.dev.yml down               # 停止开发环境
make dev-up                                                 # Makefile 快捷方式
make dev-shell                                              # 进入开发容器

# === 核心收割 (scripts/ops/) ===
docker-compose -f docker-compose.dev.yml exec dev npm start                # 生产收割器
docker-compose -f docker-compose.dev.yml exec dev npm run seed             # 赛程种子数据
docker-compose -f docker-compose.dev.yml exec dev npm run smelt            # 特征熔炼

# Swarm 蜂群收割 (推荐，多 Worker 并发)
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/swarm_test.js           # 默认 3 Worker
docker-compose -f docker-compose.dev.yml exec dev env SWARM_CONCURRENCY=5 node scripts/ops/swarm_test.js  # 自定义并发

# 直接调用脚本 (支持参数)
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/run_production.js --limit 100
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/run_production.js --dry-run

# === 代码质量 ===
docker-compose -f docker-compose.dev.yml exec dev npm run lint              # ESLint 检查
docker-compose -f docker-compose.dev.yml exec dev npm run lint:fix          # ESLint 自动修复
docker-compose -f docker-compose.dev.yml exec dev npm run format            # Prettier 格式化
docker-compose -f docker-compose.dev.yml exec dev npm run lint:python       # Ruff Python 检查
docker-compose -f docker-compose.dev.yml exec dev npm run qa                # 全量检查 (lint + test)
make lint                                                                # Makefile: Lint 检查
make format                                                              # Makefile: 格式化代码

# === 测试 ===
# Node.js 测试
docker-compose -f docker-compose.dev.yml exec dev npm test                  # 运行所有 Node.js 单元测试
docker-compose -f docker-compose.dev.yml exec dev npm run test:unit         # 单元测试
docker-compose -f docker-compose.dev.yml exec dev npm run test:coverage     # 带覆盖率测试

# Python 测试
docker-compose -f docker-compose.dev.yml exec dev pytest tests/ -v          # 运行所有 Python 测试
docker-compose -f docker-compose.dev.yml exec dev pytest tests/ml/ -v       # ML 模块测试
docker-compose -f docker-compose.dev.yml exec dev pytest tests/ -k "关键词" -v  # 按关键词筛选

# === 数据库 ===
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db  # 进入 PostgreSQL Shell
make db-shell                                                             # Makefile 快捷方式

# === 依赖安装 (容器内) ===
docker-compose -f docker-compose.dev.yml exec dev npm install               # 安装 Node.js 依赖
docker-compose -f docker-compose.dev.yml exec dev pip install -r requirements.txt  # 安装 Python 依赖
docker-compose -f docker-compose.dev.yml exec dev npm run install-browsers  # 安装 Playwright 浏览器

# === 清理 ===
make clean               # 清理垃圾文件 (pyc, __pycache__, .pytest_cache)
make clean-all           # 完全清理 (包括临时文件和日志)
```

## 可用 npm 脚本 (package.json)

### 数据流水线

| 命令 | 描述 |
|------|------|
| `npm start` | 生产收割器 (`scripts/ops/run_production.js`) |
| `npm run seed` | L1 赛程种子数据 |
| `npm run seed:all` | 全量赛程种子 |
| `npm run smelt` | L3 特征熔炼 |
| `npm run harvest` | 超频收割 (`hyper_swarm.js`) |
| `npm run harvest:swarm` | 蜂群收割 (`swarm_test.js`) |
| `npm run harvest:production` | 生产收割器 |

### ML 训练与预测

| 命令 | 描述 |
|------|------|
| `npm run train` | 模型训练 (默认参数) |
| `npm run train:fast` | 快速训练 (100 estimators, depth 4) |
| `npm run train:deep` | 深度训练 (500 estimators, depth 8) |
| `npm run predict` | 运行预测流水线 |
| `npm run predict:dry` | 预测流水线 (dry-run 模式) |
| `npm run predict:json` | 预测流水线 (JSON 输出) |

### 监控与状态

| 命令 | 描述 |
|------|------|
| `npm run metrics` | 启动指标服务 (端口 8000) |
| `npm run monitor:up` | 启动监控栈 (Prometheus + Grafana) |
| `npm run monitor:down` | 停止监控栈 |
| `npm run status` | 数据完整性检查 |
| `npm run status:db` | 数据库层级统计 |
| `npm run status:health` | 容器健康状态 |

### 开发环境

| 命令 | 描述 |
|------|------|
| `npm run dev:up` | 启动开发容器 |
| `npm run dev:down` | 停止开发容器 |
| `npm run dev:shell` | 进入开发容器 Shell |
| `npm run dev:logs` | 查看容器日志 |

### 测试与质量

| 命令 | 描述 |
|------|------|
| `npm test` | 运行所有 Node.js 单元测试 |
| `npm run test:unit` | 单元测试 |
| `npm run test:l1` | L1 赛程测试 |
| `npm run test:integration` | 集成测试 |
| `npm run test:coverage` | 带覆盖率测试 |
| `npm run lint` | ESLint 检查 |
| `npm run lint:fix` | ESLint 自动修复 |
| `npm run lint:python` | Ruff Python 检查 |
| `npm run format` | Prettier 格式化 |
| `npm run format:check` | 格式化检查 |
| `npm run format:python` | Ruff 格式化 |
| `npm run qa` | 全量检查 (lint + test:unit) |

## Makefile 命令

### 服务管理

| 命令 | 描述 |
|------|------|
| `make help` | 显示所有可用命令 |
| `make up` | 启动核心服务 (db + redis) |
| `make up-pipeline` | 启动核心服务 + 数据流水线 |
| `make up-api` | 启动核心服务 + API |
| `make up-dev` | 启动开发环境 (包含管理工具) |
| `make up-all` | 启动所有服务 |
| `make down` | 停止所有服务 |
| `make restart` | 重启核心服务 |
| `make ps` | 查看容器状态 |
| `make health` | 检查服务健康状态 |

### 日志与监控

| 命令 | 描述 |
|------|------|
| `make logs` | 查看核心服务日志 |
| `make logs-api` | 查看 API 日志 |
| `make logs-all` | 查看所有服务日志 |
| `make dashboard` | 启动战神仪表盘 |

### 构建与部署

| 命令 | 描述 |
|------|------|
| `make build` | 构建生产镜像 |
| `make build-test` | 构建测试镜像 |
| `make build-no-cache` | 无缓存构建 |
| `make deploy` | 部署到生产环境 |

### 代码质量

| 命令 | 描述 |
|------|------|
| `make lint` | 运行 Lint 检查 (ruff/flake8) |
| `make format` | 格式化代码 (ruff/black) |
| `make test` | 运行全量测试 |
| `make test-unit` | 运行单元测试 |
| `make security` | 运行安全扫描 |
| `make verify` | 完整验证 (lint + test + security) |

### 数据库与缓存

| 命令 | 描述 |
|------|------|
| `make db-shell` | 进入 PostgreSQL Shell |
| `make db-backup` | 备份数据库 |
| `make db-reset` | 重置数据库 (危险操作!) |
| `make redis-shell` | 进入 Redis CLI |

### 清理

| 命令 | 描述 |
|------|------|
| `make clean` | 清理垃圾文件 (pyc, **pycache**) |
| `make clean-csv` | 清理临时测试 CSV 文件 |
| `make clean-logs` | 清理超过 7 天的日志 |
| `make clean-docker` | 清理 Docker 资源 |
| `make clean-all` | 完全清理 (包括临时文件和日志) |

---

# ══════════════════════════════════════════════════════════════════════════════

# 系统架构 (Architecture)

# ══════════════════════════════════════════════════════════════════════════════

双语言足球预测平台，四层架构：

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  L1 Discovery   │───▶│  C++ Fuzzy      │───▶│  L2/L3 Harvest  │───▶│  ML Prediction  │
│  (Node.js)      │    │  Bridge (Python)│    │  (Node.js)      │    │  (Python)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

**数据层级：**

| 层级 | 数据源 | 说明 | 存储表 |
|------|--------|------|--------|
| **L1** | FotMob API | 比赛发现、基础信息 | `matches` |
| **L2** | FotMob Details + OddsPortal | 身价/阵容/xG/评分 + 赔率数据 | `raw_match_data`, `l2_match_data` |
| **L3** | 特征工程 | 12061 维特征向量 | `l3_features` |

**系统核心资产地图：**

| 功能模块 | 唯一指定文件 | 入口脚本 |
|----------|-------------|---------|
| **L1 Discovery** | `src/infrastructure/services/DiscoveryService.js` | `scripts/ops/seed_fixtures.js` |
| **L2 Harvest** | `src/infrastructure/harvesters/ProductionHarvester.js` | `scripts/ops/run_production.js` |
| **Swarm Harvest** | `src/infrastructure/harvesters/SwarmHarvester.js` | `scripts/ops/swarm_test.js` |
| **L3 Smelt** | `src/feature_engine/smelter/FeatureSmelter.js` | `scripts/ops/smelt_all.js` |
| **身份管理** | `src/infrastructure/network/SessionManager.js` | - |
| **代理池** | `src/infrastructure/network/NetworkShield.js` | - |
| **Prometheus 监控** | `src/infrastructure/monitoring/MetricsClient.js` | - |
| **C++ 桥接** | `src/utils/cpp_bridge_radar.py` | - |

**关键目录结构：**

```
src/
├── core/                      # 核心基础设施 (IPC, 进程管理, 浏览器管理)
├── parsers/                   # 数据解析器 (FotMob, NextData)
├── models/                    # 数据模型 Query 封装
├── feature_engine/            # Node.js 特征引擎 (GoldenFeature, EloRating, OddsMovement)
├── infrastructure/            # 基础设施 (ProductionHarvester, NetworkShield, DiscoveryService)
├── ml/                        # 机器学习 (inference, training, features)
│   ├── inference/             # 模型推理 (predictor, model_loader, multi_model_validator)
│   ├── training/              # 模型训练
│   ├── features/              # Python 特征提取
│   ├── feature_engine/        # Python 特征引擎 (processors/*)
│   ├── models/                # 模型定义
│   ├── strategy/              # 投注策略 (fractional_kelly)
│   └── backtest/              # 回测引擎
└── utils/                     # 工具函数 (cpp_bridge_radar, team_alias)

scripts/
├── ops/                       # 运维脚本 (run_production, seed_fixtures, smelt_all)
└── maintenance/               # 维护工具 (check_system_health, fotmob_historical_backfill)

config/
└── factory_config.js          # 工厂级配置中心 (所有魔术数字归口管理)
```

**核心基础设施组件：**

| 组件 | 功能 | 位置 |
|------|------|------|
| `ProductionHarvester` | L2/L3 数据收割主入口 | `src/infrastructure/harvesters/` |
| `SwarmHarvester` | 多 Worker 并发收割 (3x 吞吐提升) | `src/infrastructure/harvesters/` |
| `DiscoveryService` | L1 赛程发现与种子 | `src/infrastructure/services/` |
| `NetworkShield` | 22 节点代理池管理、熔断保护 | `src/infrastructure/network/` |
| `SessionManager` | 无人值守身份管理、Cookie 自动注入 | `src/infrastructure/network/` |
| `MetricsClient` | Prometheus 指标暴露 (`/metrics`) | `src/infrastructure/monitoring/` |
| `BridgeRadarEngine` | C++ 模糊匹配桥接 | `src/utils/cpp_bridge_radar.py` |
| `PostgresClient` | 数据库连接池 | `src/infrastructure/database/` |

**多模型共识 (3-Model Consensus):**

| 模型 | 特征维度 | 用途 |
|------|---------|------|
| Model A | 37 | 通用预测 |
| Model B | 6000+ | 联赛专项 |
| Model C | 19 | 赔率模型 |

共识规则: UNANIMOUS (3/3) > MAJORITY (2/3) > SPLIT (无共识)

---

## 性能基准 (Performance Benchmarks)

### 吞吐量指标

| 指标 | 数值 | 测试条件 |
|------|------|----------|
| **收割吞吐量** | 5.8 场/分钟 | 5-Worker 并发 |
| **峰值吞吐量** | 12+ 场/分钟 | 10-Worker 并发 |
| **日处理能力** | 8,000+ 场 | 24h 连续运行 |

### 响应时延

| 操作 | P50 | P95 | P99 |
|------|-----|-----|-----|
| **单场收割** | 10.3s | 15.2s | 22.8s |
| **L2 数据采集** | 4.7s | 8.1s | 12.5s |
| **L3 特征熔炼** | 0.8s | 1.2s | 2.1s |
| **模型预测** | <100ms | <150ms | <200ms |

### Worker 并发扩展矩阵

| Workers | 吞吐量 (场/分) | 代理占用 | 推荐场景 |
|---------|---------------|----------|----------|
| 1 | 1.2 | 1/22 | 调试 / 单场测试 |
| 3 | 3.6 | 3/22 | 日常收割 |
| 5 | 5.8 | 5/22 | 生产环境 (推荐) |
| 10 | 10.2 | 10/22 | 高峰期 |
| 22 | 18.5 | 22/22 | 极限压测 |

---

## Match ID 规范

系统采用统一的 Match ID 格式，确保跨层数据一致性：

```
格式: [LeagueID]_[Season]_[MatchID]

示例: 55_20242025_4803413
      │  │        │
      │  │        └── FotMob 比赛 ID
      │  └── 赛季 (YYYYYYYY 格式)
      └── 联赛 ID (FotMob League ID)

常用联赛 ID:
├── 55   = Premier League (英超)
├── 54   = La Liga (西甲)
├── 53   = Bundesliga (德甲)
├── 52   = Serie A (意甲)
├── 51   = Ligue 1 (法甲)
└── 详见 config/league_registry.json
```

---

## EV 计算与投注策略

### EV (Expected Value) 计算公式

```python
# 有赔率时的 EV 计算
EV = P × Odds - 1

# 示例
P = 64.7%, Odds = 1.47
EV = 0.647 × 1.47 - 1 = -4.9%  (负值，不推荐投注)
```

### 无赔率时的保守估算 (条件从高到低)

```python
if p > 0.70:    ev = min(0.10, theoretical_ev + 0.05)
elif p > 0.60:  ev = min(0.05, theoretical_ev + 0.02)
elif p > 0.50:  ev = min(0.03, theoretical_ev)
elif p > 0.40:  ev = max(-0.05, theoretical_ev - 0.02)
else:           ev = max(-0.10, theoretical_ev - 0.05)
```

### EV 阈值决策矩阵

| EV 范围 | 决策 | 仓位建议 |
|---------|------|----------|
| **EV > 10%** | 强烈推荐 | 1/2 Kelly |
| **5% < EV < 10%** | 推荐 | 1/4 Kelly |
| **0% < EV < 5%** | 边缘 | 1/8 Kelly 或跳过 |
| **EV < 0%** | **拒绝** | 0 (负期望值) |

### Fractional Kelly 计算公式

```
Kelly% = (P × Odds - 1) / (Odds - 1)
实际仓位 = Kelly% × 分数系数 (推荐 0.25)

示例:
P = 55%, Odds = 2.10, EV = 15.5%
Kelly% = (0.55 × 2.10 - 1) / (2.10 - 1) = 14.1%
实际仓位 = 14.1% × 0.25 = 3.5%
```

---

## GoldenFeatureExtractor 四层回退逻辑

身价提取策略 (单位: 欧元):

| 策略 | 路径 | 可靠性 | 单位转换 |
|------|------|--------|----------|
| **策略 1** | `content.lineup.{team}Team.totalStarterMarketValue` | ★★★★★ | × 1e6 |
| **策略 2** | `content.lineup.{team}Team.starters[].marketValue` 求和 | ★★★★☆ | 每个 × 1e6 后求和 |
| **策略 3** | `content.lineup.{team}Team.subs[].marketValue` 求和 | ★★★☆☆ | 每个 × 1e6 后求和 |
| **策略 4** | 深度搜索 (table.all/players/details.stats) | ★★☆☆☆ | - |
| **策略 5** | 数据缺失 → `market_value_total = 0` | - | 标记 `not_found` |

**重要**: FotMob API 返回的 `marketValue` 单位是**百万欧元**，必须乘以 1e6 转换为欧元。

---

# ══════════════════════════════════════════════════════════════════════════════

# 配置系统 (Configuration System)

# ══════════════════════════════════════════════════════════════════════════════

所有配置集中在 `config/factory_config.js`，**严禁在业务代码中硬编码参数**。

| 配置模块 | 说明 |
|----------|------|
| `QUALITY_GATE` | 数据质量门禁 (最小体积、必须路径、错误关键字) |
| `TIMING` | 延时配置 (minDelayMs: 10s, maxDelayMs: 15s) |
| `RETRY` | 重试策略 (最多 3 次、指数退避) |
| `CONCURRENCY` | 并发配置 (maxWorkers: 1, batchSize: 50) |
| `PROXY_CONFIG` | 22 节点代理池 (端口 7890-7911) |
| `CIRCUIT_BREAKER` | 熔断器 (5 次失败触发 60 秒冷却) |
| `FINGERPRINT` | 浏览器指纹池 (20+ UA、静态指纹) |
| `BROWSER` | 浏览器配置 (profilePath, headless, launchArgs) |

```javascript
// 使用示例
const FactoryConfig = require('../../../config/factory_config');
const delay = FactoryConfig.getRandomDelay([FactoryConfig.TIMING.minDelayMs, FactoryConfig.TIMING.maxDelayMs]);
```

---

# ══════════════════════════════════════════════════════════════════════════════

# 关键规则 (Critical Rules)

# ══════════════════════════════════════════════════════════════════════════════

### 队名匹配

**必须**使用 `BridgeRadarEngine` 进行 FotMob 与 OddsPortal 的 URL 匹配：

```python
# ✓ 正确方式
from src.utils.cpp_bridge_radar import BridgeRadarEngine
bridge = BridgeRadarEngine()
result = bridge.dynamic_bridge(fotmob_home="Man Utd", fotmob_away="Chelsea", league_name="Premier League")

# ✗ 禁止手动拼接 URL
const url = `https://oddsportal.com/${home}-${away}/`;  # 这会导致匹配失败
```

### 代理系统 (NetworkShield)

- 22 个代理节点，端口 7890-7911
- 熔断机制：连续 5 次失败触发 60 秒冷却
- Session Stickiness：Worker 与端口一对一绑定
- 配置文件：`config/active_registry.json`

```bash
curl -x http://172.25.16.1:7891 https://httpbin.org/ip  # 测试代理
```

### 身份管理 (SessionManager)

- 自动身份捕获：可见浏览器过 Turnstile
- 身份热加载：Cookie 自动注入到无头浏览器
- 22 节点一对一身份绑定
- 会话存储路径：`/app/data/sessions/session_port_{端口}.json`
- 容器环境无 X Server 时自动跳过可见浏览器刷新

---

# ══════════════════════════════════════════════════════════════════════════════

# 环境变量 (Environment Variables)

# ══════════════════════════════════════════════════════════════════════════════

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DB_PASSWORD` | 数据库密码 (**必填**) | - |
| `DB_HOST` | 数据库主机 | `host.docker.internal` |
| `DB_PORT` | 数据库端口 | `5432` |
| `DB_NAME` | 数据库名称 | `football_db` |
| `DB_USER` | 数据库用户 | `football_user` |
| `MAX_WORKERS` | Worker 数量 | `1` |
| `MIN_DELAY_MS` | 最小延时 (ms) | `10000` |
| `MAX_DELAY_MS` | 最大延时 (ms) | `15000` |
| `PROXY_HOST` | 代理服务器地址 | `172.25.16.1` |
| `LOG_LEVEL` | 日志级别 | `info` |
| `BROWSER_PROFILE_PATH` | 浏览器配置文件路径 | `/app/data/browser_profile` |

---

# ══════════════════════════════════════════════════════════════════════════════

# 故障排查 (Troubleshooting)

# ══════════════════════════════════════════════════════════════════════════════

| 问题 | 诊断命令 | 解决方案 |
|------|---------|---------|
| **代理熔断** | `curl -x http://172.25.16.1:7891 https://httpbin.org/ip` | `docker-compose restart dev` |
| **数据库连接** | `docker-compose exec db pg_isready -U football_user` | `docker-compose restart db` |
| **浏览器崩溃** | `ps aux \| grep chromium` | `npx playwright install chromium --force` |
| **数据不一致** | `python scripts/maintenance/check_system_health.py` | 运行 `clean_corrupt_l2.py` |
| **Turnstile 拦截** | 检查 `/app/data/sessions/` 是否有会话文件 | 宿主机运行 `node scripts/capture_auth.js` 手动捕获身份 |

---

# ══════════════════════════════════════════════════════════════════════════════

# 代码风格 (Code Style)

# ══════════════════════════════════════════════════════════════════════════════

**Python (Ruff + Type Hints):**

```python
def fuzzy_match_teams(fotmob_home: str, oddsportal_home: str, *, min_threshold: float = 0.65) -> FuzzyMatchResult | None:
    """模糊匹配队名。"""
```

**Node.js (ESLint + Prettier):**

```javascript
/**
 * @param {string} matchId - 比赛标识符
 * @returns {Promise<MatchPrediction>}
 */
async function fetchPrediction(matchId, options = {}) { ... }
```

---

# ══════════════════════════════════════════════════════════════════════════════

# 数据库表结构 (Database Schema)

# ══════════════════════════════════════════════════════════════════════════════

| 表名 | 用途 | 数据层级 |
|------|------|----------|
| `matches` | 比赛基础信息 | L1 |
| `raw_match_data` | L2 原始数据 (JSONB 赔率) | L2 |
| `l3_features` | 特征向量 (12061 维) | L3 |
| `predictions` | 预测结果 | - |
| `fundamentals` | 基本面数据 | - |

**常用查询：**

```sql
-- 查看待收割比赛
SELECT match_id, home_team, away_team, match_time FROM matches WHERE l2_harvested = false;

-- 查看高置信度预测
SELECT * FROM predictions WHERE final_confidence > 0.65 ORDER BY match_time;

-- 检查数据完整性
SELECT COUNT(*) as total, COUNT(l2_harvested) as l2_done FROM matches WHERE match_time > NOW();
```

---

# ══════════════════════════════════════════════════════════════════════════════

# 测试体系 (Testing System)

# ══════════════════════════════════════════════════════════════════════════════

### 测试目录结构

```
tests/
├── conftest.py              # 统一测试配置和 Fixtures
├── unit/                    # Node.js 单元测试 (*.test.js)
│   ├── test_core/           # 核心模块测试
│   ├── mock_factories.py    # Mock 工厂
│   └── *.test.js            # 各模块测试
├── integration/             # 集成测试
├── integrity/               # 数据完整性和边缘情况测试
└── Z_LEGACY_ARCHIVE_PRE_V4.46.8/  # ⚠️ 历史归档 (pytest 已排除，请勿修改)
```

> **注意**: `Z_LEGACY_ARCHIVE_PRE_V4.46.8/` 包含 V4.46.8 之前的测试文件，已被 pytest 自动排除 (见 `pytest.ini`)。

### pytest 测试标记

| 标记 | 用途 | 示例 |
|------|------|------|
| `unit` | 单元测试 | `pytest -m unit` |
| `integration` | 集成测试 | `pytest -m integration` |
| `integrity` | 数据完整性测试 | `pytest -m integrity` |
| `slow` | 慢速测试 | `pytest -m "not slow"` |
| `network` | 需要网络的测试 | `pytest -m network` |
| `e2e` | 端到端测试 | `pytest -m e2e` |
| `performance` | 性能测试 | `pytest -m performance` |

### 测试命令

```bash
# Node.js 单独测试
docker-compose -f docker-compose.dev.yml exec dev node --test tests/unit/DiscoveryService.test.js

# Python 单独测试
docker-compose -f docker-compose.dev.yml exec dev pytest tests/test_core_logic.py -v

# Python 带调试输出
docker-compose -f docker-compose.dev.yml exec dev pytest tests/unit/test_ev_calculator.py -v -s

# 只运行特定测试函数
docker-compose -f docker-compose.dev.yml exec dev pytest tests/test_core_logic.py::test_specific_function -v

# 带覆盖率运行
docker-compose -f docker-compose.dev.yml exec dev pytest tests/ --cov=src/ml --cov-report=term-missing

# 按标记运行测试
docker-compose -f docker-compose.dev.yml exec dev pytest -m unit              # 只运行单元测试
docker-compose -f docker-compose.dev.yml exec dev pytest -m "not slow"       # 排除慢速测试
docker-compose -f docker-compose.dev.yml exec dev pytest -m integrity        # 运行完整性测试

# 异步测试 (自动检测)
# pytest.ini 已配置 asyncio_mode = auto，无需额外配置
```

### 测试 Fixtures (conftest.py)

| Fixture | 作用域 | 用途 |
|---------|--------|------|
| `db_connection` | session | 数据库连接 (回归测试) |
| `historical_match_sample` | session | 2021-2022 历史比赛样本 |
| `recent_match_sample` | session | 2024-2025 近期比赛样本 |
| `playwright_browser` | function | E2E 浏览器实例 |
| `sample_match_data` | function | 标准比赛数据样本 |
| `sample_feature_df` | function | 标准特征 DataFrame |
| `mock_lightgbm_model` | function | Mock LightGBM 模型 |
| `mock_config` | function | Mock 配置对象 |

---

# ══════════════════════════════════════════════════════════════════════════════

# 调试技巧 (Debugging Tips)

# ══════════════════════════════════════════════════════════════════════════════

### 日志级别调整

```bash
# 临时启用 DEBUG 日志
docker-compose -f docker-compose.dev.yml exec -e LOG_LEVEL=debug dev npm start

# 查看实时日志
tail -f logs/harvester.log
```

### Python 调试器

```python
# 在代码中添加断点
import pdb; pdb.set_trace()

# 或使用 ipdb (更友好)
import ipdb; ipdb.set_trace()
```

### 常见错误诊断

```bash
# 检查代理连通性
curl -x http://172.25.16.1:7890 https://httpbin.org/ip --connect-timeout 5

# 检查数据库连接
docker-compose -f docker-compose.dev.yml exec db pg_isready -U football_user

# 检查 Redis 连接
docker-compose -f docker-compose.dev.yml exec redis redis-cli ping

# 查看容器资源使用
docker stats football_prediction_dev
```

---

**更新日期**: 2026-03-11

---

# ══════════════════════════════════════════════════════════════════════════════

# V4.47.0-BATTLE 新增特征 (TITAN Battle Features)

# ══════════════════════════════════════════════════════════════════════════════

## TitanFeaturePro 生产级特征计算器

**唯一入口**: `src/ml/feature_engine/titan_feature_pro.py`

### 新增 5 维战斗特征

| 特征名称 | 维度 | 用途 | 计算逻辑 |
|----------|------|------|----------|
| `momentum_home` | 1 | 主队动量评分 | 表现残差加权平均 + Tanh归一化 |
| `momentum_away` | 1 | 客队动量评分 | 表现残差加权平均 + Tanh归一化 |
| `xg_balance_index` | 1 | xG平衡指数 | 1 / (abs(home_xg - away_xg) + 0.1) |
| `double_wall_score` | 1 | 双强防守指数 | (home_def + away_def) / 2 / max_rating |
| `scoreless_momentum` | 1 | 低比分动量 | 近期低比分场次占比 |
| **总计** | **5** | | |

### 特征贡献度 (Ablation Study)

| 特征组合 | Accuracy | Draw Recall | vs 基准 |
|----------|----------|-------------|--------|
| 仅基础特征 (11维) | 54.40% | 33.04% | 基准 |
| 基础 + 动量 (13维) | 58.33% | 41.96% | +3.93% |
| **全部特征 (16维)** | **59.03%** | **44.64%** | **+4.63%** |

### 模型性能指标

| 指标 | 单次测试 | 10折期望 | 判断 |
|------|----------|----------|------|
| Accuracy | 59.03% | 61.9% ± 3.5% | ✅ 稳定 |
| Draw Recall | 44.64% | 44.9% ± 7.7% | ✅ 提升 |
| 高置信度准确率 (>=90%) | 100% | - | ✅ 可靠 |

### 调用规范

```python
from src.ml.feature_engine.titan_feature_pro import TitanFeaturePro

pro = TitanFeaturePro()
result = pro.calculate_all_features(
    home_recent_matches=[{"result": "W", "expected_score": 0.6}, ...],
    away_recent_matches=[{"result": "L", "expected_score": 0.4}, ...],
    home_xg_l5=[1.2, 1.0, 1.5, 1.1, 1.3],
    away_xg_l5=[0.8, 1.0, 0.9, 1.1, 1.0],
    home_def_rating=7.5,
    away_def_rating=6.8,
)

if result.success:
    features = result.features  # Dict[str, float]
```

### 高置信度保守性

模型在高置信度 (>90%) 预测时具备 **100% 准确率**：

- 保守估计：实际准确率始终高于预期
- 适合实战投注：高置信度预测更为可靠

---
