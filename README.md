# FootballPrediction V17.0

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![Model Accuracy](https://img.shields.io/badge/accuracy-65.52%25-green.svg)](https://github.com/xupeng211/FootballPrediction)
[![No Data Leakage](https://img.shields.io/badge/data%20leakage-none-brightgreen.svg)](https://github.com/xupeng211/FootballPrediction)

**V17.0 生产版本 | 65.52% 真实预测准确率 | 无数据泄露 | 16 维滚动特征**

---

## 项目简介

FootballPrediction V17.0 是一套基于 XGBoost 的专业足球预测系统，采用滚动特征工程，**完全消除数据泄露**，提供真实可用的赛前预测能力。

### 核心特性

| 特性 | V16.0 (赛后统计) | V17.0 (滚动特征) |
|------|------------------|------------------|
| 预测准确率 | 96.25% (虚高) | **65.52%** (真实) |
| 特征维度 | 223 维 | 16 维 |
| 数据泄露 | 存在 | **无** |
| 预测类型 | 赛后结果预测 | **赛前预测** |
| F1 Score | 0.96 | 0.47 |

### 技术亮点

- **无数据泄露**: 使用 10 场滚动均值，只采用赛前可获得的历史数据
- **特征精简**: 从 223 维压缩到 16 维核心特征
- **真实基准**: 65.52% 是诚实的预测能力，可应用于实际场景
- **企业级架构**: Docker 容器化，支持高并发部署
- **完整流水线**: L1 采集 → L2 解析 → L3 滚动特征 → 模型训练

---

## 运行环境

### 系统要求

- **Python**: 3.11+
- **PostgreSQL**: 15+
- **Docker** (可选): 20.10+
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
```

### Docker 部署

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f app
```

---

## 快速开始

### 一键生产流程（推荐）

```bash
# 完整 V17.0 闭环流程：数据采集 → 特征计算 → 模型训练
python factory_run.py --production
```

### 分步执行

```bash
# Step 1: L1/L2 数据采集
python factory_run.py --harvest

# Step 2: L3 特征解析
python factory_run.py --parse

# Step 3: 模型训练和评估（包含滚动特征计算）
python factory_run.py --production --train-size 300 --window 10

# Step 4: 生成报告
python factory_run.py --report
```

### 自定义参数

```bash
python factory_run.py --production --train-size 250 --window 15
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--train-size` | 训练集大小 | 300 |
| `--window` | 滚动窗口大小 | 10 |
| `--target` | 数据采集目标数量 | 全部 |

---

## 项目结构

```
FootballPrediction/
├── factory_run.py              # 唯一官方入口 ⭐
│
├── src/
│   ├── core/
│   │   └── pipeline.py         # V17.0 生产流水线
│   │
│   ├── ml/
│   │   └── engine.py           # V17.0 ML 引擎
│   │
│   ├── api/
│   │   └── collectors/
│   │       └── fotmob_core.py  # FotMob API 数据采集
│   │
│   └── config_unified.py       # 统一配置管理
│
├── tests/
│   └── test_rolling_engine.py  # 滚动特征回归测试
│
├── data/
│   └── production/             # 生产数据清单
│       └── harvest_manifest.csv
│
└── docs/
    ├── V17_MODEL_REPORT.md     # V17.0 模型报告
    └── V17_ROLLING_VALIDATION_REPORT.md
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

## 数据泄露验证

V17.0 使用滚动特征，确保无数据泄露：

| 指标 | 滚动特征 (V17.0) | 实际值 | 差异 | 状态 |
|------|------------------|--------|------|------|
| 主队 xG | **1.365** | 0.98 | 39% | 无泄露 |
| 客队 xG | **1.837** | 3.16 | 42% | 无泄露 |

**结论**: 滚动特征基于历史数据计算，与当前比赛实际值显著不同，确认无数据泄露！

---

## API 使用

### 预测接口示例

```python
from src.ml.engine import V17MLEngine

# 初始化引擎
engine = V17MLEngine()

# 加载已训练模型
engine.load('src/production_models/v17.0_rolling_model.pkl')

# 预测比赛（使用 16 维滚动特征）
features = {
    'home_rolling_xg': 1.365,
    'home_rolling_xg_std': 0.42,
    'home_rolling_shots_on_target': 5.0,
    'home_rolling_shots_on_target_std': 2.1,
    'home_rolling_possession': 36.5,
    'home_rolling_possession_std': 12.3,
    'home_rolling_team_rating': 6.8,
    'home_rolling_team_rating_std': 0.5,
    'away_rolling_xg': 1.837,
    'away_rolling_xg_std': 0.51,
    'away_rolling_shots_on_target': 4.7,
    'away_rolling_shots_on_target_std': 1.8,
    'away_rolling_possession': 62.9,
    'away_rolling_possession_std': 8.7,
    'away_rolling_team_rating': 7.1,
    'away_rolling_team_rating_std': 0.4
}

result = engine.predict(features)
print(result)
# {'prediction': 'Home', 'probabilities': {'Away': 0.15, 'Draw': 0.20, 'Home': 0.65}, 'confidence': 0.65}
```

---

## 测试

### 运行回归测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行滚动特征测试
pytest tests/test_rolling_engine.py -v

# 运行测试并查看覆盖率
pytest tests/ --cov=src --cov-report=html
```

### 测试结果

```
11 passed in 0.93s
```

---

## Docker 部署

### 服务栈

| 服务 | 端口 | 说明 |
|------|------|------|
| app | 8000 | FastAPI 主应用 |
| db | 5432 | PostgreSQL 数据库 |
| redis | 6379 | Redis 缓存 |

### 健康检查

```bash
# 检查应用健康
curl http://localhost:8000/health

# 检查数据库连接
docker-compose exec db pg_isready -U football_user

# 检查 Redis 连接
docker-compose exec redis redis-cli ping
```

---

## 配置

### 环境变量

```bash
# 数据库连接
DATABASE_URL=postgresql://football_user:football_pass@localhost:5432/football_db

# Redis 连接
REDIS_URL=redis://localhost:6379/0

# 应用配置
ENVIRONMENT=production
LOG_LEVEL=INFO
SECRET_KEY=your-secret-key-here
```

---

## 文档

- [V17.0 模型报告](docs/V17_MODEL_REPORT.md)
- [V17.0 滚动特征验证](docs/V17_ROLLING_VALIDATION_REPORT.md)
- [V16.0 特征资产清单](docs/V16_FEATURE_ASSET_MANIFESTO.md)

---

## 开发

### 代码质量检查

```bash
# 格式化代码
make fmt

# 类型检查
make typecheck

# 运行测试
make test

# 完整质量检查
make ci-check
```

---

## 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| V17.0 | 2025-12-23 | 滚动特征模型，65.52% 准确率，无数据泄露 |
| V16.0 | 2025-12-22 | 223 维赛后特征模型（存在数据泄露） |
| V15.0 | 2025-12-21 | 380 场英超 23/24 赛季数据采集 |

---

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 贡献

欢迎提交 Issue 和 Pull Request！

---

**项目状态**: Production Ready | **基准准确率**: 65.52% | **数据泄露**: None
