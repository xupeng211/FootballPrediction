# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 🚨 语言要求（最高优先级）

**请务必使用中文回复用户！**

---

## 📚 文档导航

**推荐阅读顺序**：
1. **本文档** (CLAUDE.md) - 完整项目文档和开发指南
2. **README.md** - 项目概览和快速开始
3. **docs/system_architecture.md** - 系统架构详解
4. **docs/RELEASE_V144_9.md** - 最新版本发布说明

---

## 📋 项目概览

**FootballPrediction** - 基于 XGBoost 3.0+ 的专业足球比赛预测系统

**项目愿景**: 以年化 25% 的真实收益率为北极星指标，构建可验证、可复制、可持续的体育预测系统

### 当前系统状态

| 属性 | 值 |
|------|-----|
| **状态** | ✅ Production Ready |
| **项目版本** | **V26.7.0** (pyproject.toml) |
| **生产版本** | **V41.832** (工业级归档收割机) |
| **命令中心** | **V144.9** (Multi-Source Command Center - Final Baseline) |
| **核心模型** | **V26.8** (联赛专项) |
| **数据采集** | **V142.0** (HarvesterService) + **V144.5** (FotMob) |
| **数据同步** | **V36.3** (auto_sync_and_alchemy_v2.sh) |
| **特征引擎** | **V41.380** (Golden Extractor) + **V41.390** (滚动特征) + **V41.500** (自动化特征工厂) |
| **Docker 版本** | **V51.0** (Industrial Grade Ready) |
| **模型框架** | XGBoost 3.0+ + CatBoost (V41.430) |
| **代码质量** | **V106.0** (Ruff 配置) |
| **基线准确率** | 56% (真赛前) |
| **推理延迟** | <100ms |
| **最后更新** | 2026-01-23 |

---

## 📈 版本演进概览

项目采用严格的版本管理体系，各主要组件版本独立演进：

### 最新版本发布：V41.832 工业级归档收割机 (Production Blueprint)

**说明**: V41.832 是一个工业级重构蓝图，将单文件脚本重构为模块化架构

| 特性 | 说明 |
|------|------|
| **物理点击机制** | Playwright 精确定位分页按钮，解决 Vue.js 动态加载问题 |
| **内容锁设计** | 等待页面内容完全填充后再提取，拒绝零场成功 |
| **事务自愈逻辑** | 每场比赛独立 try-except 包裹，execute 报错立即 rollback |
| **模块化架构** | 5 个独立模块 (harvesters, parsers, database_inserter, browser_helper, config) |
| **16/16 测试通过** | 完整的单元测试覆盖，支持英超/西甲/意甲/德甲/法甲 |
| **100% Type Hints** | 完整的类型注解覆盖 |
| **Google Style Docstrings** | 标准化的文档字符串 |

**详细文档**: `docs/MR_V41.832_production_blueprint.md`

**五大联赛总攻计划**:
- ✅ **英超**: 完成 (2024/2025 赛季已收割 380 场)
- 🚀 **西甲**: V41.840 系列 (计划中)
- 🚀 **意甲**: V41.850 系列 (计划中)
- 🚀 **德甲**: V41.860 系列 (计划中)
- 🚀 **法甲**: V41.870 系列 (计划中)

### 核心组件版本系列

| 组件 | 版本系列 | 说明 |
|------|----------|------|
| **数据采集** | V41.x | 运维工具和采集器 (V41.810 最新) |
| **命令中心** | V144.x | 统一入口和数据源路由 (V144.7 最新) |
| **预测模型** | V26.x | 特征引擎和模型训练 (V26.8 最新) |
| **收割服务** | V142.x | 统一收割服务架构 (V142.0 最新) |
| **Ghost Protocol** | V141.x | 反爬检测基础能力 (V141.0 最新) |
| **特征工厂** | V41.500+ | 自动化特征提取引擎 (V41.500 最新) |
| **代码质量** | V106.0 | Ruff 配置 (line-length: 100) |

### 关键里程碑

- **V41.832** (2026-01): 工业级归档收割机 - 物理分页、内容锁与事务自愈
- **V41.510** (2026-01): Automated Feature Factory Integration - Production Ready
- **V41.810** (2026-01): Archive Brute Force - 档案暴力破解
- **V41.800** (2026-01): Archive Breaker - 档案破解器
- **V41.720** (2026-01): Lightning Harvest - 网络拦截型极速收割
- **V41.710** (2026-01): 进度监控脚本
- **V41.500** (2026-01): 自动化特征工厂 - Schema 韧性配置
- **V144.9** (2026-01): Multi-Source Command Center - Final Baseline
- **V41.287** (2026-01): UTC 审计 + Golden Shield 特征透视
- **V51.0** (2025-12): 工业级 Docker 部署就绪
- **V106.0** (2025-12): Ruff 代码质量配置
- **V29.1** (2024-11): 多格式特征解析引擎

