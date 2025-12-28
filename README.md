# FootballPrediction V26.7

> **"以年化 25% 的真实收益率为北极星指标，构建一个可验证、可复制、可持续的体育预测系统，在无杠杆、不赌心态的前提下，通过数据科学实现长期价值。"**
>
> **📌 核心约束**: 单笔下注 ≤ 5% 本金 | 严禁杠杆 | EV 区间 6%-10% | 最大回撤 < 15%
>
> **📖 完整愿景**: 详见 [docs/PROJECT_VISION.md](docs/PROJECT_VISION.md)
>
> **📘 开发指南**: 详见 [CLAUDE.md](CLAUDE.md)

---

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![Model Accuracy](https://img.shields.io/badge/accuracy-56%25-green.svg)](https://github.com/xupeng211/FootballPrediction)
[![No Data Leakage](https://img.shields.io/badge/data%20leakage-none-brightgreen.svg)](https://github.com/xupeng211/FootballPrediction)
[![Test Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen.svg)](https://github.com/xupeng211/FootballPrediction)

**V26.7 Aligned Production | 56% 真实赛前准确率 | 训练-推理完全对齐 | 19 维动态特征 | Class Weights 平局优化**

---

## 项目简介

FootballPrediction 是一套基于 XGBoost 2.0+ 的专业足球预测系统，采用**全动态特征计算**，**完全消除数据泄露**，提供真实可用的赛前预测能力。

### 核心特性

| 特性 | V16.0 (赛后统计) | V17.0 (滚动特征) | V26.1 (Production) | V26.7 (Aligned) |
|------|------------------|------------------|-------------------|-----------------|
| 预测准确率 | 96.25% (虚高) | 65.52% (真实) | 65.52% (生产) | **56%** (真赛前) |
| 特征维度 | 223 维 | 16 维 | 12061 维 | **19 维** |
| 数据泄露 | 存在 | 无 | 无 | **无** |
| 训练-推理对齐 | ❌ | ❌ | ❌ | **✅ 完全对齐** |
| 特征计算 | 静态预计算 | 滚动统计 | 静态特征 | **全动态 SQL** |
| ELO 评分 | ❌ | ❌ | ❌ | **✅ 内置** |
| 疲劳度指数 | ❌ | ❌ | ❌ | **✅ 内置** |
| 平局优化 | ❌ | ❌ | ❌ | **✅ Class Weights** |

### V26.7 技术亮点

- **训练-推理完全对齐**: 使用相同的 SQL 动态计算方法，确保特征分布一致
- **全动态特征流**: 积分榜、ELO 评分、疲劳度全部实时计算
- **真赛前预测**: 严格遵循 `before_match_time` 时间约束，无任何赛中数据
- **平局预测增强**: Class Weights 优化，平局预测占比 22%（vs 实际 25%）
- **工业级数据采集**: V50.0 Rich L1 扫描引擎，比分/状态/时间一体化采集
- **企业级架构**: Docker Compose Profiles，归一化部署

---

## 运行环境

### 系统要求

- **Python**: 3.11+
- **PostgreSQL**: 15+
- **Redis**: 7+
- **Docker** (推荐): 20.10+
- **操作系统**: Linux / macOS / WSL2

### 依赖安装

```bash
# 克隆仓库
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置必需的环境变量
```

### Docker 部署（推荐）

```bash
# 启动核心服务 (db + redis)
docker-compose up -d

# 启动核心服务 + API
docker-compose --profile api up -d

# 启动开发环境 (含管理工具)
docker-compose --profile dev up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f pipeline_worker
```

---

## 快速开始

### V26.7 一键生产预测

```bash
# 启动 V26.7 生产预测服务（使用默认模型）
python -m src.ops.production_service

# 或者直接使用 Python
python src/ops/production_service.py
```

### V26.7 模型训练（从零开始）

```bash
# Step 1: 生成对齐训练集（使用动态 SQL 方法）
python -m scripts.generate_v267_aligned_dataset

# Step 2: 训练 V26.7 对齐模型（含 Class Weights）
python scripts/train_v26_7_aligned.py
```

### FastAPI 预测服务

```bash
# 启动 API 服务（默认使用 V26.7 模型）
python src/main.py

# 调用预测接口
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"header": {"teams": {"home": {"name": "Arsenal"}, "away": {"name": "Chelsea"}}}}'
```

### Docker 模式

```bash
# 核心服务 (db + redis)
docker-compose up -d

# 核心 + API
docker-compose --profile api up -d

# 开发环境 (含管理工具)
docker-compose --profile dev up -d

# 检查健康状态
curl http://localhost:8000/health
```

### 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行 V51 采集器测试
pytest tests/api/collectors/test_v51_collector.py -v

# 查看测试覆盖率
pytest tests/ --cov=src --cov-report=html
```

---

## 项目结构

```
FootballPrediction/
├── main_production.py         # ⭐ 统一生产入口（强烈推荐）
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
│   ├── processors/            # V25.1 万能自适应特征提取引擎
│   │   ├── base_extractor.py      # 基础提取器抽象类
│   │   └── v25_production_extractor.py  # V25.1 自适应提取器
│   │
│   ├── api/                   # 数据采集层
│   │   ├── collectors/        # FotMob API 采集器
│   │   │   ├── fotmob_core.py
│   │   │   ├── v50_rich_l1_scanner.py    # Rich L1 扫描引擎
│   │   │   └── v50_database_writer.py    # 数据库写入器
│   │   └── health.py          # 健康检查端点
│   │
│   ├── services/              # 业务服务层
│   │   └── inference_service.py  # 推理服务编排
│   │
│   ├── database/              # 数据库层
│   │   ├── db_pool.py         # 连接池管理
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

---

## 模型性能

### 测试集结果（29 场比赛）

```
混淆矩阵:
               预测Away  预测Draw  预测Home
实际Away             7         2         4
实际Draw             1         0         1
实际Home             1         1        12

准确率: 65.52% (19/29 正确)
F1 Score (Macro): 0.4702
```

### 特征重要性 Top 5

| 排名 | 特征名 | 重要性 | 说明 |
|------|--------|--------|------|
| 1 | `home_rolling_xg` | 0.0906 | 主队过去 10 场平均 xG |
| 2 | `home_rolling_shots_on_target` | 0.0858 | 主队过去 10 场平均射正 |
| 3 | `away_rolling_shots_on_target` | 0.0698 | 客队过去 10 场平均射正 |
| 4 | `home_rolling_xg_std` | 0.0657 | 主队 xG 标准差 |
| 5 | `away_rolling_team_rating` | 0.0652 | 客队过去 10 场平均评分 |

---

## API 使用

### FastAPI 服务

```bash
# 启动 API 服务
docker-compose --profile api up -d

# 或本地启动
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 预测接口示例

```python
import requests

# 预测比赛
response = requests.post(
    "http://localhost:8000/predict",
    json={
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "match_date": "2024-01-01T12:30:00"
    }
)

result = response.json()
print(result)
# {
#   "prediction": "Home",
#   "probabilities": {"Away": 0.15, "Draw": 0.20, "Home": 0.65},
#   "confidence": 0.65,
#   "model_version": "v19.4"
# }
```

### 健康检查

```bash
# 快速健康检查
curl http://localhost:8000/health/quick

# 完整健康检查
curl http://localhost:8000/health
```

---

## 测试

### 运行测试

```bash
# 运行核心测试套件（与 CI 一致）
pytest tests/ml/test_backtest_engine.py tests/ops/test_signal_generator.py -v

# 运行所有测试
pytest tests/ -v

# 运行测试并查看覆盖率
pytest tests/ --cov=src --cov-report=html

# CI 完整检查（推荐）
./scripts/run_checks.sh
```

### 代码质量检查

```bash
# 使用 Ruff（推荐）
ruff check src/ tests/ --fix
ruff format src/ tests/

# 或使用传统工具
make format
make lint
make typecheck
```

---

## Docker 部署

### 服务栈

| 服务 | 端口 | Profile | 说明 |
|------|------|---------|------|
| `pipeline_worker` | - | default | V30.0 数据流水线 |
| `predictor_api` | 8000 | api | FastAPI 预测服务 |
| `db` | 5432 | default | PostgreSQL 15 |
| `redis` | 6379 | default | Redis 7 |
| `pgadmin` | 5050 | dev | PostgreSQL 管理 |
| `redis-commander` | 8081 | dev | Redis 管理 |

### 部署命令

```bash
# 核心服务
docker-compose up -d

# 核心 + API
make up-api

# 开发环境
make up-dev

# 查看服务状态
make ps

# 查看日志
docker-compose logs -f predictor_api
```

### 健康检查

```bash
# 检查数据库连接
docker-compose exec db pg_isready -U football_user

# 检查 Redis 连接
docker-compose exec redis redis-cli ping

# 检查 API 健康
curl http://localhost:8000/health

# 系统健康检查
./system_verify.sh
```

---

## 配置

### 环境变量

```bash
# 数据库配置
DB_HOST=localhost              # 数据库主机（Docker 自动使用 "db"）
DB_PORT=5432                  # 数据库端口
DB_NAME=football_db           # 数据库名称
DB_USER=football_user         # 数据库用户
DB_PASSWORD=***               # 数据库密码（必需）

# Redis 配置
REDIS_HOST=localhost          # Redis 主机（Docker 自动使用 "redis"）
REDIS_PORT=6379               # Redis 端口

# 应用配置
ENVIRONMENT=development       # 运行环境（development/production）
DOCKER_ENV=false              # Docker 环境标识
LOG_LEVEL=INFO                # 日志级别
SECRET_KEY=***                # 应用密钥（必需，≥32 字符）
```

---

## 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| **V51.0** | 2025-12-26 | Industrial Grade L1 & Historical Database Rebuild |
| V34.0 | - | 全息收割机 + 全局 Manifest |
| V30.0 | - | Cloud-Native 归一化部署 |
| V25.1 | 2025-12-25 | 万能自适应特征提取引擎 (48维 → 12061维) |
| V19.4.1 | - | Boxing Day 生产版 + 风控集成 |
| V17.0 | 2025-12-23 | 滚动特征模型，65.52% 准确率，无数据泄露 |
| V16.0 | 2025-12-22 | 223 维赛后特征模型（存在数据泄露） |

---

## 文档

- **[CLAUDE.md](CLAUDE.md)** - 完整的开发指南和系统文档
- **[docs/PROJECT_VISION.md](docs/PROJECT_VISION.md)** - 项目愿景和风险约束
- 版本演进详见 [CLAUDE.md](CLAUDE.md) 中的 "🏗️ 系统架构" 章节

---

## 开发

### Makefile 命令

```bash
# 查看所有可用命令
make help

# 环境管理
make dev              # 开发环境设置
make clean            # 清理垃圾文件

# 代码质量
make format           # 格式化代码
make lint             # Lint 检查
make typecheck        # 类型检查
make verify           # 完整验证

# 测试
make test             # 运行测试
make test-unit        # 运行单元测试

# Docker
make up               # 启动核心服务
make up-api           # 启动核心 + API
make down             # 停止所有服务
make logs             # 查看日志

# 数据库
make db-shell         # 进入 PostgreSQL Shell
make db-backup        # 备份数据库
```

### 提交前检查

```bash
# 推荐使用 CI 脚本
./scripts/run_checks.sh

# 或手动执行
ruff check src/ tests/ --fix
pytest tests/ml/test_backtest_engine.py tests/ops/test_signal_generator.py -v
```

---

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 贡献

欢迎提交 Issue 和 Pull Request！提交前请确保通过 `./scripts/run_checks.sh` 检查。

---

**项目状态**: Production Ready | **基准准确率**: 65.52% | **数据泄露**: None | **架构**: Cloud-Native
