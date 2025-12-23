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

| 属性 | 值 |
|------|-----|
| **状态** | ✅ Production Ready |
| **版本** | V19.4 (Draw Sensitivity) |
| **准确率** | 65.52% 真实赛前预测（无数据泄露） |
| **数据量** | 760 场英超 22/23 + 23/24 赛季 |
| **特征维度** | 48 维（滚动 + 赛前 + 高级动态 + 平局敏感度） |

### 🔧 技术栈
- **ML**: XGBoost 2.0+, scikit-learn
- **Backend**: Python 3.11+, FastAPI, PostgreSQL 15, Redis 7
- **DevOps**: Docker, Docker Compose
- **Quality**: Black, Flake8, MyPy, Bandit, pytest

### ⚡ 日常开发 Top 6 命令

```bash
# 1. 快速开发环境设置
make dev

# 2. V18.0 完整流程（24维特征，推荐）
python factory_run.py --v18

# 3. V19.4 统一生产流程（48维特征）
python main_production.py --full-pipeline

# 4. 代码质量检查
make quality

# 5. Docker 服务启动
docker-compose up -d

# 6. Smart Tests 快速验证
pytest tests/unit/utils tests/unit/cache tests/unit/core -v
```

### 📋 常用命令速查表

| 操作 | 命令 | 耗时 |
|------|------|------|
| 环境准备 | `make dev` | ~2 分钟 |
| V18.0 流程 | `python factory_run.py --v18` | ~10 分钟 |
| V19.4 流程 | `python main_production.py --full-pipeline` | ~15 分钟 |
| 质量检查 | `make quality` | ~1 分钟 |
| 快速测试 | `pytest tests/unit/utils tests/unit/cache tests/unit/core -v` | ~2 分钟 |
| 系统验证 | `./system_verify.sh` | ~30 秒 |
| Docker 部署 | `docker-compose up -d` | ~1 分钟 |

### 🎯 常见场景命令

```bash
# 新机器环境设置
make dev && ./system_verify.sh

# 提交前检查
make quality && make test

# 收割英超赛季数据
python factory_run.py --harvest --season 2324

# 系统健康检查
python main_production.py health-check

# 实时市场巡检（V19.4 新功能）
python main_production.py monitor --match-id 4813551 --match-time "2025-12-26 12:30"
```

### 🎯 Skills 集成

项目配置了专业化技能，触发条件：

| Skill | 场景 |
|-------|------|
| `code-quality` | 代码质量检查、格式化、类型检查 |
| `data-collection` | 采集比赛数据、更新数据库 |
| `database-operations` | 数据库操作、性能优化 |
| `football-prediction` | 比赛预测、准确率分析 |
| `machine-learning-engineering` | 模型优化、特征工程、超参调优 |

**使用 Skill 时必须先调用 `Skill` 工具。**

---

## 🏗️ 系统架构

### 📊 系统版本演进

| 版本 | 核心特性 | 特征维度 | 准确率 | 状态 |
|------|----------|----------|--------|------|
| V16.0 | 赛后统计（存在数据泄露） | 223 维 | 96.25% | 废弃 |
| V17.0 | 滚动特征（基线） | 16 维 | 65.52% | 生产 |
| V18.0 | 赛前特征 + 平局优化 | 24 维 | 验证中 | 推荐 |
| V19.0 | 高级动态特征（ELO/疲劳/战意） | 39 维 | 实验性 | 实验中 |
| V19.3 | NaN 鲁棒性 + 联赛编码 | 45 维 | 生产级 | 生产 |
| V19.4 | 平局敏感度 + 加权损失 | 48 维 | 实验性 | 实验中 |

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

### 📈 版本演进对比

| 版本 | 核心特性 | 特征维度 | 准确率 | 状态 |
|------|----------|----------|--------|------|
| V16.0 | 赛后统计（数据泄露） | 223 | 96.25% | ❌ 废弃 |
| V17.0 | 滚动特征（基线） | 16 | 65.52% | ✅ 生产 |
| V18.0 | 赛前特征 + 平局优化 | 24 | 验证中 | ⭐ 推荐 |
| V19.0 | ELO/疲劳/战意 | 39 | 实验性 | 🧪 实验中 |
| V19.3 | NaN 鲁棒 + 联赛编码 | 45 | 生产级 | ✅ 生产 |
| V19.4 | 平局敏感度 + 加权损失 | 48 | 实验性 | 🧪 实验中 |

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
make test
make quality
```

**代码标准**:
- Python: 3.11+
- Style: Black + Flake8, line-length: 120
- Type Check: MyPy 严格配置
- Security: Bandit 扫描
- Testing: pytest，目标覆盖率 40%

### 🔨 开发工作流

#### Makefile 命令
```bash
# 环境管理
make venv | install | dev | clean | env-check

