# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**当前版本**: V175.0.0 | **最后更新**: 2026-03-01

> 📖 **相关文档**: [README.md](./README.md) 包含项目概述和完整命令列表。

---

# ═══════════════════════════════════════════════════════════════════════════════
# ★★★ 大厂工程铁律 (ENGINEERING CONSTITUTION) ★★★
# ═══════════════════════════════════════════════════════════════════════════════

> ⚠️ **宪法级文档**：以下 5 条铁律具有最高优先级，任何操作都必须遵守。
>
> **无论本文件其他内容如何修改，以下铁律必须永久保留在文件最顶部，不可删除、降级或弱化。**
>
> 违反任何一条将视为严重工程事故。

---

## ★ 铁律 1：沟通协议 (Communication Protocol)

| 规则 | 说明 |
|------|------|
| **强制语言** | 所有回复、注释、日志输出必须使用【中文】 |
| **严禁切换** | 禁止私自切换到英文或其他语言 |
| **代码层面** | 变量名、函数名可使用英文；注释和日志必须是中文 |

---

## ★ 铁律 2：容器化优先 (Container-First Mindset)

| 规则 | 说明 |
|------|------|
| **运行环境** | 禁止在宿主机直接运行 Node/Python。所有指令必须封装在 Docker 容器内 |
| **路径规范** | 严禁使用宿主机绝对路径。必须使用容器映射路径（如 `/app/data/`） |
| **权限管理** | I/O 操作必须通过 Docker Volume 解决，严禁往 `/tmp` 等非持久化目录写生产数据 |
| **持久化** | 日志写入 `/app/logs/`，数据写入 `/app/data/`，通过 Volume 映射到宿主机 |

**正确示例：**
```bash
# ✅ 在容器内执行
docker-compose -f docker-compose.dev.yml exec dev npm run harvest
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/backfill.py
```

**错误示例：**
```bash
# ❌ 在宿主机直接执行
npm run harvest
python scripts/ops/backfill.py
```

---

## ★ 铁律 3：分支与版本隔离 (Branching Strategy)

| 规则 | 说明 |
|------|------|
| **main 保护** | 严禁在 `main` 分支进行任何开发操作 |
| **新特性分支** | 命名格式：`feat/<功能描述>` |
| **实验研究分支** | 命名格式：`lab/<实验描述>` |
| **紧急修复分支** | 命名格式：`fix/<问题描述>` |
| **原子提交** | 每次 Commit 必须是一个完整的功能闭环 |
| **提交规范** | 消息必须遵循 Angular 规范（feat/fix/refactor/test/chore/docs） |

**分支检查命令：**
```bash
git branch --show-current  # 开始工作前必须确认分支正确
```

---

## ★ 铁律 4：数据完整性 (Data Integrity)

| 规则 | 说明 |
|------|------|
| **零模拟原则** | 严禁使用 `Math.random()` 或 Synthetic Data 伪造数据 |
| **真实优先** | 没有抓取到真实网页数据时，系统应直接报错并中止 |
| **拒绝假数据** | 绝不允许用模拟数据应付，宁可失败也不要虚假成功 |
| **测试数据隔离** | 测试数据必须明确标注来源，不得混淆生产环境 |

**正确行为：**
```python
# ✅ 数据缺失时报错
if not real_data:
    raise DataNotFetchedError("无法获取真实数据，任务中止")
```

**错误行为：**
```python
# ❌ 用随机数伪造数据
xg_home = random.uniform(0.5, 2.5)  # 绝对禁止！
```

---

## ★ 铁律 5：幂等性要求 (Idempotency)

| 规则 | 说明 |
|------|------|
| **可重复执行** | 所有回填和收割任务必须支持重复执行 |
| **去重逻辑** | 数据库已存在相同 `match_id` 且数据完整时，应跳过或安全更新 |
| **无副作用** | 重复执行不应产生冗余数据或覆盖正确数据 |
| **状态追踪** | 记录执行状态，支持断点续传 |

