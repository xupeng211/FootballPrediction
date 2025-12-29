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
| **生产版本** | **V26.8** (联赛专项) + **V50.0** (数据采集) + **V25.1** (特征引擎) |
| **基线准确率** | 56% (真赛前) |
| **特征维度** | 19 维动态特征 |
| **数据量** | 9,305+ 场对齐训练数据 |
| **推理延迟** | <100ms |
| **训练-推理对齐** | ✅ 完全对齐 |
| **模型分发** | ✅ ModelDispatcher (联赛专项 vs 通用) |

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
| **模型分发** | **ModelDispatcher** | `src/ml/engine.py:ModelDispatcher` |
| **数据采集** | **V50.0** | `src/api/collectors/v50_*.py` |
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
- **实验代码**: 统一存放于 `experiments/` 目录
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
├── src/                      # ⭐ 生产代码（仅 V25/V26/V50）
│   ├── api/
│   │   └── collectors/       # V50.0 数据采集器
│   ├── config_unified.py     # 统一配置管理
│   ├── core/                 # 核心业务逻辑
│   ├── database/             # 数据库层
│   ├── main.py               # FastAPI 入口
│   ├── ml/                   # 机器学习层
│   │   ├── engine.py         # XGBoost 训练引擎
│   │   ├── features/         # 特征工程
│   │   ├── inference/        # 推理服务
│   │   └── data/             # 数据加载器
│   ├── ops/                  # 运维脚本
│   ├── processors/           # V25.1 特征提取引擎
│   └── services/             # 业务服务层
│
├── scripts/                  # 核心脚本
│   ├── run_v26_full_pipeline.py      # ⭐ 完整流水线
│   ├── auto_harvest_batches.py       # ⭐ 自动收割
│   ├── run_v26_full_harvest.py        # ⭐ 全量收割
│   ├── collectors/                   # 数据采集器
│   └── exploration/                  # 🔍 探索性脚本（非生产）
│       └── l3_feature_explorer.py    # L3 特征探索工具
│
├── experiments/              # 🔬 实验性代码（V33+）
│   ├── ml/
│   │   ├── miners_v33/       # V33.0 实验性挖掘器
│   │   └── miners_v34/       # V34.0 全息收割机
│   └── v3*_*.py              # 其他实验脚本
│
├── model_zoo/                # 📦 历史模型仓库
│   ├── registry.md           # 模型注册表
│   └── v1*.pkl               # 历史模型文件
│
├── data/                     # 📊 数据目录
│   ├── production/           # L1/L2 原始数据
│   ├── processed/            # L3 特征数据
│   └── models/               # 当前生产模型
│
├── tests/                    # ✅ 测试套件
├── archive/                  # 📦 历史归档
├── docker-compose.yml        # Docker 编排
├── pyproject.toml            # 项目配置
└── CLAUDE.md                 # 本文档
```

### 目录职责说明

| 目录 | 职责 | 允许内容 | 禁止内容 |
|------|------|----------|----------|
| `src/` | 生产代码 | V25/V26/V50 相关代码 | ❌ 任何旧版本代码 |
| `scripts/` | 核心脚本 | 流水线、收割脚本 | ❌ 一次性脚本 |
| `scripts/exploration/` | 探索性脚本 | 特征探索、数据诊断 | ❌ 生产代码 |
| `experiments/` | 实验性代码 | V33+ 研发代码 | ❌ 生产代码 |
| `model_zoo/` | 历史模型 | .pkl/.json 模型文件 | ❌ 源代码 |
| `data/` | 数据文件 | L1/L2/L3 数据 | ❌ 旧版本数据 |
| `tests/` | 测试代码 | 测试脚本 | ❌ 已删除功能的测试 |

---

## 📊 数据流架构

### L1/L2/L3 三层数据流

```
┌─────────────────────────────────────────────────────────────┐
│                    L1: 数据采集层                           │
│  V50.0 Rich L1 扫描引擎 (src/api/collectors/v50_*.py)    │
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
│  工业级特征锻造 + V26.1 稀疏度过滤                       │
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
│  FastAPI + Redis 缓存 + <100ms 推理延迟                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 开发指南

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

**必须使用统一配置**:
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
| `DB_PASSWORD` | **是** | - | 数据库密码 |
| `SECRET_KEY` | **是** | - | 应用密钥（≥32 字符） |
| `REDIS_HOST` | 否 | localhost | Redis 主机 |
| `ENVIRONMENT` | 否 | development | 运行环境 |

### Docker 服务栈

| 服务 | Profile | 说明 |
|------|---------|------|
| `pipeline_worker` | default | V26.1 数据流水线 |
| `predictor_api` | api | FastAPI 预测服务 |
| `db` | default | PostgreSQL 15 |
| `redis` | default | Redis 7 |
| `pgadmin` | dev | PostgreSQL 管理 |
| `redis-commander` | dev | Redis 管理 |

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

**Claude Code 必须严格遵守以下工程规范**：

