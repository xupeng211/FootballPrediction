# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 🚨 语言要求（最高优先级）

**请务必使用中文回复用户！**

---

## 📋 项目概览

**FootballPrediction** - 基于 XGBoost 2.0+ 的专业足球比赛预测系统

**项目愿景**: 以年化 25% 的真实收益率为北极星指标，构建可验证、可复制、可持续的体育预测系统

### 当前系统状态

| 属性 | 值 |
|------|-----|
| **状态** | ✅ Production Ready |
| **生产版本** | **V26.7** (全链路收割可靠性验证 - 生产级工业标准) |
| **命令中心** | **V144.7** (Multi-Source Command Center) |
| **核心模型** | **V26.8** (联赛专项) + **V26.7** (通用底座) |
| **数据采集** | **V144.5** (FotMob) + **V144.2** (OddsPortal + Ghost Protocol) + **V26.6** (全球数据扩充) |
| **收割服务** | **V142.0** (HarvesterService) |
| **特征引擎** | **V25.1** (万能自适应特征提取) + **V26.7** (特征清单管理器) |
| **Docker 版本** | **V106.0** (Dockerfile + docker-compose.prod.yml) |
| **基线准确率** | 56% (真赛前) |
| **推理延迟** | <100ms |
| **最后更新** | 2026-01-07 |

### 核心技术栈

- **ML**: XGBoost 3.0+, scikit-learn, Playwright (浏览器自动化)
- **Backend**: Python 3.11+, FastAPI, PostgreSQL 15, Redis 7
- **DevOps**: Docker, Docker Compose, GitHub Actions
- **Code Quality**: Ruff (主要), Black, isort, flake8, MyPy, Bandit
- **Testing**: pytest, pytest-cov, pytest-asyncio

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

### 环境要求

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15

### 核心开发命令

```bash
# 启动核心服务 (db + redis)
make up

# 运行代码质量检查（提交前必需）
make verify

# 统一命令入口 (V144.7) - 推荐方式
python main.py --mode single --league "Premier League" --season "23/24"

# V144.7: 多数据源支持
python main.py --source fotmob --mode single --limit 10      # FotMob API 数据源
python main.py --source oddsportal --mode single --limit 10  # OddsPortal RPA 数据源
python main.py --source fotmob --mode cruise                 # FotMob 24h 巡航模式

# 24h 全自动巡航模式
python main.py --mode cruise

# 数据质量检查
python main.py --mode check

# 测试代理连接 (V144.7)
python main.py --test-proxy

# FastAPI 服务
python src/main.py

# 生产预测服务（联赛专项模型）
python -m src.ops.production_service

# V26.6: 历史数据回填
python scripts/maintenance/fotmob_historical_backfill.py              # 回填所有联赛
python scripts/maintenance/fotmob_historical_backfill.py --league-id 47 --years 5  # 回填指定联赛
python scripts/maintenance/fotmob_historical_backfill.py --dry-run     # 干跑模式

# V26.7: 特征管理和离线解析
python scripts/ops/check_db_consistency.py                           # 数据库一致性检查
python scripts/ops/lock_feature_manifest.py                          # 特征清单锁定
python scripts/maintenance/reprocess_from_local.py                   # 离线特征重解析
```

### 快速诊断

| 问题 | 解决方案 |
|------|----------|
| `connection refused` | `docker-compose up -d db` |
| `db_password 不能为空` | 在 `.env` 中配置 |
| `Module import error` | `pip install -r requirements.txt` |
| `HTTP 429/403` | API 采集被封禁，等待 6-24 小时冷却 |

---

## ⚙️ 配置状态说明

### MCP 工具配置
- ⚠️ **部分配置未实现**：`.claude/settings.json` 中原本配置了 postgres/redis/filesystem/system-monitor 服务器，
  但实际只有 `git_server.py` 可用
- ✅ **当前可用工具**：Git log (read-only) - 位于 `.claude/mcp_servers/git_server.py`
- 📝 **配置已简化**：2026-01-08 已清理配置文件，移除未实现的服务器

### Skills 配置
- ⚠️ **状态未验证**：`.claude/skills/` 目录包含 15+ 个详细技能定义文档，
  但自动加载机制未经验证
- 📖 **参考用途**：技能文档可作为项目功能参考和架构理解
- 🔧 **配置已禁用**：2026-01-08 已将 `skills.enabled` 设为 `false`

### 对开发的影响
- ✅ **核心功能不受影响**：所有核心功能（数据采集、ML 模型、API 服务）都正常工作
- ✅ **本文档仍然有效**：CLAUDE.md 中的命令、架构和最佳实践都是准确的
- ℹ️ **使用标准工具**：优先使用本文档中明确的命令（如 `python main.py`、`make verify`）
- ℹ️ **技能文档作为参考**：`.claude/skills/` 目录中的文档可用于理解项目架构和功能

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
│  │  • single: 单次收割 (指定联赛/赛季)                        │
│  │  • cruise: 24h 全自动巡航                                  │ │
│  │  • check: 数据质量检查                                     │ │
│  │  • --test-proxy: 代理连接测试                              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│  环境预检: WSL2 检测、代理自动发现、IP 检测                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    HarvesterService (V142.0)                     │
│  src/api/services/harvester_service.py                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  队列驱动架构 (match_search_queue)                         │ │
│  │  Ghost Protocol 集成 (BaseExtractor V141.0)                │ │
│  │  全路径试错匹配 (TeamNameNormalizer V140.0)                │ │
│  │  信号处理 (SIGINT/SIGTERM)                                 │ │
│  │  优雅关闭机制                                               │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    BaseExtractor (V141.0)                        │
│  src/api/collectors/base_extractor.py                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Ghost Protocol - V144.0 增强指纹混淆                      │ │
│  │  • 30+ 主流浏览器指纹池 (Chrome/Edge/Safari/Firefox)      │ │
│  │  • 5 种常见屏幕分辨率随机化                                │ │
│  │  • 人类行为模拟 (滚动 + 点击噪声)                          │ │
│  │  • 深度拦截检测 (Cloudflare, IP 封禁)                      │ │
│  │  • 自动错误截图 (logs/error_screens/)                      │ │
│  │  • WSL2 自动代理发现                                       │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    TeamNameNormalizer (V140.0)                   │
│  src/utils/text_processor.py                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  全路径试错匹配                                             │ │
│  │  • 处理多连字符队名 (e.g., "Manchester United")           │ │
│  │  • Fuzzy matching 算法                                     │ │
│  │  • 去重保护 + 详细日志                                     │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    PostgreSQL 持久层
              matches 表 + metrics_multi_source_data 表
```

### V26.6 全球数据支持（2026-01-06 新增）

V26.6 引入**FotMob 全球数据扩充系统**，在 OddsPortal 冷却期间扩展数据采集范围：

```
┌─────────────────────────────────────────────────────────────────┐
│                    V26.6 全球联赛注册表                          │
│  src/api/collectors/fotmob_league_registry.py                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  31 个全球联赛完整元数据                                    │ │
│  │  • 欧洲 (17): 英超、西甲、德甲、意甲、法甲、葡超、荷甲等 │ │
│  │  • 美洲 (4): 美职联、巴甲、阿甲、墨超                        │ │
│  │  • 亚洲 (7): 日职联、中超、K联赛、沙特超、澳超等           │ │
│  │  • 非洲 (3): 南非超、埃及超、尼日利亚超                      │ │
│  │                                                            │ │
│  │  Tier 质量分级系统:                                        │ │
│  │  • Tier 1 Premium: 5 大联赛（英超、西甲、德甲、意甲、法甲） │ │
│  │  • Tier 2 Standard: 次级联赛（英冠、葡超、荷甲等）         │ │
│  │  • Tier 3 Basic: 低级别联赛（印超、南非超等）               │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    V26.6 配置管理系统                             │
│  src/config/harvest_config.py + config/global_harvest_list.yaml  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  YAML 配置文件，轻松启用/禁用联赛                          │ │
│  │  • enabled: true/false 开关控制                            │ │
│  │  • seasons: 赛季列表（23/24, 24/25, 2024, 2025）            │ │
│  │  • 采集任务列表自动生成                                    │ │
│  │  • V26.5 哨兵配置集成                                      │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    V26.6 历史回填引擎                              │
│  scripts/maintenance/fotmob_historical_backfill.py               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  自动发现历史比赛 ID（3-5 年）                             │ │
│  │  批量采集比赛数据                                          │ │
│  │  哨兵系统集成（自动停机保护）                              │ │
│  │  断点续传 + 干跑模式                                       │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**全球联赛覆盖清单**：

