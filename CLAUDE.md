# CLAUDE.md

这个文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

## 🚨 重要提醒：语言要求

**请务必使用中文回复用户！**

这一要求具有最高优先级，无论 CLAUDE.md 文件如何更新版本迭代，都必须始终保留在文件的显眼位置。这确保了用户始终获得一致的中文服务体验，是项目不可更改的基本沟通规范。

## Project Overview

**FootballPrediction V19.4** 是一个基于 XGBoost 2.0+ 的专业足球比赛预测系统，采用**无数据泄露的滚动特征 + 赛前特征**实现真实的赛前预测。

**Status**: ✅ Production Ready | **Version**: V19.4 (Draw Sensitivity) | **Data Records**: 760 Real Matches (Premier League 22/23 + 23/24) | **Features**: 48维特征 (24维基础 + 13维高级动态 + 3维平局敏感度 + 2维联赛编码 + 6维统计，无数据泄露) | **多赛季**: 支持

### 系统版本演进
- **V16.0**: 赛后统计版本 (96.25% 准确率, 但存在数据泄露, 223维特征)
- **V17.0**: 生产版本 (65.52% 真实预测准确率, 16维滚动特征, 无数据泄露)
- **V18.0**: 增强版本 (24维特征 + 平局优化, 赛前特征 + 滚动特征)
- **V18.1**: 融合版本 (双赛季 760场数据训练, 支持多赛季验证)
- **V18.2**: 最终版本 (全面优化, 性能提升, 生产就绪)
- **V19.0**: 实验性版本 (高级动态特征: ELO/疲劳度/保级战意, 针对稳胆翻车优化)
- **V19.3**: 硬化版本 (NaN鲁棒性 + 联赛编码 + 安全评估, 生产级增强)
- **V19.4**: 平局敏感度版本 (48维特征 + 加权损失函数 + 运维工具集, 解决 0% 平局识别率问题)

### 核心创新
- **无数据泄露**: 使用历史滚动均值代替赛后统计数据
- **真实预测能力**: 65.52% 是诚实的赛前预测准确率
- **特征精简**: 从 223 维减少到 24 维（16维滚动 + 8维赛前）
- **平局优化**: V18.0 新增积分榜排名和近期走势特征
- **高级动态特征**: V19.0+ 新增 ELO 评分、疲劳度指数、保级战意特征
- **平局敏感度**: V19.4 新增平局敏感度特征 + 加权损失函数，解决 0% 平局识别率问题
- **运维工具集**: V19.4 新增实时市场监控、风险监控、每日工作流、周度 PNL 报告

---

## 🎯 系统概览

### 核心特性
- **无数据泄露**: 基于历史滚动均值的赛前特征，避免使用赛后统计数据
- **65.52% 真实预测准确率**: 诚实的赛前预测基准（29场测试集验证）
- **48维特征 (V19.4)**: 16维滚动特征 + 8维赛前特征 + 13维高级动态特征 + 3维平局敏感度 + 2维联赛编码 + 6维额外统计
- **多赛季数据**: 英超 22/23 + 23/24 赛季 760 场完整数据（V18.1+ 双赛季融合）
- **企业级架构**: Docker 容器化 + FastAPI + PostgreSQL + Redis
- **V11.0 哨兵机制**: API 调用稳定性保护（联赛分级动态哨兵 + 自适应解码 + 熔断机制）
- **生产级鲁棒性**: V19.3 硬化版本，NaN 值处理 + 联赛编码支持 + 安全评估
- **运维工具集 (V19.4)**: 实时市场监控、风险监控、每日工作流、周度 PNL 报告

### 技术栈
- **ML Framework**: XGBoost 2.0+ (梯度提升算法)
- **Backend**: Python 3.11+, FastAPI, PostgreSQL 15, Redis 7
- **DevOps**: Docker, Docker Compose
- **Code Quality**: Black, Flake8, isort, MyPy, Bandit, pytest (40% 覆盖率目标)
- **Monitoring**: Prometheus, Grafana, Structured Logging

---

## 🚀 快速参考（最常用命令）

### 日常开发 Top 6
```bash
make dev                              # 快速开发环境（venv + install + env-check）
python factory_run.py --v18           # V18.0 完整流程（24维特征，推荐）
python main_production.py --full-pipeline  # V19.4 统一生产流程（推荐）
make quality                          # 代码质量检查（format + lint + typecheck + security）
docker-compose up -d                  # 启动 Docker 服务栈
pytest tests/unit/utils tests/unit/cache tests/unit/core -v  # Smart Tests 快速验证（<2分钟）
```

### 快速命令速查表
| 操作 | 命令 | 耗时 |
|------|------|------|
| **环境准备** | `make dev` | ~2 分钟 |
| **V18.0 流程** | `python factory_run.py --v18` | ~10 分钟 |
| **V19.4 流程** | `python main_production.py --full-pipeline` | ~15 分钟 |
| **质量检查** | `make quality` | ~1 分钟 |
| **快速测试** | `pytest tests/unit/utils tests/unit/cache tests/unit/core -v` | ~2 分钟 |
| **系统验证** | `./system_verify.sh` | ~30 秒 |
| **Docker 部署** | `docker-compose up -d` | ~1 分钟 |
| **数据质量报告** | `make db-quality-report` | ~30 秒 |

### 常见场景一键命令
```bash
# 场景 1: 新机器环境设置
make dev && ./system_verify.sh

# 场景 2: 代码修改后提交前检查
make quality && make test

# 场景 3: 收割英超赛季数据
python factory_run.py --harvest --season 2324

# 场景 4: V19.4 完整流水线（L1 + L2 + 训练 + 预测）
python main_production.py --full-pipeline

# 场景 5: Docker 环境一键启动验证
docker-compose up -d && docker-compose exec db pg_isready -U football_user

# 场景 6: 查看数据库状态
make db-stats

# 场景 7: 系统健康检查
python main_production.py health-check

# 场景 8: 实时市场巡检（V19.4 新功能）
python main_production.py monitor --match-id 4813551 --match-time "2025-12-26 12:30"
```

---

## 🎯 Skills 集成说明

项目配置了多个专业化技能，当任务匹配以下场景时，应使用对应的 Skill 工具：

| Skill 名称 | 使用场景 | 触发条件 |
|-----------|---------|---------|
| `code-quality` | 运行代码质量检查、格式化、类型检查 | 用户要求检查代码质量、运行 make quality、准备提交代码 |
| `data-collection` | 收集足球数据、更新预测数据集 | 用户需要采集比赛数据、更新数据库、收集历史统计 |
| `data-engineering` | 设计/优化数据流水线、ETL 处理 | 用户提到数据管道、ETL、数据转换优化 |
| `database-operations` | 数据库迁移、查询优化、连接管理 | 用户需要数据库操作、性能优化、备份恢复 |
| `deployment-management` | Docker 部署、服务管理 | 用户需要部署应用、管理 Docker 容器 |
| `deployment-operations` | 容器化部署自动化、健康监控、故障诊断 | 用户需要一键部署、容器健康检查 |
| `docker-devops` | 创建 Dockerfile、docker-compose 配置 | 用户需要容器化应用、配置 CI/CD |
| `fastapi-development` | 创建/优化 FastAPI 端点、异步处理 | 用户需要创建 API、优化响应时间 |
| `football-prediction` | 足球比赛预测、分析模型性能 | 用户需要预测比赛结果、查看准确率 |
| `machine-learning-engineering` | 优化 ML 模型、特征工程、超参调优 | 用户需要改进模型、调参、特征分析 |
| `performance-monitoring` | 系统监控、性能分析、指标收集 | 用户需要查看系统状态、性能报告 |
| `report-generation` | 生成分析报告（PDF/Excel） | 用户需要生成预测报告、数据可视化 |

