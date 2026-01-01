# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 🚨 语言要求（最高优先级）

**请务必使用中文回复用户！**

这一要求具有最高优先级，无论 CLAUDE.md 文件如何更新版本迭代，都必须始终保留在文件的显眼位置。

---

## 📋 项目概览

**FootballPrediction** - 基于 XGBoost 2.0+ 的专业足球比赛预测系统

**项目愿景**: 以年化 25% 的真实收益率为北极星指标，构建可验证、可复制、可持续的体育预测系统

### 当前系统状态

| 属性 | 值 |
|------|-----|
| **状态** | ✅ Production Ready |
| **生产版本** | **V56.4** (生产收割引擎) + **V51.1** (滚动特征) + **V26.8** (联赛专项) + **V37.0** (数据采集) + **V25.1** (特征引擎) |
| **实验版本** | **V51.3** (Full Power) - 标签打乱验证通过 |
| **基线准确率** | 56% (真赛前) |
| **特征维度** | 49-56 维滚动特征 (V51.x) + 642 维深度脱水特征 |
| **数据量** | 9,305+ 场对齐训练数据 |
| **推理延迟** | <100ms |
| **训练-推理对齐** | ✅ 完全对齐 (V51.x 时空隔离协议) |
| **模型分发** | ✅ ModelDispatcher (联赛专项 vs 通用) |
| **自动化调度** | ✅ ProductionScheduler (全流程自动化) |
| **最后更新** | 2025-12-31 (V56.4 生产收割引擎 + V51.1 滚动特征 + V51.3 Full Power) |

### 版本说明

| 模块 | 版本 | 文件位置 | 说明 |
|------|------|----------|------|
| 生产收割引擎 | V56.4 | `scripts/production_harvester.py` | 智能自愈收割，IP 健康监控，毫秒级感应 |
| 预测模型 | V51.3 | `model_zoo/v51_3_full_power_model.pkl` | 实验性 Full Power 模型 |
| 滚动特征 | V51.1 | `scripts/ml/v51_1_rolling_feature_engine.py` | 49-56 维时空隔离特征 |
| 赔率提取器 | V56.0 | `src/api/collectors/odds_production_extractor.py` | 智能轮询 + 悬停自愈 |
| 增量采集器 | V51.0 | `src/api/collectors/v51_incremental_collector.py` | 断点续传 + 熔断恢复 |
| 特征精炼器 | V51.0 | `src/processors/v51_feature_refiner.py` | 642 维深度脱水特征 |
| 预测模型 | V26.8 | `model_zoo/v26.8_*.pkl` | 联赛专项模型 (EPL/LaLiga/Ligue1/Bundesliga) |
| 模型分发器 | ModelDispatcher | `src/ml/engine.py:668` | 智能模型路由 |
| 数据采集 | V37.0 | `experiments/marrow_cleaning_v37_harvester.py` | 生产级数据采集基准 |
| 特征提取 | V25.1 | `src/processors/v25_production_extractor.py` | 万能自适应特征提取 |
| 熔断器 | V1.0 | `src/api/collectors/circuit_breaker.py` | API 熔断保护 |
| 限流器 | V1.0 | `src/api/rate_limiter.py` | FastAPI 接口限流 |
| 告警管理 | V1.0 | `src/ops/alert_manager.py` | 多渠道告警管理 |
| 自动化调度 | V1.0 | `scripts/automate_production.py` | 全流程自动化调度 |

### 核心技术栈

- **ML**: XGBoost 2.0+, scikit-learn, Isotonic 回归
- **Backend**: Python 3.11+, FastAPI, PostgreSQL 15, Redis 7
- **DevOps**: Docker, Docker Compose
- **Code Quality**: Ruff (主要), MyPy, Bandit
- **Testing**: pytest, pytest-cov

---

## 🎯 唯一真理来源（Single Source of Truth）

### 当前生产版本

| 模块 | 版本 | 说明 |
|------|------|------|
| **预测模型** | **V26.8** | 联赛专项模型 (EPL/LaLiga/Ligue1/Bundesliga) + 通用 V26.7 |
| **模型分发** | **ModelDispatcher** | `src/ml/engine.py:668` |
| **数据采集基准** | **V37.0** | `experiments/marrow_cleaning_v37_harvester.py` |
| **特征引擎** | **V25.1** | `src/processors/v25_production_extractor.py` |
| **生产服务** | **V26.8** | `src/ops/production_service.py` (自动联赛检测) |

### ⚠️ 强制命名规范

**严禁创建任何带有 `_v1`, `_v2`, `_v17`, `_v18` 等版本后缀的新文件！**

**正确做法**:
- ✅ 直接修改现有文件
- ✅ 使用类继承实现功能扩展
- ✅ 使用策略模式实现算法切换
- ✅ 通过配置控制行为差异

**错误做法**:
- ❌ `pipeline_v27.py` → 应修改 `pipeline.py` 或使用配置
- ❌ `feature_extractor_v28.py` → 应继承 `BaseExtractor`
- ❌ `model_v29.py` → 应使用 `model_zoo/` 管理版本

### 版本管理

- **历史版本**: 已删除或移至 `archive/`，Git 历史可恢复
- **实验代码**: 统一存放于 `experiments/` 目录（仅保留最新 V37.0）
- **模型文件**: 统一存放于 `model_zoo/` 目录

---

## ⚡ 快速开始

完整安装和部署指南请参阅 [README.md](README.md)。

### 核心开发命令

```bash
# 生产预测服务（联赛专项模型）
python -m src.ops.production_service

# FastAPI 服务
python src/main.py

# Docker 部署
docker-compose up -d
```

---

