# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**当前版本**: V175.0.0-stable | **最后更新**: 2026-03-02

> ⚠️ **重要**: `npm run harvest/watch/report/diagnose` 不可用（脚本已删除）。可用脚本见 `scripts/ops/` 目录。

---

# ═══════════════════════════════════════════════════════════════════════════════
# ★★★ 大厂工程铁律 (ENGINEERING CONSTITUTION) ★★★
# ═══════════════════════════════════════════════════════════════════════════════

> **宪法级文档**：以下 5 条铁律具有最高优先级，任何操作都必须遵守。违反任何一条将视为严重工程事故。

---

## ★ 铁律 1：沟通协议

| 规则 | 说明 |
|------|------|
| **强制语言** | 所有回复、注释、日志输出必须使用【中文】 |
| **代码层面** | 变量名、函数名可使用英文；注释和日志必须是中文 |

---

## ★ 铁律 2：容器化优先

| 规则 | 说明 |
|------|------|
| **运行环境** | 禁止在宿主机直接运行 Node/Python。所有指令必须封装在 Docker 容器内 |
| **路径规范** | 严禁使用宿主机绝对路径。必须使用容器映射路径（如 `/app/data/`） |
| **持久化** | 日志写入 `/app/logs/`，数据写入 `/app/data/` |

```bash
# ✅ 正确：在容器内执行
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/run_production.js

# ❌ 错误：在宿主机直接执行
node scripts/ops/run_production.js
```

---

## ★ 铁律 3：分支与版本隔离

| 规则 | 说明 |
|------|------|
| **main 保护** | 严禁在 `main` 分支进行任何开发操作 |
| **分支命名** | `feat/<功能>` / `lab/<实验>` / `fix/<修复>` |
| **提交规范** | 消息必须遵循 Angular 规范（feat/fix/refactor/test/chore/docs） |

```bash
git branch --show-current  # 开始工作前必须确认分支正确
```

---

## ★ 铁律 4：数据完整性

| 规则 | 说明 |
|------|------|
| **零模拟原则** | 严禁使用 `Math.random()` 或 Synthetic Data 伪造数据 |
| **真实优先** | 没有抓取到真实数据时，系统应直接报错并中止 |

```python
# ✅ 数据缺失时报错
if not real_data:
    raise DataNotFetchedError("无法获取真实数据，任务中止")

# ❌ 禁止用随机数伪造数据
xg_home = random.uniform(0.5, 2.5)  # 绝对禁止！
```

---

## ★ 铁律 5：幂等性要求

| 规则 | 说明 |
|------|------|
| **可重复执行** | 所有回填和收割任务必须支持重复执行 |
| **去重逻辑** | 数据库已存在相同 `match_id` 且数据完整时，应跳过或安全更新 |

```python
# ✅ 先检查再写入
existing = db.query("SELECT * FROM matches WHERE match_id = ?", match_id)
if existing and existing.is_complete():
    logger.info(f"比赛 {match_id} 已存在且完整，跳过")
    return
```

---

# ═══════════════════════════════════════════════════════════════════════════════
# 常用命令 (Commands)
# ═══════════════════════════════════════════════════════════════════════════════

```bash
# === 开发环境 ===
docker-compose -f docker-compose.dev.yml up -d              # 启动开发容器 (db + redis + dev)
docker-compose -f docker-compose.dev.yml exec dev bash      # 进入开发容器 Shell
make dev-up                                                 # 启动开发环境 (Makefile 快捷方式)

# === 核心收割 (scripts/ops/) ===
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/run_production.js   # 生产收割器
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/seed_fixtures.js    # 赛程种子数据
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/smelt_all.js        # 特征熔炼

# === 维护脚本 (scripts/maintenance/) ===
docker-compose -f docker-compose.dev.yml exec dev python scripts/maintenance/check_system_health.py
docker-compose -f docker-compose.dev.yml exec dev python scripts/maintenance/fotmob_historical_backfill.py
docker-compose -f docker-compose.dev.yml exec dev python scripts/maintenance/clean_corrupt_l2.py

# === 代码质量 ===
docker-compose -f docker-compose.dev.yml exec dev npm run lint              # ESLint 检查
docker-compose -f docker-compose.dev.yml exec dev npm run lint:fix          # ESLint 自动修复
docker-compose -f docker-compose.dev.yml exec dev npm run format            # Prettier 格式化
docker-compose -f docker-compose.dev.yml exec dev npm run qa                # 全量检查

# === 测试 ===
# Node.js 测试
docker-compose -f docker-compose.dev.yml exec dev npm test                  # 运行所有 Node.js 单元测试
docker-compose -f docker-compose.dev.yml exec dev node --test tests/unit/parser.test.js  # 单个测试

# Python 测试
docker-compose -f docker-compose.dev.yml exec dev pytest tests/ -v          # 运行所有 Python 测试
docker-compose -f docker-compose.dev.yml exec dev pytest tests/ml/ -v       # ML 模块测试

# === 数据库 ===
docker-compose -f docker-compose.dev.yml exec dev alembic upgrade head      # 应用所有迁移
docker-compose -f docker-compose.dev.yml exec dev alembic revision --autogenerate -m "描述"  # 生成新迁移
docker-compose exec db psql -U football_user -d football_db                  # 进入 PostgreSQL Shell

# === 依赖安装 (容器内) ===
docker-compose -f docker-compose.dev.yml exec dev npm install               # 安装 Node.js 依赖
docker-compose -f docker-compose.dev.yml exec dev pip install -r requirements.txt  # 安装 Python 依赖
docker-compose -f docker-compose.dev.yml exec dev npx playwright install chromium  # 安装浏览器
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
| **L2** | OddsPortal | 赔率数据（开盘/收盘、1X2、亚洲盘） | `l2_match_data` |
| **L3** | 特征工程 | 12061 维特征向量 | `l3_features` |

**关键目录：**
```
src/
├── core/                      # 核心基础设施 (IPC, 进程管理, 浏览器管理)
├── parsers/                   # 数据解析器 (FotMob, NextData)
├── models/                    # 数据库 Query 封装
├── feature_engine/            # 特征引擎 (GoldenFeature, EloRating, OddsMovement)
├── infrastructure/            # 基础设施 (QuantHarvester, NetworkShield, FixtureSeeder)
├── ml/                        # 机器学习 (inference, training)
└── utils/                     # 工具函数 (cpp_bridge_radar, team_alias)

scripts/
├── ops/                       # 运维脚本 (run_production, seed_fixtures, smelt_all)
└── maintenance/               # 维护工具 (check_system_health, fotmob_historical_backfill)
```

**多模型共识 (3-Model Consensus):**
| 模型 | 特征维度 | 用途 |
|------|---------|------|
| Model A | 37 | 通用预测 |
| Model B | 6000+ | 联赛专项 |
| Model C | 19 | 赔率模型 |

共识规则: UNANIMOUS (3/3) > MAJORITY (2/3) > SPLIT (无共识)

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
- 熔断机制：连续失败触发冷却
- 配置文件：`config/active_registry.json`

```bash
curl -x http://172.25.16.1:7891 https://httpbin.org/ip  # 测试代理
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

| 提取器 | 功能 | 位置 |
|--------|------|------|
| `GoldenFeatureExtractor` | 身价/伤病/评分统计 | `src/feature_engine/extractors/` |
| `TacticalMomentumExtractor` | 战术动量/控球走势 | `src/feature_engine/extractors/` |
| `EloRatingExtractor` | Elo 动态评分 | `src/feature_engine/extractors/` |
| `OddsMovementExtractor` | 赔率变动/Steam 信号 | `src/feature_engine/extractors/` |