**重要**: 使用 Skill 工具时，必须在任何其他响应之前立即调用 `Skill` 工具。

---

## 🚀 Primary Entry Points (主要入口点)

### 1. V19.4 统一生产入口（推荐，最新）
```bash
# V19.4 完整流程（48维特征 + 平局敏感度 + 加权损失）
python main_production.py --full-pipeline

# 分步执行
python main_production.py l1-harvest --season 2324 --target 10  # L1数据采集
python main_production.py l2-parse                             # L2特征解析
python main_production.py train --train-size 600 --test-size 160  # V19.4模型训练
python main_production.py predict --model v19.4               # V19.4模型预测
python main_production.py monitor --match-id 4813551 --match-time "2025-12-26 12:30"  # 实时市场巡检
python main_production.py risk-status                          # 风控状态检查
python main_production.py health-check                         # 系统健康检查
```

### 2. V18.0/V18.1/V18.2 增强版流水线（官方入口）
```bash
# V18.0 单赛季完整流程（23/24赛季，24维特征 + 平局优化）
python factory_run.py --v18

# V18.1/V18.2 双赛季融合训练（22/23 + 23/24，760场数据）
python factory_run.py --v18-multi

# V19.0/V19.3 实验性高级特征流水线（39维特征，含 ELO/疲劳/战意）
python src/core/pipeline_v19.py

# V19.4 平局敏感度流水线（48维特征，Draw Sensitivity + Weighted Loss）
python src/core/pipeline_v19_4.py

# V17.0 基线版本（16维滚动特征）
python factory_run.py --production --train-size 300 --window 10

# 分步执行
python factory_run.py --harvest           # L1/L2 数据采集（FotMob API）
python factory_run.py --parse             # L3 特征解析入库
python factory_run.py --report            # 生成报告
```

### 2. FastAPI 服务
```bash
# 启动 FastAPI 服务器
python src/main.py
# 或使用项目脚本
football-server
# Docker 模式
docker-compose up -d
```

### 3. 系统验证脚本
```bash
# 系统健康验证（关键验证）
./system_verify.sh
```

### 4. 开发工作流
```bash
# 快速开发环境设置
make dev
# 代码质量检查
make quality
# 运行测试
make test
# 提交前检查
make prepush
```

### 5. Docker 自动化部署
```bash
# 完整 Docker 栈部署
docker-compose up -d
# 容器健康检查
docker-compose exec db pg_isready -U football_user
docker-compose exec redis redis-cli ping
```

**❌ 禁止操作**:
- 绕过 `factory_run.py` 或 `main_production.py` 直接调用底层流水线（破坏标准化流程）
- 未经业务逻辑直接操作数据库
- 使用非官方脚本进行数据操作
- 硬编码数据库连接参数（必须使用 config_unified.py）

---

## 🏗️ 系统架构

### V18.0/V18.1/V18.2 增强版流水线架构
```
┌─────────────────────────────────────────────────────────────────┐
│                  V18.0/V18.1/V18.2 增强版流水线架构              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ Phase 1  │ -> │ Phase 2  │ -> │ Phase 3  │ -> │ Phase 4  │  │
│  │ L1 数据  │    │ L2 解析  │    │ L3 特征  │    │ 模型训练  │  │
│  │ 采集     │    │ 入库     │    │ 计算+赛前│    │ 评估     │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│                                          ↓                        │
│                                  24维特征 (16滚动+8赛前)          │
│                           (V18.2 支持双赛季融合训练)            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 核心组件
1. **V19.4 统一生产入口** (`main_production.py`): V19.4 唯一统一入口，支持 L1/L2/训练/预测/监控
2. **V17.0/V18.0/V18.1/V18.2 生产流水线** (`factory_run.py`): V17-V18 官方入口，协调完整流程
3. **V17ProductionPipeline** (`src/core/pipeline.py`): L3滚动特征计算 + 模型训练
4. **V18ProductionPipeline** (`src/core/pipeline_v18.py`): 24维特征 + 平局优化 + 多赛季支持
5. **V19ProductionPipeline** (`src/core/pipeline_v19.py`): 39维高级特征 + ELO/疲劳/战意 + 概率校准
6. **V19_4TrainingPipeline** (`src/core/pipeline_v19_4.py`): 48维特征 + 平局敏感度 + 加权损失函数（解决0%平局识别率问题）
7. **V17 ML 引擎** (`src/ml/engine.py`): XGBoost 模型训练和预测
8. **FotMob 数据采集** (`src/api/collectors/fotmob_core.py`): V11.0 哨兵机制 API 采集
9. **特征锻造器** (`src/ml/features/industrial_feature_forge.py`): 工业级特征提取
10. **赛前特征提取器** (`src/ml/features/prematch_features.py`): 积分榜和近期走势特征
11. **V19 高级特征提取器** (`src/ml/features/v19_advanced_features.py`): ELO/疲劳度/保级战意特征
12. **V19.4 平局敏感度提取器** (`src/ml/features/draw_sensitivity_features.py`): table_proximity, low_scoring_tendency, elo_diff_cluster
13. **积分榜计算器** (`src/ml/features/standings_calculator.py`): 动态积分榜计算
14. **V19 概率校准器** (`src/ml/v19_probability_calibrator.py`): Isotonic 回归校准
15. **统一配置** (`src/config_unified.py`): Pydantic Settings 配置管理，支持 Docker 环境自动注入
16. **Database**: PostgreSQL 存储英超 22/23 + 23/24 赛季 760+ 场比赛数据
17. **运维工具集** (`src/ops/`): 生产级运维工具
    - `market_live_monitor.py`: 实时市场监控
    - `risk_monitor.py`: 风险监控
    - `daily_workflow.py`: 每日工作流
    - `weekly_pnl_statement.py`: 周度 PNL 报告
    - `market_price_verifier.py`: 市场价格验证
    - `v19_4_production_prediction.py`: V19.4 生产预测

### 数据流架构
```
FotMob API → V11.0 动态联赛分级哨兵检查 → 自适应解码 → PostgreSQL 存储
                                                   ↓
              历史比赛数据 ← 滚动特征计算 + 赛前特征提取 ← L3 特征提取器
                                                   ↓
                    XGBoost 训练 ← 24维/39维/48维特征数据集
                                      V18: 16滚动+8赛前
                                      V19: +13高级动态+2联赛编码
                                      V19.4: +3平局敏感度+加权损失
                                                   ↓
                    概率校准 ← Isotonic 回归 (V19+)
                                                   ↓
                    模型评估 → 保存为生产模型 (.pkl)
```

### V18.0 完整特征列表（24维 - 无数据泄露）

#### V17.0 滚动特征（16维）
```
主队特征（8个）:
- home_rolling_xg, home_rolling_xg_std
- home_rolling_shots_on_target, home_rolling_shots_on_target_std
- home_rolling_possession, home_rolling_possession_std
- home_rolling_team_rating, home_rolling_team_rating_std