### 核心规范文件
- **[.claude/context_lock.skill.md](.claude/context_lock.skill.md)** - 核心资产冻结
- **[.claude/architecture_boundary.skill.md](.claude/architecture_boundary.skill.md)** - 架构分层约束
- **[.claude/test_guard.skill.md](.claude/test_guard.skill.md)** - 测试保护
- **[.claude/minimal_change.skill.md](.claude/minimal_change.skill.md)** - 最小修改原则

### 优先级金字塔
1. **Context Lock**: P0 核心模块修改需人工授权
2. **Architecture Boundary**: 架构正确性 > 代码简洁性
3. **Test Guard**: 功能正确性 > 性能优化
4. **Minimal Change**: 满足上述条件后，修改行数越少越好

---

## 🚨 故障处理

### 常见问题诊断

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `connection refused` | PostgreSQL 未启动 | `docker-compose up -d db` |
| `db_password 不能为空` | 缺少环境变量 | 在 `.env` 中配置 |
| `Module import error` | 依赖未安装 | `pip install -r requirements.txt` |
| `导入路径错误` | 引用了已删除的旧代码 | 更新导入路径 |

### 日志位置

| 日志类型 | 路径 |
|----------|------|
| 应用日志 | `logs/app.log` |
| 错误日志 | `logs/error.log` |
| 收割日志 | `logs/auto_harvest.log` |

---

## 🚨 灾难恢复 (Disaster Recovery)

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

### 技能调用

项目配置了专业化技能（`.claude/skills/`），Claude Code 会自动调用：

#### 核心业务技能 (4个)
- `football-prediction` - 足球预测核心 (XGBoost 2.0+, 67.2% 准确率, <100ms 响应)
- `report-generation` - 报告生成 (PDF/Word/Excel, 专业可视化)
- `machine-learning-engineering` - ML 工程工具 (XGBoost 调优, SHAP 解释)
- `data-collection` - 数据采集 (FotMob API L2 数据, 实时统计)

#### 运维支撑技能 (4个)
- `performance-monitoring` - 性能监控 (Prometheus + Grafana)
- `deployment-management` - 部署管理 (Docker, 蓝绿部署, 回滚)
- `deployment-operations` - 部署运维 (容器化管理, 健康监控, 故障诊断)
- `database-operations` - 数据库操作 (PostgreSQL 连接池, 查询优化)

#### 开发工具技能 (6个)
- `code-quality` - 代码质量管理 (Ruff, MyPy, Bandit, pytest)
- `api-testing` - API 测试工具 (FastAPI endpoint 测试)
- `data-engineering` - 数据管道工具 (ETL, 特征流水线)
- `docker-devops` - Docker 运维 (容器编排, 健康监控)
- `fastapi-development` - FastAPI 最佳实践 (异步/await, API 设计)
- `feature-engineering` - 特征工程 (V25.1 自适应提取, 48→12061维)

#### 数据采集技能 (1个)
- `v26-harvest` - V26 生产级数据收割 (零缺陷, 批处理, 监控)

#### 技能使用示例

```
User: "预测曼联对阿森纳的比赛"
→ Claude 自动加载 football-prediction 技能
→ 运行: python -m src.ops.production_service

User: "检查代码质量"
→ Claude 自动加载 code-quality 技能
→ 运行: make verify

User: "收集 FotMob 实时数据"
→ Claude 自动加载 data-collection 技能
→ 运行 V50.0 采集器
```

#### 工程规范约束技能

除了上述专业技能外，项目还配置了 4 个核心约束技能（`.claude/*.skill.md`）：

| 技能 | 约束等级 | 核心目标 |
|------|----------|----------|
| `minimal_change` | 🔴 RED | 防止过度重构，保持系统稳定 |
| `architecture_boundary` | 🔴 RED | 维护清晰的层次结构 |
| `test_guard` | 🔴 RED | 确保测试的真实价值 |
| `context_lock` | 🔴 RED | 保护核心模块不被破坏 |

**注意**: 约束技能优先级高于业务技能，任何操作都必须首先通过约束检查。

#### 辅助技能文件

除了技能目录外，项目还提供了 3 个辅助技能文件（`.claude/skills/*.md`）：

| 文件 | 用途 |
|------|------|
| `async_testing.md` | 异步测试指南 (pytest-asyncio, 异步 mock) |
| `dependency_injection_mock.md` | 依赖注入模拟 (FastAPI 依赖, Mock 策略) |
| `naming_convention.md` | 命名规范 (文件名、变量名、类名规范) |

---

## 🔒 永久保留条款

### 语言要求
**请务必使用中文回复用户！**

这一要求具有最高优先级，无论 CLAUDE.md 文件如何更新版本迭代，都必须始终保留在文件的显眼位置。

---

**🚨 CRITICAL**: This is a production system support document.

**🧬 当前版本**: V26.8 (联赛专项) + V50.0 (数据采集) + V25.1 (特征引擎) |
**最后更新**: 2025-12-29 (技能目录补充 + Makefile 命令完善) |
**基线准确率**: 56% (真赛前) |
**生产状态**: Production Ready |
**项目愿景**: 年化 25% 收益率 |