### 版本文档

详细版本变更记录位于 `docs/V*.md` 文件中，每个版本都有对应的验收报告和技术规范。

---

## ⚡ 快速开始

### 5 分钟上手

1. **启动核心服务**
   ```bash
   make up
   ```

2. **验证环境**
   ```bash
   python main.py --test-proxy
   ```

3. **运行单次收割（测试模式）**
   ```bash
   python main.py --source fotmob --mode single --limit 1 --dry-run
   ```

4. **检查代码质量**
   ```bash
   make verify
   ```

### 核心开发命令

```bash
# 环境管理
make up                  # 启动核心服务 (db + redis)
make ps                  # 查看容器状态
make verify              # 运行代码质量检查（提交前必需）
make logs                # 查看核心服务日志

# 数据采集 (V144.7 统一命令入口)
python main.py --source fotmob --mode single --limit 10      # FotMob API 数据源
python main.py --source oddsportal --mode single --limit 10  # OddsPortal RPA 数据源
python main.py --mode cruise                                # 24h 全自动巡航
python main.py --test-proxy                                 # 测试代理

# 测试
make test-unit           # 运行单元测试
pytest tests/ -v         # 运行所有测试

# 数据库
make db-shell            # 进入 PostgreSQL Shell
```

---

## 🏗️ 系统架构

### V144.7 Multi-Source Command Center 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    main.py - V144.7 统一入口                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  数据源路由 (--source):                                     │ │
│  │  • oddsportal: OddsPortal RPA 采集 (V144.2)               │ │
│  │  • fotmob: FotMob API 采集 (V144.5)                       │ │
│  │                                                            │ │
│  │  运行模式 (--mode):                                        │ │
│  │  • single: 单次收割 (指定联赛/赛季)                        │ │
│  │  • cruise: 24h 全自动巡航                                  │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    HarvesterService (V142.0)                     │
│  队列驱动架构 + Ghost Protocol + 全路径试错匹配                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    BaseExtractor (V141.0)                        │
│  Ghost Protocol - 30+ 浏览器指纹池 + 人类行为模拟                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    PostgreSQL 持久层
              matches 表 + metrics_multi_source_data 表
```

### 三层生产级架构 (V56.3)

```
1. Master 调度层：跨赛季/跨联赛编排、智能跳过检测、反封禁机制
2. Production 提取层：智能轮询、悬停自愈、IP健康监控
3. Database 持久层：PostgreSQL 15 + Unified Schema
```

### 核心目录结构

```
FootballPrediction/
├── src/                          # 生产代码
│   ├── api/                      # API 层
│   │   ├── collectors/           # 数据采集器 (V141.0/V142.0)
│   │   │   ├── base_extractor.py     # V141.0 Ghost Protocol 基类
│   │   │   ├── fotmob_core.py        # FotMob API 采集
│   │   │   ├── odds_production_extractor.py  # 赔率提取
│   │   │   └── lineup_collector.py  # V41.284 阵容采集器
│   │   └── services/           # 业务服务层
│   │       └── harvester_service.py  # V142.0 统一收割服务
│   ├── config_unified.py         # V26.0 统一配置管理
│   ├── core/                     # V105.0 核心基础设施
│   │   ├── exceptions.py         # 统一异常体系
│   │   ├── environment_detector.py  # 环境智能检测
│   │   └── scrapers/             # V41.156 代理管理器
│   ├── database/                 # 数据库层
│   ├── harvesters/               # V41.832 工业级收割机
│   │   └── oddsportal_archive.py # 模块化归档收割
│   ├── parsers/                  # V41.832 数据解析器
│   │   └── match_parser.py       # 比赛数据解析
│   ├── ml/                       # ML 引擎
│   │   └── engine.py             # XGBoost 引擎 + ModelDispatcher
│   ├── models/                   # V41.155 数据模型
│   │   └── match_schema.py      # MatchSchema 统一数据模型
│   ├── processors/               # V25.1 特征提取
│   │   ├── v41_380_golden_extractor.py    # Golden Shield 特征提取
│   │   ├── rolling_feature_calculator.py  # V41.390 滚动特征计算
│   │   ├── feature_factory.py    # V41.510 自动化特征工厂
│   │   └── path_resolver.py      # Schema-Agnostic 路径解析
│   └── utils/                    # 工具类
│       └── text_processor.py     # V140.0 TeamNameNormalizer
├── scripts/                      # 核心脚本
│   ├── ops/                      # V41.x 系列运维工具
│   │   ├── v41_277_p0_lineup_rush.py    # 阵容急速采集
│   │   ├── v41_280_async_harvest.py      # 异步收割
│   │   ├── v41_287_utc_audit.py          # UTC 时间审计
│   │   ├── v41_287_golden_shield_audit.py # 特征深度透视
│   │   ├── v41_290_golden_vault_seal.py  # 库存封存
│   │   ├── v41_291_diagnostic_tool.py   # 诊断工具
│   │   ├── v41_800_archive_breaker.py   # V41.800 档案破解器
│   │   ├── v41_810_archive_brute_force.py # V41.810 档案暴力破解
│   │   ├── v41_820_archive_real_click.py # V41.820 真实点击
│   │   ├── v41_830_data_janitor.py      # V41.830 数据清理
│   │   ├── v41_831_deep_purge.py        # V41.831 深度清理
│   │   └── auto_sync_and_alchemy_v2.sh  # V36.3 数据同步
│   ├── maintenance/              # 维护脚本
│   ├── ml/                       # ML 训练脚本
│   ├── sql/                      # SQL 迁移脚本
│   └── run_checks.sh             # CI 质量门禁
├── tests/                        # 测试套件
│   └── harvesters/               # V41.832 收割机测试
│       └── test_oddsportal_archive.py
├── config/                       # 配置文件
│   ├── titan_config.yaml         # V41.151 统一代理和联赛配置
│   ├── global_harvest_list.yaml  # 全球联赛注册表
│   ├── harvester_v2.yaml        # 收割器配置
│   └── schema_map.yaml          # V41.500+ JSON 路径配置
├── storage/                      # V41.153 存储层
│   ├── html_vault/               # HTML 存储库
│   └── injection_queue/          # 注入队列
├── model_zoo/                    # 模型仓库
├── main.py                       # V144.7 统一命令入口 ⭐
├── Makefile                      # 统一命令入口
├── requirements.txt              # 生产依赖
├── pyproject.toml                # Poetry 配置
├── docs/                         # 文档目录
│   └── MR_V41.832_production_blueprint.md  # V41.832 工业级蓝图
└── CLAUDE.md                     # 本文件
```

---

## 🔧 开发指南

### 配置管理

使用 `src.config_unified.get_settings()` 获取配置：

```python
from src.config_unified import get_settings