客队特征（8个）:
- away_rolling_xg, away_rolling_xg_std
- away_rolling_shots_on_target, away_rolling_shots_on_target_std
- away_rolling_possession, away_rolling_possession_std
- away_rolling_team_rating, away_rolling_team_rating_std
```

#### V18.0/V18.1/V18.2 新增赛前特征（8维）
```
积分榜排名特征（4个）:
- home_table_position        # 主队积分榜排名
- away_table_position        # 客队积分榜排名
- table_position_diff        # 排名差异（主-客）

积分特征（3个）:
- home_points                # 主队积分
- away_points                # 客队积分
- points_diff                # 积分差异（主-客）

近期走势特征（2个）:
- home_recent_form_points    # 主队近期得分（最近5场）
- away_recent_form_points    # 客队近期得分（最近5场）
```

#### V19.0 高级动态特征（实验性）
```
三大核心特征（针对"稳胆翻车"问题优化，共13维新特征）:

1. ELO 相对差距特征:
   - raw_elo_gap: 原始 ELO 差距（含主场优势）
   - adjusted_elo_gap: 调整后 ELO 差距（考虑疲劳和赛程密度）
   - fatigue_impact: 疲劳对 ELO 的影响
   - schedule_impact: 赛程密度对 ELO 的影响

2. 疲劳度指数特征:
   - home_fatigue_index: 主队疲劳度 (0-1)
   - away_fatigue_index: 客队疲劳度 (0-1)
   - fatigue_diff: 疲劳度差异
   - home_rest_days: 主队休息天数
   - away_rest_days: 客队休息天数
   - 考虑因素：过去7天比赛负担、欧战强度、旅行距离、连续作战

3. 保级战意特征:
   - home_relegation_incentive: 主队保级战意指数 (0-1)
   - away_relegation_incentive: 客队保级战意指数 (0-1)
   - incentive_diff: 战意差异
   - home_desperation: 主队绝望程度 (0-1)
   - 考虑因素：距离降级区分差、剩余轮次、对手是否无欲无求
```

#### V19.4 平局敏感度特征（实验性）
```
针对 V19.3 审计中发现的 0% 平局识别率问题，新增 3 个平局敏感度特征:

1. 积分榜接近度特征 (table_proximity):
   - 计算主客队积分榜位置的接近程度
   - 值越小表示两队实力越接近，平局概率越高

2. 低得分倾向特征 (low_scoring_tendency):
   - 基于 xG (Expected Goals) 计算得分倾向
   - 低 xG 差距 + 低射正数 → 高平局概率

3. ELO 差距聚类 (elo_diff_cluster):
   - 将 ELO 差距分桶 (0-5, 5-15, 15-25, 25+)
   - 中等差距区间 (5-15) 历史上平局率最高

4. 加权损失函数 (Weighted Loss):
   - draw_class_weight = 3.0 (平局类别权重)
   - 通过样本权重提升模型对平局的关注度
```

---

## 📊 数据库连接标准

### 统一连接方法 (必须使用)
```python
# 使用统一配置系统
from src.config_unified import get_settings
settings = get_settings()
db = settings.database

# 标准连接，必须使用 RealDictCursor
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

### 安全要求
- ✅ 必须使用 `config_unified.py` 获取连接参数
- ✅ 必须使用连接池或异步连接
- ✅ 必须实现异常处理和资源清理
- ❌ 绝不硬编码连接参数
- ❌ 绝不使用基础游标 - 必须使用 `RealDictCursor`

---

## 🧬 特征工程体系 (V17.0 16维滚动特征)

### V16.0 vs V17.0 特征对比

| 维度 | V16.0 赛后统计特征 | V17.0 滚动特征 |
|------|---------------------|----------------|
| **数据类型** | 赛后统计数据 | 历史滚动均值 |
| **时间序列** | 无时序保证 | 严格按时间序 |
| **特征数量** | 223 维 | 16 维 |
| **数据泄露** | 存在 | 无 |
| **预测类型** | 赛后结果预测 | 赛前结果预测 |

### V17.0 滚动特征规格

| 特征名 | 说明 | 示例值 | 重要性 |
|--------|------|--------|--------|
| `home_rolling_xg` | 主队过去10场平均xG | 1.365 | 0.0906 (最高) |
| `home_rolling_xg_std` | 主队过去10场xG标准差 | 0.42 | 0.0657 |
| `home_rolling_shots_on_target` | 主队过去10场平均射正 | 5.00 | 0.0858 |
| `home_rolling_shots_on_target_std` | 主队过去10场射正标准差 | 2.1 | - |
| `home_rolling_possession` | 主队过去10场平均控球率 | 36.5% | 0.0640 |
| `home_rolling_possession_std` | 主队过去10场控球率标准差 | 12.3% | - |
| `home_rolling_team_rating` | 主队过去10场平均评分 | 6.8 | - |
| `home_rolling_team_rating_std` | 主队过去10场评分标准差 | 0.5 | - |
| *(客队同上8个)* | | | |

### 核心 API 提取路径映射（L1/L2 数据采集）

#### xG (Expected Goals) 特征
```
FotMob API路径: content.stats.Periods.All.stats[0].stats[].key = "expected_goals"
├── 主队xG: stats[0]
├── 客队xG: stats[1]
└── 备用路径: shotmap.shots[].expectedGoals
```

#### 控球率特征
```
FotMob API路径: content.stats.Periods.All.stats[0].stats[].key = "BallPossesion"
├── 主队控球率: stats[0]
├── 客队控球率: stats[1]
└── 备用路径: general.teamStats[].possession
```

#### 其他特征
- **角球**: `content.stats.Periods.All.stats[0].stats[].key = "Corners"`
- **红黄牌**: `content.stats.Periods.All.stats[0].stats[].key = "YellowCards"`
- **射正**: `content.stats.Periods.All.stats[0].stats[].key = "ShotsOnTarget"`

### V11.0 哨兵机制特性
- **联赛分级动态哨兵**: 根据联赛质量等级设置不同的响应长度阈值
  - **Tier 1 Premium** (五大联赛 + 欧冠): 100KB 阈值
  - **Tier 2 Standard** (英冠、葡超、荷甲等): 50KB 阈值
  - **Tier 3 Basic** (意乙、德乙、苏冠等): 20KB 阈值
  - **Default Tier** (未分类联赛): 20KB 阈值
- **自适应解码**: 智能 Gzip/Brotli/JSON 解码
- **故障熔断**: 连续失败 5 次触发 30 分钟休眠
- **断点续传**: 仅采集缺失数据，避免 API 浪费
- **空心场次日志**: `data/logs/hollow_matches.log` 记录被哨兵拒绝的比赛

---

## 🛡️ 代码质量规范

### 修改前验证 (强制要求)
```bash
# 任何代码修改后，必须运行以下验证命令
./system_verify.sh
make test
make quality
```

**验证要求**:
- ✅ 系统验证脚本通过: `./system_verify.sh`
- ✅ 数据库连接测试: Success
- ✅ 配置测试: 所有项目正确加载
- ✅ 模型测试: 预测引擎成功加载
- ✅ API 测试: 外部 API 正常连接
- ✅ 单元测试通过: `make test`
- ✅ 代码质量检查通过: `make quality`
- ❌ 任何失败 = 禁止代码合并

### 代码标准
- **Python Version**: 3.11+ (在 pyproject.toml 中指定)
- **Style**: Black (格式化) + Flake8 (代码检查), line-length: 120
  - 格式化: `python -m black src/ tests/`
  - 检查: `python -m flake8 src/ tests/ --max-line-length=120`