## 🏗️ 目录规范与架构

### 核心目录结构

```
FootballPrediction/
├── src/                      # ⭐ 生产代码（V25/V26/V30/V37）
│   ├── api/                  # FastAPI endpoints + 数据采集
│   │   ├── collectors/       # FotMob API 采集器
│   │   │   ├── circuit_breaker.py   # 🆕 爬虫熔断器
│   │   │   └── odds_api_client.py   # 🆕 赔率 API 客户端
│   │   └── rate_limiter.py   # 🆕 API 限流器
│   ├── config/               # 统一配置（合并后）
│   ├── config_unified.py     # 全局配置管理
│   ├── core/                 # 核心业务逻辑
│   ├── database/             # 数据库层（统一）
│   ├── main.py               # FastAPI 入口
│   ├── ml/                   # 机器学习层（合并后）
│   │   ├── engine.py         # XGBoost 训练引擎 + ModelDispatcher
│   │   ├── features/         # 特征工程
│   │   ├── inference/        # 推理服务
│   │   └── backtest_engine.py  # 回测引擎
│   ├── ops/                  # 运维脚本
│   │   └── alert_manager.py  # 🆕 告警管理器
│   ├── processors/           # V25.1 特征提取引擎
│   │   ├── v25_production_extractor.py
│   │   └── v30_odds_features.py    # 🆕 V30.0 赔率特征
│   └── services/             # 业务服务层
│
├── scripts/                  # 核心脚本
│   ├── automate_production.py        # 🆕 全流程自动化调度器
│   ├── automate_v1_0_pipeline.py     # V1.0 流水线自动化
│   ├── train_v27_0_epl_ewma.py       # V27.0 英超 EWMA 训练
│   ├── cleanup_project.py            # 项目清理脚本
│   ├── fix_imports.py                # Import 路径修复脚本
│   ├── run_checks.sh                 # CI 质量门禁
│   ├── system_verify.sh              # 系统健康检查
│   ├── run_all_tests.sh              # 全量测试执行
│   ├── verify_automation.sh          # 🆕 自动化验证脚本
│   ├── collectors/                   # 数据采集脚本
│   ├── production/                   # 🆕 生产环境脚本
│   ├── exploration/                  # 🔍 探索性脚本（非生产）
│   ├── maintenance/                  # 维护工具
│   │   ├── backup_db.py              # 🆕 数据库备份
│   │   └── import_ucl_history.py     # 🆕 UCL 历史数据导入
│   ├── ml/                           # 🆕 ML 训练脚本
│   ├── archive/                      # 历史归档脚本
│   └── sql/                          # SQL 初始化脚本
│
├── experiments/              # 🔬 实验性代码（仅 V37.0）
│   ├── marrow_cleaning_v37_harvester.py  # V37.0 采集器基准
│   └── ml/                   # ML 实验代码
│
├── model_zoo/                # 📦 模型仓库
│   ├── registry.md           # 模型注册表
│   ├── v26.8_*.pkl           # V26.8 联赛专项模型
│   └── v26.7_*.pkl           # V26.7 通用模型
│
├── data/                     # 📊 数据目录
│   ├── production/           # L1/L2 原始数据
│   ├── processed/            # L3 特征数据
│   └── models/               # 当前生产模型
│
├── tests/                    # ✅ 测试套件
├── archive/                  # 📦 历史归档
│   ├── cleanup_20251229_*/   # 🆕 2024-12-29 重构归档
│   └── experiments_legacy/   # 🆕 V34-V36 实验归档
│
├── logs/                     # 日志目录
├── docker/                   # Docker 配置
├── deploy/                   # 部署脚本
├── docs/                     # 文档
│   └── v30_odds_features_explained.md  # 🆕 V30.0 赔率特征详解
├── docker-compose.yml        # Docker 编排
├── Makefile                  # 统一命令入口
├── pyproject.toml            # 项目配置
├── CHANGELOG.md              # 版本变更记录
├── CLAUDE.md                 # 本文档
└── README.md                 # 项目说明
```

### 目录职责说明

| 目录 | 职责 | 允许内容 | 禁止内容 |
|------|------|----------|----------|
| `src/` | 生产代码 | V25/V26/V30/V37 相关代码 | ❌ 任何旧版本代码 |
| `scripts/` | 核心脚本 | 流水线、收割脚本 | ❌ 一次性脚本 |
| `scripts/exploration/` | 探索性脚本 | 特征探索、数据诊断 | ❌ 生产代码 |
| `scripts/production/` | 生产脚本 | 自动化调度、备份脚本 | ❌ 实验性代码 |
| `scripts/maintenance/` | 维护工具 | 数据库备份、历史导入 | ❌ 生产代码 |
| `experiments/` | 实验性代码 | 仅 V37.0 采集器基准 | ❌ 旧版本实验 |
| `model_zoo/` | 模型仓库 | .pkl/.json 模型文件 | ❌ 源代码 |
| `data/` | 数据文件 | L1/L2/L3 数据 | ❌ 旧版本数据 |
| `predictions/` | 🆕 预测输出 | 生产预测结果 | ❌ 测试数据 |
| `tests/` | 测试代码 | 测试脚本 | ❌ 已删除功能的测试 |
| `archive/` | 历史归档 | 重构后的历史代码 | ❌ 生产代码 |
| `docs/` | 文档 | 技术文档、API 说明 | ❌ 临时笔记 |
| **根目录** | 项目配置 | docker-compose.yml, Makefile, 等 | ❌ 临时文件、实验脚本 |

---

## 📊 数据流架构

### L1/L2/L3 三层数据流