**Tier 1 Premium (5 大联赛)**：
- ✅ 英超 (47) - Premier League
- ✅ 西甲 (87) - La Liga
- ✅ 德甲 (78) - Bundesliga
- ✅ 意甲 (126) - Serie A
- ✅ 法甲 (53) - Ligue 1

**Tier 2 Standard (17 个次级联赛)**：
- ✅ 英冠 (48) - Championship
- ✅ 西乙 (94) - Segunda División
- ✅ 德乙 (95) - 2. Bundesliga
- ✅ 意乙 (127) - Serie B
- ✅ 葡超 (155) - Liga Portugal
- ✅ 荷甲 (129) - Eredivisie
- ✅ 比甲 (118) - Jupiler Pro League
- ✅ 苏超 (157) - Scottish Premiership
- ✅ 土超 (201) - Süper Lig
- ✅ 希超 (96) - Super League Greece
- ✅ 俄超 (153) - Premier League Russia
- ✅ 乌超 (186) - Premier Liha
- ✅ 美职联 (203) - MLS
- ✅ 巴甲 (274) - Serie A Brazil
- ✅ 日职联 (345) - J-League Division 1
- ✅ 沙特超 (410) - Saudi Pro League
- ✅ 澳超 (312) - A-League

**Tier 3 Basic (9 个基础联赛)**：
- ✅ 阿甲 (275) - Liga Profesional
- ✅ 墨超 (298) - Liga MX
- ✅ 中超 (322) - Chinese Super League
- ✅ K联赛 (353) - K-League 1
- ✅ 阿联酋职业联赛 (411) - ADNOC Pro League
- ✅ 印超 (397) - Indian Super League
- ✅ 南非超 (288) - Premier Soccer League
- ✅ 埃及超 (287) - Premier League
- ✅ 尼日利亚职业足球联赛 (412) - NPFL

**V26.6 核心特性**:
- ✅ **全球覆盖**: 31 个联赛，涵盖欧洲、美洲、亚洲、非洲四大洲
- ✅ **Tier 分级**: 3 个质量等级，优先采集高价值联赛
- ✅ **配置驱动**: YAML 配置文件，轻松启用/禁用联赛
- ✅ **历史回填**: 自动发现和采集 3-5 年历史数据
- ✅ **哨兵兼容**: 100% 兼容 V26.5 安全锁和监控系统

### 旧版本脚本归档

以下脚本已被移动到 `scripts/archive/` 目录 (V142.0 标准化重构):
- `production_harvester.py` (旧版收割引擎)
- `v117_1_monitor_harvest.sh/sql`
- `v120_0_init_search_queue.py`
- `v121_*.py` (测试脚本)
- `v126_*.py` ~ `v139_*.py` (探索性版本)
- `v54_6_url_sniffer.py` → `scripts/exploration/`

### 核心目录结构

```
FootballPrediction/
├── src/                          # 生产代码
│   ├── api/                      # API 层
│   │   ├── collectors/           # 数据采集器 (V141.0/V142.0)
│   │   │   ├── base_extractor.py     # V141.0 Ghost Protocol 基类
│   │   │   ├── odds_production_extractor.py  # 赔率提取
│   │   │   ├── fotmob_core.py        # L1 FotMob API 基础数据
│   │   │   └── epl_*.py              # 英超专项采集器
│   │   ├── services/           # 业务服务层 (V142.0)
│   │   │   └── harvester_service.py  # 统一收割服务
│   │   ├── v1/endpoints/         # API 路由
│   │   └── schemas.py            # 数据模型
│   ├── config_unified.py         # 统一配置管理
│   ├── core/                     # 核心引擎
│   ├── database/                 # 数据库层 (migrations, models)
│   ├── ml/                       # ML 引擎
│   │   ├── engine.py             # XGBoost 引擎 + ModelDispatcher
│   │   ├── features/             # 特征工程
│   │   └── inference/            # 推理服务
│   ├── processors/               # V25.1 特征提取
│   │   └── feature_manifest.py   # V26.7 特征清单管理器
│   ├── utils/                    # 工具类
│   │   └── text_processor.py     # V140.0 TeamNameNormalizer
│   └── main.py                   # FastAPI 入口
├── scripts/                      # 核心脚本
│   ├── archive/                  # V142.0: 旧版本脚本归档
│   │   ├── v117_*.py ~ v139_*.py
│   │   └── production_harvester.py
│   ├── debug/                    # V144.7: 调试脚本归档
│   │   ├── diagnose_network.py
│   │   ├── diagnose_slug_parsing.py
│   │   ├── diagnose_url_filtering.py
│   │   ├── debug_ip_reputation.py
│   │   ├── debug_proxy_rotation.py
│   │   ├── capture_mock_html.py
│   │   ├── extract_inline_data.py
│   │   └── analyze_api_samples.py
│   ├── exploration/              # 探索性脚本
│   │   └── debug_v54_6_url_sniffer.py
│   ├── maintenance/              # 维护脚本
│   │   ├── fotmob_historical_backfill.py  # V26.6 历史回填
│   │   └── reprocess_from_local.py       # V26.7 离线解析
│   ├── ops/                      # 运维脚本
│   │   ├── check_db_consistency.py       # V26.7 一致性检查
│   │   └── lock_feature_manifest.py      # V26.7 特征锁定
│   ├── sql/                      # SQL 脚本目录
│   │   └── v26_7_*.sql           # V26.7 数据库迁移脚本
│   ├── v82_0_grand_harvest.py    # V82.6 全量收割
│   ├── v82_6_final_extractor.py  # V82.6 最终提取器
│   ├── v88_*.py                  # V88.x 数据回填和清理脚本
│   ├── health_check.py           # 健康检查脚本
│   ├── check_data_quality.py     # 数据质量检查
│   ├── dashboard.py              # V139.0 监控仪表盘
│   └── run_checks.sh             # 质量门禁脚本
├── tests/                        # 测试套件
│   ├── ml/                       # ML 测试
│   ├── ops/                      # 运维测试
│   ├── unit/                     # 单元测试
│   └── mocks/                    # Mock 数据
├── legacy_research/              # 旧版本脚本归档
├── archive/                      # 历史归档
│   └── logs/                     # 旧日志和审计文件
├── model_zoo/                    # 模型仓库 (.pkl 文件)
├── config/                       # 配置文件
│   └── v26_feature_manifest.json # V26.7 特征清单 (6346维锁定)
├── .github/workflows/            # CI/CD 配置
├── .claude/                      # Claude Code 技能配置
├── main.py                       # V144.7 统一命令入口 ⭐
├── docker-compose.yml            # Docker 编排
├── docker-compose.prod.yml       # 生产环境配置
├── Dockerfile                    # Docker 镜像构建
├── Makefile                      # 统一命令入口
├── requirements.txt              # 生产依赖
├── pyproject.toml                # Poetry 配置
├── ruff.toml                     # Ruff 配置
├── pytest.ini                    # Pytest 配置
├── mypy.ini                      # MyPy 配置
├── .env.example                  # 环境变量模板
└── CLAUDE.md                     # 本文件
```

---

## 🔗 关键文件依赖图

### 数据流依赖链

```
main.py → HarvesterService → BaseExtractor → TeamNameNormalizer
                          ↓
                    OddsProductionExtractor → PostgreSQL
                          ↓
                    V25ProductionExtractor → 特征计算 → ML Engine
```

### 修改影响评估表

| 修改文件 | 直接影响 | 间接影响 | 必须运行的测试 |
|---------|---------|---------|---------------|
| `src/api/collectors/base_extractor.py` | 所有采集器 | 无 | `tests/api/collectors/` |
| `src/utils/text_processor.py` | 所有采集器 | 数据匹配 | `tests/unit/test_config.py` |
| `src/processors/v25_production_extractor.py` | 特征提取 | ML 预测 | `tests/ml/test_v26_feature_engine.py` |
| `src/ml/engine.py` | 推理服务 | API 预测 | `tests/legacy/test_ml_inference.py` |
| `src/api/services/harvester_service.py` | 数据收割 | 特征计算 | `tests/integration/test_services_integration.py` |
| `src/config_unified.py` | 全局配置 | 所有模块 | `tests/unit/test_config.py` |
| `main.py` | 命令入口 | 数据采集 | `tests/integration/test_cli.py` |

### 变更验证路径