- **Import Sorting**: isort (配置为 black 兼容模式)
- **Type Checking**: MyPy 严格配置和覆盖配置
- **Security**: Bandit 扫描
- **Testing**: pytest，目标覆盖率 40%
- **Logging**: INFO (生产), DEBUG (开发) 使用 structlog
- **Error Handling**: 强制 try-catch 和适当的日志记录
- **Documentation**: 所有公共方法必须有 docstring

---

## 📋 开发工作流命令

### 使用 Makefile (推荐)
```bash
# 环境管理
make venv       # 创建虚拟环境
make install    # 安装项目依赖
make dev        # 快速开发环境（venv + install + env-check）
make clean      # 清理环境和缓存
make env-check  # 环境检查

# 代码质量
make format     # 代码格式化
make lint       # 代码风格检查
make typecheck  # 类型检查（MyPy）
make security   # 安全扫描（Bandit）
make quality    # 完整质量检查 (format + lint + typecheck + security)

# 测试
make test       # 运行单元测试
make coverage   # 覆盖率测试
make test-coverage-no-fail  # 运行覆盖率测试（不因覆盖率过低而失败）

# 提交前检查
make prepush    # 完整提交前清单 (quality + test)

# 生产部署
make up         # 启动 Docker 服务
make down       # 停止 Docker 服务
make predict    # 运行预测
make verify     # 系统验证（运行 system_verify.sh）

# 项目监控
make status     # 项目状态概览

# 数据库管理
make db-reset   # 重置数据库（清空数据）
make db-drop    # 删除并重建数据库
make db-stats   # 显示数据库统计信息
make db-quality-report  # 显示数据质量报告

# 赛季收割
make harvest-season     # 一键收割英超整个赛季数据（380场）
make harvest-watch      # 实时监控收割进度
make season-full-reset  # 一键重置并收割整个赛季
```

### 运行单个测试
```bash
# 运行单个测试文件
pytest tests/unit/test_specific.py -v

# 运行特定测试函数
pytest tests/unit/test_engine.py::test_prediction -v

# 运行带关键字匹配的测试
pytest tests/ -k "test_inference" -v

# 快速调试单个测试
pytest tests/unit/test_specific.py -v -s --tb=short

# 按标记运行测试
pytest -m "unit and api" -v          # 单元+API测试
pytest -m "not slow"                 # 排除慢速测试
pytest -m "critical" --maxfail=5     # 关键功能测试
```

### Smart Tests 快速验证
```bash
# Smart Tests - 核心稳定测试模块（<2分钟）
pytest tests/unit/utils tests/unit/cache tests/unit/core -v

# 更具体的测试模块路径：
# - tests/unit/test_config_comprehensive.py     # 配置系统测试
# - tests/unit/test_health_real_api.py          # API健康检查
# - tests/unit/test_database_connection_realistic.py  # 数据库连接测试
# - tests/unit/test_core_business_logic.py      # 核心业务逻辑
# - tests/unit/test_ml_inference_comprehensive.py  # ML推理测试
```

### 代码目录结构（关键模块）
```
src/
├── core/
│   ├── pipeline.py             # V17.0 生产流水线（L3滚动特征 + 模型训练）
│   ├── pipeline_v18.py         # V18.0 增强版流水线（24维特征 + 平局优化）
│   ├── pipeline_v18_2.py       # V18.2 最终版流水线（全面优化）
│   ├── pipeline_v19.py         # V19.0 实验性流水线（高级特征）
│   ├── pipeline_v19_3_hardened.py  # V19.3 硬化版本流水线
│   ├── pipeline_v19_4.py       # V19.4 平局敏感度流水线（48维特征）
│   ├── main_engine_v5.py       # 主入口，数据收割和预测
│   ├── inference_engine.py     # XGBoost 推理核心
│   └── league_harvester.py     # 联赛数据收集
├── ml/
│   ├── engine.py               # V17.0 ML 引擎
│   ├── rolling_feature_engine.py  # 滚动特征引擎
│   ├── standard_trainer.py     # 标准训练器
│   ├── probability_calibrator.py  # 概率校准
│   ├── v18_1_optuna_optimizer.py  # V18.1 Optuna超参优化器
│   ├── v19_probability_calibrator.py  # V19.0 概率校准器
│   ├── features/
│   │   ├── industrial_feature_forge.py  # 工业级特征锻造器
│   │   ├── prematch_features.py  # 赛前特征提取器（V18.0）
│   │   ├── l3_pre_match_extractor.py  # L3赛前特征提取
│   │   ├── standings_calculator.py  # 积分榜计算器
│   │   ├── v19_advanced_features.py  # V19.0高级特征（ELO/疲劳/保级战意）
│   │   ├── draw_sensitivity_features.py  # V19.4平局敏感度特征
│   │   ├── elo_rating_system.py  # ELO评分系统
│   │   ├── h2h_calculator.py    # 交锋历史计算
│   │   └── venue_analyzer.py    # 场馆分析器
│   └── models/                 # 模型定义
├── api/
│   ├── health.py               # 健康检查端点
│   ├── monitoring.py           # 监控指标暴露
│   ├── model_management.py     # 模型管理API
│   ├── schemas.py              # API数据模式
│   ├── fotmob_client.py        # FotMob API客户端
│   ├── collectors/
│   │   ├── fotmob_core.py      # V11.0 哨兵机制数据采集器
│   │   ├── fotmob_web_scraper.py  # FotMob 网页抓取器
│   │   ├── premier_league_l1_harvester.py  # 英超L1采集
│   │   ├── season_discoverer.py    # 赛季发现器
│   │   ├── season_manifest_generator.py  # 赛季清单生成器
│   │   ├── epl_discoverer_2223.py    # 英超22/23赛季发现器
│   │   ├── epl_finder_2223.py        # 英超22/23赛季查找器
│   │   └── epl_manifest_2223_official.py  # 英超22/23赛季清单
│   ├── predictions/            # 预测 API 路由
│   │   └── predict_router.py
│   └── v1/                     # API v1版本
│       └── endpoints/
│           └── admin.py        # 管理端点
├── services/
│   ├── inference_service.py    # 推理服务（依赖注入）
│   ├── prediction_service.py   # 预测服务
│   ├── core_inference.py       # 核心推理
│   ├── collection_service.py   # 数据采集服务
│   ├── high_performance_inference.py  # 高性能推理
│   ├── explainability_service.py  # 可解释性服务
│   └── mlops/
│       └── retraining_service.py  # 模型重训练服务
├── database/
│   ├── connection.py           # 数据库连接管理（异步）
│   ├── connection_factory.py   # 连接工厂
│   ├── config.py               # 数据库配置
│   ├── db_pool.py              # 数据库连接池
│   ├── enhanced_connection.py  # 增强连接
│   ├── models.py               # SQLAlchemy模型
│   ├── schema_manager.py       # Schema管理
│   └── migrations/             # 数据库迁移
├── strategy/                   # 投注策略
│   ├── kelly_criterion.py      # 凯利公式
│   ├── tuner.py                # 策略调优
│   └── execution_threshold_filter.py  # 执行阈值过滤
├── ops/                        # V19.4 运维工具集
│   ├── market_live_monitor.py  # 实时市场监控
│   ├── risk_monitor.py         # 风险监控
│   ├── daily_workflow.py       # 每日工作流
│   ├── weekly_pnl_statement.py # 周度 PNL 报告
│   ├── market_price_verifier.py # 市场价格验证
│   └── v19_4_production_prediction.py  # V19.4 生产预测
├── analysis/                   # 分析工具（V18.2+ 新增）
│   ├── true_roi_audit.py       # 真实赔率ROI审计（扣除5%庄家抽水）
│   ├── strict_oos_backtest.py  # 严格样本外回测
│   ├── yield_audit_v19_4.py    # V19.4 收益率审计
│   └── v19_diagnostic.py       # V19.0诊断工具
├── scripts/                    # 脚本工具
│   ├── download_real_odds.py   # 下载真实赔率数据
│   └── deep_harvest_v19.py     # V19 深度数据采集
├── utils/                      # 工具函数
│   └── safe_eval.py            # 安全表达式求值
├── config_unified.py           # 统一配置入口 (Pydantic Settings)
└── main.py                     # FastAPI 应用主入口

# 根目录关键文件
main_production.py              # V19.4 统一生产入口（推荐）
factory_run.py                  # V17.0/V18.0 唯一官方入口
system_verify.sh                # 系统健康验证脚本
Makefile                        # 项目管理命令
pyproject.toml                  # 现代Python项目配置

# 生产模型
src/production_models/
├── v17.0_rolling_model.pkl               # V17.0模型 (16维滚动特征)
├── v17.0_rolling_metadata.json           # V17.0元数据
├── v18.0_enhanced_model.pkl              # V18.0增强模型 (24维特征)
├── v18.0_enhanced_metadata.json          # V18.0元数据
├── v18.2_final_beast_model.pkl           # V18.2最终版本模型
├── v18.2_final_beast_metadata.json       # V18.2元数据
├── v19.0_reconstruction_model.pkl        # V19.0重构版本模型
├── v19.0_reconstruction_metadata.json    # V19.0元数据
├── v19.1_final_model.pkl                 # V19.1最终版本模型
├── v19.1_final_metadata.json             # V19.1元数据
├── v19.2_audit_report.json               # V19.2审计报告
├── v19.3_hardened_model.pkl              # V19.3硬化版本模型 (45维特征)
├── v19.3_hardened_metadata.json          # V19.3元数据
├── v19.4_draw_sensitivity_model.pkl      # V19.4平局敏感度模型 (48维特征)
└── v19.4_draw_sensitivity_metadata.json  # V19.4元数据
```