**幂等性检查：**
```python
# ✅ 先检查再写入
existing = db.query("SELECT * FROM matches WHERE match_id = ?", match_id)
if existing and existing.is_complete():
    logger.info(f"比赛 {match_id} 已存在且完整，跳过")
    return
```

---

# ═══════════════════════════════════════════════════════════════════════════════
# 快速收割三部曲 (Quick Start)
# ═══════════════════════════════════════════════════════════════════════════════

> **3 步完成从数据采集到预测输出的完整闭环**

### 📍 Step 1: 目标锁定 (URL 提取)
```bash
docker-compose -f docker-compose.dev.yml exec dev npm run extract-urls
# 提取未来比赛的 OddsPortal URL Hash
# 输出示例: ✅ Liverpool vs West Ham → KbUrxW1T
```

### 📍 Step 2: 全息收割 (数据采集)
```bash
docker-compose -f docker-compose.dev.yml exec dev npm run harvest           # 批量收割 (50 场)
docker-compose -f docker-compose.dev.yml exec dev npm run harvest:limit 10  # 限制收割 10 场
```
**收割内容:**
- L2 (FotMob): xG, 控球率, 射门, 球员评分
- L3 (OddsPortal): 开盘赔率, 即时赔率, 变动轨迹

### 📍 Step 3: 战果验收 (预测查看)
```bash
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/check_daily_bets.py
# 或查询数据库:
docker-compose exec db psql -U football_user -d football_db \
  -c "SELECT * FROM predictions WHERE final_confidence > 0.65"
```

### 🏆 SSR 信号阈值
- **SSR (Super Strong Recommendation)**: 置信度 ≥ 80% + 3 模型一致
- **黄金名单**: 置信度 > 65% 的预测

---

# ═══════════════════════════════════════════════════════════════════════════════
# 命令参考 (Commands)
# ═══════════════════════════════════════════════════════════════════════════════

