# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**系统版本**: V4.21-stable | **最后更新**: 2026-03-07

> ⚠️ **版本说明**: 本项目采用**语义化独立版本管理**，不同组件独立迭代：
> - 📄 **文档版本** (CLAUDE.md): V4.21 - 反映最新架构重组
> - 📦 **NPM 包版本** (package.json): V178 - 反映 API 稳定性
> - 🚀 **收割引擎** (ProductionHarvester.js): V186 - 反映引擎迭代
> - ⚙️ **配置模块** (factory_config.js): V178 - 反映配置成熟度
>
> ⚠️ **过时命令**: README.md 中部分命令已过时。以下脚本**不可用**：
> - `npm run harvest/watch/report/diagnose/status` - 已删除
> - `npm run harvest:quick/harvest:limit/extract-urls/scheduler` - 已删除
> - `npm run test:v171/test:python` - 已删除
>
> **可用脚本**请参考下方「常用命令」章节或直接查看 `package.json`。
>
> 📋 **环境配置**: 复制 `.env.example` 为 `.env` 并填入 `DB_PASSWORD`。

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
# ✅ 正确
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/run_production.js

# ❌ 错误
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

## Claude Skills 约束体系

本项目采用**受约束的 AI 开发模式**，通过 Claude Skills 约束体系确保代码质量。

### 核心 Skills

| Skill | 用途 | 约束等级 |
|-------|------|----------|
| `minimal_change` | 最小修改策略，防止过度重构 | 🔴 RED |
| `architecture_boundary` | 架构边界保护，维护层次结构 | 🔴 RED |
| `test_guard` | 测试质量保护 | 🔴 RED |
| `context_lock` | 核心模块冻结，保护系统基石 | 🔴 RED |
| `change_impact` | 变更影响分析 | 🔴 RED |

### 可用 Skills (`.claude/skills/`)

| Skill | 触发关键词 |
|-------|-----------|
| `football-prediction` | "预测比赛", "XGBoost", "比赛分析" |
| `data-collection` | "收集数据", "FotMob", "API" |
| `report-generation` | "生成报告", "PDF", "可视化" |
| `code-quality` | "检查代码", "lint", "质量" |
| `performance-monitoring` | "监控", "性能", "Prometheus" |
| `deployment-management` | "部署", "Docker", "生产" |
| `database-operations` | "数据库", "PostgreSQL", "查询" |
| `machine-learning-engineering` | "ML", "特征工程", "模型训练" |

### MCP 服务器

| MCP 服务器 | 权限 | 允许行为 |
|-----------|------|----------|
| **postgres** | READ-ONLY | SELECT / DESCRIBE / EXPLAIN |
| **filesystem** | PROJECT ROOT | 读 / diff / 受控写 |
| **git** | READ-ONLY | commit history / diff / blame |
| **pytest** | RESTRICTED | 运行 pytest / 列出测试 |

> ⚠️ **MCP 不拥有生产环境控制权**，禁止任何不可逆或高风险自动化操作。

---

# ═══════════════════════════════════════════════════════════════════════════════
# 常用命令 (Commands)
# ═══════════════════════════════════════════════════════════════════════════════

## 可用 npm 脚本 (package.json)

| 命令 | 描述 |
|------|------|
| `npm start` | 生产收割器 (`scripts/ops/run_production.js`) |
| `npm run seed` | 赛程种子数据 |
| `npm run seed:all` | 全量赛程种子 |
| `npm run smelt` | 特征熔炼 |
| `npm test` | 运行所有 Node.js 单元测试 |
| `npm run test:unit` | 单元测试 |
| `npm run test:l1` | L1 模块测试 (FixtureSeeder) |
| `npm run test:coverage` | 带覆盖率测试 |
| `npm run lint` | ESLint 检查 |
| `npm run lint:fix` | ESLint 自动修复 |
| `npm run format` | Prettier 格式化 |
| `npm run lint:python` | Ruff Python 检查 |
| `npm run qa` | 全量检查 (lint + test:unit) |

## 开发环境