### 架构设计原则
- **微服务架构**: FastAPI + PostgreSQL + Redis + Docker
- **依赖注入**: Constructor Injection 模式，实现松耦合
- **异步处理**: 全面采用 async/await 模式
- **单例模式**: DatabaseManager, InferenceEngine 全局管理
- **工厂模式**: FeatureFactory, ModelFactory 动态创建
- **策略模式**: ProbabilityCalibration, ValueBettingStrategy 可插拔

### 现代 Python 项目管理 (pyproject.toml)
```bash
# 安装开发依赖
pip install -e .[dev]

# 安装所有可选依赖
pip install -e .[all]

# 项目脚本 (在 pyproject.toml 中定义)
football-predict    # 运行预测引擎
football-train      # 运行训练流水线
football-server     # 启动 FastAPI 服务器

# 开发工具配置
python -m black src/ tests/  # 代码格式化
python -m flake8 src/ tests/ --max-line-length=120  # 代码检查
pytest tests/                # 测试
mypy src/                    # 类型检查 (配置覆盖范围)
```

---

## 🚀 生产环境规格

### V17.0/V18.0/V18.1 性能指标
- **Response Time**: 单次预测 <100ms
- **Accuracy**: 65.52% 预测准确率（29 场测试集验证）
- **Data Integrity**: 709 场英超 22/23 + 23/24 赛季有效数据（V18.1 双赛季）
- **V17.0 Feature Dimensions**: 16 维滚动特征（无数据泄露）
- **V18.0/V18.1 Feature Dimensions**: 24 维特征（16维滚动 + 8维赛前）
- **Training Set**: 300 场比赛（单赛季）/ 600+ 场（双赛季 V18.1）
- **Test Set**: 29 场比赛
- **System Availability**: 99.9%+ 正常运行时间

### 版本对比
| 指标 | V16.0 | V17.0 | V18.0 | V18.1 | V18.2 | V19.0 | V19.3 | V19.4 | 说明 |
|------|-------|-------|-------|-------|-------|-------|-------|-------|------|
| **测试准确率** | 96.25% | **65.52%** | 待验证 | 待验证 | 待验证 | 实验性 | 生产级 | 实验性 | ✅ 真实预测能力 |
| **特征维度** | 223 维 | 16 维 | 24 维 | 24 维 | 24 维 | 39 维 | 45 维 | 48 维 | ✅ V19+ 高级特征 |
| **数据泄露** | 存在 | 无 | 无 | 无 | 无 | 无 | 无 | 无 | ✅ 合规预测 |
| **预测类型** | 赛后结果预测 | 赛前结果预测 | 赛前结果预测 | 赛前结果预测 | 赛前结果预测 | 赛前结果预测 | 赛前结果预测 | 赛前结果预测 | ✅ 真正预测 |
| **平局优化** | 无 | 无 | 有 | 有 | 有 | 有 | 有 | **加权损失** | ✅ V18.0+ 新增 |
| **高级特征** | 无 | 无 | 无 | 无 | 无 | ELO/疲劳/战意 | ELO/疲劳/战意 | **平局敏感度** | ✅ V19.0+ 新增 |
| **概率校准** | 无 | 无 | 无 | 无 | 无 | Isotonic | Isotonic | Isotonic | ✅ V19.0+ 新增 |
| **NaN鲁棒性** | 无 | 无 | 无 | 无 | 无 | 有限 | 完整 | 完整 | ✅ V19.3 增强 |
| **联赛编码** | 无 | 无 | 无 | 无 | 无 | 无 | One-Hot | One-Hot | ✅ V19.3 新增 |
| **训练数据** | 380场 | 329场 | 329场 | 709场 (双赛季) | 709场 | 开发中 | 760场 | 760场 | ✅ V18.1+ 融合训练 |

### 告警阈值
- 数据收集失败率 >5% → 立即告警
- 模型准确率下降 >2% → 立即告警
- 系统响应时间 >200ms → 立即告警
- API 哨兵触发 >10次/小时 → 立即告警
- 数据库连接失败 → 立即告警

---

## 🔧 开发和部署

### 环境变量配置清单

| 环境变量 | 是否必需 | 默认值 | 说明 |
|---------|---------|-------|------|
| **运行环境** |
| `ENVIRONMENT` | 否 | development | 运行环境：development/production/testing/staging |
| `DOCKER_ENV` | 否 | false | Docker 环境标识（设为 true 时自动使用容器服务名） |
| `LOG_LEVEL` | 否 | INFO | 日志级别：DEBUG/INFO/WARNING/ERROR/CRITICAL |
| **数据库配置** |
| `DB_HOST` | 否 | localhost | 数据库主机（Docker 环境自动使用 "db"） |
| `DB_PORT` | 否 | 5432 | 数据库端口 |
| `DB_NAME` | 否 | football_prediction | 数据库名称 |
| `DB_USER` | 否 | football_user | 数据库用户名 |
| `DB_PASSWORD` | **是** | - | 数据库密码（生产环境必须设置） |
| `DB_SSL_MODE` | 否 | false | 是否启用 SSL 连接 |
| **Redis 配置** |
| `REDIS_HOST` | 否 | localhost | Redis 主机（Docker 环境自动使用 "redis"） |
| `REDIS_PORT` | 否 | 6379 | Redis 端口 |
| `REDIS_DB` | 否 | 0 | Redis 数据库编号 |
| `REDIS_PASSWORD` | 否 | - | Redis 密码（可选） |
| **API 配置** |
| `FOTMOB_BASE_URL` | 否 | https://www.fotmob.com/api | FotMob API 基础 URL |
| `FOTMOB_X_MAS_HEADER` | 否 | - | FotMob API 自定义 Header（可选） |
| **安全配置** |
| `SECRET_KEY` | **是** | - | 应用密钥（生产环境必须至少 32 字符） |
| **监控配置** |
| `ENABLE_METRICS` | 否 | true | 是否启用 Prometheus 指标收集 |
| `METRICS_PORT` | 否 | 9090 | 指标暴露端口 |