```bash
# === 开发环境 ===
docker-compose -f docker-compose.dev.yml up -d              # 启动开发容器
docker-compose -f docker-compose.dev.yml exec dev bash      # 进入开发容器 Shell
make dev-up                                                 # 启动开发环境 (Makefile 快捷方式)

# === 核心收割 (容器内执行) ===
docker-compose -f docker-compose.dev.yml exec dev npm run harvest           # 批量收割 (50 场)
docker-compose -f docker-compose.dev.yml exec dev npm run harvest:quick     # 快速收割测试
docker-compose -f docker-compose.dev.yml exec dev npm run harvest:limit 10  # 限制收割 10 场
docker-compose -f docker-compose.dev.yml exec dev npm run scheduler         # 启动无人值守调度器
docker-compose -f docker-compose.dev.yml exec dev npm run extract-urls      # 提取真实 OddsPortal URL Hash

# === V174 装甲群收割器 (生产级) ===
docker-compose -f docker-compose.dev.yml exec dev npm run harvest           # 装甲群收割 (Master-Worker 模式)
docker-compose -f docker-compose.dev.yml exec -e MAX_WORKERS=3 dev npm run harvest  # 指定 Worker 数量
docker-compose -f docker-compose.dev.yml exec -e MIN_DELAY_MS=8000 -e MAX_DELAY_MS=15000 dev npm run harvest  # 自定义延时

# === 监控与诊断 ===
docker-compose -f docker-compose.dev.yml exec dev npm run watch     # 启动中央监控大屏
docker-compose -f docker-compose.dev.yml exec dev npm run report    # 生成资产报告
docker-compose -f docker-compose.dev.yml exec dev npm run diagnose  # 运行诊断实验

# === 历史回填 (Backfill) ===
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/check_db_consistency.py      # 检查数据一致性

# === 代码质量 ===
docker-compose -f docker-compose.dev.yml exec dev npm run lint              # ESLint 检查
docker-compose -f docker-compose.dev.yml exec dev npm run lint:fix          # ESLint 自动修复
docker-compose -f docker-compose.dev.yml exec dev npm run format            # Prettier 格式化
docker-compose -f docker-compose.dev.yml exec dev npm run lint:python       # Ruff Python 检查
docker-compose -f docker-compose.dev.yml exec dev npm run qa                # 全量检查 (lint + python)
make lint / make format / make verify             # Makefile 快捷方式

# === 测试 ===
# ─────────────────────────────────────────────────────────────────────────────
# Node.js 测试 (使用内置 `node --test`)
# ─────────────────────────────────────────────────────────────────────────────
docker-compose -f docker-compose.dev.yml exec dev npm test                        # 运行所有 Node.js 单元测试
docker-compose -f docker-compose.dev.yml exec dev npm run test:unit               # 同上
docker-compose -f docker-compose.dev.yml exec dev npm run test:integration        # 运行集成测试
docker-compose -f docker-compose.dev.yml exec dev npm run test:coverage           # 带覆盖率报告

# 单个 Node.js 测试文件
docker-compose -f docker-compose.dev.yml exec dev node --test tests/unit/parser.test.js
docker-compose -f docker-compose.dev.yml exec dev node --test tests/core/browser/BrowserManager.test.js

# ─────────────────────────────────────────────────────────────────────────────
# Python 测试 (使用 pytest)
# ─────────────────────────────────────────────────────────────────────────────
docker-compose -f docker-compose.dev.yml exec dev pytest tests/ -v                # 运行所有 Python 测试
docker-compose -f docker-compose.dev.yml exec dev pytest tests/ml/ -v             # ML 模块测试
docker-compose -f docker-compose.dev.yml exec dev pytest tests/parsers/ -v        # 解析器测试
docker-compose -f docker-compose.dev.yml exec dev pytest tests/models/ -v         # 数据库模型测试
docker-compose -f docker-compose.dev.yml exec dev pytest -k "关键词" -v           # 按关键词过滤

# 单个 Python 测试
docker-compose -f docker-compose.dev.yml exec dev pytest tests/test_foo.py::TestClass::test_method -v
docker-compose -f docker-compose.dev.yml exec dev pytest -x --pdb                 # 首次失败进入调试器

# ─────────────────────────────────────────────────────────────────────────────
# 测试目录结构
# ─────────────────────────────────────────────────────────────────────────────
# Node.js 测试 (tests/*.test.js):
#   tests/unit/parser.test.js              # 解析器测试
#   tests/core/browser/BrowserManager.test.js  # 浏览器管理测试
#   tests/core/ipc/WorkerMessenger.test.js     # IPC 通信测试
#   tests/models/Queries.test.js               # 数据库查询测试
#
# Python 测试 (tests/*.py):
#   tests/ml/                               # ML 模块测试
#   tests/parsers/                          # 解析器测试
#   tests/models/                           # 数据库模型测试

# === Docker/数据库 ===
# 开发环境 (推荐)
docker-compose -f docker-compose.dev.yml up -d              # 启动开发容器 (db + redis + dev)
docker-compose -f docker-compose.dev.yml exec dev bash       # 进入开发容器 Shell
make dev-up                                                  # 启动开发环境 (Makefile 快捷方式)

# 开发环境服务说明:
# - db: PostgreSQL 15 数据库
# - redis: Redis 缓存 (可选)
# - dev: 开发容器 (Node.js 18+ / Python 3.11+)

# 生产环境
make up                         # 启动核心服务 (db + redis)
make down                       # 停止所有服务
make db-shell                   # 进入 PostgreSQL Shell
make db-backup                  # 备份数据库
make redis-shell                # 进入 Redis CLI
make logs                       # 查看服务日志
make clean                      # 清理垃圾文件和缓存
make verify                     # 运行完整验证 (lint + test + security)

# === 数据库迁移 (Alembic) ===
docker-compose -f docker-compose.dev.yml exec dev alembic upgrade head              # 应用所有迁移
docker-compose -f docker-compose.dev.yml exec dev alembic downgrade -1              # 回滚一个版本
docker-compose -f docker-compose.dev.yml exec dev alembic revision --autogenerate -m "描述"  # 生成新迁移
docker-compose -f docker-compose.dev.yml exec dev alembic current                   # 查看当前版本
docker-compose -f docker-compose.dev.yml exec dev alembic history                   # 查看迁移历史

# === 依赖安装 (容器内) ===
docker-compose -f docker-compose.dev.yml exec dev npm install                     # 安装 Node.js 依赖
docker-compose -f docker-compose.dev.yml exec dev pip install -r requirements.txt # 安装 Python 依赖
docker-compose -f docker-compose.dev.yml exec dev npx playwright install chromium # 安装浏览器
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
     FotMob API         RapidFuzz              Playwright             XGBoost/Scikit
     Match Discovery    URL Hash Extraction    OddsPortal Scraper     Multi-model Consensus
```