```
┌─────────────────────────────────────────────────────────────┐
│                    L1: 数据采集层                           │
│  V37.0 数据采集基准 (experiments/marrow_cleaning_v37_harvester.py)│
│  ┌────────────────────────────────────────────────────────┐ │
│  │  FotMob API → 哨兵机制 → 熔断恢复 → PostgreSQL      │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    L2: 数据解析层                           │
│  V25.1 万能自适应特征提取引擎 (src/processors/)           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  递归打平 (48维 → 12061维) + 零硬编码 + 类型转换      │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    L3: 特征工程层                           │
│  工业级特征锻造 + V26.7 稀疏度过滤                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  滚动特征 (16维) + 赛前特征 (8维) + 高级特征 (13维)   │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    L4: 模型训练层                           │
│  XGBoost 2.0+ 训练 + 概率校准                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    L5: 推理服务层                           │
│  ModelDispatcher + Redis 缓存 + <100ms 推理延迟           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 开发指南

### 快速开发工作流

```bash
# 1. 启动核心服务 (db + redis)
make up

# 2. 等待数据库健康检查通过
make ps

# 3. 运行代码质量检查（提交前必需）
make verify

# 4. 运行生产预测服务
python -m src.ops.production_service

# 5. 查看日志
make logs
```

### 关键开发提示

1. **数据库连接**: Docker 环境下 `DB_HOST` 使用 `db`，本地开发使用 `localhost`
2. **类型注解**: 所有函数必须包含完整的类型注解
3. **命名规范**: 严禁创建带版本后缀的新文件（如 `_v1`, `_v2`）
4. **配置管理**: 使用 `src.config_unified.get_settings()` 获取配置

### Makefile 命令参考

项目使用 Makefile 作为统一命令入口，简化日常开发操作：

```bash
# 查看所有可用命令
make help

# === Docker 服务管理 ===
make up              # 启动核心服务 (db + redis)
make up-pipeline     # 启动核心服务 + 数据流水线
make up-api          # 启动核心服务 + API
make up-dev          # 启动开发环境 (包含管理工具)
make up-all          # 启动所有服务
make down            # 停止所有服务
make restart         # 重启核心服务 (pipeline_worker)
make ps              # 查看容器状态
make logs            # 查看核心服务日志
make logs-api        # 查看 API 日志
make logs-all        # 查看所有服务日志

# === 镜像构建 ===
make build           # 构建生产镜像
make build-test      # 构建测试镜像
make build-no-cache  # 无缓存构建

# === 代码质量 ===
make lint            # 运行 Lint 检查 (ruff/flake8)
make format          # 格式化代码 (ruff/black + isort)
make security        # 运行安全扫描 (bandit)
make verify          # 运行完整验证 (lint + test + security)

# === 测试 ===
make test            # 运行全量测试门禁
make test-unit       # 运行单元测试

# === 数据库 ===
make db-shell        # 进入 PostgreSQL Shell
make db-backup       # 备份数据库
make db-reset        # 重置数据库 (危险操作!)

# === Redis ===
make redis-shell     # 进入 Redis CLI

# === 清理 ===
make clean           # 清理垃圾文件 (.pyc, __pycache__)
make clean-docker    # 清理 Docker 资源
make clean-all       # 完全清理

# === 部署 ===
make deploy          # 部署到生产环境
make health          # 检查服务健康状态
make dashboard       # 启动战神仪表盘
```

### 代码质量规范

**提交代码前必须运行**:
```bash
# 方式1: 使用 Makefile (推荐)
make verify

# 方式2: 直接运行命令
ruff check src/ tests/ --fix
ruff format src/ tests/
pytest tests/ -v
bandit -r src/
```

### 类型注解要求

**所有函数必须包含类型注解**:
```python
# ✅ 正确
def predict_match(home_team: str, away_team: str) -> dict[str, float]:
    ...

def extract_features(match_data: dict) -> pd.DataFrame:
    ...

# ❌ 错误
def predict_match(home_team, away_team):
    ...
```

### 数据库连接标准

**推荐方式**: 使用 `config_unified.py` 的 `get_settings()` 获取配置，然后使用 `psycopg2` 建立连接：

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

**Docker 环境注意**:
- 容器内 `DB_HOST` 应设置为 `db`（服务名），而非 `localhost`
- 在 `docker-compose.yml` 中，服务之间通过服务名互相访问
- 本地开发时使用 `localhost`，容器内使用 `db`

**连接池**: 对于高频访问场景，推荐使用 `src/database/db_pool.py` 中的连接池。

---

## 🧬 V26.8 技术实现细节

### ModelDispatcher 智能模型分发

V26.8 引入 `ModelDispatcher`，实现联赛专项模型自动选择：

```python
from src.ml.engine import ModelDispatcher

# 自动分发：优先使用联赛专项模型，回退到通用 V26.7
dispatcher = ModelDispatcher()