**场景 1: 修改核心业务逻辑**
```bash
修改代码 → 单元测试 → 代码质量检查 → 集成测试 → 手动验证 → 提交
   ↓         ↓          ↓            ↓           ↓        ↓
  编辑    pytest    make verify   pytest -m   main.py   git
  文件     specific   (lint+test)  integration  --test   commit
```

**场景 2: 修改数据采集器**
```bash
修改代码 → 采集器测试 → 干跑验证 → 完整测试 → 提交
   ↓         ↓          ↓          ↓        ↓
  编辑    pytest    main.py     make     git
  文件     -k collector  --dry-run  verify  commit
```

**场景 3: 修改 ML 特征工程**
```bash
修改代码 → ML 测试 → 特征验证 → 回测验证 → 提交
   ↓         ↓          ↓          ↓        ↓
  编辑    pytest    特征维度    回测     git
  文件     tests/     检查      脚本    commit
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

**重要环境差异**:
| 环境 | `DB_HOST` | `DB_NAME` |
|------|-----------|-----------|
| Docker | `db` | `football_db` |
| 本地开发 | `localhost` | `football_db` |

### 数据库连接标准

```python
from src.config_unified import get_settings
from psycopg2.extras import RealDictCursor

settings = get_settings()
conn = psycopg2.connect(
    host=settings.database.host,
    port=settings.database.port,
    database=settings.database.name,
    user=settings.database.user,
    password=settings.database.password.get_secret_value(),
    cursor_factory=RealDictCursor
)
```

### 核心数据库表结构

**matches 表** - 比赛基础信息
```sql
match_id          VARCHAR(50) PRIMARY KEY
league_name       VARCHAR(255)
season            VARCHAR(20)
home_team         VARCHAR(255)
away_team         VARCHAR(255)
match_time        TIMESTAMP
l2_raw_json       JSONB           -- FotMob L2 原始数据
l3_features       JSONB           -- V25.1 特征向量
```

**metrics_multi_source_data 表** - 赔率数据
```sql
match_id          VARCHAR(50) REFERENCES matches(match_id)
source_name       VARCHAR(50)     -- Entity_P (Pinnacle), Entity_B3 (1xBet)
init_h/d/a        FLOAT           -- 开盘赔率
opening_time_h/d/a TIMESTAMP      -- 开盘时间
final_h/d/a       FLOAT           -- 终盘赔率
integrity_score   FLOAT           -- 完整性分数: 1/P1 + 1/P2 + 1/P3
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

-- 查找需要重新处理的比赛
SELECT match_id, league_name, season
FROM matches
WHERE l2_raw_json IS NOT NULL
  AND l3_features IS NULL
LIMIT 10;
```

### 代码质量规范

**提交代码前必须运行**:
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
| 工具 | 优先级 | 用途 | 备注 |
|------|--------|------|------|
| **Ruff** | 🔴 主要 | 格式化 + Lint | 替代 Black、flake8、isort |
| **MyPy** | 🟡 推荐 | 类型检查 | 需配置 `mypy.ini` |
| **Bandit** | 🟡 推荐 | 安全扫描 | 检测常见安全问题 |
| Black | 🟢 备用 | 格式化 | 当 Ruff 不可用时 |
| flake8 | 🟢 备用 | Lint | 当 Ruff 不可用时 |
| isort | 🟢 备用 | 导入排序 | 当 Ruff 不可用时 |

**类型注解要求**: 所有函数必须包含类型注解
```python
# ✅ 正确
def predict_match(home_team: str, away_team: str) -> dict[str, float]:
    ...

# ❌ 错误
def predict_match(home_team, away_team):
    ...
```

### Makefile 命令参考

```bash
# 服务管理
make help              # 显示所有可用命令
make up                # 启动核心服务 (db + redis)
make up-pipeline       # 启动核心服务 + 数据流水线
make up-api            # 启动核心服务 + API
make up-dev            # 启动开发环境 (含管理工具: pgadmin, redis-commander)
make up-all            # 启动所有服务
make down              # 停止所有服务
make restart           # 重启核心服务 (pipeline_worker)

# 代码质量
make verify            # 运行完整验证 (lint + test + security)
make test              # 运行全量测试
make test-unit         # 运行单元测试
make lint              # 代码风格检查 (ruff/flake8)
make format            # 格式化代码 (ruff/black)
make security          # 安全扫描 (bandit)

# 数据库操作
make db-shell          # 进入 PostgreSQL Shell (database: football_db)
make db-backup         # 备份数据库
make db-reset          # 重置数据库 (危险操作!)
make redis-shell       # 进入 Redis CLI

# 日志和监控
make logs              # 查看核心服务日志
make logs-api          # 查看 API 日志
make logs-all          # 查看所有服务日志
make ps                # 查看容器状态
make health            # 检查服务健康状态
make dashboard         # 启动战神仪表盘

# 清理命令
make clean             # 清理垃圾文件和缓存
make clean-csv         # 清理临时 CSV 文件
make clean-logs        # 清理过期日志文件
make clean-docker      # 清理 Docker 资源
make clean-all         # 完全清理 (所有清理操作)

# 部署
make deploy            # 部署到生产环境
```

### CI 质量门禁 (run_checks.sh vs make verify)

**方式一：完整质量门禁** (推荐用于 CI/CD)
```bash
./scripts/run_checks.sh  # 执行 7 步完整检查
```

**方式二：快速验证** (推荐用于本地开发)
```bash
make verify  # 执行 lint + test-unit + security
```

**run_checks.sh 完整检查列表**：
```bash
# 1. 导入排序检查 (isort)
# 2. 代码格式化检查 (ruff format/black)
# 3. Lint 检查 (ruff check/flake8)
# 4. 类型检查 (mypy)
# 5. 单元测试 (pytest) - 运行 test_backtest_engine.py 和 test_signal_generator.py
# 6. 模型性能回归测试 (accuracy >= 55%)
# 7. 安全扫描 (bandit)
```

**注意**: `make verify` 是快速验证（3 步），`./scripts/run_checks.sh` 是完整质量门禁（7 步）。如需运行全量测试，使用 `pytest tests/ -v`。

### GitHub Actions CI/CD 流程

项目使用 GitHub Actions 进行持续集成和部署，配置文件位于 `.github/workflows/ci.yml`：

**CI 流程包含以下任务**：

1. **quality-checks** - 代码质量检查
   - Black 格式化检查
   - isort 导入排序检查
   - flake8 Lint 检查
   - MyPy 类型检查
   - Bandit 安全扫描
   - Vulture 死代码检测

2. **unit-tests** - 单元测试
   - 启动 db 和 redis 服务
   - 运行单元测试并生成覆盖率报告
   - 上传覆盖率到 Codecov

3. **integration-tests** - 集成测试
   - 启动完整服务栈
   - 初始化数据库 schema
   - 运行集成测试
   - 测试特征提取功能

4. **build-test** - 构建测试
   - 构建发布包
   - 使用 twine 检查包完整性

5. **performance-test** - 性能测试
   - 运行性能基准测试

6. **docs-build** - 文档构建
   - 使用 mkdocs 构建项目文档
   - 仅在存在 `mkdocs.yml` 时执行

7. **deploy-staging** - 部署到测试环境
   - 仅在 `develop` 分支触发
   - 依赖于 quality-checks 和测试任务

---

## 🧬 核心模块说明

### main.py - V144.7 Multi-Source Command Center

项目的主要入口点，提供统一命令行界面，支持多数据源路由：

```bash
# V144.7: 多数据源支持
python main.py --source fotmob --mode single --limit 10      # FotMob API 数据源
python main.py --source oddsportal --mode single --limit 10  # OddsPortal RPA 数据源
python main.py --source fotmob --mode cruise                 # FotMob 24h 巡航模式

# 单次收割模式
python main.py --mode single --league "Premier League" --season "23/24"

# 24h 全自动巡航模式
python main.py --mode cruise

# 数据质量检查
python main.py --mode check

# 测试代理连接 (V144.7)
python main.py --test-proxy

# 禁用 Ghost Protocol (调试用)
python main.py --mode single --no-ghost

# 限制处理数量
python main.py --mode single --limit 50

