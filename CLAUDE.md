# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 重要提醒：语言要求

**请务必使用中文回复用户！**

无论文件如何更新版本，都必须保留这一要求。这是项目的基本沟通规范，确保用户获得一致的中文服务体验。

## Project Overview

**FootballPrediction V2.3.1** is a production-ready football match prediction system with 60.00% accuracy using XGBoost 2.0+ ML model. The system collects real-time data from FotMob API, maintains a database of 415 "golden" matches, and provides real-time predictions with dynamic feature backfilling.

**Status**: ✅ Production Ready | **Model Accuracy**: 60.00% | **Version**: V2.3.1 Real Scores

---

## 🏗️ 工业级标准目录结构

```
FootballPrediction/
├── 📁 src/                          # 核心源代码目录
│   ├── 📁 core/                     # 核心引擎模块
│   │   └── ⚙️ main_engine_v5.py     # 主数据收集与预测引擎
│   ├── 📁 api/                      # API客户端层
│   │   ├── fotmob_client.py         # FotMob API客户端
│   │   └── v1/                      # API v1版本接口
│   ├── 📁 schemas/                  # 数据模式定义
│   │   └── match_features.py        # 106字段特征模式
│   ├── 📁 data_access/              # 数据访问层
│   │   └── 📁 processors/           # 数据处理器
│   │       └── advanced_feature_extractor.py  # 106字段特征提取器
│   ├── 📁 database/                 # 数据库模块
│   │   ├── models.py                # 数据模型
│   │   └── migrations/              # 数据库迁移
│   ├── 📁 ml/                       # 机器学习模块
│   │   ├── inference/               # 推理引擎
│   │   ├── training/                # 训练模块
│   │   └── features/                # 特征工程
│   ├── 📁 services/                 # 服务层
│   └── 📁 utils/                    # 工具模块
├── 📁 configs/                      # 配置文件目录
├── 📁 docs/                         # 文档目录
├── 📁 scripts/                      # 脚本目录
├── 📁 tests/                        # 测试目录
├── 📁 data/                         # 数据存储目录
│   ├── 📁 models/                   # 模型文件存储
│   ├── 📁 cache/                    # 缓存数据
│   ├── 📁 raw/                      # 原始数据
│   └── 📁 processed/                # 处理后数据
├── 📁 logs/                         # 日志目录
├── 🐳 docker-compose.yml            # Docker编排文件
├── 🐳 Dockerfile                    # Docker镜像构建
├── 📋 CLAUDE.md                     # Claude AI开发指南
└── 🚀 run_daily_predict.sh          # 日常预测脚本
```

### 📁 目录标准化完成时间：2025-12-21
### 🎯 标准化目标：消除AI编程噪音，实现语义清晰、结构严谨的工业级代码资产

---

## 🚀 Primary Entry Points (MANDATORY)

### 1. Main Data Collection & Prediction Engine
```bash
# Production mode (recommended)
python src/core/main_engine_v5.py --mode full --limit 700

# Test mode (REQUIRED after any code changes)
python src/core/main_engine_v5.py --mode test
```

### 2. Docker Automation
```bash
# One-click daily prediction system
./run_daily_predict.sh

# System health verification
./system_verify.sh

# Full Docker stack deployment
docker-compose up -d

# Container health checks
docker-compose exec db pg_isready -U football_user
docker-compose exec redis redis-cli ping
```

### 3. Programmatic Model Inference
```python
from core.inference_engine import get_inference_engine
engine = get_inference_engine()
prediction = engine.predict_match(home_team, away_team, features)
```

**❌ FORBIDDEN ACTIONS**:
- Never bypass `main_engine_v5.py` for direct API calls
- Never operate database directly without business logic
- Never use non-official scripts for data operations

---

## 🔗 Database Connection Standards