### Docker 环境自动配置

当设置 `DOCKER_ENV=true` 时，系统会自动将以下主机名替换为容器服务名：

| 配置项 | 本地开发默认值 | Docker 环境自动值 |
|--------|--------------|-----------------|
| `DB_HOST` | localhost | **db** |
| `REDIS_HOST` | localhost | **redis** |

### 环境设置
```bash
# 生产环境
export ENVIRONMENT=production
export DOCKER_ENV=true
export LOG_LEVEL=INFO

# 开发环境
export ENVIRONMENT=development
export LOG_LEVEL=DEBUG
```

### Docker 部署
```bash
# 构建镜像
docker build -t footballprediction:v2.3.1 .

# 运行服务栈
docker-compose up -d

# 健康检查
docker-compose exec db pg_isready -U football_user
```

### 关键服务 (docker-compose.yml)
- **app**: FastAPI 主应用服务 (端口 8000)
- **db**: PostgreSQL 15 数据库服务 (端口 5432)
- **redis**: Redis 7 缓存服务 (端口 6379)

### 服务间通信
```yaml
# 服务依赖关系
app:
  depends_on: [db, redis]  # 应用依赖数据库和缓存
  environment:
    - DB_HOST=db           # 数据库服务名
    - REDIS_HOST=redis     # 缓存服务名
```

### 数据库架构
- **主表**: `matches` - 比赛基础信息 + L2数据
- **缓存表**: `l2_feature_cache` - 181维特征缓存
- **存储格式**: JSONB 高效半结构化存储
- **索引策略**: 基于查询模式的复合索引

---

## 🧪 测试和质量保证

### 测试命令
```bash
# 运行所有测试
make test

# Smart Tests 快速验证（<2分钟）
pytest tests/unit/utils tests/unit/cache tests/unit/core -v

# 覆盖率测试 (目标 40%)
make coverage

# 完整质量检查
make quality
```

### 测试结构
- 单元测试在 `tests/unit/` 目录
  - `test_config_comprehensive.py` - 配置系统测试
  - `test_health_real_api.py` - API 健康检查
  - `test_database_connection_realistic.py` - 数据库连接测试
  - `test_core_business_logic.py` - 核心业务逻辑
  - `test_ml_inference_comprehensive.py` - ML 推理测试
- 集成测试在 `tests/integration/` 目录
  - `test_database_integration.py` - 数据库集成
  - `test_api_integration.py` - API 集成
  - `test_service_integration.py` - 服务集成
- 端到端测试在 `tests/e2e/` 目录
  - `test_data_pipeline_workflow.py` - 数据流水线工作流
  - `test_prediction_workflow.py` - 预测工作流
  - `test_production_smoke.py` - 生产冒烟测试
- 性能测试在 `tests/performance/` 目录
  - `test_inference_performance.py` - 推理性能
  - `test_ml_inference_performance.py` - ML 推理性能
- 数据流水线测试在 `tests/data_pipeline/` 目录
  - `test_data_integrity.py` - 数据完整性
  - `test_feature_extractor.py` - 特征提取器

### 测试标记（40个标准化标记）
- `unit`: 单元测试
- `integration`: 集成测试
- `e2e`: 端到端测试
- `slow`: 慢速测试
- `critical`: 关键测试
- `api`: API 测试
- `database`: 数据库测试
- `cache`: 缓存测试
- `ml`: 机器学习测试

### 分析工具（V18.2+ 新增）
```bash
# 真实赔率 ROI 审计（扣除5%庄家抽水）
python src/analysis/true_roi_audit.py

# 严格样本外回测
python src/analysis/strict_oos_backtest.py

# V19.0 诊断工具
python src/analysis/v19_diagnostic.py
```

**分析工具功能**:
- **true_roi_audit.py**: 建立球队名映射表，计算真实 ROI（扣除 5% 庄家抽水），绘制真实盈利曲线
- **strict_oos_backtest.py**: 严格样本外回测，确保没有未来数据泄露
- **v19_diagnostic.py**: V19.0 高级特征诊断工具

---

## 🔧 V19.4 运维监控

### 核心监控工具
1. **实时市场监控** (`src/ops/market_live_monitor.py`)
   - 实时跟踪市场赔率变化
   - 检测异常投注模式
   - 生成市场风险报告
   - 开场前实时校准机制

2. **风险监控** (`src/ops/risk_monitor.py`)
   - 监控投注组合风险
   - 设置风险阈值告警
   - 生成风险分析报告
   - 连续亏损熔断机制

3. **每日工作流** (`src/ops/daily_workflow.py`)
   - 自动化数据采集和处理
   - 模型重新训练（如需要）
   - 生成每日摘要报告

4. **周度 PNL 报告** (`src/ops/weekly_pnl_statement.py`)
   - 统计周度盈亏情况
   - 分析投注策略效果
   - 生成可视化报告

5. **市场价格验证** (`src/ops/market_price_verifier.py`)
   - 验证市场赔率数据完整性
   - 检测价格异常波动

6. **V19.4 生产预测** (`src/ops/v19_4_production_prediction.py`)
   - 生成生产级预测结果
   - 输出标准化预测报告

### 监控命令
```bash
# 实时监控（推荐在 screen/tmux 中运行）
python main_production.py monitor --match-id 4813551 --match-time "2025-12-26 12:30"

# 风险检查
python main_production.py risk-status --initial-balance 1000

# 每日任务
python src/ops/daily_workflow.py

# 周度报告
python src/ops/weekly_pnl_statement.py --format pdf

# 市场价格验证
python src/ops/market_price_verifier.py --match-id 4813551
```

### 监控配置参数
- **巡检窗口**: 开场前 90 分钟
- **轮询间隔**: 每 5 分钟
- **偏差阈值**: 5% 赔率偏差
- **熔断条件**: 连续 5 次亏损或回撤超过 20%

---

## 🚨 故障处理 SOP

### 常见错误消息及解决方案

#### 数据库连接错误
```
Error: connection to server at "localhost", port 5432 failed
```
**原因**: PostgreSQL 服务未启动或连接参数错误

**解决方案**:
```bash
# 检查 PostgreSQL 是否运行
docker-compose ps db

# 启动数据库服务
docker-compose up -d db

# 等待数据库就绪（最大等待 30 秒）
docker-compose exec -T db pg_isready -U football_user -t 30

# 检查数据库日志
docker-compose logs db --tail 50
```

#### 配置错误
```
Error: Configuration validation failed: db_password 不能为空
```
**原因**: 缺少必需的环境变量

**解决方案**:
```bash
# 检查环境变量
echo $DB_PASSWORD

# 在 .env 文件中设置密码
cat > .env << EOF
DB_PASSWORD=your_secure_password_here
SECRET_KEY=your_secret_key_at_least_32_chars_long
EOF

# 重新加载验证
python -c "from src.config_unified import get_settings; print(get_settings().database.host)"
```