# 干跑模式 (不实际采集)
python main.py --mode single --dry-run
```

**V144.7 新特性**:
- `--source` 参数支持数据源切换 (oddsportal/fotmob)
- 路由到 `run_oddsportal_mode()` 或 `run_fotmob_mode()` 处理器
- Ghost Protocol 统一验证日志

**多源路由实现** (main.py:239-310):
```python
# OddsPortal 模式
async def run_oddsportal_mode(args) -> int:
    """V144.7: Run OddsPortal harvesting mode."""
    service = HarvesterService(
        mode="single" if args.mode == "single" else "cruise",
        enable_ghost_protocol=not args.no_ghost,
        enable_queue=not args.no_queue,
        limit=args.limit,
        dry_run=args.dry_run,
        proxy_file=args.proxy_file,
    )
    await service.run()
    return 0

# FotMob 模式
async def run_fotmob_mode(args) -> int:
    """V144.7: Run FotMob harvesting mode."""
    from src.api.collectors.fotmob_core import FotMobCoreCollector
    collector = FotMobCoreCollector()
    logger.info(f"[V144.7] 🛡️ Unified Ghost Protocol initialized for fotmob")
    return 0
```

**环境预检功能**:
- WSL2 环境检测
- 代理自动发现 (环境变量 → WSL2 自动探测 → 直连)
- IP 地址检测
- 数据库连接检查
- 日志目录自动创建

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
    proxy_file="proxies.txt"    # 代理配置文件
)
await service.run()
```

**核心特性**:
- 队列驱动架构 (match_search_queue)
- Ghost Protocol 集成 (BaseExtractor V141.0)
- 全路径试错匹配 (TeamNameNormalizer V140.0)
- 信号处理 (SIGINT/SIGTERM)
- 优雅关闭机制
- 流量弹性 (V142.5)

### BaseExtractor - V141.0 Ghost Protocol

位于 `src/api/collectors/base_extractor.py`，提供反爬检测基础能力：

```python
from src.api.collectors.base_extractor import BaseExtractor

extractor = BaseExtractor(auto_proxy=True)

# 获取随机 UA
ua = extractor.get_random_user_agent()

# 获取随机视口
viewport = extractor.get_random_viewport()

# 获取代理配置 (WSL2 自动发现)
proxy_config = extractor.get_proxy_config()

# 创建浏览器上下文
context = await browser.new_context(
    user_agent=ua,
    viewport=viewport,
    proxy=proxy_config
)
```

**Ghost Protocol 特性**:
- 30+ 主流浏览器指纹池 (Chrome/Edge/Safari/Firefox)
- 5 种常见屏幕分辨率随机化
- 人类行为模拟 (滚动 + 点击噪声)
- 深度拦截检测 (Cloudflare, IP 封禁)
- 自动错误截图 (logs/error_screens/)
- WSL2 自动代理发现

### TeamNameNormalizer - V140.0 全路径试错匹配

位于 `src/utils/text_processor.py`，处理队名标准化和匹配：

```python
from src.utils.text_processor import TeamNameNormalizer

normalizer = TeamNameNormalizer()

# 标准化队名
normalized = normalizer.normalize_team_name("Manchester United")

# 全路径试错匹配
matched = normalizer.fuzzy_match_team_name(
    raw_name="man-utd",
    candidates=["Manchester United", "Manchester City", ...]
)
```

### OddsProductionExtractor - V82.6 统一提取引擎

位于 `src/api/collectors/odds_production_extractor.py`：

```python
from src.api.collectors.odds_production_extractor import OddsProductionExtractor

extractor = OddsProductionExtractor()

# L2: FotMob 开盘赔率 (悬停提取)
result = await extractor.extract_opening_via_hover(
    page=page,
    entity_code="Entity_P",
    match_date=datetime(2024, 4, 20)
)

# L3: OddsPortal 终盘赔率 (直接提取)
result = await extractor.extract_oddsportal_final_odds(
    url="https://www.oddsportal.com/match/...",
    match_id=12345
)
```

**V82.6 核心修复**：
- 只选择 `.odds-text` 元素（排除 `.odds-cell`）
- 避免同一值被重复提取
- 正确提取主、平、客赔率

### ModelDispatcher (V26.8)

联赛专项模型自动分发，位于 `src/ml/engine.py:668`：

```python
from src.ml.engine import ModelDispatcher

dispatcher = ModelDispatcher()
prediction = dispatcher.predict(
    home_team="Arsenal",
    away_team="Chelsea",
    league_name="Premier League"  # 自动选择 EPL 专项模型
)
```

**支持的联赛专项模型**:
- `model_zoo/v26.8_epl_production.pkl` - 英超
- `model_zoo/v26.8_la_liga_production.pkl` - 西甲
- `model_zoo/v26.8_ligue1_production.pkl` - 法甲
- `model_zoo/v26.8_bund_production.pkl` - 德甲

### ML 引擎多版本代码说明

`src/ml/engine.py` 包含多个历史版本（**这是有意保留的**）：

| 类名 | 版本 | 用途 |
|------|------|------|
| `V17MLEngine` | V17.0 | 滚动特征训练引擎（16维特征） |
| `V26Predictor` | V26.4 | 统一推理接口 |
| `ModelDispatcher` | V26.8 | 联赛专项模型分发器 |

**新增代码应遵循**: 优先使用 `ModelDispatcher` 进行预测，训练新模型时可参考 `V17MLEngine`。

### V26.7 核心特征

19 维完全对齐的赛前特征，通过 `src/database/schema_manager.py` 动态计算：

```python
V26_7_FEATURES = [
    # 滚动特征 (8个) - 最近 N 场历史平均值
    "rolling_xg_home", "rolling_xg_away",
    "rolling_shots_on_target_home", "rolling_shots_on_target_away",
    "rolling_possession_home", "rolling_possession_away",
    "rolling_team_rating_home", "rolling_team_rating_away",

    # 积分榜特征 (7个) - 赛前已知
    "home_table_position", "away_table_position", "table_position_diff",
    "home_points", "away_points", "points_diff",
    "home_recent_form_points",

    # 高级特征 (4个) - 动态计算
    "raw_elo_gap", "adjusted_elo_gap",
    "home_fatigue_index", "away_fatigue_index",
]
```

### V56.4 生产收割引擎

三层架构实现自动化赔率数据收割：

```python
from scripts.production_harvester import ProductionHarvester

harvester = ProductionHarvester()
stats = await harvester.run()
```

**核心特性**:
1. 智能轮询 - `wait_for_selector(60s)` 替代硬等待
2. 悬停自愈 - 鼠标抖动自动重试
3. IP 健康监控 - 连续 3 次错误 → 5 分钟冷却
4. 数据完整性审计 - `Score = 1/P1 + 1/P2 + 1/P3`

### HarvestConfigManager - V26.6 配置管理系统

位于 `src/config/harvest_config.py`，管理全球联赛采集配置：

```python
from src.config.harvest_config import get_config_manager

# 获取配置管理器单例
config_manager = get_config_manager()

# 查看配置摘要
config_manager.print_summary()

# 获取启用的联赛
enabled_leagues = config_manager.get_enabled_leagues()

# 按 Tier 获取联赛
tier1_leagues = config_manager.get_leagues_by_tier(tier=1)  # 5 大联赛

# 生成采集任务列表
tasks = config_manager.get_harvest_tasks()
```

**核心特性**:
- YAML 配置文件驱动 (`config/global_harvest_list.yaml`)
- 31 个全球联赛元数据管理
- 联赛启用/禁用状态控制
- 采集任务列表自动生成
- V26.5 哨兵配置集成

### FotMobHistoricalBackfill - V26.6 历史回填引擎

位于 `scripts/maintenance/fotmob_historical_backfill.py`：

```bash
# 回填所有启用的联赛（默认 3 年）
python scripts/maintenance/fotmob_historical_backfill.py

# 回填指定联赛
python scripts/maintenance/fotmob_historical_backfill.py --league-id 47 --years 5

# 干跑模式（不实际采集）
python scripts/maintenance/fotmob_historical_backfill.py --dry-run

# 禁用哨兵系统
python scripts/maintenance/fotmob_historical_backfill.py --no-sentry
```

**核心特性**:
- 自动发现历史比赛 ID（3-5 年）
- 批量采集比赛数据
- 哨兵系统集成（自动停机保护）
- 断点续传支持
- 干跑模式（测试用）

### CollectionSentry - V26.5 自动巡航哨兵

位于 `src/api/collectors/collection_sentry.py`：

```python
from src.api.collectors.collection_sentry import CollectionSentry

# 初始化哨兵系统
sentry = CollectionSentry(
    window_size=100,
    success_rate_threshold=0.7,
    consecutive_failure_threshold=5,
    pause_duration_hours=12
)

# 记录采集结果
sentry.record_result(success=True)

# 检查是否应该停机
if sentry.should_stop():
    logger.warning("⚠️ 哨兵触发：成功率过低，自动停机保护")
```