### Unified Connection Method (REQUIRED)
```python
# Use unified configuration system
from src.config_unified import get_settings
settings = get_settings()
db = settings.database

# Standard connection with RealDictCursor (REQUIRED)
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

### Security Requirements
- ✅ MUST use `config_unified.py` for connection parameters
- ✅ MUST use connection pooling or async connections
- ✅ MUST implement exception handling and resource cleanup
- ❌ NEVER hardcode connection parameters
- ❌ NEVER use basic cursors - always use `RealDictCursor`

---

## 🛡️ Code Quality Mandates

### Pre-Change Validation (MANDATORY)
```bash
# After ANY code modification, MUST run this command with 100% pass rate
python src/core/main_engine_v5.py --mode test
```

**Validation Requirements**:
- ✅ Database connection test: Success
- ✅ Configuration test: All items loaded properly
- ✅ Model test: Prediction engine loads successfully
- ✅ API test: External API connects normally
- ❌ Any failure = Code merge prohibited

### Code Standards
- **Python Version**: 3.11+ (specified in pyproject.toml)
- **Style**: Black (line-length: 120) + Flake8 + isort
- **Type Checking**: MyPy with strict configuration and configured overrides
- **Security**: Bandit scanning + Safety dependency checking
- **Testing**: pytest with 96.35% coverage requirement
- **Logging**: INFO (production), DEBUG (development) using structlog
- **Error Handling**: Mandatory try-catch with proper logging
- **Documentation**: All public methods must have docstrings
- **Code Quality**: Integrated Python Code Quality Claude Skills

---

## 📊 Production Environment Specifications

### Data Flow Architecture
```
External API → Data Validation → Feature Extraction → Database Storage
     ↓
Real-time Prediction ← Model Inference ← Dynamic Feature Backfill ← Historical Data Query
```

### Performance Monitoring
- **Response Time**: Single prediction <100ms
- **Accuracy**: Maintain 60.00% baseline
- **Data Integrity**: 415 golden matches 100% complete
- **System Availability**: 99.9%+ uptime

### Alert Thresholds
- Data collection failure rate >5% → Immediate alert
- Model accuracy drop >2% → Immediate alert
- System response time >200ms → Immediate alert
- Database connection failure → Immediate alert

---

## 🔧 Development & Deployment

### Environment Setup
```bash
# Production environment
export ENVIRONMENT=production
export DOCKER_ENV=true
export LOG_LEVEL=INFO

# Development environment
export ENVIRONMENT=development
export LOG_LEVEL=DEBUG
```

### Docker Deployment
```bash
# Build image
docker build -t footballprediction:v2.0 .

# Run service stack
docker-compose up -d

# Health check
docker-compose exec db pg_isready -U football_user
```

### Key Services (docker-compose.yml)
- **db**: PostgreSQL 15 with 415 golden matches preloaded
- **redis**: Redis 7 for caching and real-time data
- **engine**: Main prediction engine (port 8000)
- **monitor**: Data quality monitoring service (port 8001)

---

## 🎯 System Architecture

### Core Components
1. **MainEngineV5** (`src/core/main_engine_v5.py`): Data harvesting and real-time prediction engine
2. **InferenceEngine** (`src/core/inference_engine.py`): XGBoost V2.0 model inference core
3. **FotMobAPIClient** (`src/api/fotmob_client.py`): External data source interface
4. **AdvancedFeatureExtractor**: Extracts 106 features from raw match data
5. **Database**: PostgreSQL with comprehensive match data schema

### Model Details
- **Algorithm**: XGBoost 2.0+ with 60.00% accuracy
- **Core Features** (10 primary): xG, possession, odds, and derivatives
- **Dynamic Feature Backfilling**: Uses team's last 5 matches for future predictions
- **Total Feature Dimensions**: 106 with engineered features

### Database Schema
- `matches`: Match metadata and collection status
- `match_features_training`: 4-field feature set for model training
- Complete L2 features including raw JSON data storage

---

## 🧪 Testing and Quality Assurance

### Test Commands
```bash
# Run all tests (630 tests expected)
make test

# Coverage test (96.35% expected)
make coverage

# Full quality check
make quality

# CI pipeline (includes all checks)
make ci
```

### Test Structure
- Unit tests in `tests/` directory
- Smoke tests for basic functionality
- Integration tests for API and database
- Mock tests for external dependencies

---

## 🚨 Troubleshooting SOP

### Data Collection Issues
1. Check FotMob API connectivity
2. Verify database connection
3. Check rate limiting settings
4. Review detailed error logs

### Model Prediction Issues
1. Verify model file integrity: `ls -la models/xgb_football_v2_real_scores.*`
2. Validate feature data format
3. Check scaler status
4. Rollback to previous version if needed

### Database Issues
1. Check connection pool status
2. Verify disk space
3. Check query performance
4. Execute data backup if needed

---

## 📋 Development Workflow Commands

### Using Makefile (Recommended)
```bash
# Environment setup
make dev        # Quick development environment
make dev-full   # Full environment with code quality tools (incl. Claude Skills)