settings = get_settings()
# 访问配置
db_host = settings.database.host
db_name = settings.database.name
```

#### 配置文件说明 (config/ 目录)

| 文件 | 用途 |
|------|------|
| `.env` | 环境变量配置（数据库、Redis、代理等） |
| `leagues.yaml` | 联赛配置（tier 分级、名称映射） |
| `global_harvest_list.yaml` | 全球联赛注册表 |
| `titan_config.yaml` | 统一代理和联赛配置 |
| `harvester_v2.yaml` | 收割器配置 |
| `schema_map.yaml` | V41.500+ JSON 路径配置（数据源变动适配） |

#### 环境智能检测 (V41.59)

系统通过 `src.core.environment_detector` 自动检测运行环境：

| 环境 | `DB_HOST` | 检测方式 |
|------|-----------|----------|
| **Docker** | `db` | 检测 `DOCKER_ENV` 环境变量 |
| **WSL2 本地** | `172.25.16.1` | 检测 `/proc/version` 包含 "microsoft" |
| **本地开发** | `localhost` | 默认环境 |

**数据库连接池配置** (V41.49):
```python
# 支持高并发连接池
pool_size: int = 15           # 基础连接数
max_overflow: int = 20        # 最大溢出数 (理论最大 35)
pool_timeout: int = 10        # 连接超时 (秒)
pool_recycle: int = 600       # 连接回收时间 (10分钟)
```

#### WSL2 代理自动发现

BaseExtractor 支持自动发现 WSL2 环境下的代理配置：
```python
from src.api.collectors.base_extractor import BaseExtractor

extractor = BaseExtractor(auto_proxy=True)
# 自动检测环境变量或 WSL2 桥接网关
proxy_config = extractor.get_proxy_config()
```

#### 单数据库准则 (V41.51)

系统强制只允许连接 `football_db` 数据库，防止环境偏差：
```python
# 违规会抛出 DatabaseConfigurationError
# DB_NAME=football_db  # 唯一合法值
```

### 数据库连接标准

```python
from src.config_unified import get_settings
import psycopg2
from psycopg2.extras import RealDictCursor