**核心特性**:
- 滑动窗口统计（最近 N 个结果）
- 成功率监控（低于 70% 触发停机）
- 连续失败监控（超过 6 次触发停机）
- 自动设置冷却期（12 小时）

### FeatureManifest - V26.7 特征清单管理器

位于 `src/processors/feature_manifest.py`，实现"特征字典锁定"确保不同批次间的特征严格对齐：

```python
from src.processors.feature_manifest import FeatureManifest

# 加载特征清单
manifest = FeatureManifest.from_file("config/v26_feature_manifest.json")

# 获取必需特征列表
required_features = manifest.get_required_features()

# 获取特征别名映射
aliases = manifest.get_feature_aliases()

# 验证特征清单完整性
is_valid = manifest.validate()
```

**核心特性**:
- 固定特征清单（6346 维锁定）
- 验证提取的特征是否符合清单
- 填充缺失特征，确保所有比赛的特征维度一致
- 导出标准化特征字典（用于离线解析）
- 特征别名映射（API 字段名 → 标准特征名）

### V26.7 离线解析能力

位于 `scripts/maintenance/reprocess_from_local.py`，实现"零网络请求"下的特征重解析：

```bash
# 从数据库读取 l2_raw_json，使用 V25ProductionExtractor 离线生成特征
python scripts/maintenance/reprocess_from_local.py

# 指定比赛 ID
python scripts/maintenance/reprocess_from_local.py --match-id 12345

# 干跑模式
python scripts/maintenance/reprocess_from_local.py --dry-run
```

**核心特性**:
- 零网络请求的离线特征重解析
- 从数据库读取 `l2_raw_json` 数据
- 使用 `V25ProductionExtractor` 生成特征
- 支持单场比赛或批量处理
- 干跑模式验证

### V26.7 数据库一致性工具

位于 `scripts/ops/check_db_consistency.py`，检查数据库特征一致性：

```bash
# 检查数据库一致性
python scripts/ops/check_db_consistency.py

# 检查指定联赛
python scripts/ops/check_db_consistency.py --league "Premier League"

# 修复不一致
python scripts/ops/check_db_consistency.py --fix
```

**核心特性**:
- 检查特征维度一致性
- 检测缺失或多余特征
- 自动修复不一致数据
- 生成一致性报告

### V26.7 League ID 数字骨架升级

V26.7 引入 League ID 字段，实现双重识别（ID + Name）：

**Schema 迁移脚本**:
```bash
# 添加 League ID 字段
psql -U football_user -d football_db -f scripts/sql/v26_7_add_league_id.sql

# 数据标签清理
psql -U football_user -d football_db -f scripts/sql/v26_7_data_label_cleanup.sql

# 历史数据对齐
psql -U football_user -d football_db -f scripts/sql/v26_7_history_alignment.sql
```

**核心特性**:
- League ID 字段添加
- 双重识别（ID + Name）
- 性能与可读性兼顾
- 历史数据自动对齐

### src/core - V105.0 核心基础设施

位于 `src/core/__init__.py`，提供系统级基础设施：

```python
from src.core import Config, Logger, config, logger
from src.core import CircuitBreaker, GracefulShutdownManager, get_logger
```

**核心功能**:
- **配置管理** (`Config`): 统一的配置读写和持久化机制
  - 配置文件存储在 `~/.footballprediction/config.json`
  - 自动处理文件不存在或格式错误的情况
  - 支持内存配置更新和持久化

- **日志系统** (`Logger`, `ComponentLogger`): 结构化日志管理
  - 支持多种日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - 事件代码系统 (EventCode) 用于日志分类
  - 性能计时器 (performance_timer) 用于性能监控

- **异常处理**:
  - `FootballPredictionError`: 基础异常类
  - `ConfigError`: 配置相关异常
  - `DataError`: 数据处理异常

- **熔断器** (`CircuitBreaker`): V105.0 新增
  - 防止级联故障
  - 自动恢复机制
  - 预定义熔断器: `api_breaker`, `database_breaker`, `network_breaker`

- **优雅关闭** (`GracefulShutdownManager`): V105.0 新增
  - SIGINT/SIGTERM 信号处理
  - 资源清理保证
  - 上下文管理器支持

**使用示例**:
```python
from src.core import get_logger, log_context, performance_timer

logger = get_logger("my_module")

# 结构化日志上下文
with log_context(module="my_module", operation="harvest"):
    logger.info("开始数据采集")

# 性能计时
with performance_timer("operation_name"):
    # 执行操作
    pass
```

### 新增运维脚本

V150.0+ 新增运维脚本，位于 `scripts/ops/`:

| 脚本 | 功能 |
|------|------|
| `e2e_link_test.py` | 端到端链接测试 |
| `check_url_health.py` | URL 健康检查 |
| `smoke_test_production.py` | 生产环境冒烟测试 |
| `dashboard_quality.py` | 数据质量仪表盘 |
| `harvest_fotmob_full.py` | FotMob 全量收割 |
| `harvest_pinnacle_odds.py` | Pinnacle 赔率收割 |

---

## 🛠️ 技术栈

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **语言** | Python | 3.11+ | 核心开发语言 |
| **数据库** | PostgreSQL | 15 | 生产数据存储 |
| **缓存** | Redis | 7 | 分布式缓存 |
| **浏览器** | Playwright | 1.57 | 智能网页自动化 |
| **反爬检测** | playwright-stealth | 2.0 | 浏览器指纹混淆 |
| **ML 框架** | XGBoost | 3.0+ | 预测模型 |
| **数据处理** | pandas | 2.2.3 | 数据分析 |
| **数据压缩** | brotli | 1.0+ | API 响应解压 |
| **Web** | FastAPI | 0.124 | REST API |
| **测试** | Pytest | 9.0 | 单元测试 |
| **容器** | Docker | 24+ | 容器化部署 |
| **代码质量** | Ruff | 0.8+ | 格式化 + Lint |
| **类型检查** | MyPy | 1.8+ | 静态类型检查 |
| **安全扫描** | Bandit | 1.9+ | 安全漏洞检测 |

---

## ⚡ 性能基准

### 推理性能
- 单次预测延迟: <100ms (P95)
- 批量预测 (100 场): <5s

### 数据采集性能
- FotMob API 采集: ~50 场/分钟
- OddsPortal RPA: ~10 场/分钟 (受网络和反爬限制)

### 数据库性能
- 特征提取查询: <500ms (单场)
- 批量特征插入: 1000 场 <30s

### 性能监控
```bash
# 运行性能基准测试
pytest tests/performance/test_inference_performance.py -v

# 检查实际性能
python scripts/health_check.py --benchmark
```

---

## 🐛 常见错误速查表

| 错误信息 | 可能原因 | 快速解决方案 |
|---------|---------|-------------|
| `psycopg2.OperationalError: FATAL: database "football_db" does not exist` | 数据库未初始化 | `make up` 后运行 `docker-compose exec db psql -U football_user -c "CREATE DATABASE football_db"` |
| `playwright._impl._api_types.TimeoutError: Timeout 30000ms exceeded` | 网络慢或页面加载慢 | 检查代理配置，增加 `BaseExtractor` 的 timeout 参数 |
| `KeyError: 'rolling_xg_home'` | 特征提取失败 | 检查 `matches` 表是否有足够的历史数据 |
| `AssertionError: Model file not found` | 模型文件缺失 | 运行模型训练脚本或从备份恢复 |
| `HTTP 429 Too Many Requests` | API 限流 | 等待 6-24 小时或使用代理轮换 |
| `HTTP 403 Forbidden` | IP 被封禁 | 检查代理配置，启用 Ghost Protocol |
| `ConnectionRefusedError: [Errno 61] Connect call failed ('127.0.0.1', 5432)` | 数据库未启动 | 运行 `make up` 启动数据库服务 |
| `ModuleNotFoundError: No module named 'src'` | Python 路径问题 | 确保在项目根目录运行，使用 `python -m` 方式运行模块 |
| `AttributeError: 'NoneType' object has no attribute 'predict'` | 模型加载失败 | 检查模型文件路径，验证模型格式 |
| `ValueError: cannot reindex on an axis with duplicate labels` | 数据重复 | 检查数据源，运行 `python main.py --mode check` |
| `asyncio.exceptions.CancelledError` | 任务被取消 | 检查是否有 SIGINT 信号，查看日志 |
| `Redis connection error` | Redis 未启动 | 运行 `make up` 确保 Redis 服务运行 |
| `TypeError: 'NoneType' object is not subscriptable` | API 返回空数据 | 检查 API 密钥，验证网络连接 |

