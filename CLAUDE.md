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

---

## 🚨 语言要求（最高优先级）

**请务必使用中文回复用户！**

这一要求具有最高优先级，无论 CLAUDE.md 文件如何更新版本迭代，都必须始终保留在文件的显眼位置。

## ⚠️ 当前系统状态

**当前版本**: V19.4.1 (Boxing Day Production) + V20.0 (数据中台重构)
**Boxing Day 封锁期**: 已结束 (2025-12-24 ~ 2025-12-26)
**系统状态**: ✅ Production Ready
**代码规范**: 正常开发流程已恢复

**历史封锁公告**: 详见 `CODE_FREEZE_NOTICE.md`

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
| **版本** | V19.4.1 (Boxing Day Production) |
| **准确率** | 65.52% 真实赛前预测（无数据泄露） |
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

### ⚡ 日常开发 Top 6 命令

```bash
# 1. 快速开发环境设置
make dev

# 2. V19.4 统一生产流程（48维特征，最新推荐）
python main_production.py --full-pipeline

# 3. V18.0 完整流程（24维特征）
python factory_run.py --v18

# 4. 代码质量检查（Ruff）
ruff check src/ tests/ && ruff format src/ tests/

# 5. Docker 服务启动
docker-compose up -d

# 6. 系统健康检查
./system_verify.sh
```

### 📋 常用命令速查表

| 操作 | 命令 | 耗时 |
|------|------|------|
| 环境准备 | `make dev` | ~2 分钟 |
| V19.4 流程 | `python main_production.py --full-pipeline` | ~15 分钟 |
| V18.0 流程 | `python factory_run.py --v18` | ~10 分钟 |
| 质量检查 | `ruff check src/ tests/ --fix` | ~30 秒 |
| 快速测试 | `pytest tests/unit/utils tests/unit/cache tests/unit/core -v` | ~2 分钟 |
| 系统验证 | `./system_verify.sh` | ~30 秒 |
| Boxing Day 验收 | `./verify_ready.sh` | ~2 分钟 |
| Docker 部署 | `docker-compose up -d` | ~1 分钟 |

### 🎯 常见场景命令

```bash
# 新机器环境设置
make dev && ./system_verify.sh

# 提交前检查
ruff check src/ tests/ --fix && pytest tests/unit/utils tests/unit/cache tests/unit/core -v

# 收割英超赛季数据
python factory_run.py --harvest --season 2324

# 系统健康检查
python main_production.py health-check

# 实时市场巡检（V19.4 新功能）
python main_production.py monitor --match-id 4813551 --match-time "2025-12-26 12:30"

# Boxing Day 实战检查（V19.4.1）
./verify_ready.sh
```

---

## 🏗️ 系统架构

### 📊 系统版本演进

#### 生产版本
| 版本 | 核心特性 | 特征维度 | 准确率 | 状态 |
|------|----------|----------|--------|------|
| V17.0 | 滚动特征（基线） | 16 维 | 65.52% | 生产基线 |
| V19.4.1 | Boxing Day 生产版 + 风控集成 | 48 维 | 65.52% | 生产推荐 |
| V20.0 | 数据中台重构（元数据管理+Schema无关解析） | - | - | 架构完成 |

#### 实验版本
| 版本 | 核心特性 | 特征维度 | 状态 |
|------|----------|----------|------|
| V16.0 | 赛后统计（存在数据泄露） | 223 维 | 废弃 |
| V18.0 | 赛前特征 + 平局优化 | 24 维 | 验证中 |
| V19.0 | 高级动态特征（ELO/疲劳/战意） | 39 维 | 实验中 |
| V19.3 | NaN 鲁棒性 + 联赛编码 | 45 维 | 生产级 |

#### 研发版本（V20.x 实验性）
| 版本 | 核心特性 | 特征维度 | 状态 |
|------|----------|----------|------|
| V20.5 | 全息特征索引（659维冻结Schema） | 659 维 | 实验性 |
| V20.6 | 全量合成全息矩阵（ShotmapAggregator） | 66+ 维 | 实验性 |
| V20.7 | 原子级数据对齐引擎（800+维全量对齐） | 800+ 维 | 实验性 |
| V20.8 | 焦土收割机（Scorched Earth回填引擎） | 800+ 维 | 最新 |

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