**数据层级说明：**
| 层级 | 数据源 | 说明 | 存储表 |
|------|--------|------|--------|
| **L1** | FotMob API | 比赛发现、基础信息（队伍、时间、联赛） | `matches` |
| **L2** | OddsPortal | 赔率数据（开盘/收盘、1X2、亚洲盘） | `l2_match_data` |
| **L3** | 特征工程 | 12061 维特征向量（V25.1/V26 自适应提取） | `l3_features` |

**核心组件：**
- `src/infrastructure/engines/` - 核心收割引擎 (discovery, FotMob, network guardian)
- `src/ml/inference/` - ML 模型，含 `multi_model_validator.py` 多模型共识预测
- `src/utils/cpp_bridge_radar.py` - RapidFuzz 队名匹配（必须用于 URL 生成）
- `config/active_registry.json` - 22 节点代理池配置 (NetworkShield)
- `scripts/ops/` - 运维脚本（收割、调度、回填）

**多模型共识 (3-Model Consensus):**
| 模型 | 特征维度 | 用途 |
|------|---------|------|
| Model A | 37 | 通用预测 |
| Model B | 6000+ | 联赛专项 |
| Model C | 19 | 赔率模型 |

共识规则: UNANIMOUS (3/3一致) > MAJORITY (2/3一致) > SPLIT (无共识)

**关键目录结构：**
```
src/
├── core/                      # [V174] 核心基础设施
│   ├── ipc/                   # IPC 通信 (WorkerMessenger)
│   ├── process/               # 进程管理 (ZombieKiller)
│   └── browser/               # 浏览器管理 (BrowserManager, StealthInjector)
├── parsers/                   # [V174] 数据解析器 (纯函数)
│   └── fotmob/                # FotMob 解析 (NextDataParser, XGExtractor, CloudflareDetector)
├── models/                    # [V174] 数据库 Query 封装
│   ├── MatchQueries.js        # 比赛数据操作
│   └── RawDataQueries.js      # 原始数据操作
├── scripts/                   # [V174] 业务入口
│   └── harvest_worker_entry.js # Worker 进程入口
├── infrastructure/engines/    # 核心收割引擎 (SignalRadar, TrajectoryParser)
│   ├── services/              # 业务服务层 (网络拦截、数据提取)
│   ├── parsers/               # 数据解析层 (轨迹解析、Payout 计算)
│   └── utils/                 # 工具函数 (常量、选择器)
├── ml/                        # 机器学习模块
│   ├── inference/             # 模型推理 (多模型共识)
│   └── training/              # 模型训练 (XGBoost + Platt Scaling)
├── collectors/                # 数据采集器 (FotMob, L3 特征处理器)
├── database/                  # 数据库模型和迁移
│   ├── models.py              # SQLAlchemy 模型
│   └── migrations/            # Alembic 迁移脚本
├── api/                       # FastAPI 接口 (可选启动)
└── utils/                     # 工具函数
    ├── cpp_bridge_radar.py    # RapidFuzz 模糊匹配 (队名 → URL)
    └── team_alias.py          # 队名标准化与别名展开

config/
├── active_registry.json      # 22 节点代理池配置
├── team_mapping.json         # 队名映射表
└── v26_feature_manifest.json # V26 特征清单

scripts/ops/                  # 运维脚本
├── harvest_fleet_master.js   # 装甲群收割主控 (Master-Worker)
├── harvest_worker.js         # 收割 Worker
├── monitor_dashboard.js      # 中央监控大屏
├── asset_report.js           # 资产报告生成
├── diagnostic_experiment.js  # 诊断实验
└── *.py                      # Python 运维工具
```