### 调试流程

```bash
# 1. 检查服务状态
make ps

# 2. 查看日志
make logs

# 3. 运行健康检查
python scripts/health_check.py

# 4. 运行测试定位问题
pytest tests/ -v -k "test_name"

# 5. 检查配置
python -c "from src.config_unified import get_settings; print(get_settings())"
```

---

## 🚨 灾难恢复

### 数据库连接失败

```bash
# 检查数据库状态
docker-compose ps db
docker-compose exec db pg_isready -U football_user -d football_db

# 重启数据库
docker-compose restart db

# 查看数据库日志
docker-compose logs db
```

### API 采集器封禁

**症状**: HTTP 429 Too Many Requests 或 403 Forbidden

**恢复策略**:
1. 等待冷却期 (6-24 小时)
2. 降低采集频率 (延迟到 2-5 秒)
3. 使用增量采集器的断点续传功能

### 日志位置

| 日志类型 | 路径 |
|----------|------|
| 应用日志 | `logs/app.log` |
| 错误日志 | `logs/error.log` |
| 采集器日志 | `logs/auto_harvest.log` |

---

## 📚 版本历史与升级指南

### 近期重大版本

| 版本 | 日期 | 核心变更 | 升级注意事项 |
|------|------|---------|-------------|
| V26.7 | 2026-01-07 | 全链路收割可靠性验证 - 特征清单管理器、离线解析、数据库一致性 | 需运行 v26_7_* 数据库迁移脚本 |
| V149.0 | 2026-01-06 | SchemaManager API 修复，Circuit Breaker 硬编码 | 需更新数据库 schema 调用方式 |
| V148.5 | 2026-01-05 | Final Master Sweep - 160 模块稳定 | 旧脚本已归档至 scripts/archive/ |
| V148.0 | 2026-01-04 | 总攻最终生产基线 | 需重新训练模型 |
| V144.7 | 2026-01-06 | Multi-Source Command Center | 需更新 main.py 调用方式 |
| V142.0 | 2025-12-30 | HarvesterService 重构 | 旧脚本已移至 scripts/archive/ |
| V141.0 | 2025-12-28 | Ghost Protocol 集成 | 需更新采集器基类 |
| V140.0 | 2025-12-25 | TeamNameNormalizer | 队名匹配逻辑变更 |
| V26.8 | 2025-12-20 | 联赛专项模型分发器 | 需更新模型路径配置 |
| V26.7 (旧) | 2025-12-18 | 19 维对齐特征 | 需重新计算特征 |

### 升级前检查清单

- [ ] 备份数据库 (`make db-backup`)
- [ ] 备份模型文件 (`model_zoo/`)
- [ ] 运行完整测试 (`./scripts/run_checks.sh`)
- [ ] 检查 git diff 确认变更范围
- [ ] 准备回滚方案
- [ ] 阅读版本发布说明

### 升级流程

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 检查版本变更
git log --oneline -10

# 3. 备份数据
make db-backup

# 4. 运行测试
make verify

# 5. 应用数据库迁移（如有）
alembic upgrade head

# 6. 重启服务
make restart

# 7. 验证服务健康
make health
```

### 版本兼容性矩阵

| 组件版本 | Python | PostgreSQL | Docker | 备注 |
|---------|--------|------------|--------|------|
| V149.x | 3.11+ | 15 | 24+ | 最新稳定版 |
| V148.x | 3.11+ | 15 | 24+ | 生产推荐 |
| V144.x | 3.11+ | 15 | 24+ | 多数据源支持 |
| V142.x | 3.11+ | 15 | 24+ | HarvesterService |
| V140.x | 3.10+ | 14 | 20+ | 旧版本，建议升级 |

---

## 🔐 环境变量配置

### 必需的环境变量 (.env)

```bash
# 数据库配置
DB_HOST=localhost              # 或 db (Docker 环境)
DB_PORT=5432
DB_NAME=football_db
DB_USER=football_user
DB_PASSWORD=your_secure_password

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# API 配置
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
LOG_LEVEL=INFO

# 代理配置 (可选)
# PROXY_SERVER=http://172.25.16.1:7890
# HTTPS_PROXY=http://172.25.16.1:7890

# 哨兵配置 (V26.5)
COLLECTION_PAUSE_UNTIL=        # 哨兵暂停截止时间 (空 = 未暂停)
```

### 环境变量加载顺序

1. `.env` 文件 (项目根目录)
2. 系统环境变量
3. WSL2 自动代理发现 (仅 WSL2 环境)

### V138.0+ URL Harvest 配置

```bash
# URL 搜索并发 (L2 Layer)
URL_SEARCH_CONCURRENCY=4                # 并发搜索数量
URL_SEARCH_TIMEOUT_MS=30000             # 搜索超时时间
URL_SEARCH_RETRY_ATTEMPTS=3             # 重试次数

# URL 格式验证 (关键: 仅支持新格式)
URL_FORMAT_VALIDATE=true                # 启用格式验证
URL_ALLOW_NEW_FORMAT=true               # 允许新格式 URL
URL_ALLOW_LEGACY_FORMAT=false           # 禁用旧格式 URL (已废弃)
```

### V139.0 Auto Cruise Controller 配置

```bash
# 导航设置
CRUISE_NAVIGATION_DELAY_MS=2000         # 导航延迟
CRUISE_SCROLL_ATTEMPTS=3                # 滚动尝试次数
CRUISE_WAIT_FOR_SELECTOR_TIMEOUT_MS=60000  # 等待超时

# 提取设置
CRUISE_EXTRACT_CONCURRENCY=2             # 提取并发数
CRUISE_HOVER_RETRY_ATTEMPTS=10          # 悬停重试次数
CRUISE_HOVER_RETRY_DELAY_MS=500         # 悬停重试延迟

# 数据完整性
CRUISE_INTEGRITY_SCORE_MIN=1.02         # 最小完整性分数
CRUISE_INTEGRITY_SCORE_MAX=1.08         # 最大完整性分数
CRUISE_VALIDATE_PROBABILITIES=true      # 验证概率
```

### Playwright 浏览器配置

```bash
# 浏览器选择
PLAYWRIGHT_BROWSER_TYPE=chromium        # 浏览器类型
PLAYWRIGHT_HEADLESS=true               # 无头模式
PLAYWRIGHT_STEALTH_ENABLED=true         # 启用隐身模式

# 视口配置
PLAYWRIGHT_VIEWPORT_WIDTH=1920          # 视口宽度
PLAYWRIGHT_VIEWPORT_HEIGHT=1080         # 视口高度

# User-Agent 随机化
PLAYWRIGHT_RANDOM_UA=true               # 随机 UA

# 页面加载策略
PLAYWRIGHT_WAIT_UNTIL=networkidle       # 等待策略
PLAYWRIGHT_NAVIGATION_TIMEOUT_MS=90000  # 导航超时
```

### 业务逻辑配置

```bash
# 默认阈值
DEFAULT_CONFIDENCE_THRESHOLD=0.6       # 默认置信度阈值
MIN_EDGE=7.0                            # 最小优势
MIN_CONFIDENCE=45.0                     # 最小置信度
TARGET_ROI=13.35                        # 目标 ROI
```

### 备份与维护配置

```bash
# 数据库备份
BACKUP_ENABLED=false                    # 启用备份
BACKUP_INTERVAL_HOURS=24                # 备份间隔
BACKUP_RETENTION_DAYS=30                # 保留天数
BACKUP_PATH=backups/                    # 备份路径

# 日志清理
LOG_CLEANUP_ENABLED=true                # 启用日志清理
LOG_CLEANUP_DAYS=7                      # 清理天数
LOG_CLEANUP_INTERVAL_HOURS=24           # 清理间隔
```

---

## 🌿 Git 工作流建议

### 分支策略

```bash
# 主分支
main                    # 生产环境，永远保持稳定

# 开发分支 (按需创建)
feature/新功能名称       # 功能开发
fix/问题描述            # Bug 修复
refactor/模块名称       # 代码重构
hotfix/紧急修复         # 生产环境紧急修复
```

### 提交规范

```bash
# 提交格式
<type>(<scope>): <subject>

<body>