### 📁 核心组件

| 组件 | 文件路径 | 职责 |
|------|----------|------|
| **V19.4 统一入口** | `main_production.py` | L1/L2/训练/预测/监控 |
| **V17-V18 官方入口** | `factory_run.py` | V17/V18 流程协调 |
| **V17 流水线** | `src/core/pipeline.py` | L3 滚动特征 + 训练 |
| **V18 流水线** | `src/core/pipeline_v18.py` | 24 维特征 + 平局优化 |
| **V19 流水线** | `src/core/pipeline_v19.py` | 39 维高级特征 |
| **V19.4 流水线** | `src/core/pipeline_v19_4.py` | 48 维 + 平局敏感度 |
| **ML 引擎** | `src/ml/engine.py` | XGBoost 训练/预测 |
| **数据采集** | `src/api/collectors/fotmob_core.py` | V11.0 哨兵机制 API |
| **元数据管理** | `src/api/collectors/metadata_manager.py` | V20.0 动态联赛元数据 |
| **Schema无关解析** | `src/api/collectors/schema_agnostic_parser.py` | V20.0 递归JSON解析 |
| **V20.7 特征引擎** | `src/ml/feature_forge_v20.py` | V20.7 原子级数据对齐引擎 (800+维) |
| **V20.6 射门聚合** | `src/ml/shotmap_aggregator.py` | ShotmapAggregator 合成引擎 (66维) |
| **V20.7 原子对齐** | `src/ml/atomic_align_v20_7.py` | 原子级数据对齐引擎 |
| **V20.8 焦土收割** | `src/ops/backfill_v20.8_scorched_earth.py` | 全量历史数据回填引擎 |
| **熔断器保护** | `src/ml/fault_tolerance.py` | 熔断器、断点续传、容错机制 |
| **数据验证卫士** | `src/ml/data_guard.py` | Schema 验证、数据完整性检查 |
| **数据映射器** | `src/ml/mappers.py` | 数据映射和转换工具 |
| **特征锻造** | `src/ml/features/industrial_feature_forge.py` | 工业级特征提取 |
| **赛前特征** | `src/ml/features/prematch_features.py` | 积分榜/近期走势 |
| **高级特征** | `src/ml/features/v19_advanced_features.py` | ELO/疲劳/战意 |
| **平局敏感度** | `src/ml/features/draw_sensitivity_features.py` | table_proximity 等 |
| **统一配置** | `src/config_unified.py` | Pydantic Settings 管理 |

### 🎯 主要入口点

#### V19.4 统一生产入口（最新）
```bash
# 完整流程
python main_production.py --full-pipeline

# 分步执行
python main_production.py l1-harvest --season 2324 --target 10
python main_production.py l2-parse
python main_production.py train --train-size 600 --test-size 160
python main_production.py predict --model v19.4
python main_production.py monitor --match-id 4813551 --match-time "2025-12-26 12:30"
python main_production.py health-check
```

#### V18.0 增强版流水线（推荐）
```bash
# 完整流程（24 维特征）
python factory_run.py --v18

# 双赛季融合
python factory_run.py --v18-multi
```

#### V17.0 基线版本
```bash
# 完整流程（16 维滚动特征）
python factory_run.py --production --train-size 300 --window 10
```

#### FastAPI 服务
```bash
python src/main.py              # 启动服务
docker-compose up -d            # Docker 模式
```

### ❌ 禁止操作
- 绕过 `factory_run.py` 或 `main_production.py` 直接调用底层流水线
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

项目配置了专业化技能，位于 `.claude/skills/` 目录。使用 Skill 时必须先调用 `Skill` 工具：

```bash
# 使用 code-quality skill 进行代码质量检查
# 首先调用 Skill 工具
Skill: code-quality

# 然后进行代码质量检查
ruff check src/ tests/ --fix && ruff format src/ tests/
```

