# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**当前版本**: V173.0.0 (Stable) | **最后更新**: 2026-02-28

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

# === V173 装甲群收割器 (生产级) ===
docker-compose -f docker-compose.dev.yml exec dev npm run harvest           # 装甲群收割 (Master-Worker 模式)
docker-compose -f docker-compose.dev.yml exec -e MAX_WORKERS=3 dev npm run harvest  # 指定 Worker 数量
docker-compose -f docker-compose.dev.yml exec -e MIN_DELAY_MS=8000 -e MAX_DELAY_MS=15000 dev npm run harvest  # 自定义延时

# === 监控与诊断 ===
docker-compose -f docker-compose.dev.yml exec dev npm run watch     # 启动中央监控大屏
docker-compose -f docker-compose.dev.yml exec dev npm run report    # 生成资产报告
docker-compose -f docker-compose.dev.yml exec dev npm run diagnose  # 运行诊断实验

# === 历史回填 (Backfill) ===
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/v171_mass_backfill.js          # 批量回填
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/v171_real_backfill.js          # 真实回填
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/v171_backfill_manager.js       # 回填管理器
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/check_db_consistency.py      # 检查数据一致性

# === 代码质量 ===
docker-compose -f docker-compose.dev.yml exec dev npm run lint              # ESLint 检查
docker-compose -f docker-compose.dev.yml exec dev npm run lint:fix          # ESLint 自动修复
docker-compose -f docker-compose.dev.yml exec dev npm run format            # Prettier 格式化
docker-compose -f docker-compose.dev.yml exec dev npm run lint:python       # Ruff Python 检查
docker-compose -f docker-compose.dev.yml exec dev npm run qa                # 全量检查 (lint + python)
make lint / make format / make verify             # Makefile 快捷方式

# === 测试 ===
docker-compose -f docker-compose.dev.yml exec dev npm test                        # 运行所有 Node.js 测试
docker-compose -f docker-compose.dev.yml exec dev npm run test:python             # Python 测试 (pytest)
docker-compose -f docker-compose.dev.yml exec dev npm run test:v171               # V171 数据库配置测试
docker-compose -f docker-compose.dev.yml exec dev pytest tests/test_foo.py -v     # 运行单个 Python 测试
docker-compose -f docker-compose.dev.yml exec dev npm run test:coverage           # 覆盖率测试

# 测试分类:
docker-compose -f docker-compose.dev.yml exec dev pytest tests/ml/ -v             # ML 模块测试
docker-compose -f docker-compose.dev.yml exec dev pytest tests/integration/ -v    # 集成测试
docker-compose -f docker-compose.dev.yml exec dev pytest tests/unit/ -v           # 单元测试
docker-compose -f docker-compose.dev.yml exec dev pytest -k "关键词" -v           # 按关键词过滤测试
docker-compose -f docker-compose.dev.yml exec dev node --test tests/engines/      # 运行指定目录的 Node.js 测试

# 单个测试用例调试:
docker-compose -f docker-compose.dev.yml exec dev pytest tests/test_foo.py::TestClass::test_method -v  # 运行单个测试方法
docker-compose -f docker-compose.dev.yml exec dev pytest tests/test_foo.py::TestClass -v               # 运行单个测试类
docker-compose -f docker-compose.dev.yml exec dev pytest -x --pdb                 # 首次失败时进入调试器

# === Docker/数据库 ===
# 开发环境 (推荐)
docker-compose -f docker-compose.dev.yml up -d              # 启动开发容器 (db + redis + dev)
docker-compose -f docker-compose.dev.yml exec dev bash       # 进入开发容器 Shell
make dev-up                                                  # 启动开发环境 (Makefile 快捷方式)

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
├── infrastructure/engines/   # 核心收割引擎 (SignalRadar, TrajectoryParser)
│   ├── services/             # 业务服务层 (网络拦截、数据提取)
│   ├── parsers/              # 数据解析层 (轨迹解析、Payout 计算)
│   └── utils/                # 工具函数 (常量、选择器)
├── ml/                       # 机器学习模块
│   ├── inference/            # 模型推理 (多模型共识)
│   └── training/             # 模型训练 (XGBoost + Platt Scaling)
├── collectors/               # 数据采集器 (FotMob, L3 特征处理器)
├── database/                 # 数据库模型和迁移
│   ├── models.py             # SQLAlchemy 模型
│   └── migrations/           # Alembic 迁移脚本
├── api/                      # FastAPI 接口 (可选启动)
└── utils/                    # 工具函数
    ├── cpp_bridge_radar.py   # RapidFuzz 模糊匹配 (队名 → URL)
    └── team_alias.py         # 队名标准化与别名展开

config/
├── active_registry.json      # 22 节点代理池配置
├── team_mapping.json         # 队名映射表
└── v26_feature_manifest.json # V26 特征清单

scripts/ops/                  # 运维脚本
├── harvest_fleet_master.js   # V173 装甲群收割主控 (Master-Worker)
├── harvest_worker.js         # 收割 Worker
├── monitor_dashboard.js      # 中央监控大屏
├── asset_report.js           # 资产报告生成
├── diagnostic_experiment.js  # 诊断实验
├── v171_mass_harvest.js      # 批量收割 (兼容)
├── v171_scheduler.js         # 定时调度
├── v171_mass_backfill.js     # 批量回填
└── *.py                      # Python 运维工具
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

`.env` 必需配置：
```bash
# 数据库配置
DB_PASSWORD=your_secure_password_here   # 必填
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_db
DB_USER=football_user

# 日志与代理
LOG_LEVEL=info
ENABLE_PROXY_ROTATION=true
PROXY_HOST=172.25.16.1

# Redis 配置 (可选)
REDIS_PORT=6379

# API 配置 (可选)
API_PORT=8000
API_WORKERS=2
```

**V173 收割器配置 (环境变量):**
| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MIN_DELAY_MS` | 5000 | 最小延时 (ms) |
| `MAX_DELAY_MS` | 12000 | 最大延时 (ms) |
| `MIN_SIZE_BYTES` | 5000 | 质量门禁阈值 (bytes) |
| `MAX_WORKERS` | 5 | 最大 Worker 数量 |
| `MAX_RETRY_ATTEMPTS` | 3 | 最大重试次数 |
| `CIRCUIT_BREAKER_THRESHOLD` | 3 | 熔断阈值 |
| `PROXY_PORTS` | 7890-7894 | 代理端口池 |

```bash
# 示例：自定义收割器配置
docker-compose -f docker-compose.dev.yml exec -e MIN_DELAY_MS=8000 -e MAX_DELAY_MS=15000 -e MAX_WORKERS=3 dev npm run harvest
```

---

# ═══════════════════════════════════════════════════════════════════════════════
# 故障排查 (Troubleshooting)
# ═══════════════════════════════════════════════════════════════════════════════

```bash
# 代理熔断
curl -x http://172.25.16.1:7891 https://httpbin.org/ip  # 测试代理
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/reset_proxy_health.py  # 重置代理状态
docker-compose -f docker-compose.dev.yml restart dev                              # 重置容器

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