**V174 核心模块使用示例：**

```javascript
// ═══════════════════════════════════════════════════════════════════════════
// IPC 通信层 (src/core/ipc/)
// ═══════════════════════════════════════════════════════════════════════════

// Master 与 Worker 消息传递
import { WorkerMessenger } from './src/core/ipc/WorkerMessenger.js';
const messenger = new WorkerMessenger(workerId, dbPool);
await messenger.sendHeartbeat({ status: 'running', processed: 10 });
await messenger.sendResult({ matchId: '12345', success: true });

// Master 端消息路由
import { MasterGate } from './src/core/ipc/MasterGate.js';
const masterGate = new MasterGate();
masterGate.on('worker:heartbeat', (data) => console.log(data));

// ═══════════════════════════════════════════════════════════════════════════
// 进程管理层 (src/core/process/)
// ═══════════════════════════════════════════════════════════════════════════

// 僵尸进程清理 - 启动前必须调用
import { ZombieKiller } from './src/core/process/ZombieKiller.js';
await ZombieKiller.preFlightCleanup();  // 清理残留浏览器进程
await ZombieKiller.forceKillBrowser();  // 强制终止浏览器

// ═══════════════════════════════════════════════════════════════════════════
// 浏览器管理层 (src/core/browser/)
// ═══════════════════════════════════════════════════════════════════════════

// 浏览器生命周期管理
import { BrowserManager } from './src/core/browser/BrowserManager.js';
const browserManager = new BrowserManager();
const context = await browserManager.createContext(proxy, fingerprint);
await browserManager.close();  // 确保资源释放

// 反检测脚本注入
import { StealthInjector } from './src/core/browser/StealthInjector.js';
await StealthInjector.inject(page);

// ═══════════════════════════════════════════════════════════════════════════
// 网络层 (src/core/network/)
// ═══════════════════════════════════════════════════════════════════════════

// 代理注册 - Worker 端口映射
import { ProxyRegistry } from './src/core/network/ProxyRegistry.js';
const proxyRegistry = new ProxyRegistry();
const port = proxyRegistry.getPortForWorker(workerId);  // Worker 1 → 7890
const server = proxyRegistry.getServer(port);  // http://172.25.16.1:7890

// ═══════════════════════════════════════════════════════════════════════════
// 调度层 (src/core/scheduler/)
// ═══════════════════════════════════════════════════════════════════════════

// 任务队列管理
import { TaskPool } from './src/core/scheduler/TaskPool.js';
const taskPool = new TaskPool(dbPool);
await taskPool.loadTasks(limit);
const task = taskPool.getNext();
await taskPool.requeue(task);  // 任务重新入队

// ═══════════════════════════════════════════════════════════════════════════
// 解析器层 (src/parsers/fotmob/)
// ═══════════════════════════════════════════════════════════════════════════

// FotMob Next.js 数据提取
import { NextDataParser } from './src/parsers/fotmob/NextDataParser.js';
const matchData = NextDataParser.parse(htmlContent);

// xG 数据提取
import { XGExtractor } from './src/parsers/fotmob/XGExtractor.js';
const xgData = XGExtractor.extract(rawJson);

// Cloudflare 检测
import { CloudflareDetector } from './src/parsers/fotmob/CloudflareDetector.js';
const isBlocked = CloudflareDetector.detect(htmlContent);

// ═══════════════════════════════════════════════════════════════════════════
// 数据库操作层 (src/models/)
// ═══════════════════════════════════════════════════════════════════════════

// 比赛查询
import { MatchQueries } from './src/models/MatchQueries.js';
const pendingMatches = await MatchQueries.findPendingHarvest(dbPool, limit);
await MatchQueries.updateMatchStatus(dbPool, matchId, 'completed');

// 原始数据操作
import { RawDataQueries } from './src/models/RawDataQueries.js';
await RawDataQueries.insertRawData(dbPool, matchId, rawData);
```

---

# ═══════════════════════════════════════════════════════════════════════════════
# 配置系统 (Configuration System)
# ═══════════════════════════════════════════════════════════════════════════════