settings = get_settings()
conn = psycopg2.connect(
    host=settings.database.host,
    database=settings.database.name,
    user=settings.database.user,
    password=settings.database.password.get_secret_value(),
    cursor_factory=RealDictCursor  # 返回字典而非元组
)
```

### 核心数据库表

**matches 表** (Source_F - 比赛基础信息)
```sql
match_id VARCHAR(50) PRIMARY KEY
league_name VARCHAR(255)
season VARCHAR(20)
home_team VARCHAR(255)
away_team VARCHAR(255)
match_time TIMESTAMP
technical_features JSONB      -- 152 维技术特征
l2_raw_json JSONB            -- FotMob L2 原始数据
l3_extraction_status VARCHAR(20) -- V36.1 特征提取状态
```

**matches_mapping 表** (哈希对齐)
```sql
fotmob_id VARCHAR(50) REFERENCES matches(match_id)
oddsportal_hash VARCHAR(8)
oddsportal_url TEXT
match_date TIMESTAMP
mapping_method VARCHAR(50)
confidence FLOAT
review_status VARCHAR(20)
```

**metrics_multi_source_data 表** (赔率数据)
```sql
match_id VARCHAR(50) REFERENCES matches(match_id)
source_name VARCHAR(50)      -- Entity_P (Pinnacle)
init_h/d/a FLOAT             -- 开盘赔率
final_h/d/a FLOAT            -- 终盘赔率
integrity_score FLOAT        -- 完整性分数
```

### 常用 SQL 查询

```sql
-- 查看数据采集统计
SELECT
    source_name,
    COUNT(*) as total_records,
    COUNT(opening_time_h) as with_opening_time,
    ROUND(100.0 * COUNT(opening_time_h) / COUNT(*), 2) as success_rate
FROM metrics_multi_source_data
GROUP BY source_name;

-- 查看赛季覆盖情况
SELECT
    m.season,
    m.league_name,
    COUNT(DISTINCT m.match_id) as total_matches,
    COUNT(DISTINCT CASE WHEN msd.opening_time_h IS NOT NULL THEN m.match_id END) as with_pinnacle_data
FROM matches m
LEFT JOIN metrics_multi_source_data msd
    ON m.match_id = msd.match_id
    AND msd.source_name = 'Entity_P'
GROUP BY m.season, m.league_name
ORDER BY m.season DESC;

-- 检查数据完整性评分分布
SELECT
    CASE
        WHEN integrity_score < 1.02 THEN 'Too Low'
        WHEN integrity_score > 1.08 THEN 'Too High'
        ELSE 'Valid'
    END as score_category,
    COUNT(*) as count,
    ROUND(AVG(integrity_score), 4) as avg_score
FROM metrics_multi_source_data
WHERE source_name = 'Entity_P'
    AND integrity_score IS NOT NULL
GROUP BY score_category;
```

### 代码质量规范

**提交前必须运行**:
```bash
make verify  # 快速验证 (lint + test-unit + security)
```

**工具配置**:
- **Ruff (V106.0)**: `ruff.toml` - 主代码质量工具
  - `line-length`: 100 字符
  - `target-version`: Python 3.11
  - 规则集: E, W, F, I, N, UP, B, C4, DTZ, T10, EM, ISC, ICN, G, PIE, T20, PT, Q, RSE, RET, SIM, TID, TCH, ARG, PTH, ERA, PL, TRY, FLY, PERF, RUF
  - McCabe 复杂度阈值: 15
- **pyproject.toml**: 备用配置 (line-length: 120)

**推荐的代码质量工作流**：
```bash
# 1. 格式化代码（主要工具）
ruff format src/ tests/

# 2. Lint 检查（主要工具）
ruff check src/ tests/

# 3. 自动修复
ruff check src/ tests/ --fix

# 4. 类型检查
mypy src/

# 5. 安全扫描
bandit -r src/
```

**工具优先级**：
| 工具 | 优先级 | 用途 |
|------|--------|------|
| **Ruff** | 🔴 主要 | 格式化 + Lint (ruff.toml) |
| **MyPy** | 🟡 推荐 | 类型检查 |
| **Bandit** | 🟡 推荐 | 安全扫描 |

---

## 🚀 典型开发工作流

### 工作流 1: 添加新特征到数据模型

1. **修改数据模型**
   ```bash
   # 编辑特征提取处理器
   src/ml/feature_engine/processors/your_feature.py
   ```

2. **添加单元测试**
   ```bash
   # 创建测试文件
   tests/ml/test_your_feature.py
   ```

3. **运行质量检查**
   ```bash
   make verify
   ```

4. **提交变更**
   ```bash
   git add src/ml/feature_engine/processors/your_feature.py
   git add tests/ml/test_your_feature.py
   git commit -m "feat: 添加新特征 XXX"
   ```

### 工作流 2: 调试数据采集问题

1. **启用详细日志**
   ```bash
   export LOG_LEVEL=DEBUG
   python main.py --source fotmob --mode single --limit 1
   ```

2. **检查代理状态**
   ```bash
   python main.py --test-proxy
   ```

3. **查看数据库记录**
   ```bash
   make db-shell
   # 在 psql 中运行查询
   SELECT match_id, l2_raw_json IS NOT NULL as has_l2_data FROM matches LIMIT 10;
   ```

4. **使用诊断工具**
   ```bash
   python scripts/ops/v41_291_diagnostic_tool.py --match-id <MATCH_ID>
   ```

### 工作流 3: 更新数据源配置

1. **编辑配置文件**
   ```bash
   # 编辑联赛配置
   config/global_harvest_list.yaml
   ```

2. **验证配置格式**
   ```bash
   python -c "import yaml; yaml.safe_load(open('config/global_harvest_list.yaml'))"
   ```

3. **测试单个联赛**
   ```bash
   python main.py --source fotmob --mode single --league "Premier League" --limit 1
   ```

### 工作流 4: 运行特征提取流水线

1. **检查待处理比赛**
   ```sql
   SELECT COUNT(*) FROM matches WHERE l3_extraction_status = 'PENDING';
   ```

2. **运行流水线**
   ```bash
   python scripts/production_harvester.py --mode l3-extraction --batch-size 50
   ```

3. **监控进度**
   ```bash
   tail -f logs/v144_7_main.log
   ```

---

## 🧬 核心模块说明

### main.py - V41.360 Production-Ready Command Center

项目的主要入口点，提供统一命令行界面：

```bash
# V41.360: 一键收割 (Consolidated Engine)
python main.py --task harvest --limit 2000

