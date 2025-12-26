# CLAUDE.md

这个文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

---

## 📑 目录导航

- [🚨 语言要求（最高优先级）](#🚨-语言要求最高优先级)
- [🛡️ 工程规范约束](#️-工程规范约束)
- [⚡ 快速开始](#-快速开始)
- [🏗️ 系统架构](#️-系统架构)
- [📊 版本与特征](#-版本与特征)
- [🔧 开发指南](#-开发指南)
- [🚀 部署与运维](#-部署与运维)
- [🚨 故障处理](#️-故障处理)
- [🔬 实验性版本管理](#-实验性版本管理)
- [📊 监控与可观测性](#-监控与可观测性)

---

## 🚨 语言要求（最高优先级）

**请务必使用中文回复用户！**

这一要求具有最高优先级，无论 CLAUDE.md 文件如何更新版本迭代，都必须始终保留在文件的显眼位置。

## ⚠️ 当前系统状态

**当前版本**: V30.0 (Full Blood Cloud-Native)
**系统状态**: ✅ Production Ready
**架构**: 归一化部署架构 - Docker Compose Profiles
**代码规范**: 正常开发流程已恢复

**版本演进**:
- V30.0: Cloud-Native 归一化部署 (当前)
- V29.0: 服务解耦与配置优化
- V19.4.1: Boxing Day Production (稳定基线)

**实验性分支**: v34/v38/v39/v40 系列正在研发中（详见 `src/ml/miners_v34/`、`src/ml/models/v38_*.py`、`src/ml/features/v40_*.py`）

---

## 🛡️ 工程规范约束

**Claude Code 必须严格遵守以下定义在 `.claude/` 目录下的工程规范。**

### 核心技能文件
- **[.claude/context_lock.skill.md](.claude/context_lock.skill.md)** (🔒 核心资产冻结)
- **[.claude/architecture_boundary.skill.md](.claude/architecture_boundary.skill.md)** (🏗️ 架构分层约束)
- **[.claude/test_guard.skill.md](.claude/test_guard.skill.md)** (✅ 测试保护)
- **[.claude/change_impact.skill.md](.claude/change_impact.skill.md)** (📊 变更影响分析)
- **[.claude/minimal_change.skill.md](.claude/minimal_change.skill.md)** (🤏 最小修改原则)

### 约束优先级金字塔
1.  🔴 **Context Lock**: P0 核心模块修改需人工授权
2.  🟠 **Architecture Boundary**: 架构正确性 > 代码简洁性
3.  🟡 **Test Guard**: 功能正确性 > 性能优化
4.  🟢 **Minimal Change**: 满足上述条件后，修改行数越少越好

### 强制自检清单
在生成业务代码前检查：
- [ ] 我是否正在修改 P0 级别冻结文件？
- [ ] 我的修改是否引入了架构层反向依赖？
- [ ] 这个修改是否会破坏现有 API 契约？

---

## ⚡ 快速开始

### 🎯 项目概览

**FootballPrediction V19.4** - 基于 XGBoost 2.0+ 的专业足球比赛预测系统

**项目愿景**: 以年化 25% 的真实收益率为北极星指标，构建可验证、可复制、可持续的体育预测系统

| 属性 | 值 |
|------|-----|
| **状态** | ✅ Production Ready |
| **版本** | V30.0 (Full Blood Cloud-Native) |
| **基线版本** | V19.4.1 (65.52% 准确率) |
| **数据量** | 761 场英超 22/23 + 23/24 赛季 |
| **特征维度** | 48 维（滚动 + 赛前 + 高级动态 + 平局敏感度） |

**核心风险约束**（详见 `docs/PROJECT_VISION.md`）:
- 单笔下注 ≤ 5% 本金
- 严禁杠杆（0%）
- EV 区间 6%-10%
- 最大回撤 < 15%

### 🔧 技术栈
- **ML**: XGBoost 2.0+, scikit-learn, Isotonic 回归
- **Backend**: Python 3.11+, FastAPI, PostgreSQL 15, Redis 7
- **DevOps**: Docker, Docker Compose
- **Code Quality**: **Ruff** (主要，统一处理格式化+Lint), MyPy (类型检查), Bandit (安全扫描)
- **Testing**: pytest (单元测试), pytest-cov (覆盖率)
- **监控**: Prometheus, Grafana

> **注意**: Makefile 中保留 Black/Flake8 仅用于兼容性，日常开发请使用 Ruff

### 🎯 快速决策树

```
你的目标是什么？
│
├─ 新机器环境设置？
│  └─→ make dev && ./system_verify.sh
│
├─ 运行生产预测（推荐）？
│  └─→ python main_production.py --full-pipeline
│
├─ 代码质量检查？
│  └─→ ruff check src/ tests/ --fix && ruff format src/ tests/
│
├─ 运行测试？
│  └─→ ./scripts/run_checks.sh
│
├─ 启动 Docker 服务？
│  └─→ docker-compose up -d (核心服务) 或 make up-api (包含 API)
│
└─ 提交代码前检查？
   └─→ ./scripts/run_checks.sh
```

### ⚡ 日常开发 Top 6 命令

```bash
# 1. 快速开发环境设置
make dev

# 2. 生产流程（推荐）
python main_production.py --full-pipeline

# 3. 代码质量检查（Ruff）
ruff check src/ tests/ && ruff format src/ tests/

# 4. Docker 服务启动（多模式）
docker-compose up -d              # 核心服务 (pipeline_worker + db + redis)
docker-compose --profile api up -d  # 核心服务 + API
make up-api                        # 核心服务 + API (推荐)
make up-dev                        # 开发环境 (含管理工具)

# 5. 系统健康检查
./system_verify.sh

# 6. 快速测试（与 CI 一致）
pytest tests/ml/test_backtest_engine.py tests/ops/test_signal_generator.py -v
```

### 📋 常用命令速查表

| 操作 | 命令 | 耗时 |
|------|------|------|
| 环境准备 | `make dev` | ~2 分钟 |
| V19.4 流程 | `python main_production.py --full-pipeline` | ~15 分钟 |
| CI 完整检查 | `./scripts/run_checks.sh` | ~3 分钟 |
| 质量检查 | `ruff check src/ tests/ --fix` | ~30 秒 |
| 快速测试 | `pytest tests/ml/test_backtest_engine.py tests/ops/test_signal_generator.py -v` | ~2 分钟 |
| 系统验证 | `./system_verify.sh` | ~30 秒 |
| Docker 核心服务 | `docker-compose up -d` | ~1 分钟 |
| Docker + API | `make up-api` | ~1 分钟 |
| Docker 开发环境 | `make up-dev` | ~2 分钟 |

### 🎯 常见场景命令

```bash
# 新机器环境设置
make dev && ./system_verify.sh

# 提交前检查（推荐使用 CI 脚本）
./scripts/run_checks.sh

# 提交前检查（手动执行）
ruff check src/ tests/ --fix && pytest tests/ml/test_backtest_engine.py tests/ops/test_signal_generator.py -v

# 完整生产流程
python main_production.py --full-pipeline

# 系统健康检查
./system_verify.sh

# Boxing Day 实战检查（V19.4.1）
./verify_ready.sh
```

---

## 🏗️ 系统架构

### 📊 系统版本演进

#### 生产版本（推荐使用）
| 版本 | 核心特性 | 特征维度 | 准确率 | 状态 |
|------|----------|----------|--------|------|
| **V30.0** | Cloud-Native 归一化部署 | 48 维 | 65.52% | **当前 Docker** |
| **V19.4.1** | Boxing Day 生产版 + 风控集成 | 48 维 | 65.52% | **本地生产** |
| V17.0 | 滚动特征（基线） | 16 维 | 65.52% | 生产基线 |

#### 实验性版本（研发中）
| 版本 | 核心特性 | 特征维度 | 状态 |
|------|----------|----------|------|
| V18.0 | 赛前特征 + 平局优化 | 24 维 | 验证中 |
| V19.0 | 高级动态特征（ELO/疲劳/战意） | 39 维 | 实验中 |
| V20.x | 数据中台 + 高维特征引擎 | 800+ 维 | 实验性 |

### 🔄 V30.0 Cloud-Native 架构

**归一化部署架构** - 服务解耦与 Docker Compose Profiles:

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Orchestration              │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Default Profile (核心服务)                            │  │
│  │  - pipeline_worker: V30.0 Full Blood 流水线           │  │
│  │  - db: PostgreSQL 15 (健康检查 + 资源限制)            │  │
│  │  - redis: Redis 7 (LRU 缓存策略)                      │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  API Profile (按需启动)                                │  │
│  │  - predictor_api: FastAPI 预测服务 (uvicorn workers)  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Dev Profile (开发工具)                                │  │
│  │  - pgadmin: PostgreSQL Web 管理                       │  │
│  │  - redis-commander: Redis Web 管理                    │  │
│  │  - dashboard: 战神仪表盘                               │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Data Volumes (持久化)                                 │  │
│  │  - postgres_data, redis_data, app_data, app_logs      │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**多阶段 Dockerfile 优化**:
- Stage 1 (builder): 安装所有依赖 + 编译 C 扩展
- Stage 2 (runner): 只拷贝必要代码，镜像体积缩小 70% (~350MB)

### 🔄 数据流架构

```
FotMob API
    ↓
V11.0 哨兵机制（联赛分级动态哨兵）
    ↓
自适应解码 + 熔断机制
    ↓
PostgreSQL 存储
    ↓
L3 特征提取器（滚动特征 + 赛前特征）
    ↓
XGBoost 训练（24维/39维/48维特征数据集）
    ↓
概率校准（Isotonic 回归，V19+）
    ↓
模型评估 → 保存为生产模型 (.pkl)
```

### 📁 目录结构速查

```
FootballPrediction/
├── main_production.py         # V19.4 统一生产入口
├── docker-compose.yml         # V30.0 服务编排
│
├── src/
│   ├── config_unified.py      # 统一配置管理（Pydantic Settings）
│   ├── main.py                # FastAPI 应用入口
│   │
│   ├── core/                  # 核心流水线
│   │   ├── pipeline.py        # V17.0 滚动特征流水线
│   │   ├── pipeline_v18.py    # V18.0 赛前特征流水线
│   │   └── pipeline_v19_4.py  # V19.4 生产流水线
│   │
│   ├── ml/                    # 机器学习引擎
│   │   ├── engine.py          # V17.0 ML 引擎
│   │   ├── inference/         # 推理服务（predictor, model_loader）
│   │   ├── features/          # 特征工程
│   │   │   ├── extractor.py       # 钻石特征提取器
│   │   │   ├── industrial_feature_forge.py  # 工业级特征锻造
│   │   │   └── v19_advanced_features.py      # V19 高级动态特征
│   │   ├── data/              # 数据加载器
│   │   │   └── postgres_loader.py   # PostgreSQL 数据加载
│   │   └── backtest/          # 回测引擎
│   │
│   ├── api/                   # 数据采集层
│   │   ├── collectors/        # FotMob API 采集器
│   │   │   └── fotmob_core.py
│   │   └── health.py          # 健康检查端点
│   │
│   ├── services/              # 业务服务层
│   │   └── inference_service.py  # 推理服务编排
│   │
│   ├── database/              # 数据库层
│   │   ├── db_pool.py         # 连接池管理（同步+异步）
│   │   └── migrations/        # Alembic 迁移文件
│   │
│   └── ops/                   # 运维脚本
│       ├── data_pipeline_v25.py  # V25.0 数据流水线
│       ├── market_live_monitor.py  # 实时市场监控
│       └── risk_monitor.py        # 风险监控
│
├── tests/                     # 测试套件
│   ├── unit/                  # 单元测试
│   ├── integration/           # 集成测试
│   ├── performance/           # 性能测试
│   └── v2/                    # V2 推理核心测试
│
├── scripts/                   # 运维脚本
│   ├── system_verify.sh       # 系统健康检查
│   ├── run_checks.sh          # CI 质量门禁
│   └── verify_ready.sh        # Boxing Day 验收
│
├── deploy/                    # 部署配置
│   └── docker/
│       └── Dockerfile         # V30.0 多阶段构建
│
├── data/                      # 数据目录
│   ├── production/            # 生产数据
│   └── models/                # 训练好的模型文件
│
└── .claude/                   # Claude Code 工程规范
    ├── context_lock.skill.md          # 核心资产冻结
    ├── architecture_boundary.skill.md # 架构分层约束
    └── test_guard.skill.md            # 测试保护
```

### 📁 核心组件

| 组件 | 文件路径 | 职责 |
|------|----------|------|
| **统一生产入口** | `main_production.py` | L1/L2/训练/预测/监控 |
| **ML 引擎** | `src/ml/engine.py` | XGBoost 训练/预测 |
| **数据采集** | `src/api/collectors/fotmob_core.py` | 哨兵机制 API |
| **特征锻造** | `src/ml/features/industrial_feature_forge.py` | 工业级特征提取 |
| **统一配置** | `src/config_unified.py` | Pydantic Settings 管理 |

> 其他实验性组件详见 `src/core/pipeline_*.py` 和 `src/ml/features/` 目录

### 🎯 主要入口点

#### 统一生产入口（推荐）
```bash
# 完整流程
python main_production.py --full-pipeline

# 分步执行
python main_production.py l1-harvest --season 2324 --target 10
python main_production.py l2-parse
python main_production.py train --train-size 600 --test-size 160
python main_production.py predict
python main_production.py health-check
```

#### FastAPI 服务
```bash
python src/main.py              # 启动服务
docker-compose up -d            # Docker 模式
```

### ❌ 禁止操作
- 绕过 `main_production.py` 直接调用底层流水线
- 未经业务逻辑直接操作数据库
- 使用非官方脚本进行数据操作
- 硬编码数据库连接参数

---

## 📊 版本与特征

> 版本演进详见 [🏗️ 系统架构](#🏗️-系统架构) 章节

### 🧬 特征体系

#### V17.0 滚动特征（16 维）
```
主队/客队各 8 维:
- rolling_xg, rolling_xg_std
- rolling_shots_on_target, rolling_shots_on_target_std
- rolling_possession, rolling_possession_std
- rolling_team_rating, rolling_team_rating_std
```

#### V18.0 新增赛前特征（8 维）
```
- home_table_position, away_table_position, table_position_diff
- home_points, away_points, points_diff
- home_recent_form_points, away_recent_form_points
```

#### V19.0 高级动态特征（13 维）
```
ELO 相对差距:
- raw_elo_gap, adjusted_elo_gap, fatigue_impact, schedule_impact

疲劳度指数:
- home_fatigue_index, away_fatigue_index, fatigue_diff
- home_rest_days, away_rest_days

保级战意:
- home_relegation_incentive, away_relegation_incentive
- incentive_diff, home_desperation
```

#### V19.4 平局敏感度特征（3 维）
```
- table_proximity: 积分榜接近度
- low_scoring_tendency: 低得分倾向
- elo_diff_cluster: ELO 差距聚类
```

#### V20.0 数据中台特性（架构重构）
```
动态联赛元数据管理:
- 自动从 FotMob allLeagues API 抓取联赛信息
- 维护赛季别名映射 (API格式 ↔ 存储格式)
- 提供联赛ID动态查询
- 支持五大联赛自动发现

Schema-Agnostic 递归解析器:
- 递归深度搜索核心数据字段
- 防止循环引用
- 容错性更强，支持 API 结构变化
- 智能熔断机制（按ID跳过而非全局休眠）
```

#### V20.6 全量合成特征（66 维）
```
ShotmapAggregator 合成特征:
- home_all_synth_total_shots, home_all_synth_xg
- home_FH_synth_xg, home_SH_synth_shots
- home_all_synth_peak_xg, home_all_synth_volatility
- 共 66 个合成特征
```

#### V20.7 原子级数据对齐（800+ 维）
```
原子级回填 (Atomic Backfill):
- 自动触发 shotmap 填充缺失字段
- home_FirstHalf_expected_goals (回填)
- away_SecondHalf_total_shots (回填)
- 共 32+ 个字段自动回填

球员-球队级联聚合:
- home_team_total_accurate_passes (11人加总)
- away_team_total_touches (11人加总)
- 共 44 个聚合特征

动量特征深度解剖:
- home_momentum_velocity_mean (正向动量变化率)
- home_momentum_neg_acceleration_mean (防线崩溃速度)
- 共 15 个动量特征

全量 Schema 对齐 (Zero-Padding):
- 所有 270+ 个标准字段强制存在
- 缺失字段统一填充 0.0 或 -1.0
- 确保所有比赛特征数量严格相等
```

#### V20.8 焦土收割机（Scorched Earth 回填引擎）
```
全量历史数据回填:
- 自动扫描并回填所有缺失的历史比赛数据
- 支持 800+ 维特征的完整回填
- 断点续传机制，支持大规模数据处理

Docker 后台服务:
- 独立容器运行 `src/ops/backfill_v20.8_scorched_earth.py`
- 自动重启机制，保证数据采集稳定性
- 独立日志输出到 `logs/` 目录
```

### 🔌 数据库连接标准

```python
# 必须使用统一配置
from src.config_unified import get_settings
settings = get_settings()
db = settings.database

# 必须使用 RealDictCursor
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(
    host=db.host,
    port=db.port,
    database=db.name,
    user=db.user,
    password=db.password.get_secret_value()
)
```

---

## 🔧 开发指南

### 📋 代码质量规范

**修改前验证（强制）**:
```bash
./system_verify.sh
ruff check src/ tests/ --fix
pytest tests/unit/utils tests/unit/cache tests/unit/core -v
```

**代码标准**:
- **Python**: 3.11+
- **代码风格**: Ruff (格式化 + Lint)
- **行长度限制**: **严格 120 字符** (配置在 `pyproject.toml` 和 Ruff 中)
- **类型检查**: MyPy 严格配置
- **安全扫描**: Bandit
- **测试框架**: pytest，目标覆盖率 40%

### 🔨 开发工作流

#### Makefile 命令
```bash
# 环境管理
make venv | install | dev | clean | env-check

# 代码质量（Black/Flake8/MyPy - Makefile 使用传统工具）
make format | lint | typecheck | security | quality

# 现代替代方案（Ruff - 推荐使用）
ruff check src/ tests/ --fix
ruff format src/ tests/

# 测试
make test | coverage | prepush

# Docker 部署
make up | down | predict | verify

# 数据库
make db-reset | db-drop | db-stats | db-quality-report

# 赛季收割
make harvest-season | harvest-watch | season-full-reset
```

#### Ruff 命令（推荐使用）
```bash
# 代码检查和修复
ruff check src/ tests/ --fix
ruff format src/ tests/

# 选择性修复
ruff check src/ --select=I,F401,F841 --fix

# 查看问题
ruff check src/ --output-format=concise

# 代码复杂度分析
ruff check src/ --select=C901 --show-source
```

**Ruff 配置**: 项目使用 Black/Flake8 兼容配置（行长度 120 字符），详见 `pyproject.toml` 中 `[tool.black]` 和 `[tool.flake8]` 部分。Ruff 自动继承这些配置。

### 🔌 Skills 使用说明

项目配置了专业化技能，位于 `.claude/skills/` 目录。每个技能包含独立的 SKILL.md 配置文件。

**可用 Skills**:

| Skill | 描述 | 使用场景 |
|-------|------|----------|
| `code-quality` | 代码质量管理（Ruff/Black/Flake8/MyPy/Bandit） | 提交前检查、格式化代码 |
| `data-collection` | 数据采集（FotMob API、历史数据） | 更新比赛数据、赛季收割 |
| `data-engineering` | 数据管道工程（ETL、PostgreSQL、Redis） | 构建数据流、优化查询 |
| `database-operations` | 数据库操作（迁移、查询优化、备份） | 数据库维护、性能调优 |
| `deployment-management` | 部署管理（Docker、生产环境） | 部署到生产、服务编排 |
| `deployment-operations` | 容器化部署和自动化运维 | Docker 容器管理、健康监控 |
| `docker-devops` | Docker 和 DevOps 最佳实践 | 创建 Dockerfile、CI/CD 流水线 |
| `fastapi-development` | FastAPI 异步 API 开发 | 创建 REST 端点、性能优化 |
| `football-prediction` | 足球比赛预测（XGBoost 模型） | 预测比赛结果、分析准确率 |
| `machine-learning-engineering` | ML 模型优化和特征工程 | 超参调优、模型部署 |
| `performance-monitoring` | 系统性能监控（Prometheus/Grafana） | 检查系统健康、分析指标 |
| `report-generation` | 专业分析报告生成（PDF/Word/Excel） | 生成比赛分析报告 |
| `api-testing` | API 测试（FastAPI 端点、集成测试） | 接口测试、性能验证 |

**使用方法**:
```bash
# 调用 Skill（Claude Code 自动处理）
Skill: code-quality

# 然后执行相关命令
ruff check src/ tests/ --fix && ruff format src/ tests/
```

### 🔄 CI/CD 质量门禁

项目配置了 GitHub Actions 质量门禁（`.github/workflows/quality-gates.yml`）：

**质量门禁标准**:
- 代码格式化：Black 检查通过
- 代码风格：Flake8 检查通过
- 测试执行：核心测试通过
- 覆盖率：总体 ≥25%，推理服务 ≥90%
- 安全扫描：Bandit 扫描无高危漏洞

**自动化检查**:
```bash
# 本地运行质量门禁检查（模拟 CI）
make quality

# 运行安全扫描
bandit -r src/

# 运行性能测试
pytest tests/performance/ -v
```

### 🧪 测试指南

| 测试类型 | 命令 | 说明 |
|---------|------|------|
| **CI 完整检查** | `./scripts/run_checks.sh` | 导入排序 + 格式化 + Lint + 类型检查 + 单元测试 + 安全扫描 |
| **Smart Tests** | `pytest tests/ml/test_backtest_engine.py tests/ops/test_signal_generator.py -v` | 核心测试套件（与 CI 一致） |
| **全部测试** | `pytest tests/ -v` | 运行所有单元测试 |
| **单文件测试** | `pytest tests/unit/test_specific.py -v` | 运行指定测试文件 |
| **单函数测试** | `pytest tests/unit/test_engine.py::test_prediction -v` | 运行指定测试函数 |
| **关键词过滤** | `pytest tests/ -k "test_inference" -v` | 运行匹配关键词的测试 |
| **标记过滤** | `pytest -m "unit and api" -v` | 按标记运行测试 |
| **覆盖率测试** | `pytest tests/ --cov=src --cov-report=html` | 生成覆盖率报告 |
| **配置测试** | `pytest tests/unit/test_config*.py -v` | 配置相关测试 |
| **数据库测试** | `pytest tests/unit/test_database*.py -v` | 数据库相关测试 |
| **API 测试** | `pytest tests/unit/test_api_*.py -v` | API 相关测试 |

**提交前检查（推荐）**:
```bash
# 使用 CI 脚本（推荐）
./scripts/run_checks.sh

# 或手动执行核心测试
pytest tests/ml/test_backtest_engine.py tests/ops/test_signal_generator.py -v
```

### 🏛️ 架构设计原则

**多版本流水线并存**: V17/V18/V19.4 流水线独立维护，各自入口文件明确

**L1/L2/L3 数据流分层**:
- L1: FotMob 哨兵机制数据收割
- L2: Schema-Agnostic 递归解析
- L3: 特征提取 + 模型训练

**配置管理统一**: 所有配置通过 `src/config_unified.py` Pydantic Settings 管理

---

## 🚀 部署与运维

### 🔧 环境变量配置

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `ENVIRONMENT` | 否 | development | 运行环境 |
| `DOCKER_ENV` | 否 | false | Docker 环境标识 |
| `DB_HOST` | 否 | localhost | 数据库主机（Docker 自动使用 "db"） |
| `DB_PASSWORD` | **是** | - | 数据库密码 |
| `SECRET_KEY` | **是** | - | 应用密钥（≥32 字符） |

### 🐳 Docker 部署

#### V30.0 Cloud-Native 架构

**Docker Compose Profiles 多模式部署**:

```bash
# 核心服务 (pipeline_worker + db + redis)
docker-compose up -d

# 核心服务 + API (predictor_api)
docker-compose --profile api up -d
make up-api

# 开发环境 (核心 + API + 管理工具)
docker-compose --profile dev up -d
make up-dev

# 全部服务
docker-compose --profile all up -d
make up-all

# 查看服务状态
make ps
docker-compose ps
```

**Dockerfile 多阶段构建**:

```bash
# 使用新的 Dockerfile (deploy/docker/Dockerfile)
# 构建生产镜像
docker build -f deploy/docker/Dockerfile -t footballprediction:v30.0-fullblood .

# 查看镜像大小 (~350MB, 优化 70%)
docker images | grep footballprediction

# 健康检查
docker-compose exec db pg_isready -U football_user
docker-compose exec redis redis-cli ping
```

### 🏭 V30.0 服务栈配置

**核心服务**:
- `db` - PostgreSQL 15 数据库（默认启动）
- `pipeline_worker` - V30.0 Full Blood 数据流水线（默认启动）
- `redis` - Redis 7 缓存服务（默认启动）

**可选服务** (via profiles):
- `predictor_api` - FastAPI 预测服务 (`--profile api`)
- `harvester` - V20.8 焦土回填服务 (`--profile harvester`)
- `dashboard` - 战神仪表盘 (`--profile dashboard`)
- `pgadmin` - PostgreSQL 管理工具 (`--profile dev`)
- `redis-commander` - Redis 管理工具 (`--profile dev`)

**数据卷** (Docker Volumes):
- `postgres_data` - PostgreSQL 持久化数据
- `redis_data` - Redis 持久化数据
- `app_data` - 应用数据目录
- `app_logs` - 应用日志目录

**网络**:
- `football_network` - 内部桥接网络 (172.20.0.0/16)

### 📊 服务栈

| 服务 | 端口 | Profile | 说明 |
|------|------|---------|------|
| `pipeline_worker` | - | default | V30.0 Full Blood 数据流水线 |
| `predictor_api` | 8000 | api | FastAPI 预测服务 |
| `db` | 5432 | default | PostgreSQL 15 |
| `redis` | 6379 | default | Redis 7 |
| `harvester` | - | harvester | V20.8 焦土收割机 |
| `dashboard` | - | dashboard/dev | 战神仪表盘 |
| `pgadmin` | 5050 | dev | PostgreSQL 管理 |
| `redis-commander` | 8081 | dev | Redis 管理 |

### 🗄️ 数据库迁移

项目使用 Alembic 进行数据库迁移管理：

```bash
# 运行所有迁移
alembic upgrade head

# 回滚一个版本
alembic downgrade -1

# 创建新迁移（自动生成）
alembic revision --autogenerate -m "描述变更内容"

# 查看当前版本
alembic current

# 查看迁移历史
alembic history
```

**迁移文件位置**: `src/database/migrations/versions/`

**注意事项**:
- 迁移前确保已配置正确的数据库连接
- 生产环境迁移前务必备份数据库
- 复杂迁移需要人工审查自动生成的脚本

### 🔍 V19.4 运维监控

| 工具 | 文件 | 功能 |
|------|------|------|
| 实时市场监控 | `src/ops/market_live_monitor.py` | 赔率变化、异常检测 |
| 风险监控 | `src/ops/risk_monitor.py` | 风险指标、熔断机制 |
| 每日工作流 | `src/ops/daily_workflow.py` | 数据采集、自动训练 |
| 周度 PNL 报告 | `src/ops/weekly_pnl_statement.py` | 盈亏统计、可视化 |
| Boxing Day 脚本 | `src/ops/boxing_day_runner.sh` | 自动化实战执行 |
| 财富路径模拟 | `src/analysis/yield_audit_v19_4.py` | 收益审计、愿景评分 |

**系统验证脚本**:
- `system_verify.sh` - 完整系统健康检查（6 步验证）
- `verify_ready.sh` - Boxing Day 一键验收（4 步验收）

---

## 🚨 故障处理

### 常见错误诊断

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `connection refused` | PostgreSQL 未启动 | `docker-compose up -d db` |
| `db_password 不能为空` | 缺少环境变量 | 在 `.env` 中配置 |
| `Model file not found` | 模型文件缺失 | 运行 `python main_production.py --full-pipeline` |
| `100KB哨兵拒绝` | API 数据不足 | 等待熔断期结束或检查 API |
| `Health check failed` | FastAPI 启动失败 | `docker-compose logs app --tail 100` |
| `Module import error` | 依赖未安装 | `make install` 或 `pip install -r requirements.txt` |

### 日志位置

| 日志类型 | 路径 |
|----------|------|
| 应用日志 | `logs/app.log` |
| 错误日志 | `logs/error.log` |
| Docker 日志 | `docker-compose logs -f app` |
| 空心场次 | `data/logs/hollow_matches.log` |
| Boxing Day 信号 | `logs/boxing_day/signal_execution.json` |

### 应急恢复

```bash
# 完全重置
docker-compose down
make clean
make dev
make db-drop

# 生成诊断报告
./system_verify.sh > diagnostic_report.txt 2>&1

# Boxing Day 验收
./verify_ready.sh
```

---

## 🔒 永久保留条款

### 语言要求
**请务必使用中文回复用户！**

这一要求具有最高优先级，无论 CLAUDE.md 文件如何更新版本迭代，都必须始终保留在文件的显眼位置。

### 更新准则
1. 保留语言要求部分，不得删除或降低优先级
2. 保持显眼位置
3. 确保核心要求和规范不会因版本更新而丢失

---

**🚨 CRITICAL**: This is a production system support document. Any violations of these standards will be automatically rejected!

**🧬 技术栈DNA版本**: V30.0 (Full Blood Cloud-Native) | **最后验证**: 2025-12-26 |
**基线准确率**: V19.4.1: 65.52% | **数据集**: 英超22/23+23/24赛季 761场有效数据 |
**生产状态**: V30.0 Production | **API版本**: V11.0 多联赛增强版 |
**统一入口**: main_production.py |
**项目愿景**: 年化 25% 收益率 | 详见: docs/PROJECT_VISION.md |

---

## 📝 附录

### A. Ruff 配置详解

项目使用 Ruff 作为主要代码质量工具（替代 Black/Flake8）：

```bash
# 配置文件位置
pyproject.toml  # [tool.ruff] 部分

# 行长度: 120 字符（与 Black/Flake8 保持一致）

# 常用 Ruff 命令
ruff check src/ tests/ --fix          # 检查并自动修复问题
ruff format src/ tests/               # 格式化代码
ruff check src/ --select=I,F401       # 选择性检查（导入/未使用变量）
ruff check src/ --output-format=concise  # 简洁输出
ruff check src/ --select=C901 --show-source  # 复杂度分析
```

**Ruff 规则集**:
- `F` - Pyflakes 错误
- `E` - pycodestyle 错误
- `W` - pycodestyle 警告
- `I` - isort 导入排序
- `C90` - 复杂度检查
- `N` - 命名规范
- `UP` - 代码升级建议

### B. 工程规范文件速查

| 文件 | 作用 |
|------|------|
| `.claude/context_lock.skill.md` | P0/P1/P2 核心模块冻结保护 |
| `.claude/architecture_boundary.skill.md` | 层次职责边界约束 |
| `.claude/test_guard.skill.md` | 测试保护准则 |
| `.claude/minimal_change.skill.md` | 最小修改原则 |
| `.claude/change_impact.skill.md` | 变更影响分析 |

### C. 版本号映射

| 版本号 | 入口文件 | 流水线 | 特征维度 | 状态 |
|--------|----------|--------|----------|------|
| **V30.0** | `docker-compose up -d` | `src/ops/data_pipeline_v25.py` | 48 维 | **当前 Cloud-Native** |
| V29.0 | `docker-compose up -d` | `src/ops/data_pipeline_v25.py` | 48 维 | 服务解耦优化 |
| **V19.4.1** | `main_production.py` | `src/core/pipeline_v19_4.py` | 48 维 | **生产基线** |
| V19.3 | - | `src/core/pipeline_v19_3_hardened.py` | 45 维 | 生产级 |
| V19.0 | - | `src/core/pipeline_v19.py` | 39 维 | 实验中 |
| V18.0 | `main_production.py --v18` | `src/core/pipeline_v18.py` | 24 维 | 验证中 |
| V17.0 | `main_production.py --v17` | `src/core/pipeline.py` | 16 维 | 生产基线 |
| V20.x | - | `src/ml/feature_forge_v20.py` | 800+ 维 | 实验性 |

### D. MCP 服务器使用说明

项目已配置多个 MCP (Model Context Protocol) 服务器，Claude Code 可直接使用以下专用工具：

| MCP 服务器 | 可用工具 | 使用场景 |
|-----------|----------|----------|
| **postgres** | `execute_sql`, `get_table_info`, `get_schema_info`, `check_connection` | 数据库查询、表结构查看、Schema 分析 |
| **pytest** | `run_pytest`, `list_tests` | 运行测试、列出可用测试 |
| **filesystem** | `read_file`, `write_file`, `list_directory`, `search_files`, `git_status`, `git_diff` | 文件操作、目录遍历、Git 状态 |
| **docker** | `run_command` | 在 Docker 容器内执行命令 |
| **ide** | `getDiagnostics`, `executeCode` | 获取代码诊断、执行 Jupyter 代码 |

#### PostgreSQL MCP 详细用法

```bash
# 查询比赛数据（Claude 会自动调用 mcp__postgres__execute_sql）
用户指令: "查询最近 10 场比赛的数据"
Claude 执行: SELECT * FROM matches ORDER BY match_date DESC LIMIT 10;

# 查看表结构（Claude 会自动调用 mcp__postgres__get_table_info）
用户指令: "查看 matches 表的结构"
Claude 执行: 获取 matches 表的列信息、类型、约束

# 检查数据库连接
用户指令: "检查数据库连接状态"
Claude 执行: mcp__postgres__check_connection()
```

#### Pytest MCP 详细用法

```bash
# 运行所有测试
用户指令: "运行所有单元测试"
Claude 执行: mcp__pytest__run_pytest(test_path="tests/", args=["-v"])

# 运行特定测试文件
用户指令: "运行回测引擎测试"
Claude 执行: mcp__pytest__run_pytest(test_path="tests/ml/test_backtest_engine.py", args=["-v"])

# 列出可用测试
用户指令: "列出所有可用的测试"
Claude 执行: mcp__pytest__list_tests(test_path="tests/")
```

#### Filesystem MCP 详细用法

```bash
# 搜索文件
用户指令: "查找所有包含 'pipeline' 的文件"
Claude 执行: mcp__filesystem__search_files(pattern="pipeline", file_type="name")

# 读取文件
用户指令: "读取 main_production.py 的内容"
Claude 执行: mcp__filesystem__read_file(file_path="main_production.py")

# 查看 Git 状态
用户指令: "查看当前 Git 状态"
Claude 执行: mcp__filesystem__git_status()

# 查看 Git 差异
用户指令: "查看我修改了哪些文件"
Claude 执行: mcp__filesystem__git_diff()
```

#### Docker MCP 详细用法

```bash
# 在容器内执行命令
用户指令: "在 pipeline_worker 容器中执行 Python 脚本"
Claude 执行: mcp__docker__run_command(
    command="python src/ops/data_pipeline_v25.py",
    service="pipeline_worker"
)

# 在数据库容器中执行 SQL
用户指令: "在数据库容器中查看表列表"
Claude 执行: mcp__docker__run_command(
    command="psql -U football_user -d football_db -c '\\dt'",
    service="db"
)
```

#### IDE MCP 详细用法

```bash
# 获取代码诊断
用户指令: "检查当前文件是否有问题"
Claude 执行: mcp__ide__getDiagnostics()

# 执行 Jupyter 代码
用户指令: "执行这段 Python 代码计算准确率"
Claude 执行: mcp__ide__executeCode(code="import numpy as np; ...")
```

### E. 数据库 Schema 说明

**核心表结构**:

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| `matches` | 比赛基础数据 | match_id, home_team, away_team, match_date, status |
| `raw_match_data` | L2 原始数据（JSON） | match_id, raw_data, collected_at |
| `odds` | 赔率数据 | match_id, home_odds, draw_odds, away_odds, bookmaker |
| `predictions` | 预测结果 | match_id, predicted_result, confidence, model_version |

**查看完整 Schema**:
```bash
# 使用 Alembic 查看迁移历史
alembic history

# 查看当前数据库版本
alembic current

# 使用 MCP 直接查询
# Claude 可调用 get_table_info 查看任意表结构
```

**数据库迁移**:
```bash
# 运行所有迁移
alembic upgrade head

# 回滚一个版本
alembic downgrade -1

# 创建新迁移
alembic revision --autogenerate -m "描述变更内容"
```

### F. 环境变量完整清单

```bash
# 数据库配置
DB_HOST=localhost          # 数据库主机（Docker 自动使用 "db"）
DB_PORT=5432              # 数据库端口
DB_NAME=football_db       # 数据库名称
DB_USER=football_user     # 数据库用户
DB_PASSWORD=***           # 数据库密码（必需）

# Redis 配置
REDIS_HOST=localhost      # Redis 主机（Docker 自动使用 "redis"）
REDIS_PORT=6379           # Redis 端口
REDIS_DB=0                # Redis 数据库

# 应用配置
ENVIRONMENT=development   # 运行环境（development/production）
DOCKER_ENV=false          # Docker 环境标识
LOG_LEVEL=INFO            # 日志级别
TZ=UTC                    # 时区
SECRET_KEY=***            # 应用密钥（必需，≥32 字符）

# 可选配置
PYTHONDEVMODE=1           # 开发者模式（代码修改实时生效）
```

### G. 实验性版本管理指南

项目采用多版本并存策略，允许在保证生产稳定性的同时进行创新实验。

#### 实验性版本清单

| 版本系列 | 核心特性 | 特征维度 | 文件位置 | 状态 |
|---------|----------|----------|----------|------|
| **V34** | 全息收割机 + 全局 Manifest | 800+ | `src/ml/miners_v34/` | 研发中 |
| **V38** | 战神模型 + 拳击日报告 | 48+ | `src/ml/models/v38_*.py` | 实验中 |
| **V39** | 差分训练 + 暴力强制 | 48+ | `src/ml/models/v39_*.py` | 实验中 |
| **V40** | 抗泄漏特征引擎 | 800+ | `src/ml/features/v40_*.py` | 实验中 |
| **V43** | 容错滚动特征 | 48+ | `src/ml/features/v43_*.py` | 实验中 |
| **V44** | Docker 导入工具 | - | `src/ops/v44_*.py` | 实验中 |
| **V45** | 纯源重建 | - | `src/ops/v45_*.py` | 实验中 |
| **V46** | 全球雷达扫描 | - | `src/ops/v46_*.py` | 实验中 |

#### 版本切换指南

```bash
# 使用 V19.4.1 生产版本（推荐）
python main_production.py --full-pipeline

# 使用 V30.0 Docker 版本
docker-compose up -d

# 实验性版本 - 直接运行
python src/ml/models/v38_1_real_trainer.py
python src/ml/models/v39_0_final.py

# 实验性版本 - Docker 模式
docker-compose --profile holographic up -d
```

#### 实验性版本测试策略

1. **隔离测试**：实验性版本应在独立的数据库环境或测试分支中运行
2. **A/B 对比**：使用相同的测试数据集对比实验版本与生产版本的准确率
3. **回归测试**：确保实验性版本不会破坏现有功能
4. **性能基准**：记录训练时间和推理延迟，确保性能可接受

#### 版本集成流程

```
实验性版本 → 验证测试 → 性能评估 → 冻结保护 → 合并主分支
     ↓           ↓           ↓           ↓           ↓
  开发环境    测试环境    预生产环境   代码审查    生产发布
```

**集成前检查清单**:
- [ ] 所有测试通过（pytest）
- [ ] 代码质量检查通过（ruff check）
- [ ] 性能基准达标（推理延迟 < 100ms）
- [ ] 准确率不低于基线版本
- [ ] 文档更新完整
- [ ] Context Lock 审批通过（P0/P1 模块）

### H. 监控与可观测性

项目使用 Prometheus + Grafana 构建完整的监控体系。

#### 监控架构

```
┌─────────────────────────────────────────────────────────────┐
│                      监控数据流                               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  应用层 (FastAPI + Pipeline Worker)                    │  │
│  │  - prometheus_client 指标暴露                          │  │
│  │  - /metrics 端点 (端口 8000)                          │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Prometheus Server                                    │  │
│  │  - 指标采集和存储 (15s 间隔)                          │  │
│  │  - PromQL 查询引擎                                    │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Grafana Dashboard                                    │  │
│  │  - 战神仪表盘 (战神仪表盘)                             │  │
│  │  - 实时可视化                                         │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### 核心监控指标

| 指标类型 | 指标名称 | 描述 | 告警阈值 |
|---------|----------|------|----------|
| **预测准确率** | `prediction_accuracy` | 模型预测准确率 | < 60% |
| **推理延迟** | `inference_latency_ms` | 单次预测响应时间 | > 100ms |
| **API 请求** | `api_requests_total` | API 请求总数 | - |
| **API 错误率** | `api_errors_total` | API 错误次数 | > 5% |
| **数据库连接** | `db_connections_active` | 活跃数据库连接数 | > 80% |
| **缓存命中率** | `cache_hit_ratio` | Redis 缓存命中率 | < 70% |
| **系统资源** | `system_cpu_usage` | CPU 使用率 | > 80% |
| **系统资源** | `system_memory_usage` | 内存使用率 | > 85% |

#### Prometheus 配置

**prometheus.yml** 示例:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'football-prediction-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']
```

#### Grafana 面板配置

**战神仪表盘** (Wargod Dashboard):
- **预测性能面板**: 准确率趋势、混淆矩阵、ROC 曲线
- **系统健康面板**: CPU/内存/磁盘使用率、服务状态
- **业务指标面板**: 预测次数、胜率统计、盈亏曲线
- **数据质量面板**: 数据采集量、空心场次比例、数据新鲜度

**启动 Grafana**:
```bash
# Docker 模式
docker-compose --profile dashboard up -d

# 访问 Dashboard
# 默认地址: http://localhost:3000
# 默认用户: admin / admin
```

#### 告警规则

**alerting.yml** 示例:
```yaml
groups:
  - name: football_prediction_alerts
    rules:
      - alert: LowPredictionAccuracy
        expr: prediction_accuracy < 0.6
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "预测准确率低于 60%"

      - alert: HighInferenceLatency
        expr: inference_latency_ms > 100
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "推理延迟超过 100ms"

      - alert: HighErrorRate
        expr: rate(api_errors_total[5m]) / rate(api_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API 错误率超过 5%"
```

#### 日志聚合

项目使用 structlog 进行结构化日志记录：

```python
import structlog

log = structlog.get_logger()
log.info("prediction_made", match_id=123, result="home", confidence=0.75)
```

**日志级别**:
- DEBUG: 详细调试信息
- INFO: 一般信息（默认）
- WARNING: 警告信息
- ERROR: 错误信息
- CRITICAL: 严重错误

**日志查看**:
```bash
# 查看应用日志
tail -f logs/app.log

# 查看 Docker 日志
docker-compose logs -f pipeline_worker
docker-compose logs -f predictor_api

# 过滤错误日志
grep "ERROR" logs/app.log
```