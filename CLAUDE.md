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
| **生产版本** | **V57.0** (版本大一统 + 智能自愈引擎) |
| **核心模型** | **V26.8** (联赛专项) + **V26.7** (通用底座) |
| **数据采集** | **V83.0** (L1/L2/L3 三层采集架构) |
| **特征引擎** | **V25.1** (万能自适应特征提取) |
| **收割引擎** | **V82.6** (OddsPortal 终盘提取) |
| **Docker 版本** | **V106.0** (Dockerfile + docker-compose.prod.yml) |
| **基线准确率** | 56% (真赛前) |
| **推理延迟** | <100ms |
| **最后更新** | 2026-01-05 |

### 核心技术栈

- **ML**: XGBoost 3.0+, scikit-learn, Playwright (浏览器自动化)
- **Backend**: Python 3.11+, FastAPI, PostgreSQL 15, Redis 7
- **DevOps**: Docker, Docker Compose, GitHub Actions
- **Code Quality**: Ruff (主要), Black, isort, flake8, MyPy, Bandit
- **Testing**: pytest, pytest-cov, pytest-asyncio

---

## ⚡ 快速开始

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

# FastAPI 服务
python src/main.py

# 生产预测服务（联赛专项模型）
python -m src.ops.production_service

# 生产收割引擎
python scripts/production_harvester.py
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

### L1/L2/L3 三层数据采集架构 (V83.0)

```
L1: FotMob API - 基础比赛数据
  └─ src/api/collectors/fotmob_core.py
     ├─ 比赛基础信息 (league, season, teams, match_time)
     ├─ 实时统计数据 (xG, shots, possession)
     └─ 哨兵机制 + 熔断恢复
              ↓
L2: FotMob Detail - 开盘赔率 (悬停提取)
  └─ src/api/collectors/odds_production_extractor.py
     ├─ extract_opening_via_hover() 方法
     ├─ 智能轮询 (wait_for_selector 60s)
     ├─ 悬停自愈 (鼠标抖动重试)
     └─ 提取目标: Pinnacle 开盘赔率 + 时间戳
              ↓
L3: OddsPortal - 终盘赔率 (直接提取)
  └─ src/api/collectors/odds_production_extractor.py
     ├─ extract_oddsportal_final_odds() 方法 (V82.6 集成)
     ├─ 选择器: .odds-text (排除 .odds-cell)
     ├─ 提取目标: Pinnacle 终盘赔率
     └─ 完整性审计: Score = 1/P1 + 1/P2 + 1/P3
              ↓
PostgreSQL 持久层
  └─ matches 表 (基础信息)
  └─ metrics_multi_source_data 表 (赔率数据)
```

### V83.0 清道夫行动 - 标准化重构

**第一阶段：目录重构**
- ✅ 创建 `legacy_research/` 存放旧版本脚本 (50 个文件)
- ✅ 移动 `audit_temp/` 到 `archive/logs/`
- ✅ 清理 `logs/` 下的旧版本日志文件

**第二阶段：生产代码固化**
- ✅ 将 V82.6 OddsPortal 提取逻辑整合到 `odds_production_extractor.py`
- ✅ 新增 `extract_oddsportal_final_odds()` 方法
- ✅ 统一 L2/L3 提取接口

### 核心目录结构