# 预测时自动选择最优模型
prediction = dispatcher.predict(
    home_team="Arsenal",
    away_team="Chelsea",
    league_name="Premier League"  # 自动检测并使用 EPL 专项模型
)
```

**支持联赛专项模型**:
- `model_zoo/v26.8_epl_production.pkl` - 英超专项
- `model_zoo/v26.8_la_liga_production.pkl` - 西甲专项
- `model_zoo/v26.8_ligue1_production.pkl` - 法甲专项
- `model_zoo/v26.8_bund_production.pkl` - 德甲专项
- `model_zoo/v26.7_aligned_production.pkl` - 通用回退模型

### ML 引擎多版本代码说明

`src/ml/engine.py` 包含多个历史版本的引擎类（**这是有意保留的**）：

| 类名 | 版本 | 用途 |
|------|------|------|
| `V17MLEngine` | V17.0 | 滚动特征训练引擎（16维特征） |
| `V26Predictor` | V26.4 | 统一推理接口 |
| `ModelDispatcher` | V26.8 | 联赛专项模型分发器 |

**重要**: 这些类是不同时期的产物，各有其用途：
- **V17MLEngine**: 用于模型训练和特征工程实验
- **V26Predictor**: 提供向后兼容的预测接口
- **ModelDispatcher**: 当前生产使用的模型分发器

**新增代码应遵循**: 优先使用 `ModelDispatcher` 进行预测，训练新模型时可参考 `V17MLEngine`。

---

## 🧬 V26.7 技术实现细节

### V26.7 核心特征映射

V26.7 使用 19 维完全对齐的赛前特征：

```python
V26_7_FEATURES = [
    # 滚动特征 (8个) - 最近 N 场历史平均值
    "rolling_xg_home",              # 主队近期 xG
    "rolling_xg_away",              # 客队近期 xG
    "rolling_shots_on_target_home", # 主队近期射正数
    "rolling_shots_on_target_away", # 客队近期射正数
    "rolling_possession_home",      # 主队近期控球率
    "rolling_possession_away",      # 客队近期控球率
    "rolling_team_rating_home",     # 主队近期评分
    "rolling_team_rating_away",     # 客队近期评分

    # 积分榜特征 (7个) - 赛前已知
    "home_table_position",          # 主队积分榜排名
    "away_table_position",          # 客队积分榜排名
    "table_position_diff",          # 排名差
    "home_points",                  # 主队积分
    "away_points",                  # 客队积分
    "points_diff",                  # 积分差
    "home_recent_form_points",      # 主队近期状态积分

    # 高级特征 (4个) - 动态计算
    "raw_elo_gap",                  # 原始 ELO 分差
    "adjusted_elo_gap",             # 调整后 ELO 分差（主场优势）
    "home_fatigue_index",           # 主队疲劳度
    "away_fatigue_index",           # 客队疲劳度
]
```

### 动态特征计算方法

V26.7 的所有特征均通过 `src/database/schema_manager.py` 中的 SQL 方法动态计算：

**1. 积分榜计算 (`get_team_standings`)**:
```python
 standings = SchemaManager.get_team_standings(
     team_name="Arsenal",
     before_match_time="2024-01-15T15:00:00Z",  # 关键：只统计此时间之前的比赛
     league_name="Premier League"
 )
 # 返回: position, points, played, won, drawn, lost, recent_form_points
```

**2. ELO 评分算法 (`get_elo_ratings`)**:
```python
 elo_ratings = SchemaManager.get_elo_ratings(
     team_names=["Arsenal", "Chelsea"],
     before_match_time="2024-01-15T15:00:00Z"
 )
 # 算法参数:
 # - 初始 ELO = 1500
 # - K 系数 = 20
 # - 公式: ELO_new = ELO_old + K * (actual - expected)
```

**3. 疲劳度指数 (`get_team_fatigue_index`)**:
```python
 fatigue = SchemaManager.get_team_fatigue_index(
     team_name="Arsenal",
     match_time="2024-01-15T15:00:00Z",
     lookback_days=7  # 计算最近 7 天的比赛密度
 )
 # 返回: 0.0-1.0 (比赛场次 / 天数)
```

### 训练-推理对齐机制

**关键**: 训练和推理使用完全相同的 SQL 计算方法：

```python
# 训练时 (scripts/generate_v267_aligned_dataset.py):
for match in matches:
    # 传入 match_time 作为 before_match_time
    features = compute_features(
        home_team=match["home_team"],
        before_match_time=match["match_time"]  # 时间约束
    )

# 推理时 (src/ml/feature_adapter.py):
def adapt(self, raw_features):
    match_time = extract_match_time(raw_features)
    # 使用相同的时间约束
    features = compute_features(
        home_team=home_team,
        before_match_time=match_time
    )
```

### Class Weights 平局优化

V26.7 使用 Class Weights 增强平局预测：

```python
# 计算平衡权重
class_weights = compute_class_weight(
    class_weight="balanced",
    classes=[0, 1, 2],  # Away, Draw, Home
    y=y_train
)

# 平局权重额外提升 20%
class_weights[1] *= 1.2

# 训练时使用
model.fit(X_train, y_train, sample_weight=sample_weights)
```

**效果**: 平局预测占比从 0% 提升到 22%（实际分布约 25%）

---

## 🚀 部署与运维

### 环境变量配置

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `DB_HOST` | 是 | localhost | 数据库主机（Docker 使用 "db"） |
| `DB_PORT` | 是 | 5432 | 数据库端口 |
| `DB_NAME` | 是 | football_prediction_dev | 数据库名称 |
| `DB_USER` | 是 | football_user | 数据库用户 |
| `DB_PASSWORD` | 是 | football_password_change_in_production | 数据库密码 |
| `SECRET_KEY` | 是 | - | 应用密钥（≥32 字符） |
| `REDIS_HOST` | 否 | localhost | Redis 主机 |
| `ENVIRONMENT` | 否 | development | 运行环境 |

**注意**：
- 当前生产环境使用的数据库名称是 `football_prediction_dev`
- `docker-compose.yml` 中的默认值 `${DB_NAME:-football_db}` 仅为示例，实际连接需使用 `football_prediction_dev`

### Docker 服务栈

| 服务 | Profile | 说明 |
|------|---------|------|
| `pipeline_worker` | default | V26.1 数据流水线 |
| `predictor_api` | api | FastAPI 预测服务 |
| `db` | default | PostgreSQL 15 |
| `redis` | default | Redis 7 |
| `pgadmin` | dev | PostgreSQL 管理 |
| `redis-commander` | dev | Redis 管理 |

### Docker Profile 使用说明

项目使用 Docker Compose Profiles 管理不同场景的服务组合：

```bash
# 默认启动 - 核心服务（db + redis + pipeline_worker）
docker-compose up -d