# V41.360: Golden Shield 审计
python main.py --task audit

# V41.360: 黄金特征提取
python main.py --task extract --concurrent 12

# 多数据源支持
python main.py --source fotmob --mode single --limit 10
python main.py --source oddsportal --mode single --limit 10
python main.py --source fotmob --mode cruise

# 环境预检
python main.py --test-proxy

# 干跑模式
python main.py --mode single --dry-run
```

### HarvesterService - V142.0 统一收割服务

位于 `src/api/services/harvester_service.py`，是数据收割的核心服务：

```python
from src.api.services.harvester_service import HarvesterService

service = HarvesterService(
    mode="single",              # single / cruise
    enable_ghost_protocol=True, # 启用 Ghost Protocol
    enable_queue=True,          # 启用队列系统
    limit=None,                 # 最大处理数量
    dry_run=False,              # 干跑模式
)
await service.run()
```

**核心特性**:
- 队列驱动架构 (match_search_queue)
- Ghost Protocol 集成 (BaseExtractor V141.0)
- 全路径试错匹配 (TeamNameNormalizer V140.0)
- 实时监控面板
- 信号处理 (SIGINT/SIGTERM)
- 优雅关闭机制

### BaseExtractor - V141.0 Ghost Protocol

位于 `src/api/collectors/base_extractor.py`，提供反爬检测基础能力：

- 30+ 主流浏览器指纹池 (Chrome/Edge/Safari/Firefox)
- 5 种常见屏幕分辨率随机化
- 人类行为模拟 (滚动 + 点击噪声)
- 深度拦截检测 (Cloudflare, IP 封禁)
- WSL2 自动代理发现

### ModelDispatcher (V26.8)

联赛专项模型自动分发，位于 `src/ml/engine.py`：

```python
from src.ml.engine import ModelDispatcher

dispatcher = ModelDispatcher()
prediction = dispatcher.predict(
    home_team="Arsenal",
    away_team="Chelsea",
    league_name="Premier League"  # 自动选择 EPL 专项模型
)
```

### LineupCollector - V41.284 Supersonic Harvest

位于 `src/api/collectors/lineup_collector.py`，阵容数据采集：

```python
from src.api.collectors.lineup_collector import LineupCollector

collector = LineupCollector()
result = collector.collect_lineup(match_id="3428850")
# result: {"success": True, "formation": "4-3-3", "starting_xi": [...], "missing": [...]}

# 采集并保存到数据库
result = collector.collect_and_save(match_id="3428850")
```

**核心功能**:
- V41.282 启发式路径发现：递归爬取 JSON 查找阵容数据
- V41.281 双结构兼容：支持新旧 FotMob API 结构
- V41.284 Supersonic Harvest：429 智能避让，5 秒休眠后自动重试

### V41.380 GoldenExtractor - 特征深度提取

位于 `src/processors/v41_380_golden_extractor.py`，深度特征提取引擎：

```python
from src.processors.v41_380_golden_extractor import GoldenExtractor

extractor = GoldenExtractor()
features = extractor.extract_golden_features(l2_raw_json)
# 提取黄金特征用于模型训练和预测
```

### V41.390 RollingFeatureCalculator - 滚动特征计算

位于 `src/processors/rolling_feature_calculator.py`，时序特征计算：

```python
from src.processors.rolling_feature_calculator import RollingFeatureCalculator

calculator = RollingFeatureCalculator()
rolling_features = calculator.calculate_team_form(team_id, window=5)
# 计算球队近期表现特征
```

### V41.500+ 自动化特征工厂 - Schema 韧性配置

**版本说明**: V41.510 (Automated Feature Factory Integration - Production Ready)

位于 `config/schema_map.yaml` 和 `src/processors/feature_factory.py`，实现数据源变动适配：

**V41.510 核心特性**:
- ✅ 自动化特征生成流水线
- ✅ Schema-Agnostic 路径访问（PathResolver）
- ✅ 疲劳度、缺阵、首发战力、赔率动向特征
- ✅ 五大联赛识别和分级
- ✅ 生产就绪的批量处理能力

**核心架构**:
```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Schema Map   │───▶│Path Resolver │───▶│Feature       │
│ (YAML 配置)   │    │(安全路径访问)  │    │Factory       │
└──────────────┘    └──────────────┘    │(特征工厂)    │
                                          └──────────────┘