```bash
# === 启动/停止 ===
docker-compose -f docker-compose.dev.yml up -d              # 启动开发容器 (db + redis + dev)
docker-compose -f docker-compose.dev.yml exec dev bash      # 进入开发容器 Shell
docker-compose -f docker-compose.dev.yml down               # 停止开发环境
make dev-up                                                 # Makefile 快捷方式
make dev-down                                               # 停止开发环境
make dev-shell                                              # 进入开发容器

# === 核心收割 (scripts/ops/) ===
docker-compose -f docker-compose.dev.yml exec dev npm start                # 生产收割器
docker-compose -f docker-compose.dev.yml exec dev npm run seed             # 赛程种子数据
docker-compose -f docker-compose.dev.yml exec dev npm run seed:all         # 全量赛程种子
docker-compose -f docker-compose.dev.yml exec dev npm run smelt            # 特征熔炼

# 直接调用脚本 (支持参数)
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/run_production.js --limit 100
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/run_production.js --dry-run

# === 维护脚本 (scripts/maintenance/) ===
docker-compose -f docker-compose.dev.yml exec dev python scripts/maintenance/check_system_health.py    # 系统健康检查
docker-compose -f docker-compose.dev.yml exec dev python scripts/maintenance/fotmob_historical_backfill.py  # 历史数据回填
docker-compose -f docker-compose.dev.yml exec dev python scripts/maintenance/clean_corrupt_l2.py  # 清理损坏的 L2 数据
docker-compose -f docker-compose.dev.yml exec dev python scripts/maintenance/fix_zombie_matches.py  # 修复僵尸比赛
docker-compose -f docker-compose.dev.yml exec dev python scripts/maintenance/database_detox.py  # 数据库清理
docker-compose -f docker-compose.dev.yml exec dev python scripts/maintenance/v190_odds_recovery.py  # V190 赔率恢复
docker-compose -f docker-compose.dev.yml exec dev python scripts/maintenance/reprocess_from_local.py  # 从本地数据重处理
docker-compose -f docker-compose.dev.yml exec dev python scripts/maintenance/reset_l2_collection.py  # 重置 L2 采集状态
docker-compose -f docker-compose.dev.yml exec dev python scripts/maintenance/reprocess_failed_matches.py  # 重处理失败比赛
docker-compose -f docker-compose.dev.yml exec dev python scripts/maintenance/monitor_war_room.py  # 战情室监控

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
docker-compose -f docker-compose.dev.yml exec dev npm run test:l1           # L1 模块测试
docker-compose -f docker-compose.dev.yml exec dev npm run test:coverage     # 带覆盖率测试

# Python 测试
docker-compose -f docker-compose.dev.yml exec dev pytest tests/ -v          # 运行所有 Python 测试
docker-compose -f docker-compose.dev.yml exec dev pytest tests/ml/ -v       # ML 模块测试
docker-compose -f docker-compose.dev.yml exec dev pytest tests/test_v171_cpp_bridge.py -v  # C++ 桥接测试
docker-compose -f docker-compose.dev.yml exec dev pytest tests/ml/test_backtest_engine.py -v -s  # 带调试输出
docker-compose -f docker-compose.dev.yml exec dev pytest tests/ -k "关键词" -v  # 按关键词筛选测试

# === Makefile 命令 ===
make help                                                  # 显示所有可用命令
make lint                                                  # 运行 Lint 检查 (ruff/flake8)
make format                                                # 格式化代码 (ruff/black)
make clean                                                 # 清理垃圾文件
make clean-all                                             # 完全清理 (包括日志)
make verify                                                # 完整验证 (lint + test + security)
make db-shell                                              # 进入数据库 Shell
make db-backup                                             # 备份数据库
make health                                                # 检查服务健康状态

# === 数据库 ===
docker-compose -f docker-compose.dev.yml exec dev alembic -c src/database/migrations/alembic.ini upgrade head  # 应用所有迁移
docker-compose -f docker-compose.dev.yml exec dev alembic -c src/database/migrations/alembic.ini revision --autogenerate -m "描述"  # 生成新迁移
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

---

# ═══════════════════════════════════════════════════════════════════════════════
# 系统架构 (Architecture)
# ═══════════════════════════════════════════════════════════════════════════════

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
| **L2** | OddsPortal | 赔率数据（开盘/收盘、1X2、亚洲盘） | `raw_match_data` |
| **L3** | 特征工程 | 12061 维特征向量 | `l3_features` |

**系统核心资产地图 (V191.2 唯一化审计)：**
| 功能模块 | 唯一指定文件 | 入口脚本 |
|----------|-------------|---------|
| **L1 Discovery** | `src/infrastructure/FixtureSeeder.js` | `scripts/ops/seed_fixtures.js` |
| **L2 Harvest** | `src/infrastructure/harvesters/ProductionHarvester.js` (V186) | `scripts/ops/run_production.js` |
| **L3 Smelt** | `src/feature_engine/smelter/FeatureSmelter.js` | `scripts/ops/smelt_all.js` |
| **身份管理** | `src/infrastructure/network/SessionManager.js` | - |
| **代理池** | `src/infrastructure/network/NetworkShield.js` | - |
| **C++ 桥接** | `src/utils/cpp_bridge_radar.py` | - |

> ⚠️ **已废弃组件 (V4.21 最终清理)**:
> - `QuantHarvester.js`, `IdentityResolver.js` - V191.2 删除
> - `src/collectors/` 整个目录 - V191.5 删除 (废弃的 Python 采集系统)
> - `src/ops/` 整个目录 - V191.5 删除 (废弃的 Python ops 脚本)
> - `src/infrastructure/engines/match_engine/` - V191.5 删除
> - `src/core/self_healing.py` - V191.5 删除
> - **V4.21 死代码清理** (2026-03-07):
>   - `src/core/behavior_simulator.py`, `ghost_protocol.py` - Ghost Protocol 残留
>   - `src/core/browser-pool.js`, `fingerprint_manager.py` - 废弃浏览器组件
>   - `src/core/scheduler/*`, `strategy_factory.py` - 废弃调度系统
>   - `src/core/semantic_refiner.py` - 废弃语义处理
>   - `src/core/ui/*` - 废弃 Dashboard
>   - `src/core/utils/*` - 废弃工具类
>   - `src/infrastructure/network/core/*` - 已迁移至 `src/core/network/`

> 📌 **`src/core/` 定位 (V4.21 重新定义)**:
> `src/core/` 现在仅作为**底层原子组件**目录，包含：
> - `browser/` - 浏览器管理原子组件
> - `ipc/` - 进程间通信原子组件
> - `network/` - 网络原子组件 (熔断器、会话管理、代理注册)
> - `process/` - 进程管理原子组件
> - 独立工具模块: `circuit_breaker.py`, `exceptions.py`, `graceful_shutdown.py`, 等
>
> **业务逻辑层**: `src/infrastructure/` | **ML 层**: `src/ml/` | **特征层**: `src/feature_engine/`

**关键目录：**
```
src/
├── core/                      # 核心基础设施 (IPC, 进程管理, 浏览器管理)
├── parsers/                   # 数据解析器 (FotMob, NextData)
├── models/                    # 数据库 Query 封装
├── feature_engine/            # Node.js 特征引擎 (GoldenFeature, EloRating, OddsMovement)
├── infrastructure/            # 基础设施 (QuantHarvester, NetworkShield, FixtureSeeder)
├── ml/                        # 机器学习 (inference, training, features)
│   ├── inference/             # 模型推理 (predictor, model_loader, multi_model_validator)
│   ├── training/              # 模型训练 (v17_engine)
│   ├── features/              # Python 特征提取 (elo, h2h, odds_movement)
│   ├── feature_engine/        # Python 特征引擎 (processors/*)
│   ├── models/                # 模型定义 (xgboost_classifier)
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
| `ProductionHarvester` | L2/L3 数据收割主入口 (V186 企业级) | `src/infrastructure/harvesters/` |
| `FixtureSeeder` | L1 赛程发现与种子 | `src/infrastructure/` |
| `NetworkShield` | 22 节点代理池管理、熔断保护 | `src/infrastructure/network/` |
| `SessionManager` | V179 无人值守身份管理、Cookie 自动注入 | `src/infrastructure/network/` |
| `BridgeRadarEngine` | C++ 模糊匹配桥接 | `src/utils/cpp_bridge_radar.py` |
| `PostgresClient` | 数据库连接池 | `src/infrastructure/database/` |

**多模型共识 (3-Model Consensus):**
| 模型 | 特征维度 | 用途 |
|------|---------|------|
| Model A | 37 | 通用预测 |
| Model B | 6000+ | 联赛专项 |
| Model C | 19 | 赔率模型 |

共识规则: UNANIMOUS (3/3) > MAJORITY (2/3) > SPLIT (无共识)

**ML 推理组件 (`src/ml/inference/`):**
| 文件 | 功能 |
|------|------|
| `predictor.py` | 统一预测接口 |
| `model_loader.py` | XGBoost 模型加载 |
| `model_dispatcher.py` | 模型路由分发 |
| `multi_model_validator.py` | 3 模型共识验证 |
| `cache_manager.py` | 预测结果缓存 |

---

# ═══════════════════════════════════════════════════════════════════════════════
# 配置系统 (Configuration System)
# ═══════════════════════════════════════════════════════════════════════════════

所有配置集中在 `config/factory_config.js`，**严禁在业务代码中硬编码参数**。

| 配置模块 | 说明 |
|----------|------|
| `QUALITY_GATE` | 数据质量门禁 (最小体积、必须路径、错误关键字) |
| `TIMING` | 延时配置 (minDelayMs: 10s, maxDelayMs: 15s) |
| `RETRY` | 重试策略 (最大 3 次、指数退避) |
| `CONCURRENCY` | 并发配置 (maxWorkers: 1, batchSize: 50) |
| `PROXY_CONFIG` | 22 节点代理池 (端口 7890-7911) |
| `CIRCUIT_BREAKER` | 熔断器 (5 次失败触发, 60 秒冷却) |
| `FINGERPRINT` | 浏览器指纹池 (20+ UA、静态指纹) |
| `FOTMOB_COOL_DOWN` | 深度静默模式 (3 次失败触发 30 分钟冷却) |
| `BROWSER` | 浏览器配置 (profilePath, headless, launchArgs) |

```javascript
// 使用示例
const FactoryConfig = require('../../../config/factory_config');
const delay = FactoryConfig.getRandomDelay([FactoryConfig.TIMING.minDelayMs, FactoryConfig.TIMING.maxDelayMs]);
```

---

# ═══════════════════════════════════════════════════════════════════════════════
# 关键规则 (Critical Rules)
# ═══════════════════════════════════════════════════════════════════════════════

### 队名匹配

**必须**使用 `BridgeRadarEngine` 进行 FotMob 到 OddsPortal 的 URL 匹配：

```python
# ✅ 正确方式
from src.utils.cpp_bridge_radar import BridgeRadarEngine
bridge = BridgeRadarEngine()
result = bridge.dynamic_bridge(fotmob_home="Man Utd", fotmob_away="Chelsea", league_name="Premier League")

# ❌ 禁止手动拼接 URL
const url = `https://oddsportal.com/${home}-${away}/`;  # 这会导致匹配失败！
```

### 代理系统 (NetworkShield)

- 22 个代理节点，端口 7890-7911
- 熔断机制：连续 5 次失败触发 60 秒冷却
- Session Stickiness：Worker 与端口一对一绑定
- 配置文件：`config/active_registry.json`

```bash
curl -x http://172.25.16.1:7891 https://httpbin.org/ip  # 测试代理
```

### 身份管理 (SessionManager - V179)

- 自动身份捕获：可见浏览器过 Turnstile
- 身份热加载：Cookie 自动注入到无头浏览器
- 22 节点一对一身份绑定
- 会话存储路径：`/app/data/sessions/session_port_{端口}.json`
- 容器环境无 X Server 时自动跳过可见浏览器刷新

```bash
# 手动身份捕获（宿主机运行，需要显示器）
node scripts/capture_auth.js

# 验证会话有效性
docker-compose -f docker-compose.dev.yml exec dev node -e "
const { SessionManager } = require('./src/infrastructure/network/SessionManager');
const sm = new SessionManager();
sm.validateSession(7890).then(console.log);
"
```

---

# ═══════════════════════════════════════════════════════════════════════════════
# 环境变量 (Environment Variables)
# ═══════════════════════════════════════════════════════════════════════════════

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
| `DISPLAY` | X Server 显示器 (身份捕获用) | 容器内无默认值 |

---

# ═══════════════════════════════════════════════════════════════════════════════
# 故障排查 (Troubleshooting)
# ═══════════════════════════════════════════════════════════════════════════════

| 问题 | 诊断命令 | 解决方案 |
|------|---------|---------|
| **代理熔断** | `curl -x http://172.25.16.1:7891 https://httpbin.org/ip` | `docker-compose -f docker-compose.dev.yml restart dev` |
| **数据库连接** | `docker-compose exec db pg_isready -U football_user` | `docker-compose restart db` |
| **浏览器崩溃** | `ps aux \| grep chromium` | `npx playwright install chromium --force` |
| **数据不一致** | `python scripts/maintenance/check_system_health.py` | 运行 `clean_corrupt_l2.py` |
| **Turnstile 拦截** | 检查 `/app/data/sessions/` 是否有会话文件 | 宿主机运行 `node scripts/capture_auth.js` 手动捕获身份 |
| **会话过期** | 检查 `session_port_*.json` 的 `expiresAt` 字段 | 重新运行身份捕获脚本 |

---

# ═══════════════════════════════════════════════════════════════════════════════
# 代码风格 (Code Style)
# ═══════════════════════════════════════════════════════════════════════════════

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

# ═══════════════════════════════════════════════════════════════════════════════
# 特征引擎 (Feature Engine)
# ═══════════════════════════════════════════════════════════════════════════════

### Node.js 特征引擎 (`src/feature_engine/extractors/*.js`)

| 提取器 | 功能 |
|--------|------|
| `GoldenFeatureExtractor` | 身价/伤病/评分统计 |
| `TacticalMomentumExtractor` | 战术动量/控球走势 |
| `EloRatingExtractor` | Elo 动态评分 |
| `OddsMovementExtractor` | 赔率变动/Steam 信号 |

### Python 特征引擎 (`src/ml/feature_engine/processors/*.py`)

| 处理器 | 功能 |
|--------|------|
| `atomic` | 原子特征 |
| `tactical` | 战术特征 |
| `tactical_cross` | 交叉战术特征 |
| `lineup` / `lineup_value` | 阵容/身价特征 |
| `injury_impact` | 伤病影响 |
| `market_odds` | 市场赔率 |
| `history` | 历史数据 |
| `context` | 上下文特征 |
| `referee` | 裁判特征 |
| `passing_dna` | 传球 DNA |

---

# ═══════════════════════════════════════════════════════════════════════════════
# 关键文件速查 (Key Files Reference)
# ═══════════════════════════════════════════════════════════════════════════════

| 文件 | 用途 | 优先级 |
|------|------|--------|
| `scripts/ops/run_production.js` | 生产收割主入口 | P0 |
| `scripts/ops/seed_fixtures.js` | L1 赛程种子 | P0 |
| `scripts/ops/smelt_all.js` | 特征熔炼 | P0 |
| `scripts/capture_auth.js` | 手动身份捕获 (宿主机运行) | P1 |
| `src/infrastructure/harvesters/ProductionHarvester.js` | L2/L3 收割器 (V186) | P0 |
| `src/infrastructure/FixtureSeeder.js` | L1 发现引擎 | P0 |
| `src/infrastructure/network/NetworkShield.js` | 代理池管理 | P1 |
| `src/infrastructure/network/SessionManager.js` | 身份管理 (V179) | P1 |
| `src/infrastructure/database/PostgresClient.js` | 数据库连接池 | P1 |
| `src/utils/cpp_bridge_radar.py` | C++ 模糊匹配桥接 | P1 |
| `config/factory_config.js` | 工厂级配置中心 | P1 |
| `config/active_registry.json` | 代理注册表 | P2 |
| `src/ml/inference/predictor.py` | ML 预测器 | P1 |
| `src/ml/inference/multi_model_validator.py` | 多模型验证 | P1 |
| `src/ml/backtest/fractional_kelly_backtest.py` | Fractional Kelly 回测 | P2 |

---

# ═══════════════════════════════════════════════════════════════════════════════
# 数据库表结构 (Database Schema)
# ═══════════════════════════════════════════════════════════════════════════════

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

# ═══════════════════════════════════════════════════════════════════════════════
# 单独运行测试 (Running Individual Tests)
# ═══════════════════════════════════════════════════════════════════════════════

```bash
# Node.js 单独测试
docker-compose -f docker-compose.dev.yml exec dev node --test tests/unit/FixtureSeeder.test.js
docker-compose -f docker-compose.dev.yml exec dev node --test tests/unit/SessionManager.test.js  # 身份管理测试

# Python 单独测试
docker-compose -f docker-compose.dev.yml exec dev pytest tests/test_v171_cpp_bridge.py -v

# Python 带调试输出
docker-compose -f docker-compose.dev.yml exec dev pytest tests/ml/test_backtest_engine.py -v -s

# 只运行特定测试函数
docker-compose -f docker-compose.dev.yml exec dev pytest tests/test_parser_integrity.py::test_specific_function -v

# 带覆盖率运行单个文件
docker-compose -f docker-compose.dev.yml exec dev pytest tests/test_v26_integration.py --cov=src/ml/feature_engine --cov-report=term-missing
```

---

# ═══════════════════════════════════════════════════════════════════════════════
# 调试技巧 (Debugging Tips)
# ═══════════════════════════════════════════════════════════════════════════════

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

# ═══════════════════════════════════════════════════════════════════════════════
# 版本历史 (Version History)
# ═══════════════════════════════════════════════════════════════════════════════

## V4.21 CORE RESET (2026-03-07)

### 核心重构
**死代码清理**: 删除 6862 行遗留代码，重新定义 `src/core/` 边界

| 删除类型 | 文件数 | 说明 |
|---------|-------|------|
| Ghost Protocol 残留 | 2 | `behavior_simulator.py`, `ghost_protocol.py` |
| 废弃浏览器组件 | 2 | `browser-pool.js`, `fingerprint_manager.py` |
| 废弃调度系统 | 4 | `scheduler/*`, `strategy_factory.py` |
| 废弃 UI/Utils | 6 | `ui/*`, `utils/*`, `semantic_refiner.py` |
| 重复网络组件 | 6 | `infrastructure/network/core/*` → `core/network/` |

### `src/core/` 新边界
```
src/core/
├── browser/      # 浏览器原子组件
├── ipc/          # IPC 原子组件
├── network/      # 网络原子组件 (统一位置)
├── process/      # 进程原子组件
└── *.py/*.js     # 独立工具模块
```

**架构原则**: `src/core/` = 底层原子组件，不含业务逻辑

---

## V4.5 HONEST BACKTEST (2026-03-07)

### 栬ll心发现
**数据泄露审计**: 发现修复前 93.1% 准确率完全来自赛后特征泄露

| 指标 | 修复前 (虚假) | 修复后 (真实) |
|------|-------------|-------------|
| 总准确率 | 93.1% | 40.4% |
| 高置信度准确率 | 100% | 51.9% |
| Walk-Forward 准确率 | - | 48.7% |

**核心工具**:
- `scripts/ops/backtest_v45_pit.py` - 时序防火墙回测
- `scripts/ops/walk_forward_backtest.py` - 步进式验证引擎

**P0 下一步**: 实现 OddsPortal 接口获取开盘赔率数据

---

## V186 ENTERPRISE (2026-03-04)

### 核心功能
| 模块 | 功能 | 位置 |
|------|------|------|
| `ProductionHarvester` | L2/L3 数据收割主入口 | `src/infrastructure/harvesters/ProductionHarvester.js` |
| `_injectStealthScripts` | WebGL/硬件指纹模拟，绕过 403 反爬 | `ProductionHarvester.js:1056` |
| `_harvestWithRetry` | 弹性重试逻辑，自动端口避障 | `ProductionHarvester.js:735` |
| `SessionManager` | V179 无人值守身份管理 | `src/infrastructure/network/SessionManager.js` |
| `FeatureSmelter` | L3 特征熔炼引擎 | `src/feature_engine/smelter/FeatureSmelter.js` |
| `Logger` | V186 企业级日志系统 (Winston + 日志轮转) | `src/infrastructure/utils/Logger.js` |

### 数据流程
```
L1 Discovery (FotMob API)
    ↓
L2 Harvest (ProductionHarvester + 22 节点代理池)
    ↓ raw_match_data
L3 Smelt (FeatureSmelter + 4 Extractors)
    ↓ l3_features
ML Prediction (XGBoost 3-Model Consensus)
```

### V186 企业级加固
- **工业级日志系统**: Winston + 日志轮转 + JSON 格式
- **错误分类**: FATAL (程序退出) vs RETRYABLE (自动重试)
- **优雅停机**: SIGINT/SIGTERM 信号处理 + 安全关闭
- **完整 JSDoc**: 所有方法添加文档注释

---

## V179-V186 版本演进| 版本 | 里程碑 | 核心变更 |
|------|--------|----------|
| V179 | 无人值守 | SessionManager 自动身份捕获 |
| V180 | 深度隐身 | WebGL/硬件指纹模拟 |
| V181 | IRON-SHIELD | 弹性重试 + 端口避障 |
| V182 | L3 熔炼 | FeatureSmelter 4 提取器 |
| V183 | 数据恢复 | xG 回填 + actual_result 计算 |
| V184 | 数据洞察 | 562 场深度分析 + 投资建议 |
| V185 | 质量加固 | 日志精简 + 错误分类 |
| V186 | 企业级 | Winston 日志 + 优雅停机 + JSDoc |
| V4.5 | 诚实回测 | 时序防火墙 + Walk-Forward 验证 + 泄露审计 |

---

**更新日期**: 2026-03-07