```
FootballPrediction/
├── src/                          # 生产代码
│   ├── api/                      # API 层
│   │   ├── collectors/           # 数据采集器 (V83.0 L1/L2/L3)
│   │   │   ├── odds_production_extractor.py  # 统一提取接口
│   │   │   ├── fotmob_core.py    # L1 FotMob API 基础数据
│   │   │   └── epl_*.py          # 英超专项采集器
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
│   ├── services/                 # 业务服务层
│   └── main.py                   # FastAPI 入口
├── scripts/                      # 核心脚本
│   ├── production_harvester.py   # V56.4 生产收割引擎
│   ├── v82_0_grand_harvest.py    # V82.6 全量收割
│   ├── v82_6_final_extractor.py  # V82.6 最终提取器
│   ├── v88_*.py                  # V88.x 数据回填和清理脚本
│   ├── health_check.py           # 健康检查脚本
│   └── sql/                      # SQL 脚本目录
├── tests/                        # 测试套件
│   ├── ml/                       # ML 测试
│   ├── ops/                      # 运维测试
│   └── unit/                     # 单元测试
├── legacy_research/              # V83.0: 旧版本脚本归档
├── archive/                      # 历史归档
│   └── logs/                     # 旧日志和审计文件
├── model_zoo/                    # 模型仓库 (.pkl 文件)
├── .github/workflows/            # CI/CD 配置
├── .claude/                      # Claude Code 技能配置
├── docker-compose.yml            # Docker 编排
├── Makefile                      # 统一命令入口
├── requirements.txt              # 生产依赖
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

### V83.0 统一提取引擎 (odds_production_extractor.py)

三层采集架构的统一接口，位于 `src/api/collectors/odds_production_extractor.py`：

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

## 🛡️ 工程规范约束

**Claude Code 必须严格遵守以下核心约束**（🔴 RED 级别）：

---

### 约束优先级（从高到低）

1. **Context Lock** - P0 核心模块修改需人工授权
2. **Architecture Boundary** - 维护清晰的层次结构
3. **Test Guard** - 确保测试的真实价值
4. **Minimal Change** - 修改行数越少越好
5. **Change Impact** - 分析变更影响

---

### 1. 核心冻结模块清单（Context Lock）

#### 🔒 P0 级别 - 预测服务核心（严禁修改）

| 文件 | 保护原因 | 禁止操作 | 允许操作 |
|------|----------|----------|----------|
| `src/ml/inference/predictor.py` | 金融级精度预测引擎（1349行） | 修改预测算法、变更接口签名 | Bug修复（需完整回归测试） |
| `src/ml/inference/model_loader.py` | 模型生命周期管理（651行） | 修改加载流程、变更缓存策略 | 补充测试用例 |
| `src/services/inference_service.py` | 企业级依赖注入架构 | 重构依赖注入、修改服务编排 | 性能监控埋点 |

#### 🔒 P1 级别 - 数据流水线（需严格审批）

| 文件 | 保护原因 | 禁止操作 |
|------|----------|----------|
| `src/ml/data/postgres_loader.py` | 生产级数据加载（377行） | 修改 SQL 查询逻辑、变更数据转换规则 |
| `src/ml/features/extractor.py` | 金融级特征工程（1198行） | 修改特征计算公式、调整业务验证规则 |

#### 🔒 P2 级别 - 高覆盖率模块（修改需完整测试）

```python
HIGH_COVERAGE_MODULES = [
    "src/api/health.py",              # API 健康检查
    "src/config_unified.py",          # 统一配置管理
    "src/database/connection.py",     # 数据库连接
    "src/core/exceptions.py",         # 核心异常处理
    "src/constants/football_logic.py", # 业务常量
]
```

---

### 2. 架构边界约束（Architecture Boundary）

#### 层次职责边界

**Adapters/Collectors 层** (`src/api/collectors/`)
- ✅ 外部 API 数据获取、协议转换
- ❌ 禁止包含业务规则判断
- ❌ 禁止直接调用 Services 层

**Services 层** (`src/services/`)
- ✅ 核心业务逻辑编排、依赖注入管理
- ❌ 禁止直接依赖 Adapters 具体实现
- ❌ 禁止包含数据转换逻辑

**Domain/Models 层** (`src/ml/models/`, `src/ml/inference/`)
- ✅ ML 模型定义、核心预测逻辑
- ❌ 禁止依赖外部资源
- ❌ 禁止包含数据库操作

**Data Access 层** (`src/ml/data/`, `src/database/`)
- ✅ 数据库连接管理、数据加载抽象
- ❌ 禁止包含业务逻辑

**Tasks/Pipelines 层**
- ✅ 任务调度和编排、ML 流水线管理
- ❌ 禁止写具体业务判断
- ❌ 禁止直接操作外部 API

#### 严禁的跨层操作

```python
# ❌ 错误示例 - Services 直接调用 Adapters
from scripts.collectors.fotmob_collector import FotMobCollector
class InferenceService:
    def __init__(self):
        self.collector = FotMobCollector()  # 违规！

# ✅ 正确示例 - 通过接口抽象
from abc import ABC, abstractmethod
class DataCollectorInterface(ABC):
    @abstractmethod
    async def collect_match_data(self, match_id: str): ...

class Service:
    def __init__(self, collector: DataCollectorInterface): ...
```

---

### 3. 最小修改策略（Minimal Change）

#### 核心原则
- 稳定性优先，禁止不必要的重构
- 每次修改必须是最小必要改动
- 禁止为了"美观"或"个人偏好"的修改

#### 禁止行为
1. **禁止新建文件**，除非现有文件确实无法满足需求
2. **禁止创建版本类文件**：
   - ❌ `*_v2`, `*_new`, `*_alt`, `*_backup`
   - ❌ `*_old`, `*_legacy`, `*_refactored`
3. **禁止重构优化**，除非存在明确的 bug 或性能问题

#### 修改前必须说明
```markdown
**修改文件**: [文件路径]
**修改内容**: [函数/类/方法]
**修改原因**: [最小必要原因，不超过50字]
```

#### 修改粒度控制
- 单次修改不超过 50 行
- 单个 PR 修改文件不超过 5 个
- 避免连锁修改

---

### 4. 测试保护约束（Test Guard）

#### 测试失败处理优先级
1. **修复源码** (首选) - 保持测试断言不变，修复源码问题
2. **修正测试** (备选) - 仅当测试确实不合理时
3. **放宽断言** (禁止) - 绝对禁止为了通过测试而放宽断言

#### 禁止的断言弱化
```python
# ❌ 禁止使用
assert True  # 无意义
assert not None  # 过于宽泛
assert result is not None  # 应该检查具体内容
assert response.status_code == 200  # 应该同时检查响应内容