> **核心配置文件**: `config/factory_config.js` - 所有魔术数字的统一归口管理

**配置模块说明：**
| 模块 | 说明 | 关键参数 |
|------|------|----------|
| `QUALITY_GATE` | 数据质量门禁 | `minSizeBytes` (5000), `errorKeywords` |
| `TIMING` | 延时配置 | `minDelayMs` (10000), `maxDelayMs` (15000) |
| `RETRY` | 重试策略 | `maxAttempts` (3), `backoffBase` (2) |
| `PROXY_CONFIG` | 代理池 | 22 个端口 (7890-7911) |
| `CIRCUIT_BREAKER` | 熔断器 | `threshold` (3), `cooldownMs` (60000) |
| `FOTMOB_COOL_DOWN` | 深度静默 | `durationMs` (30分钟), `triggerThreshold` (3) |
| `FINGERPRINT` | 指纹池 | 20 个 UA, 多视口尺寸 |

**V174 深度静默模式：**
- 连续失败 3 次 → 触发 30 分钟冷却
- 错误类型：`SIZE_TOO_SMALL`, `TURNSTILE_REQUIRED`, `BLOCKED`
- 每个 Worker 独立冷却，不影响其他 Worker

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
```

```javascript
// ❌ 禁止手动拼接 URL
const url = `https://oddsportal.com/${home}-${away}/`;  // 这会导致匹配失败！
```

### 代理系统 (NetworkShield)
- 22 个代理节点，端口 7891-7912
- 熔断机制：连续 2 次失败触发 15 分钟冷却
- 配置文件：`config/active_registry.json`

```bash
# 代理健康检查
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/check_proxy_latency.py
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/reset_proxy_health.py  # 重置代理状态
```

---

# ═══════════════════════════════════════════════════════════════════════════════
# 环境变量 (Environment Variables)
# ═══════════════════════════════════════════════════════════════════════════════

### 必需配置

| 变量 | 说明 | 示例值 |
|------|------|--------|
| `DB_PASSWORD` | 数据库密码 (**必填**) | `your_secure_password` |
| `DB_HOST` | 数据库主机 | `localhost` (本地) / `db` (Docker) |
| `DB_PORT` | 数据库端口 | `5432` |
| `DB_NAME` | 数据库名称 | `football_db` |
| `DB_USER` | 数据库用户 | `football_user` |

### V174 收割器配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MAX_WORKERS` | 1 | Worker 数量 (最稳模式) |
| `MIN_DELAY_MS` | 10000 | 最小延时 (ms) - 潜行模式 |
| `MAX_DELAY_MS` | 15000 | 最大延时 (ms) |
| `MIN_SIZE_BYTES` | 5000 | 质量门禁阈值 (bytes) |
| `MAX_RETRY_ATTEMPTS` | 3 | 最大重试次数 |
| `CIRCUIT_BREAKER_THRESHOLD` | 3 | 熔断阈值 |
| `COOL_DOWN_DURATION_MS` | 1800000 | 深度静默冷却 (30分钟) |
| `DB_POOL_MAX` | 20 | 数据库连接池最大连接数 |

### 代理配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PROXY_HOST` | `172.25.16.1` | 代理服务器地址 |
| `PROXY_PORTS` | `7890-7911` | 代理端口池 (22 个独立 IP) |
| `ENABLE_PROXY_ROTATION` | `false` | 启用代理轮换 |

### 日志与监控

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LOG_LEVEL` | `info` | 日志级别 (debug/info/warn/error) |
| `LOG_TO_FILE` | `false` | 输出到文件 |
| `LOG_DIR` | `/app/logs` | 日志目录 |

### 可选服务

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `REDIS_PORT` | `6379` | Redis 端口 |
| `REDIS_HOST` | `redis` | Redis 主机 |
| `API_PORT` | `8000` | API 服务端口 |
| `API_WORKERS` | `2` | API 工作进程数 |

### 配置示例

```bash
# .env 文件示例
DB_PASSWORD=your_secure_password_here   # 必填
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_db
DB_USER=football_user