```

**核心组件**:
| 组件 | 文件路径 | 功能 |
|------|----------|------|
| **Schema Map** | `config/schema_map.yaml` | JSON 路径配置，支持数据源变动 |
| **Path Resolver** | `src/processors/path_resolver.py` | 安全路径访问，带默认值容错 |
| **Feature Factory** | `src/processors/feature_factory.py` | 特征生成引擎（疲劳度/缺阵/赔率） |
| **Pipeline Integrator** | `src/api/collectors/v41_500_pipeline_integration.py` | 流水线自动集成器 |

**V41.500 新增特征定义**:
| 特征类别 | 特征名称 | 说明 |
|----------|----------|------|
| **疲劳度** | `home_rest_days` | 主队休息天数 |
| | `away_is_busy_week` | 客队是否为忙碌周（休息<4天） |
| | `diff_rest_days` | 休息天数差值 |
| **缺阵** | `home_unavailable_total_count` | 主队缺阵人数 |
| | `home_unavailable_total_market_value` | 主队缺阵总身价（欧元） |
| | `home_unavailable_star_count` | 主队缺阵球星数（身价>30M） |
| **首发战力** | `home_starter_avg_rating` | 主队首发平均评分 |
| | `home_missing_stars_count` | 主队缺阵大腿数（评分>=7.5） |
| **赔率动向** | `home_drop_ratio` | 主胜赔率下降比率 |
| | `total_movement` | 赔率总变化幅度 |
| **联赛等级** | `is_top_5_league` | 是否为五大联赛 |

**使用方式**:
```bash
# 1. 数据采集完成后自动处理
python -c "
from src.api.collectors.v41_500_pipeline_integration import process_match_after_collection
process_match_after_collection('match_id')
"

# 2. 批量处理最近 100 场比赛
python src/api/collectors/v41_500_pipeline_integration.py

# 3. 在代码中调用
from src.processors.feature_factory import get_feature_factory
factory = get_feature_factory()
features = factory.process_match(match_data)
```

**更新 schema_map.yaml**:
当数据源结构变化时，只需更新 `config/schema_map.yaml`，无需修改代码：
```yaml
# 示例：添加新的数据源路径
new_source:
  match_data:
    path: "data.match"
    home_team: "teams.home.name"
    unavailable: "teams.home.unavailable_list"
```

---

## 📊 系统性能基准

### 预测性能

| 指标 | 基准值 | 说明 |
|------|--------|------|
| **推理延迟** | <100ms | 单次预测响应时间 |
| **吞吐量** | >100 QPS | 批量预测能力 |
| **模型准确率** | 56% | 真赛前基线 |
| **特征维度** | 6000+ | V26.7 深度特征 |

### 数据采集性能

| 指标 | 基准值 | 说明 |
|------|--------|------|
| **FotMob API** | ~2s/match | 单场比赛采集时间 |
| **OddsPortal RPA** | ~5s/match | 单场比赛采集时间 |
| **并发采集** | 10 workers | V41.280 异步收割 |
| **成功率** | >95% | 正常网络条件下 |

### 系统资源

| 资源 | 开发环境 | 生产环境 |
|------|----------|----------|
| **内存** | 4GB | 8GB |
| **CPU** | 2 核 | 4 核 |
| **磁盘** | 20GB | 50GB |
| **网络** | 10Mbps | 100Mbps |

---

## 🛠️ 技术栈

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **语言** | Python | 3.11+ | 核心开发语言 |
| **数据库** | PostgreSQL | 15 | 生产数据存储 |
| **缓存** | Redis | 7 | 分布式缓存 |
| **浏览器** | Playwright | 1.49+ | 智能网页自动化 |
| **ML 框架** | XGBoost / CatBoost | 3.0+ / 1.2+ | 预测模型 (V41.430 支持 CatBoost) |
| **Web** | FastAPI | 0.124+ | REST API |
| **测试** | Pytest | 9.0+ | 单元测试 |
| **容器** | Docker | 24+ | 容器化部署 |
| **代码质量** | Ruff | 0.8+ | 格式化 + Lint |

---

## 🚨 V41.280+ 火力全开收割系列

### V41.273 Final URL Recovery - URL 深度恢复
```bash
python scripts/ops/v41_273_final_url_recovery.py --limit 500 --workers 3
```

### V41.277 P0 Lineup Rush - 阵容急速采集
```bash
python scripts/ops/v41_277_p0_lineup_rush.py --limit 50
```

### V41.280 Async Harvest - 异步收割
```bash
python scripts/ops/v41_280_async_harvest.py --concurrent 10
```

### V41.390 Quality Spotcheck - 质量检查
```bash
python scripts/ops/v41_390_quality_spotcheck.py --limit 100
```

### V41.480 JSON Path Audit - JSON 路径审计
```bash
python scripts/ops/v41_480_json_path_audit.py --match-id <MATCH_ID>
```

### V41.520 Backfill Audit - 数据回填审计
```bash
python scripts/ops/v41_520_backfill_audit.py --season 2024-2025
```

### V41.710 进度监控 - 哈希补全进度监控
```bash
python scripts/ops/v41_710_monitor.py
# 用于监控英超等联赛的哈希补全进度
```

### V41.720 Lightning Harvest - 网络拦截型极速收割
```bash
# 英超 2024/2025 赛季（闪电模式）
python -m scripts.ops.v41_720_lightning_harvest --league "Premier League" --season "2024/2025"