<footer>
```

**类型 (type)**:
- `feat`: 新功能
- `fix`: Bug 修复
- `refactor`: 代码重构
- `docs`: 文档更新
- `test`: 测试相关
- `chore`: 构建/工具链相关
- `perf`: 性能优化

**示例**:
```bash
git commit -m "feat(collectors): 添加 FotMob L3 采集器支持"
git commit -m "fix(database): 修复 l3_features 索引缺失问题"
git commit -m "refactor(harvester): 重构 HarvesterService 队列逻辑"
```

### 提交前检查清单

- [ ] 运行 `make verify` 通过
- [ ] 新功能有对应测试
- [ ] 更新了相关文档
- [ ] 代码符合项目风格
- [ ] 无遗留的 `TODO` 或调试代码

---

## ⚠️ 重要警告

### 禁止操作

- ❌ **不要直接修改** `model_zoo/` 中的模型文件（应重新训练）
- ❌ **不要在生产环境运行** `make db-reset`
- ❌ **不要跳过** `make verify` 直接提交代码
- ❌ **不要使用硬编码的数据库密码**
- ❌ **不要在采集器中包含业务逻辑判断**
- ❌ **不要创建版本类文件** (`*_v2`, `*_new`, `*_backup`)
- ❌ **不要为了"美观"进行不必要的重构**

### 必须操作

- ✅ **修改代码前必须运行** `git status` 确认分支
- ✅ **提交前必须运行** `make verify` 确保质量
- ✅ **修改核心模块前必须完成影响分析**
- ✅ **数据库变更前必须备份** (`make db-backup`)
- ✅ **新建文件前必须说明理由**（遵循 minimal_change 约束）
- ✅ **修改测试前必须提供充分理由**（遵循 test_guard 约束）
- ✅ **跨层修改前必须检查架构边界**（遵循 architecture_boundary 约束）

### 核心模块保护级别

| 模块 | 保护级别 | 修改要求 |
|------|----------|----------|
| `src/ml/inference/predictor.py` | P0 严格冻结 | 架构师 + 技术负责人双签 |
| `src/ml/inference/model_loader.py` | P0 严格冻结 | 架构师 + 技术负责人双签 |
| `src/services/inference_service.py` | P0 严格冻结 | 架构师 + 技术负责人双签 |
| `src/ml/data/postgres_loader.py` | P1 审批冻结 | 架构师审批 |
| `src/ml/features/extractor.py` | P1 审批冻结 | 架构师审批 |

---

## 📝 附录

### 测试目录结构

```
tests/
├── unit/           # 单元测试
├── integration/    # 集成测试
│   └── test_command_center.py  # V144.7 TDD 验收测试 (18/18 passed)
├── e2e/            # 端到端测试
├── api/            # API 测试
│   └── collectors/ # 采集器测试
├── ml/             # ML 测试
├── ops/            # 运维测试
├── performance/    # 性能测试
├── data_pipeline/  # 数据流水线测试
└── v2/             # V2 版本测试
```

### 测试指南

**pytest 标记（markers）**:
```bash
# 按标记运行测试
pytest -m unit                    # 只运行单元测试
pytest -m integration             # 只运行集成测试
pytest -m "not network"           # 排除需要网络的测试
pytest -m "network or slow"       # 运行网络或慢速测试
```

**可用标记**:
- `unit`: 单元测试
- `integration`: 集成测试
- `slow`: 慢速测试
- `network`: 需要网络的测试
- `e2e`: 端到端测试
- `performance`: 性能测试

**运行单个测试文件或测试用例**:
```bash
# 运行单个测试文件
pytest tests/unit/test_config.py -v

# 运行单个测试用例
pytest tests/unit/test_config.py::TestConfig::test_database_config -v

# 运行匹配关键词的测试
pytest -k "test_database" -v

# 显示打印输出
pytest tests/unit/test_config.py -v -s

# 失败时进入调试器
pytest tests/unit/test_config.py -v --pdb

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=html
pytest tests/ --cov=src --cov-report=term-missing  # 终端显示缺失行
```

**测试场景选择**：
```bash
# 场景 1: 本地开发快速反馈
make test-unit              # 只运行核心测试套件（2 个文件）

# 场景 2: 提交前完整验证
./scripts/run_checks.sh     # 完整质量门禁（7 步检查）

# 场景 3: 全量测试（CI 环境）
pytest tests/ -v            # 运行所有测试

# 场景 4: 调试单个测试文件
pytest tests/unit/test_config.py -v

# 场景 5: 生成覆盖率报告
pytest tests/ --cov=src --cov-report=html
```

### E2E 测试说明

端到端测试位于 `tests/e2e/` 目录，验证完整的系统功能：

```bash
# 运行所有 E2E 测试
pytest tests/e2e/ -v -m e2e

# 运行数据流水线 E2E 测试
pytest tests/e2e/test_data_pipeline_workflow.py -v

# 运行生产环境冒烟测试
pytest tests/e2e/test_production_smoke.py -v
```

**E2E 测试类型**:
| 测试文件 | 功能描述 | 运行时间 |
|----------|----------|----------|
| `test_data_pipeline_workflow.py` | 数据流水线端到端测试 | ~30s |
| `test_production_smoke.py` | 生产环境冒烟测试 | ~15s |

**E2E 测试运行前准备**:
```bash
# 1. 确保数据库服务运行
make up

# 2. 初始化测试数据库
docker-compose exec db psql -U football_user -c "CREATE DATABASE IF NOT EXISTS football_test_db"

# 3. 运行 E2E 测试
pytest tests/e2e/ -v -m e2e
```

### 新增采集器测试

V150.0+ 新增 `tests/unit/scrapers/` 目录，包含采集器单元测试：

```bash
# 运行采集器测试
pytest tests/unit/scrapers/ -v

# 运行 OddsPortal 采集器测试
pytest tests/unit/scrapers/test_oddsportal.py -v

# 生成采集器测试覆盖率报告
pytest tests/unit/scrapers/ --cov=core.scrapers --cov-report=html
```

**采集器测试覆盖**:
- 数据类 (ProxyConfig, CircuitBreakerConfig)
- 熔断器管理器状态转换
- 时区转换
- 紧急停止异常
- 人类行为模拟

---

## 🎯 常见开发场景快速指南

### 场景 1: 添加新的特征工程

当需要添加新特征时，请遵循以下步骤：

1. **在 `src/ml/features/` 下创建或修改特征提取器**
2. **确保特征有完整的类型注解**
3. **添加对应的单元测试到 `tests/ml/test_features.py`**
4. **运行 `make verify` 确保代码质量**
5. **更新模型训练脚本以包含新特征**

```python
# 示例：在 src/ml/features/custom_features.py 添加新特征
from typing import Any

def extract_custom_feature(match_data: dict[str, Any]) -> float:
    """提取自定义特征

    Args:
        match_data: 比赛数据字典

    Returns:
        特征值
    """
    # 实现特征提取逻辑
    return 0.0
```

### 场景 2: 使用统一命令入口进行数据收割

V144.7 推荐使用统一命令入口 `main.py` 进行数据收割，支持多数据源切换：

```bash
# V144.7: 多数据源支持
python main.py --source fotmob --mode single --limit 10      # FotMob API 数据源
python main.py --source oddsportal --mode single --limit 10  # OddsPortal RPA 数据源
python main.py --source fotmob --mode cruise                 # FotMob 24h 巡航模式

# 单次收割模式 - 指定联赛和赛季
python main.py --mode single --league "Premier League" --season "23/24"

# 24h 全自动巡航模式
python main.py --mode cruise

# 数据质量检查
python main.py --mode check

# 干跑模式 (不实际采集，用于测试)
python main.py --mode single --dry-run

# 限制处理数量 (用于快速测试)
python main.py --mode single --limit 50

# 禁用 Ghost Protocol (调试用)
python main.py --mode single --no-ghost
```

**代理配置** (V144.7):
- 环境变量: `export HTTPS_PROXY=http://host:port`
- WSL2 自动探测: 自动发现宿主机代理
- 代理文件: `python main.py --proxy-file proxies.txt`
- 测试代理: `python main.py --test-proxy`

### 场景 3: 调试数据采集问题

当数据采集器出现问题时：

1. **检查采集器日志** `tail -f logs/v142_0_main.log`
2. **运行健康检查** `python scripts/health_check.py`
3. **测试代理连接** `python main.py --test-proxy`
4. **检查 IP 是否被封禁** (HTTP 429/403 错误)
5. **如果被封禁，等待 6-24 小时冷却期**