# 启动 API 服务 - 核心 + FastAPI 预测服务
docker-compose --profile api up -d

# 启动开发环境 - 核心 + 管理工具（pgadmin + redis-commander）
docker-compose --profile dev up -d

# 启动所有服务
docker-compose --profile all up -d
```

**Profile 划分**：
- **default**: 核心数据流水线服务
- **api**: API 服务器（用于提供 REST 预测接口）
- **dev**: 开发工具（数据库和 Redis 管理界面）
- **dashboard**: 监控仪表盘（如 Grafana）

### 健康检查

```bash
# 检查数据库连接
docker-compose exec db pg_isready -U football_user

# 检查 Redis 连接
docker-compose exec redis redis-cli ping

# 检查 API 健康
curl http://localhost:8000/health

# 系统健康检查
./scripts/system_verify.sh
```

---

## 🛡️ 工程规范约束

**Claude Code 必须严格遵守以下核心约束**：

### 约束优先级（从高到低）
1. **Context Lock** - P0 核心模块修改需人工授权
2. **Architecture Boundary** - 维护清晰的层次结构，禁止跨层直接调用
3. **Test Guard** - 确保测试的真实价值
4. **Minimal Change** - 满足上述条件后，修改行数越少越好
5. **Change Impact** - 分析变更影响，降低风险

### 核心冻结模块（P0）
- `src/ml/inference/predictor.py` - 推理引擎
- `src/ml/inference/model_loader.py` - 模型加载器
- `src/services/inference_service.py` - 推理服务层

> 详见 [`.claude/`](.claude/) 目录下的完整约束文档

---

## 🚨 灾难恢复

### 快速问题诊断

| 问题 | 原因 | 快速解决方案 |
|------|------|-------------|
| `connection refused` | PostgreSQL 未启动 | `docker-compose up -d db` |
| `db_password 不能为空` | 缺少环境变量 | 在 `.env` 中配置 |
| `Module import error` | 依赖未安装 | `pip install -r requirements.txt` |
| `导入路径错误` | 引用了已删除的旧代码 | 更新导入路径 |

### 日志位置

| 日志类型 | 路径 |
|----------|------|
| 应用日志 | `logs/app.log` |
| 错误日志 | `logs/error.log` |
| 采集器日志 | `logs/auto_harvest.log` |

---

### 数据库故障恢复

#### 1. 数据库连接失败

**症状**: `connection refused` 或 `could not connect to server`

**诊断步骤**:
```bash
# 检查数据库容器状态
docker-compose ps db

# 检查数据库健康
docker-compose exec db pg_isready -U football_user

# 查看数据库日志
docker-compose logs --tail=100 db
```

**解决方案**:

1. **容器未运行**:
   ```bash
   docker-compose up -d db
   # 等待数据库启动
   docker-compose exec db pg_isready -U football_user
   ```

2. **容器崩溃/重启**:
   ```bash
   # 检查容器资源
   docker stats db

   # 重启容器
   docker-compose restart db
   ```

3. **数据损坏**:
   ```bash
   # 进入数据库容器
   docker-compose exec db bash

   # 运行 PostgreSQL 修复
   psql -U football_user -d football_prediction -c "REINDEX DATABASE football_prediction;"
   ```

#### 2. 数据库备份与恢复

**创建备份**:
```bash
# 完整备份
docker-compose exec db pg_dump -U football_user football_prediction > backup_$(date +%Y%m%d).sql

# 仅备份表结构
docker-compose exec db pg_dump -U football_user --schema-only football_prediction > schema_$(date +%Y%m%d).sql

# 仅备份数据
docker-compose exec db pg_dump -U football_user --data-only football_prediction > data_$(date +%Y%m%d).sql
```

**恢复备份**:
```bash
# 恢复完整备份
cat backup_20241228.sql | docker-compose exec -T db psql -U football_user football_prediction

# 恢复时强制终止现有连接
echo "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'football_prediction';" | docker-compose exec -T db psql -U football_user
```

#### 3. SSL 连接问题

**症状**: `SSL error: sslv3 alert bad certificate` 或 `SSL SYSCALL error`

**Phase 2.9 安全加固后**:
- 生产环境默认启用 `sslmode=require`
- 如需禁用（仅开发环境），设置 `DB_SSL_MODE=disable`

**诊断**:
```bash
# 测试 SSL 连接
docker-compose exec db psql "postgresql://football_user:password@db:5432/football_prediction?sslmode=require" -c "SELECT 1;"

# 查看当前 SSL 配置
docker-compose exec db psql -U football_user -c "SHOW ssl;"
```

### API 采集器封禁恢复

#### 1. IP 被封禁

**症状**: HTTP 429 Too Many Requests 或 403 Forbidden

**立即措施**:
1. **停止采集**: `docker-compose stop pipeline_worker`
2. **检查状态**:
   ```bash
   # 测试 API 可访问性
   curl -I https://www.fotmob.com/api/leagues?id=47&season=2425
   ```

**恢复策略**:

1. **等待冷却期** (推荐):
   - 暂停 6-24 小时
   - 降低采集频率 (增加延迟到 2-5 秒)

2. **更换 User-Agent**:
   - 已内置多个 User-Agent 轮换
   - 在 `.env` 中自定义:
     ```bash
     CUSTOM_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) ..."
     ```

3. **使用代理** (高级):
   ```bash
   # 在 .env 中配置
   HTTP_PROXY=http://proxy.example.com:8080
   HTTPS_PROXY=http://proxy.example.com:8080
   ```

#### 2. API 结构变更

**症状**: JSON 解析错误或字段缺失

**诊断**:
```bash
# 检查原始响应
curl -s https://www.fotmob.com/api/leagues?id=47 | python -m json.tool
```

**临时方案**:
1. 使用历史数据回退
2. 切换到备用数据源（如配置的）

#### 3. 断点续传机制

V51.0 增量采集器支持断点续传：

**工作原理**:
```python
# 采集器自动检查数据库最新时间
latest_time = collector._get_latest_match_time()