LOG_LEVEL=info
ENABLE_PROXY_ROTATION=true
PROXY_HOST=172.25.16.1

REDIS_PORT=6379
API_PORT=8000
API_WORKERS=2
```

```bash
# 自定义收割器配置示例
docker-compose -f docker-compose.dev.yml exec \
  -e MAX_WORKERS=3 \
  -e MIN_DELAY_MS=8000 \
  -e MAX_DELAY_MS=15000 \
  dev npm run harvest
```

---

# ═══════════════════════════════════════════════════════════════════════════════
# 故障排查 (Troubleshooting)
# ═══════════════════════════════════════════════════════════════════════════════

### 快速诊断速查表

| 问题 | 诊断命令 | 解决方案 |
|------|---------|---------|
| **代理熔断** | `curl -x http://172.25.16.1:7891 https://httpbin.org/ip` | `docker-compose -f docker-compose.dev.yml restart dev` |
| **数据库连接** | `docker-compose exec db pg_isready -U football_user` | `docker-compose restart db` |
| **Worker 冷却中** | 查看 `/app/logs/live_status.json` | 等待 30 分钟或重启容器 |
| **浏览器崩溃** | `ps aux \| grep chromium` | `npx playwright install chromium --force` |
| **URL Hash 缺失** | `npm run extract-urls -- --limit 50` | 检查队名映射 |
| **队名匹配失败** | `python scripts/ops/test_cpp_fuzzy_bridge.py` | 更新 `config/team_mapping.json` |
| **数据不一致** | `python scripts/ops/check_db_consistency.py` | 运行 `clean_malformed_l2.py` |
| **容器内存不足** | `docker stats football_prediction_dev` | 调整 `docker-compose.dev.yml` 资源限制 |

### 常见故障详细处理

```bash
# 代理熔断
curl -x http://172.25.16.1:7891 https://httpbin.org/ip  # 测试代理
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/reset_proxy_health.py  # 重置代理状态
docker-compose -f docker-compose.dev.yml restart dev                              # 重置容器

# V174 深度静默模式触发 (连续失败 3 次)
# 症状: Worker 进入 30 分钟冷却，日志显示 "❄️ Worker X 进入深度静默模式"
# 解决方案 1: 等待冷却结束 (30 分钟)
# 解决方案 2: 重启容器重置状态
docker-compose -f docker-compose.dev.yml restart dev

# 数据库连接超时
docker-compose ps db && docker-compose restart db
docker-compose exec db psql -U football_user -d football_db -c "SELECT 1"  # 测试连接

# URL Hash 提取失败
docker-compose -f docker-compose.dev.yml exec dev npm run extract-urls -- --limit 50 --update-db

# 队名匹配失败
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/test_cpp_fuzzy_bridge.py  # 测试模糊匹配
# 检查 config/team_mapping.json 是否有缺失映射

# 数据一致性问题
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/check_db_consistency.py
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/clean_malformed_l2.py  # 清理异常数据

# Playwright 浏览器问题
docker-compose -f docker-compose.dev.yml exec dev npx playwright install chromium --force
```

---

# ═══════════════════════════════════════════════════════════════════════════════
# Docker 环境说明 (Docker Environment)
# ═══════════════════════════════════════════════════════════════════════════════

### Volume 映射

| 容器路径 | 宿主机路径 | 用途 |
|---------|-----------|------|
| `/app` | `.` (项目根目录) | 代码热更新 |
| `/app/data/browser_profile` | `./data/browser_profile` | 浏览器指纹持久化 |
| `/app/logs` | `./logs` | 日志持久化 |
| `/var/lib/postgresql/data` | Docker Volume `postgres_dev_data` | 数据库数据 |
| `/data` | Docker Volume `redis_dev_data` | Redis 数据 |
| `/root/.cache/ms-playwright` | Docker Volume `playwright_cache` | 浏览器缓存 |

### 服务配置