**常用 Skill**:
- `code-quality` - 代码质量检查、格式化、类型检查
- `data-collection` - 采集比赛数据、更新数据库
- `football-prediction` - 比赛预测、准确率分析
- `machine-learning-engineering` - 模型优化、特征工程、超参调优
- `fastapi-development` - FastAPI 接口开发、性能优化

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
| **全部测试** | `make test` 或 `pytest tests/ -v` | 运行所有单元测试 |
| **Smart Tests** | `pytest tests/unit/utils tests/unit/cache tests/unit/core -v` | 核心稳定模块（<2 分钟） |
| **单文件测试** | `pytest tests/unit/test_specific.py -v` | 运行指定测试文件 |
| **单函数测试** | `pytest tests/unit/test_engine.py::test_prediction -v` | 运行指定测试函数 |
| **关键词过滤** | `pytest tests/ -k "test_inference" -v` | 运行匹配关键词的测试 |
| **标记过滤** | `pytest -m "unit and api" -v` | 按标记运行测试 |
| **覆盖率测试** | `make coverage` 或 `pytest tests/ --cov=src --cov-report=html` | 生成覆盖率报告 |
| **配置测试** | `pytest tests/unit/test_config*.py -v` | 配置相关测试 |
| **数据库测试** | `pytest tests/unit/test_database*.py -v` | 数据库相关测试 |
| **API 测试** | `pytest tests/unit/test_api_*.py -v` | API 相关测试 |
| **流水线测试** | `pytest tests/unit/test_pipeline*.py -v` | 流水线相关测试 |
| **风控测试** | `pytest tests/unit/test_risk_monitor*.py -v` | 风控相关测试 |

**提交前检查**:
```bash
ruff check src/ tests/ --fix && pytest tests/unit/utils tests/unit/cache tests/unit/core -v
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

```bash
# 开发环境部署
docker-compose up -d

# 生产环境部署（docker-compose.prod.yml）
docker-compose -f docker-compose.prod.yml up -d

# 构建生产镜像
docker build -f Dockerfile.prod -t footballprediction:v19.4.1 .

# 健康检查
docker-compose exec db pg_isready -U football_user
docker-compose exec redis redis-cli ping
```

### 🏭 生产环境配置（docker-compose.prod.yml）

生产环境使用独立配置文件，包含以下特性：
- **安全性**: 数据库端口不暴露到宿主机
- **资源限制**: 每个服务配置 CPU/内存限制
- **健康检查**: 所有服务配置健康检查机制
- **数据持久化**: PostgreSQL 和 Redis 数据持久化
- **内部网络**: 独立桥接网络 `football_internal_network`

```bash
# 生产环境服务栈
services:
  predictor-app  # FastAPI 主应用 (端口 8000)
  db             # PostgreSQL 15 (内部网络)
  redis          # Redis 7 (内部网络)
```

### 📊 服务栈

| 服务 | 端口 | 说明 |
|------|------|------|
| app | 8000 | FastAPI 主应用 |
| v20_8_harvester | - | V20.8 焦土收割机（后台数据采集） |
| db | 5432 | PostgreSQL 15 |
| redis | 6379 | Redis 7 |

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

**🧬 技术栈DNA版本**: V19.4.1 (Boxing Day Production) + V20.0 (数据中台重构) | **最后验证**: 2025-12-25 |
**准确率**: V17.0基线: 65.52% | **数据集**: 英超22/23+23/24赛季 761场有效数据 | **多赛季支持**: 是 |
**生产状态**: V19.4.1 Production, V20.0 数据中台完成 | **API版本**: V11.0 多联赛增强版 |
**统一入口**: main_production.py (V19.4), factory_run.py (V17-V18) |
**项目愿景**: 年化 25% 收益率 | 详见: docs/PROJECT_VISION.md

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
| V17.0 | `factory_run.py` | `src/core/pipeline.py` | 16 维 | 生产基线 |
| V18.0 | `factory_run.py` | `src/core/pipeline_v18.py` | 24 维 | 验证中 |
| V19.0 | - | `src/core/pipeline_v19.py` | 39 维 | 实验中 |
| V19.3 | - | `src/core/pipeline_v19_3_hardened.py` | 45 维 | 生产级 |
| V19.4.1 | `main_production.py` | `src/core/pipeline_v19_4.py` | 48 维 | 生产推荐 |
| V20.x | - | `src/ml/feature_forge_v20.py` | 800+ 维 | 实验性 |

### D. 环境变量完整清单

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