# 五大联赛全量
python -m scripts.ops.v41_720_lightning_harvest --season "2024/2025"
# 核心创新: 网络拦截直接捕获 XHR 响应，跳过 DOM 渲染
```

### V41.730 Bulk Harvest - 批量收割
```bash
python scripts/ops/v41_730_bulk_harvest.py
```

### V41.740 Lockdown - 封锁模式
```bash
python scripts/ops/v41_740_lockdown.py
```

### V41.750 Sovereign Harvest - 主权收割
```bash
python scripts/ops/v41_750_sovereign_harvest.py
```

### V41.760 Total Conquest - 完全征服
```bash
python scripts/ops/v41_760_total_conquest.py
```

### V41.770 Page Harvester - 页面收割器
```bash
python scripts/ops/v41_770_page_harvester.py
```

### V41.780 Perfectionist - 完美主义者
```bash
python scripts/ops/v41_780_perfectionist.py
```

### V41.781 Diagnose HTML - HTML 诊断
```bash
python scripts/ops/v41_781_diagnose_html.py
```

### V41.790 Golden Sweep - 黄金扫描
```bash
python scripts/ops/v41_790_golden_sweep.py
```

### V41.795 Diagnose Archive - 档案诊断
```bash
python scripts/ops/v41_795_diagnose_archive.py
```

### V41.795 Precision Sweep - 精密扫描
```bash
python scripts/ops/v41_795_precision_sweep.py
```

### V41.796 Direct URL Fetcher - 直接 URL 获取
```bash
python scripts/ops/v41_796_direct_url_fetcher.py
```

### V41.800 Archive Breaker - 档案破解器
```bash
python scripts/ops/v41_800_archive_breaker.py
```

### V41.832 工业级归档收割机 (Production Blueprint)

**说明**: V41.832 是工业级重构蓝图，提供了模块化架构替代单文件脚本

```bash
# 蓝图文档 (详细设计)
cat docs/MR_V41.832_production_blueprint.md

# 模块化架构 (Python API)
from src.harvesters.oddsportal_archive import OddsPortalArchiveHarvester

harvester = OddsPortalArchiveHarvester()
result = await harvester.harvest_season("Premier League", "2024/2025")

# 运行单元测试 (16/16 通过)
pytest tests/harvesters/test_oddsportal_archive.py -v
```

**核心特性**:
- **物理点击机制**: Playwright 精确定位分页按钮
- **内容锁设计**: 等待页面内容完全填充后再提取
- **事务自愈逻辑**: 每场比赛独立 try-except 包裹
- **模块化架构**: 5 个独立模块 (harvesters, parsers, database_inserter)
- **测试覆盖**: 16/16 单元测试通过

### V41.810 Archive Brute Force - 档案暴力破解
```bash
python scripts/ops/v41_810_archive_brute_force.py
```

---

## ⚠️ 重要警告

### 禁止操作

- ❌ **禁止绕过** `FotMobCoreCollector.fetch_match_details()` 直接拼写 API URL
- ❌ **禁止绕过** `technical_features` 字段存储数据
- ❌ **禁止直接修改** `model_zoo/` 中的模型文件
- ❌ **禁止在生产环境运行** `make db-reset`
- ❌ **禁止跳过** `make verify` 直接提交
- ❌ **禁止创建版本类文件** (`*_v2`, `*_new`, `*_backup`)

### 必须操作

- ✅ **所有 FotMob 采集必须使用** `FotMobCoreCollector.fetch_match_details(match_id)`
- ✅ **152 维技术特征必须存储在** `matches.technical_features` 字段
- ✅ **修改代码前运行** `git status` 确认分支
- ✅ **提交前运行** `make verify` 确保质量
- ✅ **修改核心模块前完成影响分析**

---

## 🐛 故障排除指南

### 网络与代理问题

**症状**: `HTTP 429/403` 错误频繁出现
```bash
# 1. 测试代理连通性
python main.py --test-proxy