# ✅ 推荐使用
assert prediction.home_win == 0.65
assert prediction.confidence > 0.6
assert all(0 <= p <= 1 for p in probabilities)
```

#### 修改测试前必须说明
```markdown
**测试文件**: [测试文件路径]
**原测试问题**: [为什么原测试不合理]
**新测试价值**: [新测试覆盖了什么真实业务行为]
**风险评估**: [修改可能带来的风险]
```

---

### 5. 变更影响分析（Change Impact）

#### 代码生成前的必检项
```markdown
## 📋 变更影响分析报告

### 🎯 修改文件列表
1. [文件路径1] - [修改类型]
2. [文件路径2] - [修改类型]

### 🔗 潜在影响模块
#### 直接影响
- [模块名1] - [影响描述]
#### 间接影响
- [模块名2] - [影响描述]

### 🧪 建议回归测试范围
- [测试用例1] - [测试原因]

### ⚠️ 风险评估
- **确定性风险**: [具体风险]
- **总体风险等级**: 🟢低/🟡中/🔴高
```

#### 风险等级判定
| 风险等级 | 标准 | 决策权限 |
|----------|------|----------|
| 🟢 低风险 | 单文件修改，无依赖变化 | 可自行决策 |
| 🟡 中风险 | 多文件修改，局部依赖变化 | 需要代码审查 |
| 🔴 高风险 | 跨模块修改，架构变化 | 需要架构师审批 |
| ⚫ 极高风险 | 架构重大变更，技术栈切换 | 需要团队决策 |

---

### ⚠️ 强制命名规范

**严禁创建任何带有 `_v1`, `_v2`, `_v17`, `_v18` 等版本后缀的新文件！**

**正确做法**:
- ✅ 直接修改现有文件
- ✅ 使用类继承实现功能扩展
- ✅ 使用策略模式实现算法切换

**错误做法**:
- ❌ `pipeline_v27.py` → 应修改 `pipeline.py`
- ❌ `feature_extractor_v28.py` → 应继承 `BaseExtractor`

---

### 约束违规处理流程

1. ⚠️ **检测到违规** → 自动分析违规类型
2. 🚫 **阻止操作** → 停止生成代码
3. 📝 **要求说明** → 提供违规原因和修正建议
4. ✅ **人工确认** → 获得授权后才可继续

> 详见 [`.claude/`](.claude/) 目录下的完整约束文档

---

## 🚀 部署与运维

### Docker 部署架构

项目提供两套 Docker Compose 配置：

| 配置文件 | 用途 | 适用场景 |
|----------|------|----------|
| `docker-compose.yml` | 开发环境配置 | 本地开发和测试 |
| `docker-compose.prod.yml` | 生产环境配置 (V106.0) | 生产部署 |

**V106.0 生产级特性**：
- 多阶段构建（Dockerfile）
- 资源限制和预留
- 健康检查和自动重启
- 安全加固（no-new-privileges、只读文件系统）
- 日志轮转配置
- 网络隔离（自定义 bridge 网络）

**生产部署命令**：
```bash
# 使用生产配置启动
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

### Pre-commit Hooks

项目配置了 pre-commit hooks (`.pre-commit-config.yaml`)，在提交代码前自动执行检查：

**安装 pre-commit**：
```bash
pip install pre-commit
pre-commit install
```

**自动执行的检查**：
- Ruff Lint 和格式化
- MyPy 类型检查
- Bandit 安全扫描
- 通用检查（尾随空格、YAML 语法等）
- Dockerfile Lint

**手动运行所有 hooks**：
```bash
pre-commit run --all-files
```

### Docker 服务清单

docker-compose.yml 包含以下服务：

| 服务 | 用途 | Profile | 状态 |
|------|------|---------|------|
| **db** | PostgreSQL 15 数据库 | 默认 | 核心服务 |
| **redis** | Redis 7 缓存 | 默认 | 核心服务 |
| **pipeline_worker** | V25.1 数据流水线 | pipeline/all | 按需 |
| **predictor_api** | FastAPI 预测服务 | api/all | 按需 |
| **production_cron** | 自动化调度器 (每天 3:00) | automation/all | 按需 |
| **odds_scraper** | 赔率数据采集服务 | odds/all | 按需 |
| **db_backup** | 数据库自动备份 (每天 2:00) | backup/all | 按需 |
| **dashboard** | 战神仪表盘 | dashboard/dev/all | 可选 |
| **pgadmin** | PostgreSQL 管理界面 | dev/all | 开发 |
| **redis-commander** | Redis 管理界面 | dev/all | 开发 |