# Code quality
make format     # Format code with Black
make lint       # Lint code with Flake8
make typecheck  # Type check with MyPy
make security   # Security scan with Bandit
make quality    # Complete quality check (format + lint + typecheck + security)

# Python Code Quality Claude Skills
make python-quality-check   # Run quality analysis
make python-quality-format  # Auto-format code
make python-quality-fix     # Auto-fix issues
make python-quality-score   # Show quality score

# Testing
make test       # Run unit tests (630 tests expected)
make coverage   # Coverage test (96.35% expected)

# Before committing
make prepush    # Complete pre-push checklist with CI
make ci         # Full CI pipeline (env-check + quality + test + coverage)

# Project monitoring
make status     # Project status overview
make ci-status  # GitHub Actions CI status monitoring
```

### Modern Python Project Management (pyproject.toml)
```bash
# Install with development dependencies
pip install -e .[dev]

# Install with all optional dependencies
pip install -e .[all]

# Project scripts (defined in pyproject.toml)
football-predict    # Run prediction engine
football-train      # Run training pipeline
football-server     # Start FastAPI server

# Development tools configuration
black src/          # Code formatting (configured in pyproject.toml)
isort src/          # Import sorting
pytest tests/       # Testing with configured markers
mypy src/           # Type checking with configured overrides
bandit -r src/      # Security scanning
vulture src/        # Dead code detection
```

---

## 💡 Important Notes

### Critical Architecture Decisions
- **Single Entry Point**: All operations must go through `main_engine_v5.py`
- **Configuration Management**: Unified through `config_unified.py` with Pydantic
- **Database Design**: PostgreSQL with specific schema for golden matches
- **Model Management**: XGBoost with dynamic feature backfilling capability
- **API Integration**: FotMob with proper rate limiting and error handling

### Performance Characteristics
- Single prediction response time: <100ms
- Batch processing capability: 700+ matches per run
- Database size: 50GB+ with historical data
- Memory usage: <2GB typical load
- CPU usage: <70% normal operation

### Security Best Practices
- No hardcoded credentials - use environment variables
- SQL injection protection through parameterized queries
- API key secure storage through configuration system
- Error message sanitization in production logs

---

## 🔧 CI/CD and Monitoring

### GitHub Actions CI Pipeline
- **Configuration**: `.github/workflows/ci.yml`
- **Triggers**: Push to main, Pull Requests
- **Pipeline Stages**:
  - Environment setup and dependency installation
  - Code quality checks (Black, Flake8, MyPy, Bandit)
  - Unit tests with coverage reporting
  - Integration tests
  - Security scanning
  - Docker build validation

### Monitoring and Alerting
```bash
# Real-time CI monitoring
make ci-monitor    # Monitor CI execution in real-time
make ci-status     # Check latest CI run status
make ci-analyze RUN_ID=<id>  # Deep analysis of CI failures