# 2. 检查代理健康状态
python scripts/ops/v41_291_diagnostic_tool.py --check-proxy

# 3. 等待冷却期 (6-24小时)
# 检查 COLLECTION_PAUSE_UNTIL 配置
```

**症状**: WSL2 无法连接 Docker 容器
```bash
# 1. 验证网桥 IP
ping 172.25.16.1

# 2. 检查端口转发
docker-compose ps

# 3. 重启网络
wsl --shutdown
```

### 数据库问题

**症状**: `database does not exist` 或 `Connection refused`
```bash
# 1. 启动核心服务
make up

# 2. 等待数据库就绪
docker-compose logs -f db

# 3. 手动创建数据库
make db-shell
CREATE DATABASE football_db;
```

**症状**: 连接池耗尽
```python
# 检查连接池配置
settings = get_settings()
print(f"Pool size: {settings.database.pool_size}")
print(f"Max overflow: {settings.database.max_overflow}")

# 增加连接池大小 (修改 .env)
DB_POOL_SIZE=20
DB_POOL_MAX_OVERFLOW=30
```

### 数据采集问题

**症状**: L2 数据采集失败
```bash
# 1. 检查 match_id 是否有效
python -c "from src.api.collectors.fotmob_core import FotMobCoreCollector; print(FotMobCoreCollector().fetch_match_details('3428850'))"

# 2. 启用详细日志
export LOG_LEVEL=DEBUG
python main.py --source fotmob --mode single --limit 1

# 3. 检查 API 限流
curl -I https://www.fotmob.com/api
```

**症状**: 特征提取卡住
```bash
# 1. 检查待处理队列
make db-shell
SELECT COUNT(*) FROM matches WHERE l3_extraction_status = 'PROCESSING';

# 2. 重置卡住的任务
UPDATE matches SET l3_extraction_status = 'PENDING' WHERE l3_extraction_status = 'PROCESSING';

# 3. 重新运行流水线
python scripts/production_harvester.py --mode l3-extraction
```

### 模型问题

**症状**: `Model file not found`
```bash
# 1. 检查模型仓库
ls -lh model_zoo/

# 2. 恢复备份模型
cp model_zoo/backup/*.pkl model_zoo/

# 3. 重新训练模型
python scripts/ml/train_model.py --league "Premier League"
```

**症状**: 预测结果异常
```bash
# 1. 验证输入特征
python -c "from src.ml.engine import ModelDispatcher; ModelDispatcher().validate_features(...)"

# 2. 检查模型版本
python -c "from src.ml.engine import ModelDispatcher; print(ModelDispatcher().get_model_version())"

# 3. 运行回测验证
python scripts/ml/backtest.py --model-version V26.8
```

### Docker 问题

**症状**: 容器启动失败
```bash
# 1. 检查日志
docker-compose logs --tail=100

# 2. 重新构建镜像
docker-compose build --no-cache

# 3. 清理并重启
docker-compose down -v
make up
```

**症状**: 权限错误
```bash
# 1. 修复文件权限
sudo chown -R $USER:$USER .

# 2. 检查 Docker 用户
docker-compose exec whoami
```

### 性能问题

**症状**: 响应缓慢
```bash
# 1. 检查系统资源
htop

# 2. 分析数据库查询
make db-shell
EXPLAIN ANALYZE SELECT * FROM matches LIMIT 10;

# 3. 检查慢查询日志
docker-compose exec db cat /var/lib/postgresql/data/log/postgresql.log | grep "duration:"
```

---

## 🔒 永久保留条款

### 语言要求
**请务必使用中文回复用户！**

这一要求具有最高优先级，必须始终保留在文件的显眼位置。

---

**🚨 CRITICAL**: This is a production system support document.

**🧬 当前版本**: V26.7.0 (pyproject.toml) / V41.832 (工业级归档收割机)
**命令中心**: V144.9 (Multi-Source Command Center - Final Baseline)
**收割引擎**: V142.0 (HarvesterService - 统一收割服务)
**阵容采集**: V41.284 (Supersonic Harvest - 429 智能避让)
**特征引擎**: V41.380 (Golden Extractor) + V41.390 (滚动特征) + V41.510 (自动化特征工厂)
**闪电收割**: V41.720 (Lightning Harvest - 网络拦截型极速收割)
**归档收割**: V41.832 (工业级归档收割机 - 物理点击、内容锁、事务自愈)
**Docker 版本**: V51.0 (Industrial Grade Ready)
**代码质量**: V106.0 (Ruff 配置 - line-length: 100)
**最后更新**: 2026-01-23
**基线准确率**: 56% (真赛前)
**生产状态**: Production Ready
**Python 版本**: 3.11+