```bash
# 运行诊断脚本
python scripts/diagnose_network.py

# 测试特定比赛提取
python scripts/v82_6_final_extractor.py --match_id <MATCH_ID>

# 调试单个采集器 (Python 方式)
python -m pytest tests/api/collectors/test_base_extractor.py -v -s --pdb
```

### 场景 3.1: 调试单个采集器

```bash
# 方法 1: 使用 pytest 调试
pytest tests/api/collectors/test_fotmob_core.py::TestFotMobCore::test_harvest_match -v -s

# 方法 2: 创建调试脚本
cat > debug_collector.py << 'EOF'
import asyncio
from src.api.collectors.fotmob_core import FotMobCoreCollector

async def main():
    collector = FotMobCoreCollector()
    result = collector.harvest_match_with_league("match_id_here")
    print(result)

asyncio.run(main())
EOF

python debug_collector.py

# 方法 3: 使用 Python 交互式调试
python -m pdb scripts/debug/capture_mock_html.py
```

### 场景 4: 部署新模型到生产环境

当需要部署新训练的模型时：

1. **将模型文件放入 `model_zoo/` 目录**
2. **更新 `ModelDispatcher` 中的模型映射** (`src/ml/engine.py`)
3. **添加模型元数据到配置文件**
4. **运行模型性能测试** `pytest tests/ml/test_model_performance.py`
5. **提交 PR 并通过 CI 检查**
6. **部署到生产环境** `make deploy`

```python
# 示例：在 ModelDispatcher 中添加新模型
# src/ml/engine.py
LEAGUE_MODEL_MAPPING = {
    "Premier League": "model_zoo/v26.8_epl_production.pkl",
    "La Liga": "model_zoo/v26.8_la_liga_production.pkl",
    # 添加新的联赛模型
    "Serie A": "model_zoo/v26.8_serie_a_production.pkl",
}
```

### 场景 4: 数据库迁移和 schema 变更

当需要修改数据库 schema 时：

1. **创建新的迁移文件** `alembic revision -m "描述"`
2. **编写升级和降级脚本**
3. **在本地测试迁移** `alembic upgrade head`
4. **备份数据库** `make db-backup`
5. **在生产环境执行迁移**

```bash
# 创建迁移
alembic revision -m "add_new_column_to_matches"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

### 场景 5: Docker 容器化部署

V106.0 多阶段生产级 Docker 构建：

**Dockerfile 特性**:
- **Builder 阶段**: 构建依赖和预编译字节码
- **Runtime 阶段**: 最小化运行时镜像
- **非特权用户**: `appuser` 用户运行容器
- **健康检查**: `/health` 端点健康监控

**构建镜像**:
```bash
# 构建生产镜像
docker-compose build

# 无缓存构建
docker-compose build --no-cache

# 构建测试镜像
docker build --target test -f deploy/Dockerfile -t footballprediction:test .
```

**Docker Compose 配置** (V30.0):
```bash
# 启动核心服务 (db + redis)
docker-compose up -d

# 启动核心服务 + 数据流水线
docker-compose --profile pipeline up -d

# 启动核心服务 + API 服务
docker-compose --profile api up -d

# 启动核心服务 + 自动化调度
docker-compose --profile automation up -d

# 启动开发环境 (含管理工具)
docker-compose --profile dev up -d

# 启动所有服务
docker-compose --profile all up -d
```

**服务配置说明**:

| 服务 | 功能 | 端口 | 资源限制 |
|------|------|------|----------|
| `db` | PostgreSQL 15 数据库 | 5432 | 2 CPU / 2G 内存 |
| `redis` | Redis 7 缓存服务 | 6379 | 0.5 CPU / 512M 内存 |
| `pipeline_worker` | V25.1 数据流水线 | - | 2 CPU / 2G 内存 |
| `predictor_api` | FastAPI 预测服务 | 8000 | 1 CPU / 1G 内存 |
| `dashboard` | 战神仪表盘 | - | 0.5 CPU / 512M 内存 |
| `db_backup` | 数据库自动备份 | - | 0.25 CPU / 256M 内存 |
| `odds_scraper` | 赔率数据采集 | - | 1 CPU / 1G 内存 |
| `production_cron` | 生产自动化调度 | - | 1 CPU / 1G 内存 |

**开发工具** (仅 dev profile):
| 服务 | 功能 | 端口 |
|------|------|------|
| `pgadmin` | PostgreSQL 管理 | 5050 |
| `redis-commander` | Redis 管理 | 8081 |

**Docker 环境变量**:
```bash
# .env 文件配置
DOCKER_ENV=true           # Docker 环境标识
DB_HOST=db                # Docker 内使用服务名
REDIS_HOST=redis          # Docker 内使用服务名
API_WORKERS=2             # API 工作进程数
```

**容器日志查看**:
```bash
# 查看核心服务日志
docker-compose logs -f pipeline_worker

# 查看 API 日志
docker-compose logs -f predictor_api

# 查看所有服务日志
docker-compose logs -f
```

---

## 🤖 技能自动调用机制

> ⚠️ **重要说明**：以下内容描述的是 `.claude/skills/` 目录中的技能定义，但自动加载机制未经验证。
> 技能文档应作为**项目功能参考**使用，而非实际的自动加载配置。
>
> 📝 **配置状态**：`skills.enabled` 已设为 `false`（2026-01-08）

项目配置了专业化技能（`.claude/skills/`），这些技能文档定义了项目的核心功能模块：

| 类别 | 技能 | 功能 |
|------|------|------|
| **核心业务** | `football-prediction` | XGBoost 2.0+ 预测 |
| | `machine-learning-engineering` | XGBoost 调优, SHAP |
| | `feature-engineering` | V25.1 自适应特征提取 (48→12061维) |
| | `data-collection` | FotMob API 数据采集 |
| | `v26-harvest` | V26.1 生产级收割流水线 |
| **开发工具** | `code-quality` | Ruff, MyPy, Bandit, pytest |
| | `fastapi-development` | FastAPI 开发 |
| | `api-testing` | API 单元/集成/性能测试 |
| **运维支撑** | `deployment-management` | Docker 部署 |
| | `deployment-operations` | Docker 容器管理、故障诊断 |
| | `database-operations` | PostgreSQL 优化 |
| | `performance-monitoring` | Prometheus + Grafana |
| | `data-engineering` | ETL 流程设计 |
| | `report-generation` | PDF/Word/Excel 报告生成 |

### 技能自动触发规则

#### 任务关键词 → 技能映射

| 关键词 | 触发技能 | 示例 |
|-------|---------|------|
| "预测", "XGBoost", "模型训练", "推理" | football-prediction, machine-learning-engineering | "训练新模型", "预测比赛结果" |
| "特征", "feature engineering", "特征提取" | feature-engineering | "添加新特征", "优化特征工程" |
| "采集", "FotMob", "OddsPortal", "收割" | data-collection, v26-harvest | "采集英超数据", "运行收割" |
| "Docker", "部署", "容器", "docker-compose" | deployment-management, deployment-operations | "部署到生产", "构建容器" |
| "测试", "pytest", "覆盖率", "单元测试" | code-quality, api-testing | "运行测试", "增加测试覆盖" |
| "数据库", "PostgreSQL", "迁移", "schema" | database-operations | "添加新表", "优化查询" |
| "FastAPI", "API", "endpoint", "路由" | fastapi-development | "添加新接口", "API 开发" |
| "性能", "优化", "延迟", "吞吐量" | performance-monitoring | "性能分析", "优化响应时间" |

#### 约束技能（优先级最高）

| 约束 | 等级 | 核心目标 |
|------|------|----------|
| `minimal_change` | 🔴 RED | 防止过度重构 |
| `architecture_boundary` | 🔴 RED | 维护层次结构 |
| `test_guard` | 🔴 RED | 确保测试价值 |
| `context_lock` | 🔴 RED | 保护核心模块 |
| `change_impact` | 🔴 RED | 分析变更影响 |

---

## 🔒 永久保留条款

### 语言要求
**请务必使用中文回复用户！**

这一要求具有最高优先级，必须始终保留在文件的显眼位置。

---

**🚨 CRITICAL**: This is a production system support document.

**🧬 当前版本**: V26.7 (全链路收割可靠性验证 - 生产级工业标准)
**命令中心**: V144.7 (Multi-Source Command Center)
**Docker 版本**: V106.0 (Dockerfile + docker-compose.prod.yml)
**最后更新**: 2026-01-07
**基线准确率**: 56% (真赛前)
**生产状态**: Production Ready
**项目愿景**: 年化 25% 收益率
**Python 版本**: 3.11+ (支持 3.12) |