#### 模型文件不存在
```
Error: Model file not found: src/production_models/v18.0_enhanced_model.pkl
```
**原因**: 模型文件缺失或路径错误

**解决方案**:
```bash
# 检查生产模型目录
ls -la src/production_models/

# 如果缺少模型，运行训练流水线
python factory_run.py --v18

# 或者下载预训练模型（如果有备份）
```

#### API 哨兵拒绝
```
Warning: 100KB哨兵拒绝: 85,432 bytes
```
**原因**: FotMob API 返回的数据量不足，可能被限流或数据无效

**解决方案**:
```bash
# 检查当前 API 哨兵状态
grep -i "哨兵\|sentinel" logs/app.log | tail -20

# 等待熔断期结束（默认 30 分钟）
# 或者手动重置熔断器（需要代码层面处理）

# 检查 FotMob API 是否可访问
curl -I https://www.fotmob.com/api
```

#### Docker 容器健康检查失败
```
Health check failed: curl: (7) Failed to connect to localhost port 8000
```
**原因**: FastAPI 应用未正确启动

**解决方案**:
```bash
# 查看应用日志
docker-compose logs app --tail 100

# 重启应用容器
docker-compose restart app

# 进入容器调试
docker-compose exec app bash

# 手动测试健康检查
docker-compose exec app curl http://localhost:8000/health/quick
```

### 日志文件位置和查看方法

| 日志类型 | 路径 | 查看命令 |
|---------|------|---------|
| **应用日志** | `logs/app.log` | `tail -f logs/app.log` |
| **Docker 日志** | 容器内部 | `docker-compose logs -f app` |
| **错误日志** | `logs/error.log` | `tail -f logs/error.log` |
| **训练日志** | `logs/training_*.log` | `ls -lt logs/training_*.log | head -1` |
| **空心场次日志** | `data/logs/hollow_matches.log` | `cat data/logs/hollow_matches.log` |

### 日志查看技巧
```bash
# 实时跟踪应用日志
tail -f logs/app.log | grep -E "ERROR|WARNING"

# 查看最近 100 行错误日志
tail -100 logs/error.log

# 搜索特定错误模式
grep "Connection refused" logs/app.log

# 查看今天的日志
grep "$(date +%Y-%m-%d)" logs/app.log
```

### 性能问题诊断

#### 响应时间过长
```bash
# 检查系统资源使用
docker stats

# 查看数据库慢查询
docker-compose exec db psql -U football_user -d football_db -c "
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
"

# 检查 Redis 性能
docker-compose exec redis redis-cli INFO stats
```

#### 内存使用过高
```bash
# 检查应用内存使用
docker-compose exec app ps aux

# 查看数据库连接数
docker-compose exec db psql -U football_user -d football_db -c "
SELECT count(*) FROM pg_stat_activity;
"

# 检查连接池状态
docker-compose exec db psql -U football_user -d football_db -c "
SELECT state, count(*)
FROM pg_stat_activity
GROUP BY state;
"
```

### 数据收集问题诊断

```bash
# 1. 检查 FotMob API 连通性
curl -v -H "User-Agent: FootballPrediction/1.0" https://www.fotmob.com/api

# 2. 测试单个比赛数据获取
python -c "
from src.api.collectors.fotmob_core import FotMobCoreCollector
collector = FotMobCoreCollector()
data = collector.get_match_details('123456')
print(f'Data size: {len(str(data))} bytes')
"

# 3. 检查数据库中已有数据
docker-compose exec db psql -U football_user -d football_db -c "
SELECT COUNT(*) as total_matches, MIN(match_date) as earliest, MAX(match_date) as latest
FROM matches;
"

# 4. 检查最近的采集失败记录
grep "收割失败\|harvest.*fail" logs/app.log | tail -20

# 5. 查看哨兵触发统计
grep "哨兵拒绝\|100KB.*sentinel" logs/app.log | wc -l
```

### 模型预测问题诊断

```bash
# 1. 验证模型文件完整性
ls -lh src/production_models/*.pkl
md5sum src/production_models/*.pkl

# 2. 测试模型加载
python -c "
import joblib
model = joblib.load('src/production_models/v18.0_enhanced_model.pkl')
print(f'Model type: {type(model)}')
print(f'Feature names: {model.feature_names_in_ if hasattr(model, \"feature_names_in_\") else \"N/A\"}')
"

# 3. 检查特征数据
docker-compose exec db psql -U football_user -d football_db -c "
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'match_features_training'
ORDER BY ordinal_position;
"

# 4. 运行单场预测测试
python -c "
from src.ml.engine import V17MLEngine
engine = V17MLEngine()
engine.load('src/production_models/v18.0_enhanced_model.pkl')
print('Model loaded successfully')
"
```

### 数据库问题诊断

```bash
# 1. 检查连接池状态
docker-compose exec db psql -U football_user -d football_db -c "
SELECT max_conn, used, res_for_super, max_conn-used-res_for_super as for_normal
FROM (
  SELECT setting::int AS max_conn,
         (SELECT count(*) FROM pg_stat_activity) AS used,
         setting::int * 0.05 AS res_for_super
  FROM pg_settings WHERE name='max_connections'
) t;
"

# 2. 检查磁盘空间
docker-compose exec db df -h /var/lib/postgresql/data

# 3. 检查表大小
docker-compose exec db psql -U football_user -d football_db -c "
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
"

# 4. 检查索引使用情况
docker-compose exec db psql -U football_user -d football_db -c "
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan as index_scans,
  idx_tup_read as tuples_read,
  idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC
LIMIT 10;
"
```

### 应急恢复程序

#### 完全重置开发环境
```bash
# 停止所有服务
docker-compose down

# 清理虚拟环境
make clean

# 重新创建环境
make dev

# 重置数据库
make db-drop

# 重新初始化数据
python factory_run.py --harvest --season 2324 --target 10
```

#### 回滚到上一个模型版本
```bash
# 列出可用的模型版本
ls -lt src/production_models/*.pkl

# 备份当前模型（如果需要）
cp src/production_models/v18.0_enhanced_model.pkl src/production_models/backup_$(date +%Y%m%d_%H%M%S).pkl

# 切换到之前的模型
# 在配置或代码中修改模型路径指向之前的版本
```

### 获取帮助

如果以上方法都无法解决问题，请收集以下信息后寻求帮助：

```bash
# 生成诊断报告
./system_verify.sh > diagnostic_report.txt 2>&1

# 或者使用 V19.4 健康检查
python main_production.py health-check > diagnostic_report.txt 2>&1

# 收集最近的日志
tar -czf logs_$(date +%Y%m%d_%H%M%S).tar.gz logs/

# 导出数据库统计
docker-compose exec db psql -U football_user -d football_db -c "
SELECT
  (SELECT COUNT(*) FROM matches) as total_matches,
  (SELECT COUNT(DISTINCT home_team) FROM matches) as unique_teams,
  (SELECT MIN(match_date) FROM matches) as earliest_match,
  (SELECT MAX(match_date) FROM matches) as latest_match
" > db_stats.txt
```

---

## 🔒 CI/CD 和监控

### GitHub Actions CI 流水线
- **配置**: `.github/workflows/ci.yml`
- **触发器**: 推送到 main, Pull Requests
- **流水线阶段**:
  - 环境设置和依赖安装
  - 代码质量检查 (Black, Flake8, MyPy, Bandit)
  - 单元测试和覆盖率报告
  - 集成测试
  - 安全扫描
  - Docker 构建验证