# System health monitoring
docker-compose logs -f                    # Real-time log monitoring
./system_verify.sh                        # Comprehensive system health check
python src/utils/data_quality_checker.py  # Data quality validation
```

### Performance Metrics Dashboard
- **Response Time**: Single prediction <100ms
- **Throughput**: 700+ matches per batch
- **Database Performance**: Connection pooling, query optimization
- **Memory Usage**: <2GB typical load
- **CPU Usage**: <70% normal operation
- **Error Rates**: <5% data collection failure

---

**Last Updated**: 2025-12-21
**Maintenance Team**: Claude AI Architecture Team
**Document Version**: V2.3.1 Production Ready
**CI/CD Status**: GitHub Actions Enabled

---

## 🧬 当前技术栈 DNA (Technical Stack DNA)

### 核心特征提取路径映射表 (106维特征体系)

#### 1. xG (Expected Goals) 特征组 (10维)
```
FotMob API路径: content.stats.Periods.All.stats[0].stats[].key = "expected_goals"
├── 主队xG: stats[0] (home_xg)
├── 客队xG: stats[1] (away_xg)
├── xG总计: home_xg + away_xg (xg_total)
├── xG差值: home_xg - away_xg (xg_diff)
└── 备用路径: shotmap.shots[].expectedGoals
```

#### 2. 控球率特征组 (8维)
```
FotMob API路径: content.stats.Periods.All.stats[0].stats[].key = "BallPossesion"
├── 主队控球率: stats[0] (home_possession)
├── 客队控球率: stats[1] (away_possession)
├── 控球率差值: home_possession - away_possession (possession_diff)
└── 备用路径: general.teamStats[].possession
```

#### 3. 角球特征组 (6维)
```
FotMob API路径: content.stats.Periods.All.stats[0].stats[].key = "CornerKicks"
├── 主队角球数: stats[0] (home_corners)
├── 客队角球数: stats[1] (away_corners)
├── 角球差值: home_corners - away_corners (corners_diff)
└── 备用路径: stats[].type = "cornerKicks"
```

#### 4. 红黄牌特征组 (6维)
```
FotMob API路径: content.stats.Periods.All.stats[0].stats[].key = "YellowCards"/"RedCards"
├── 主队黄牌: stats[0] (home_yellow_cards)
├── 客队黄牌: stats[1] (away_yellow_cards)
├── 主队红牌: stats[0] (home_red_cards)
├── 客队红牌: stats[1] (away_red_cards)
├── 黄牌差值: home_yellow_cards - away_yellow_cards (yellow_cards_diff)
└── 备用路径: cards[].cardType + isHome
```

#### 5. 射门特征组 (6维)
```
FotMob API路径: content.stats.Periods.All.stats[0].stats[].key = "Shots"/"ShotsOnTarget"
├── 主队射门: stats[0] (home_shots_total)
├── 客队射门: stats[1] (away_shots_total)
├── 主队射正: stats[0] (home_shots_on_target)
├── 客队射正: stats[1] (away_shots_on_target)
├── 射门差值: home_shots_total - away_shots_total (shots_total_diff)
└── 最准确路径: shotmap.shots[].eventType
```

#### 6. 赔率特征组 (6维)
```
数据源: 多个赔率提供商
├── 主队开盘赔率: home_opening_odds
├── 客队开盘赔率: away_opening_odds
├── 平局赔率: draw_odds
├── 主队当前赔率: home_current_odds
├── 客队当前赔率: away_current_odds
└── 赔率变化率: (current_odds - opening_odds) / opening_odds
```

### 动态特征回填算法 (Dynamic Feature Backfilling)
```python
# 核心算法位置: src/core/main_engine_v5.py:get_historical_team_stats()
# 冷启动保护机制:
1. 查询球队过去5场比赛历史数据
2. 如果无数据 → 查询该球队主要联赛平均水平
3. 如果仍无数据 → 使用全球平均值
4. 特征来源标识: data_source字段记录数据来源
```

### 模型推理引擎架构
```python
# 核心类: src/core/inference_engine.py:InferenceEngine
# 模型文件: models/xgb_football_v2_real_scores.joblib
# 输入特征: 106维标准特征向量
# 输出结果: [主胜概率, 平局概率, 客胜概率]
# 响应时间: <100ms
# 模型准确率: 60.00%
```

### 数据库Schema固化
```sql
-- 主表: match_features_training (83个字段)
-- 核心索引:
CREATE INDEX idx_match_features_xg ON match_features_training(home_xg, away_xg);
CREATE INDEX idx_match_features_possession ON match_features_training(home_possession, away_possession);
CREATE INDEX idx_match_features_shots ON match_features_training(home_shots_total, away_shots_total);
CREATE INDEX idx_match_features_corners ON match_features_training(home_corners, away_corners);

-- 质量检查函数:
SELECT * FROM check_data_quality(); -- 返回填充率统计
```

### API集成路径
```python
# 客户端: src/api/fotmob_client.py:FotMobAPIClient
# 请求头: FOTMOB_X_MAS_HEADER (必需)
# 基础URL: https://www.fotmob.com/api
# 速率限制: 1秒延迟
# 重试机制: 3次重试 + 指数退避
```

### 冷启动保护策略
```python
# 分层回退机制:
1. 球队历史数据 (过去5场)
2. 联赛平均水平 (主要联赛)
3. 全球平均值 (最后兜底)
4. 标识字段: data_source = "team_history"/"league_average"/"global_average"
```

---

**🚨 CRITICAL**: This is a production system support document. Any violations of these standards will be automatically rejected!

**🧬 技术栈DNA版本**: V2.3.1 | **最后验证**: 2025-12-21 | **特征覆盖率**: 100% (xG + 控球 + 角球 + 红黄牌 + 射门)

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