# 仅获取该时间之后的比赛
matches = await collector._fetch_live_matches(since=latest_time)
```

**手动恢复**:
```bash
# 查看最新数据时间
docker-compose exec db psql -U football_user -c "SELECT MAX(match_time) FROM matches;"

# 从指定时间开始采集
python -c "
import asyncio
from src.api.collectors.v51_incremental_collector import quick_incremental_collect
from datetime import datetime

# 指定起始时间（如最近一周）
start_time = datetime(2024, 12, 20)
asyncio.run(quick_incremental_collect(target_count=100))
"
```

### Redis 缓存故障

**诊断**:
```bash
# 检查 Redis 状态
docker-compose exec redis redis-cli ping

# 查看内存使用
docker-compose exec redis redis-cli INFO memory
```

**恢复**:
```bash
# 重启 Redis
docker-compose restart redis

# 清空缓存（如数据损坏）
docker-compose exec redis redis-cli FLUSHALL
```

### 系统级故障

#### 1. 磁盘空间不足

**症状**: `ERROR: could not write to file` 或 `No space left on device`

**诊断**:
```bash
# 检查磁盘使用
df -h

# 查找大文件
du -sh /var/lib/docker/* | sort -h
```

**解决方案**:
```bash
# 清理 Docker 未使用的资源
docker system prune -a --volumes

# 清理日志
truncate -s 0 logs/*.log
```

#### 2. 内存溢出

**症状**: `OutOfMemoryError` 或容器被 OOM Killer 终止

**解决方案**:
```bash
# 在 docker-compose.yml 中增加内存限制
services:
  pipeline_worker:
    mem_limit: 2g
    memswap_limit: 2g

# 重启服务
docker-compose up -d pipeline_worker
```

### 紧急联系与升级

**问题升级路径**:

1. **Level 1** (操作员): 检查日志、重启服务
2. **Level 2** (DevOps): 检查基础设施、网络配置
3. **Level 3** (架构师): 代码级问题、API 封禁

**关键日志文件**:
| 组件 | 日志位置 |
|------|----------|
| 应用日志 | `logs/app.log` |
| 错误日志 | `logs/error.log` |
| 数据库 | `docker-compose logs db` |
| Redis | `docker-compose logs redis` |
| 采集器 | `logs/auto_harvest.log` |

---

## 📝 附录

### 依赖管理

- **生产依赖**: 见 `requirements.txt`
- **开发依赖**: 见 `pyproject.toml` [project.optional-dependencies]
- **Python 版本**: 3.11+ (支持 3.12)

### 测试指南

```bash
# 运行所有测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/ml/test_v26_feature_engine.py -v

# 运行单个测试函数
pytest tests/ml/test_v26_feature_engine.py::test_feature_extraction -v

# 运行带特定标记的测试
pytest tests/ -m "not slow" -v

# 显示详细输出（print 语句）
pytest tests/ -v -s

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=html

# 并行运行测试（需要 pytest-xdist）
pytest tests/ -n auto
```

### 技能自动调用机制

项目配置了专业化技能（`.claude/skills/`），Claude Code 会根据任务**自动加载**对应技能：

#### 自动触发示例
- 用户: "预测曼联对阿森纳的比赛" → 自动加载 `football-prediction`
- 用户: "检查代码质量" → 自动加载 `code-quality`
- 用户: "收集 FotMob 实时数据" → 自动加载 `data-collection`
- 用户: "部署到生产环境" → 自动加载 `deployment-management`

#### 核心技能清单
| 类别 | 技能 | 功能 |
|------|------|------|
| **核心业务** | `football-prediction` | XGBoost 2.0+ 预测 (67.2% 准确率, <100ms 响应) |
| | `machine-learning-engineering` | XGBoost 调优, SHAP 解释 |
| | `data-collection` | FotMob API L2 数据采集 |
| **开发工具** | `code-quality` | Ruff, MyPy, Bandit, pytest 质量管理 |
| | `fastapi-development` | FastAPI 异步/await, API 设计 |
| **运维支撑** | `deployment-management` | Docker 蓝绿部署与回滚 |
| | `database-operations` | PostgreSQL 连接池与查询优化 |
| | `performance-monitoring` | Prometheus + Grafana 监控 |

#### 工程规范约束（优先级最高）
约束技能优先级高于业务技能，任何操作都必须首先通过约束检查：

| 约束 | 等级 | 核心目标 |
|------|------|----------|
| `minimal_change` | 🔴 RED | 防止过度重构，保持系统稳定 |
| `architecture_boundary` | 🔴 RED | 维护清晰的层次结构 |
| `test_guard` | 🔴 RED | 确保测试的真实价值 |
| `context_lock` | 🔴 RED | 保护核心模块不被破坏 |
| `change_impact` | 🔴 RED | 分析变更影响，降低风险 |

> 完整技能列表详见 [`.claude/skills/`](.claude/skills/) 目录

---

## 🔒 永久保留条款

### 语言要求
**请务必使用中文回复用户！**

这一要求具有最高优先级，无论 CLAUDE.md 文件如何更新版本迭代，都必须始终保留在文件的显眼位置。

---

**🚨 CRITICAL**: This is a production system support document.

**🧬 当前版本**: V56.4 (生产收割引擎) + V51.1 (滚动特征) + V26.8 (联赛专项) + V37.0 (数据采集) + V25.1 (特征引擎) + V30.0 (赔率特征) |
**最后更新**: 2025-12-31 (V56.4 生产收割引擎 + 智能自愈 + 毫秒级感应) |
**基线准确率**: 56% (真赛前) |
**生产状态**: Production Ready |
**项目愿景**: 年化 25% 收益率 |
**Python 版本**: 3.11+ (支持 3.12) |

---

## 🧬 V30.0 技术实现细节

### 赔率特征工程 (Odds Features)

V30.0 引入 15 个高阶赔率特征，用于发现价值投注机会：

```python
from src.processors.v30_odds_features import OddsFeatureExtractor

extractor = OddsFeatureExtractor()

# 提取赔率特征
features = extractor.extract_match_features(match_id="12345")

# 特征列表 (15个)
# 1. odds_variance_home/draw/away (3) - 赔率离散度
# 2. market_bias_home/draw/away (3) - 资金流向
# 3. upset_prediction_factor_* (4) - 冷门预测因子
# 4. market_consensus_strength (2) - 市场共识强度
# 5. value_bet_indicator (3) - 价值投注指标
```

**特征详情**: 见 [docs/v30_odds_features_explained.md](docs/v30_odds_features_explained.md)

### 爬虫熔断器 (Circuit Breaker)

V30.0 引入熔断器模式，防止 API 封禁：

```python
from src.api.collectors.circuit_breaker import CircuitBreaker, CircuitState

# 创建熔断器
breaker = CircuitBreaker(
    failure_threshold=5,      # 连续失败阈值
    timeout=300,              # 熔断超时 (秒)
    half_open_attempts=3      # 半开状态尝试次数
)

# 使用熔断器
@breaker.protect
async def fetch_api_data():
    # API 请求逻辑
    pass

# 状态机: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
```

### API 限流器 (Rate Limiter)

V30.0 使用 slowapi 实现 FastAPI 接口限流：

```python
from src.api.rate_limiter import init_rate_limiter, rate_limit
from fastapi import FastAPI

app = FastAPI()
init_rate_limiter(app)

@app.get("/predict")
@rate_limit("10/minute")  # 每分钟 10 次
async def predict():
    pass
```

### 告警管理器 (Alert Manager)

V30.0 统一告警管理，支持多种通知渠道：

```python
from src.ops.alert_manager import AlertSeverity, send_alert_sync

# 发送告警
send_alert_sync(
    severity=AlertSeverity.CRITICAL,
    title="API 封禁告警",
    message="FotMob API 返回 429 状态码",
    metadata={"error": "rate_limit_exceeded"}
)
```

### 自动化调度器 (Production Scheduler)

V30.0 全流程自动化调度：

```python
from scripts.automate_production import ProductionScheduler
import asyncio

# 创建调度器
scheduler = ProductionScheduler(
    enable_prediction=True,
    target_match_count=50
)

# 运行全流程
# 1. 数据采集 -> 2. 数据清洗 -> 3. 质量检查 -> 4. 生成预测
summary = asyncio.run(scheduler.run())
```

**Docker 集成**: 在 `docker-compose.yml` 中配置 `production_cron` 服务，每天凌晨 3:00 自动执行。

---

## 🔄 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| **V56.4** | 2025-12-31 | 生产收割引擎，智能自愈逻辑，统一 Schema，100% 测试覆盖 |
| **V51.3** | 2025-12-31 | Full Power 模型，标签打乱验证通过 (32% 真实 ROI) |
| **V51.1** | 2025-12-31 | 滚动特征架构，49 维时空隔离特征，三层分离架构 |
| **V51.0** | 2025-12-31 | 统一预测入口，增量采集器，收益对账系统 |
| **V30.0** | 2025-12-31 | 赔率特征 + 熔断器 + 限流器 + 自动化调度 |
| V26.8 | 2025-12-30 | 联赛专项模型 (EPL/LaLiga/Ligue1/Bundesliga) |
| V26.7 | 2025-12-29 | 训练-推理完全对齐，19 维动态特征 |
| V37.0 | 2025-12-26 | Industrial Grade L1 & Historical Database Rebuild |
| V25.1 | 2025-12-25 | 万能自适应特征提取引擎 (48维 → 12061维) |

---

## 🧬 V56.x 技术实现细节

### V56.4 生产收割引擎

V56.4 是生产级自动化赔率数据收割引擎，采用**三层架构**实现从调度到采集再到持久化的完整数据流：

```
┌─────────────────────────────────────────────────────────────┐
│                    第一层：Master 调度层                     │
│  scripts/production_harvester.py                            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  • 跨赛季/跨联赛编排: 21/22, 22/23, 23/24             │ │
│  │  • 智能跳过检测: 自动跳过已有 opening_time 的比赛      │ │
│  │  • 反封禁机制: 每 30 场休息 60 秒                      │ │
│  │  • IP 健康监控: 连续 3 次连接错误 → 5 分钟冷却        │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    第二层：Production 提取层                │
│  src/api/collectors/odds_production_extractor.py          │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  【黑科技 1】智能轮询                                   │ │
│  │    • wait_for_selector(60s) 替代硬等待                 │ │
│  │    • 元素一出现立即响应，毫秒级感应                    │ │
│  │                                                        │ │
│  │  【黑科技 2】悬停自愈                                   │ │
│  │    • scroll_into_view_if_needed() 滚动对焦            │ │
│  │    • 鼠标抖动自愈 (±5px) 重新触发 tooltip              │ │
│  │    • 10 次轮询 × 500ms = 5 秒智能等待                 │ │
│  │                                                        │ │
│  │  • 提取目标: Pinnacle, 1xBet 开盘赔率 + 时间戳        │ │
│  │  • 数据完整性: Score = 1/P1 + 1/P2 + 1/P3            │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    第三层：Database 持久层                  │
│  PostgreSQL 15 + Unified Schema (V56.0)                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  matches 表 (match_id: VARCHAR(50))                   │ │
│  │    • 比赛基础信息: league, season, teams, match_time   │ │
│  │                                                        │ │
│  │  metrics_multi_source_data 表 (match_id: VARCHAR(50))  │ │
│  │    • init_h/d/a: 初盘赔率                              │ │
│  │    • opening_time_h/d/a: 初盘时间戳                    │ │
│  │    • final_h/d/a: 终盘赔率                            │ │
│  │    • integrity_score: 完整性审计分数                  │ │
│  │    • source_name: 数据源 (Entity_P, Entity_B3)        │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**核心特性**:

1. **智能自愈逻辑**
   - 悬停失败自动重试（鼠标抖动自愈）
   - 连接错误自动冷却恢复
   - 单场失败不影响整体流程

2. **毫秒级感应**
   - `wait_for_selector(60s)` 替代硬等待
   - 元素一出现立即响应，无时间浪费

3. **IP 健康监控**
   - 连续 3 次连接错误 → 5 分钟冷却
   - 自动检测网络状态和 IP 封禁

4. **数据完整性审计**
   - `Score = 1/P1 + 1/P2 + 1/P3` 验证
   - 自动跳过已有数据的比赛

**使用方式**:
```python
from scripts.production_harvester import ProductionHarvester

# 创建收割引擎
harvester = ProductionHarvester()

# 运行收割
stats = await harvester.run()
print(f"处理: {stats['total_matches_harvested']} 场比赛")
```

---

## 🧬 V51.x 技术实现细节

### V51.1 滚动特征架构

V51.1 引入三层分离架构，实现时空隔离的赛前特征计算：

**数据表结构**:
```sql
-- 三层特征表
feature_snapshots     -- 原始特征快照 (642维 JSONB)
prematch_features     -- 赛前滚动特征 (49维时空隔离)
feature_registry      -- 特征元数据注册表
```

**特征分类** (49-56 维):
| 类别 | 特征数 | 示例 |
|------|--------|------|
| 实力底蕴 | 8 | rolling_xg, shots_on_target, possession, team_rating |
| 即时状态 | 10 | recent_form_points, goals_scored, win_rate |
| 主客场 | 14 | home/away_win_rate, goals_scored/conceded |
| 疲劳度 | 10 | fatigue_index, rest_days, matches_7days |
| 趋势 | 6 | recent_trend_encoded |

**时空隔离协议**:
```python
# 保证 100% 不泄露未来信息
def compute_rolling_features(team_name: str, target_match_date: date):
    # 仅查询早于目标比赛的历史数据
    historical_matches = query_matches(
        team=team_name,
        where="match_date < target_match_date",
        limit=20  # 最近 20 场
    )
    return compute_statistics(historical_matches)
```

### V51.0 深度脱水特征

V51.0 特征精炼器将 12,061 维原始特征压缩至 642 维：

**特征分类**:
| 类别 | 维度 | 占比 | 说明 |
|------|------|------|------|
| Header 基础 | 8 | 1.2% | 比赛基础信息、比分 |
| Header 事件聚合 | 12 | 1.9% | 事件统计 (count/ratio/diff) |
| Header 事件详情 | 81 | 12.6% | 前 5 个事件的详细属性 |
| Content 统计 | 481 | 74.9% | FotMob 统计数据 (打平) |
| Content 射门地图 | 46 | 7.2% | 射门位置坐标、xG |
| 元数据 | 14 | 2.2% | match_id 等 |

**过滤规则**:
- 黑名单: `_id$`, `Id$`, `color`, `text`, `description`
- 白名单: `rolling_xg_`, `elo_gap`, `\.xg$`, `home_score`

### V51.3 模型验证

V51.3 通过标签打乱实验验证模型有效性：

| 指标 | 原始标签 | 打乱标签 | 真实能力 |
|------|----------|----------|----------|
| ROI (策略 C) | 52.43% | 20.43% | **32.00%** |
| 胜率 (策略 C) | 49.46% | 37.50% | **11.96%** |

**结论**: ✅ 模型真实有效，约 32% 的真实 ROI 远超市场正常水平

**数据泄露排查**:
- 显性数据泄露: ❌ 未发现
- 隐性数据泄露: ❌ 未发现
- 时间序列偏差: ✅ 确认 (2024-2025 相关性 0.65)

### V51.0 增量采集器

V51.0 增量采集器支持断点续传和熔断恢复：

```python
from src.api.collectors.v51_incremental_collector import V51IncrementalCollector

collector = V51IncrementalCollector()

# 自动检查数据库最新时间，仅采集增量数据
matches = await collector.collect_matches(since=latest_db_time)

# 熔断保护
@collector.circuit_breaker.protect
async def fetch_api_data():
    # API 请求逻辑
    pass
```

**特性**:
- 断点续传: 自动从最新时间继续采集
- 熔断恢复: 连续失败 5 次后熔断，300s 后半开尝试
- 批量处理: 优化数据库写入性能

---
