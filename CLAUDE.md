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
| **生产版本** | **V41.287** (UTC Audit + Golden Shield) |
| **命令中心** | **V144.7** (Multi-Source Command Center) |
| **核心模型** | **V26.8** (联赛专项) |
| **数据采集** | **V151.3** (并发收割器) + **V144.5** (FotMob) |
| **数据同步** | **V36.3** (auto_sync_and_alchemy_v2.sh) |
| **特征引擎** | **V29.1** (多格式解析) |
| **Docker 版本** | **V51.0** (Industrial Grade Ready) |
| **基线准确率** | 56% (真赛前) |
| **推理延迟** | <100ms |
| **最后更新** | 2026-01-21 |

---

## 📈 版本演进概览

项目采用严格的版本管理体系，各主要组件版本独立演进：

### 核心组件版本系列

| 组件 | 版本系列 | 说明 |
|------|----------|------|
| **数据采集** | V41.x | 运维工具和采集器 (V41.287 最新) |
| **命令中心** | V144.x | 统一入口和数据源路由 (V144.7 最新) |
| **预测模型** | V26.x | 特征引擎和模型训练 (V26.8 最新) |
| **收割服务** | V142.x | 统一收割服务架构 (V142.0 最新) |
| **Ghost Protocol** | V141.x | 反爬检测基础能力 (V141.0 最新) |

### 关键里程碑

- **V144.7** (2026-01): 多数据源统一命令入口
- **V41.287** (2026-01): UTC 审计 + Golden Shield 特征透视
- **V51.0** (2025-12): 工业级 Docker 部署就绪
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
│   ├── ml/                       # ML 引擎
│   │   └── engine.py             # XGBoost 引擎 + ModelDispatcher
│   ├── models/                   # V41.155 数据模型
│   │   └── match_schema.py      # MatchSchema 统一数据模型
│   ├── processors/               # V25.1 特征提取
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
│   │   └── auto_sync_and_alchemy_v2.sh  # V36.3 数据同步
│   ├── maintenance/              # 维护脚本
│   ├── ml/                       # ML 训练脚本
│   ├── sql/                      # SQL 迁移脚本
│   └── run_checks.sh             # CI 质量门禁
├── tests/                        # 测试套件
├── config/                       # 配置文件
│   ├── titan_config.yaml         # V41.151 统一代理和联赛配置
│   ├── global_harvest_list.yaml  # 全球联赛注册表
│   └── harvester_v2.yaml        # 收割器配置
├── storage/                      # V41.153 存储层
│   ├── html_vault/               # HTML 存储库
│   └── injection_queue/          # 注入队列
├── model_zoo/                    # 模型仓库
├── main.py                       # V144.7 统一命令入口 ⭐
├── Makefile                      # 统一命令入口
├── requirements.txt              # 生产依赖
├── pyproject.toml                # Poetry 配置
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

**推荐的代码质量工作流**：
```bash
# 1. 格式化代码（主要工具）
ruff format src/ tests/

# 2. Lint 检查（主要工具）
ruff check src/ tests/

# 3. 类型检查
mypy src/

# 4. 安全扫描
bandit -r src/
```

**工具优先级**：
| 工具 | 优先级 | 用途 |
|------|--------|------|
| **Ruff** | 🔴 主要 | 格式化 + Lint |
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

### main.py - V144.7 Multi-Source Command Center

项目的主要入口点，提供统一命令行界面：

```bash
# V144.7: 多数据源支持
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
| **ML 框架** | XGBoost | 3.0+ | 预测模型 |
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

**🧬 当前版本**: V41.287 (UTC Audit + Golden Shield)
**命令中心**: V144.7 (Multi-Source Command Center)
**收割引擎**: V41.285 (Stabilized Flow - 连接池扩容)
**阵容采集**: V41.284 (Supersonic Harvest - 429 智能避让)
**工业审计**: V41.283 (Industrial Auditor - 异步修复)
**Docker 版本**: V51.0 (Industrial Grade Ready)
**最后更新**: 2026-01-21
**基线准确率**: 56% (真赛前)
**生产状态**: Production Ready
**Python 版本**: 3.11+