| 服务 | 镜像 | 端口 | 资源限制 |
|------|------|------|----------|
| `dev` | `footballprediction:v170.000-dev` | 8000, 3000, 5678 | 4 CPU / 8G 内存 |
| `db` | `postgres:15-alpine` | 5432 | 2 CPU / 2G 内存 |
| `redis` | `redis:7-alpine` | 6379 | 0.5 CPU / 512M 内存 |

### 容器内环境变量

| 变量 | 值 | 说明 |
|------|-----|------|
| `DOCKER_ENV` | `true` | Docker 环境标识 |
| `DB_HOST` | `host.docker.internal` | 数据库主机 (连接宿主机) |
| `HTTP_PROXY` | `http://172.25.16.1:7890` | 代理配置 (WSL2) |
| `TZ` | `Asia/Shanghai` | 时区设置 |

---

# ═══════════════════════════════════════════════════════════════════════════════
# 调试技巧 (Debugging Tips)
# ═══════════════════════════════════════════════════════════════════════════════

```bash
# === 数据库调试 ===
docker-compose exec db psql -U football_user -d football_db -c "SELECT COUNT(*) FROM matches"
docker-compose exec db psql -U football_user -d football_db -c "SELECT * FROM predictions ORDER BY created_at DESC LIMIT 10"

# === 日志查看 ===
docker-compose -f docker-compose.dev.yml exec dev tail -f logs/harvest.log         # 实时查看收割日志
docker-compose -f docker-compose.dev.yml exec dev cat logs/error.log | tail -100   # 查看最近错误

# === Python 交互式调试 ===
docker-compose -f docker-compose.dev.yml exec dev python -i scripts/ops/debug_match.py  # 交互式调试

# === 网络请求调试 ===
docker-compose -f docker-compose.dev.yml exec dev curl -v https://www.fotmob.com/api/...  # 测试 API 请求
```

---

# ═══════════════════════════════════════════════════════════════════════════════
# 代码风格 (Code Style)
# ═══════════════════════════════════════════════════════════════════════════════

**Python (Ruff + Type Hints):**
```python
def fuzzy_match_teams(
    fotmob_home: str,
    oddsportal_home: str,
    *,
    min_threshold: float = 0.65,
) -> FuzzyMatchResult | None:
    """模糊匹配队名。"""
    ...
```

**Node.js (ESLint + Prettier):**
```javascript
/**
 * @param {string} matchId - 比赛标识符
 * @param {Object} options - 配置选项
 * @returns {Promise<MatchPrediction>}
 */
async function fetchPrediction(matchId, options = {}) { ... }
```

---

# ═══════════════════════════════════════════════════════════════════════════════
# 常见开发场景 (Common Scenarios)
# ═══════════════════════════════════════════════════════════════════════════════

### 场景 1: 修改核心收割引擎
```bash
# 1. 确认当前分支
git branch --show-current

# 2. 修改代码后运行测试
docker-compose -f docker-compose.dev.yml exec dev npm test
docker-compose -f docker-compose.dev.yml exec dev npm run test:python

# 3. 运行代码质量检查
docker-compose -f docker-compose.dev.yml exec dev npm run qa

# 4. 提交前验证
make verify
```

### 场景 2: 添加新的队名映射
```bash
# 1. 编辑映射文件
vim config/team_mapping.json

# 2. 测试模糊匹配
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/test_cpp_fuzzy_bridge.py

# 3. 验证 URL 提取
docker-compose -f docker-compose.dev.yml exec dev npm run extract-urls -- --limit 5
```

### 场景 3: 调试数据库问题
```bash
# 1. 检查数据库状态
docker-compose ps db
docker-compose exec db pg_isready -U football_user

# 2. 查看表结构
docker-compose exec db psql -U football_user -d football_db -c "\d matches"

# 3. 检查数据一致性
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/check_db_consistency.py
```

### 场景 4: 代理问题排查
```bash
# 1. 测试单个代理
curl -x http://172.25.16.1:7891 https://httpbin.org/ip

# 2. 检查代理健康状态
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/check_proxy_latency.py

# 3. 重置代理状态
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/reset_proxy_health.py

# 4. 重启开发容器
docker-compose -f docker-compose.dev.yml restart dev
```