**注意**: `db_backup` 和 `production_cron` 服务需要安装 `croniter` 包，通过 `pip install croniter` 安装。

### Docker Profile 使用

```bash
# 默认启动 - 核心服务 (db + redis)
docker-compose up -d

# 启动数据流水线
docker-compose --profile pipeline up -d

# 启动 API 服务
docker-compose --profile api up -d

# 启动自动化调度
docker-compose --profile automation up -d

# 启动开发环境（含管理工具: pgadmin, redis-commander）
docker-compose --profile dev up -d

# 启动所有服务
docker-compose --profile all up -d

# 启动战神仪表盘
docker-compose --profile dashboard up -d
# 或使用: make dashboard
```

### 关键 SQL 查询

```sql
-- 查看 Pinnacle 捕获率
SELECT
    ROUND(100.0 * COUNT(opening_time_h) / COUNT(*), 2) as pinnacle_capture_rate
FROM metrics_multi_source_data
WHERE source_name = 'Entity_P';

-- 查看数据完整性评分分布
SELECT
    CASE
        WHEN integrity_score < 1.02 THEN 'Too Low'
        WHEN integrity_score > 1.08 THEN 'Too High'
        ELSE 'Valid'
    END as score_category,
    COUNT(*) as count
FROM metrics_multi_source_data
WHERE source_name = 'Entity_P' AND integrity_score IS NOT NULL
GROUP BY score_category;
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

## 📝 附录

### 测试目录结构

```
tests/
├── unit/           # 单元测试
├── integration/    # 集成测试
├── e2e/            # 端到端测试
├── api/            # API 测试
│   └── collectors/ # 采集器测试
├── ml/             # 机器学习测试
├── ops/            # 运维测试
├── performance/    # 性能测试
├── data_pipeline/  # 数据流水线测试
├── v2/             # V2 版本测试
└── legacy/         # 遗留测试
```

### 测试指南

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

**按类型运行测试**：
```bash
pytest tests/unit/ -v              # 单元测试
pytest tests/integration/ -v       # 集成测试
pytest tests/e2e/ -v               # 端到端测试
pytest tests/api/ -v               # API 测试
pytest tests/ml/ -v                # ML 测试
pytest tests/ops/ -v               # 运维测试
```

**高级测试选项**：
```bash
# 运行单个测试文件
pytest tests/ml/test_v26_feature_engine.py -v
pytest tests/unit/test_config.py -v

# 运行特定测试用例
pytest tests/unit/test_config.py::test_database_config -v

# 并行运行测试 (需要 pytest-xdist)
pytest tests/ -n auto

# 按标记运行测试
pytest tests/ -m "not slow"         # 跳过慢速测试
pytest tests/ -m "integration"      # 只运行集成测试
pytest tests/ -m "unit"             # 只运行单元测试

# 查看测试覆盖率详情
pytest tests/ --cov=src --cov-report=term-missing
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

### 场景 2: 调试数据采集问题

当数据采集器出现问题时：

1. **检查采集器日志** `tail -f logs/auto_harvest.log`
2. **运行健康检查** `python scripts/health_check.py`
3. **使用测试脚本验证特定 URL** `python scripts/test_navigation.py`
4. **检查 IP 是否被封禁** (HTTP 429/403 错误)
5. **如果被封禁，等待 6-24 小时冷却期**

```bash
# 运行诊断脚本
python scripts/v82_1_diagnostic_probe.py

# 测试特定比赛提取
python scripts/v82_6_final_extractor.py --match_id <MATCH_ID>
```

### 场景 3: 部署新模型到生产环境

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

### 场景 5: 处理 API 采集封禁

当遇到 API 采集被封禁时：

1. **识别封禁类型**：
   - HTTP 429 Too Many Requests - 请求频率限制
   - HTTP 403 Forbidden - IP 被封
   - Connection timeout - 网络问题

2. **自动恢复策略** (已在 V56.3 实现)：
   - 连续 3 次连接错误 → 5 分钟冷却
   - 智能轮询替代硬等待
   - 降低采集频率 (2-5 秒延迟)

3. **手动干预**：
   - 检查 `logs/auto_harvest.log` 确认封禁
   - 等待 6-24 小时自然冷却
   - 或更换 IP/代理后重试

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

### 约束技能（优先级最高）

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

**🧬 当前版本**: V57.0 (版本大一统 + 智能自愈引擎)
**Docker 版本**: V106.0 (Dockerfile + docker-compose.prod.yml)
**最后更新**: 2026-01-05
**基线准确率**: 56% (真赛前)
**生产状态**: Production Ready
**项目愿景**: 年化 25% 收益率
**Python 版本**: 3.11+ (支持 3.12) |
