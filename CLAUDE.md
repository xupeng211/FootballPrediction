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
| **生产版本** | **V144.7** (Multi-Source Command Center) |
| **核心模型** | **V26.8** (联赛专项) + **V26.7** (通用底座) |
| **数据采集** | **V144.5** (FotMob) + **V144.2** (OddsPortal + Ghost Protocol) |
| **收割服务** | **V142.0** (HarvesterService) |
| **特征引擎** | **V25.1** (万能自适应特征提取) |
| **Docker 版本** | **V106.0** (Dockerfile + docker-compose.prod.yml) |
| **基线准确率** | 56% (真赛前) |
| **推理延迟** | <100ms |
| **最后更新** | 2026-01-06 |

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
```

### 快速诊断

| 问题 | 解决方案 |
|------|----------|
| `connection refused` | `docker-compose up -d db` |
| `db_password 不能为空` | 在 `.env` 中配置 |
| `Module import error` | `pip install -r requirements.txt` |
| `HTTP 429/403` | API 采集被封禁，等待 6-24 小时冷却 |

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
│   ├── v82_0_grand_harvest.py    # V82.6 全量收割
│   ├── v82_6_final_extractor.py  # V82.6 最终提取器
│   ├── v88_*.py                  # V88.x 数据回填和清理脚本
│   ├── health_check.py           # 健康检查脚本
│   ├── check_data_quality.py     # 数据质量检查
│   ├── dashboard.py              # V139.0 监控仪表盘
│   ├── run_checks.sh             # 质量门禁脚本
│   └── sql/                      # SQL 脚本目录
├── tests/                        # 测试套件
│   ├── ml/                       # ML 测试
│   ├── ops/                      # 运维测试
│   ├── unit/                     # 单元测试
│   └── mocks/                    # Mock 数据
├── legacy_research/              # 旧版本脚本归档
├── archive/                      # 历史归档
│   └── logs/                     # 旧日志和审计文件
├── model_zoo/                    # 模型仓库 (.pkl 文件)
├── .github/workflows/            # CI/CD 配置
├── .claude/                      # Claude Code 技能配置
├── main.py                       # V142.0 统一命令入口 ⭐
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

---

## 🛠️ 技术栈

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **语言** | Python | 3.11+ | 核心开发语言 |
| **数据库** | PostgreSQL | 15 | 生产数据存储 |
| **缓存** | Redis | 7 | 分布式缓存 |
| **浏览器** | Playwright | 1.49 | 智能网页自动化 |
| **ML 框架** | XGBoost | 3.0+ | 预测模型 |
| **Web** | FastAPI | 0.124 | REST API |
| **测试** | Pytest | 9.0 | 单元测试 |
| **容器** | Docker | 24+ | 容器化部署 |

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
| V149.0 | 2026-01-06 | SchemaManager API 修复，Circuit Breaker 硬编码 | 需更新数据库 schema 调用方式 |
| V148.5 | 2026-01-05 | Final Master Sweep - 160 模块稳定 | 旧脚本已归档至 scripts/archive/ |
| V148.0 | 2026-01-04 | 总攻最终生产基线 | 需重新训练模型 |
| V144.7 | 2026-01-06 | Multi-Source Command Center | 需更新 main.py 调用方式 |
| V142.0 | 2025-12-30 | HarvesterService 重构 | 旧脚本已移至 scripts/archive/ |
| V141.0 | 2025-12-28 | Ghost Protocol 集成 | 需更新采集器基类 |
| V140.0 | 2025-12-25 | TeamNameNormalizer | 队名匹配逻辑变更 |
| V26.8 | 2025-12-20 | 联赛专项模型分发器 | 需更新模型路径配置 |
| V26.7 | 2025-12-18 | 19 维对齐特征 | 需重新计算特征 |

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

---

## 🤖 技能自动调用机制

项目配置了专业化技能（`.claude/skills/`），Claude Code 会根据任务自动加载对应技能：

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

**🧬 当前版本**: V144.7 (Multi-Source Command Center)
**Docker 版本**: V106.0 (Dockerfile + docker-compose.prod.yml)
**最后更新**: 2026-01-06
**基线准确率**: 56% (真赛前)
**生产状态**: Production Ready
**项目愿景**: 年化 25% 收益率
**Python 版本**: 3.11+ (支持 3.12) |