# 代码质量
make format | lint | typecheck | security | quality

# 测试
make test | coverage | prepush

# Docker 部署
make up | down | predict | verify

# 数据库
make db-reset | db-drop | db-stats | db-quality-report

# 赛季收割
make harvest-season | harvest-watch | season-full-reset
```

#### 运行单个测试
```bash
pytest tests/unit/test_specific.py -v
pytest tests/unit/test_engine.py::test_prediction -v
pytest tests/ -k "test_inference" -v
pytest -m "unit and api" -v
```

#### Smart Tests 快速验证
```bash
pytest tests/unit/utils tests/unit/cache tests/unit/core -v
```

### 🏛️ 架构设计原则

- **微服务架构**: FastAPI + PostgreSQL + Redis + Docker
- **依赖注入**: Constructor Injection 模式
- **异步处理**: 全面 async/await
- **单例模式**: DatabaseManager, InferenceEngine 全局管理
- **工厂模式**: FeatureFactory, ModelFactory
- **策略模式**: 可插拔组件

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
# 构建镜像
docker build -t footballprediction:v2.3.1 .

# 启动服务栈
docker-compose up -d

# 健康检查
docker-compose exec db pg_isready -U football_user
docker-compose exec redis redis-cli ping
```

### 📊 服务栈

| 服务 | 端口 | 说明 |
|------|------|------|
| app | 8000 | FastAPI 主应用 |
| db | 5432 | PostgreSQL 15 |
| redis | 6379 | Redis 7 |

### 🧪 测试命令

```bash
make test                              # 运行所有测试
pytest tests/unit/utils tests/unit/cache tests/unit/core -v  # Smart Tests
make coverage                          # 覆盖率测试
```

### 🔍 V19.4 运维监控

| 工具 | 文件 | 功能 |
|------|------|------|
| 实时市场监控 | `src/ops/market_live_monitor.py` | 赔率变化、异常检测 |
| 风险监控 | `src/ops/risk_monitor.py` | 风险指标、熔断机制 |
| 每日工作流 | `src/ops/daily_workflow.py` | 数据采集、自动训练 |
| 周度 PNL 报告 | `src/ops/weekly_pnl_statement.py` | 盈亏统计、可视化 |

---

## 🚨 故障处理

### 常见错误诊断

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `connection refused` | PostgreSQL 未启动 | `docker-compose up -d db` |
| `db_password 不能为空` | 缺少环境变量 | 在 `.env` 中配置 |
| `Model file not found` | 模型文件缺失 | 运行 `python factory_run.py --v18` |
| `100KB哨兵拒绝` | API 数据不足 | 等待熔断期结束或检查 API |
| `Health check failed` | FastAPI 启动失败 | `docker-compose logs app --tail 100` |

### 日志位置

| 日志类型 | 路径 |
|----------|------|
| 应用日志 | `logs/app.log` |
| 错误日志 | `logs/error.log` |
| Docker 日志 | `docker-compose logs -f app` |
| 空心场次 | `data/logs/hollow_matches.log` |

### 应急恢复

```bash
# 完全重置
docker-compose down
make clean
make dev
make db-drop

# 生成诊断报告
./system_verify.sh > diagnostic_report.txt 2>&1
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

**🧬 技术栈DNA版本**: V19.4 (平局敏感度实验性) + V20.0 (规划中) | **最后验证**: 2025-12-23 |
**准确率**: V17.0基线: 65.52% | **数据集**: 英超22/23+23/24赛季 760场有效数据 | **多赛季支持**: 是 |
**生产状态**: V19.3 Ready, V19.4 Experimental | **API版本**: V11.0 多联赛增强版 |
**统一入口**: main_production.py (V19.4), factory_run.py (V17-V18)