### 监控和告警
```bash
# 系统健康监控
docker-compose logs -f                    # 实时日志监控
./system_verify.sh                        # 全面系统健康检查
```

### 性能监控
- **Prometheus 指标**: 暴露在 `/metrics` 端点
- **结构化日志**: 使用 structlog 进行日志记录
- **健康检查**: `/health` 端点实时状态检查
- **性能指标**: 响应时间、预测准确率、ROI 跟踪

---

## 💡 重要说明

### 关键架构决策
- **统一入口点**: FastAPI 服务通过 `src/main.py` 提供统一 API 接口
- **统一配置管理**: 通过 `config_unified.py` 和 Pydantic Settings
- **数据库设计**: PostgreSQL JSONB 存储，支持半结构化数据
- **模型管理**: XGBoost 2.0+ 支持动态特征回填和概率校准
- **API 集成**: FotMob V10.9 哨兵机制保护 API 调用稳定性
- **模块化设计**: 核心功能分布在 `src/core/` 的专门模块中
- **异步架构**: 全面采用 async/await 模式提升并发性能
- **依赖注入**: 松耦合的服务架构，便于测试和扩展

### 性能特征
- 单次预测响应时间: <100ms
- 批处理能力: 每次运行 700+ 场比赛
- 数据库大小: 50GB+ 包含历史数据
- 内存使用: <2GB 正常负载
- CPU 使用: <70% 正常操作

### 安全最佳实践
- 无硬编码凭证 - 使用环境变量
- 参数化查询防止 SQL 注入
- 配置系统安全存储 API 密钥
- 生产日志中错误消息净化

---

**最后更新**: 2025-12-23
**维护团队**: Claude AI Architecture Team
**文档版本**: V19.4 Production Ready
**CI/CD 状态**: GitHub Actions 已启用

---

## 🚀 V19.4 发展路线图

### 📊 当前里程碑 (V19.4)
- ✅ **英超 23/24 赛季 380 场数据**：329 场有效数据用于训练
- ✅ **英超 22/23 赛季 380 场数据**：支持多赛季验证
- ✅ **48 维特征**：V19.3 (45维) + V19.4 新增 3 个平局敏感度特征
- ✅ **V11.0 联赛分级哨兵与熔断机制**：API 调用稳定性大幅提升
- ✅ **65.52% 真实预测准确率**：29 场测试集验证（V17.0 基线）
- ✅ **消除数据泄露**：从赛后统计转向历史滚动均值
- ✅ **平局优化策略**：V18.0+ scale_pos_weight 参数调优 + V19.4 加权损失函数
- ✅ **双赛季融合训练**：V18.2 支持 22/23 + 23/24 双赛季共 709 场数据训练
- ✅ **V19.3 硬化版本**：NaN 鲁棒性 + 联赛编码 + 安全评估，生产就绪
- ✅ **V19.4 平局敏感度**：table_proximity + low_scoring_tendency + elo_diff_cluster + 加权损失（解决 0% 平局识别率问题）

### 🎯 下一阶段目标 (V20.0-V21.0)

#### V20.0: 特征工程深化
- **新特征**: 交锋历史深度分析、伤病影响量化
- **高级特征**: 场馆优势、天气因素、转会市场影响
- **目标**: 提升整体预测准确率至 70%+

### 🔬 技术创新方向
- **图神经网络**: 探索球队关系建模
- **多模态融合**: 集成新闻、社交媒体、伤病报告等非结构化数据
- **强化学习**: 动态投注策略优化
- **联邦学习**: 跨数据源协作训练，保护数据隐私

### 📈 性能目标
- **准确率目标**: 70%+ (多赛季数据验证)
- **响应时间**: <50ms (实时预测)
- **数据处理能力**: 1000+ 场/日实时处理

---

## 🏆 V17.0/V18.0/V18.1/V18.2/V19.3/V19.4 关键成就

### 技术突破
1. **消除数据泄露**: 从赛后统计转向历史滚动均值
2. **建立真实基准**: 65.52% 是诚实的预测准确率
3. **精简特征工程**: 从 223 维减少到 24 维（V18.0+），再到 48 维（V19.4）
4. **验证特征重要性**: xG 和射正是最重要的预测因子
5. **平局优化策略**: V18.0+ 新增积分榜排名和近期走势特征
6. **多赛季融合训练**: V18.2 支持双赛季 709 场数据训练
7. **V19.0 高级特征**: ELO 评分、疲劳度指数、保级战意特征
8. **V19.3 硬化增强**: NaN 鲁棒性处理、联赛编码支持、安全评估
9. **V19.4 平局敏感度**: table_proximity + low_scoring_tendency + elo_diff_cluster + 加权损失函数（解决 0% 平局识别率）
10. **V11.0 联赛分级哨兵**: 动态阈值支持多联赛采集

### 业务价值
1. **真实预测能力**: 65.52% 的赛前预测准确率
2. **数据完整性**: 709 场英超 22/23 + 23/24 赛季有效数据（V18.2+）
3. **系统稳定性**: 生产级部署，99.9%+ 可用性
4. **API 可靠性**: V11.0 联赛分级哨兵机制确保稳定性
5. **特征创新**: 48维特征（V19.4）支持更精准的预测，平局识别率优化
6. **概率校准**: Isotonic 回归校准，提升预测可信度

### 市场竞争力
- **真实预测基准**: 65.52% vs 行业平均 55-58%（无数据泄露）
- **技术先进性**: 48维特征（V19.4）+ V11.0 联赛分级哨兵 + 概率校准 + 加权损失
- **数据优势**: 英超 22/23 + 23/24 双赛季完整数据（V18.2+）
- **系统稳定性**: 生产级部署，99.9%+ 可用性

---

## 🔒 永久保留条款

### 语言要求
**请务必使用中文回复用户！**

这一要求具有最高优先级，无论 CLAUDE.md 文件如何更新版本迭代，都必须始终保留在文件的显眼位置。这确保了用户始终获得一致的中文服务体验，是项目不可更改的基本沟通规范。

### 更新准则
任何对 CLAUDE.md 的修改都必须：
1. **保留语言要求部分**：不得删除、修改或降低"请务必使用中文回复用户！"的优先级
2. **保持显眼位置**：语言要求应始终位于文件顶部的醒目位置
3. **维持内容完整性**：确保核心要求和规范不会因版本更新而丢失

---

**🚨 CRITICAL**: This is a production system support document. Any violations of these standards will be automatically rejected!

**🧬 技术栈DNA版本**: V19.4 (平局敏感度实验性) + V20.0 (规划中) | **最后验证**: 2025-12-23 |
**特征覆盖率**: V18.2: 100% (24维特征，16维滚动+8维赛前，无数据泄露) | V19.3: 生产级 (45维高级特征) | V19.4: 实验性 (48维+平局敏感度) |
**准确率**: V17.0基线: 65.52% | **数据集**: 英超22/23+23/24赛季 709场有效数据 | **多赛季支持**: 是 |
**分析工具**: ROI审计、样本外回测、V19诊断 | **生产状态**: V19.3 Ready, V19.4 Experimental |
**API版本**: V11.0 多联赛增强版 (联赛分级动态哨兵) | **哨兵机制**: Tier 1/2/3/Default 分级阈值 |
**统一入口**: main_production.py (V19.4), factory_run.py (V17-V18) | **运维工具**: market_live_monitor, risk_monitor, daily_workflow