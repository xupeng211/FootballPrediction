# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**重要提醒**: 与用户交流时，请始终使用中文回复。

## Important Development Commands

### Environment Setup
```bash
make install          # Install dependencies and create virtual environment
make env-check        # Verify environment is properly configured
make dev              # Quick development environment setup
make venv             # Create virtual environment
make lock             # Generate dependency lock file
make clean            # Clean environment and cache
```

### Testing and Quality
```bash
make test             # Run unit tests (630 tests active, target: 80%+ coverage)
make coverage         # Run tests with coverage report (current: 96.35%)
make ci               # Complete CI simulation (env-check, quality, test, coverage)
make prepush          # Pre-commit full check
./ci-verify.sh        # Local CI verification script (141 lines)
```

### Code Quality
```bash
make format           # Format code with black
make lint             # Run flake8 linting
make typecheck        # Run mypy type checking
make security         # Run bandit security scan
make quality          # Run all quality checks (format, lint, typecheck, security)
make complexity       # Run code complexity analysis with radon
make deadcode         # Run dead code detection with vulture
make fix              # Quick fix: format + lint

# Enhanced Python code quality with Claude Skills
make python-quality-setup    # Install Python code quality Claude Skills tools
make python-quality-check    # Run comprehensive code quality analysis
make python-quality-format   # Auto-format code with quality standards
make python-quality-fix      # Auto-fix common code quality issues
make python-quality-score    # Get code quality score and recommendations
```

### Local Development
```bash
# Docker管理脚本 (v2.0推荐)
./scripts/docker-manager.sh dev                    # 启动完整开发环境
./scripts/docker-manager.sh status                 # 查看服务状态
./scripts/docker-manager.sh logs -f app           # 实时查看应用日志
./scripts/docker-manager.sh shell                  # 进入容器shell
./scripts/docker-manager.sh health                 # 检查服务健康状态
./scripts/docker-manager.sh test                  # Run tests in containers
./scripts/docker-manager.sh quality               # Run quality checks

# Enhanced MCP development
./scripts/mcp_manager.sh start                     # Start all MCP servers
./scripts/enhanced_mcp_manager.sh dev             # Development mode with MCP
./scripts/test_mcp_servers.sh                     # Test MCP server connectivity

# 传统Docker命令
docker-compose up --build                         # 启动完整开发栈
docker-compose ps                                 # 检查服务状态
docker-compose logs app                           # 查看应用日志
docker-compose logs -f app                        # 实时跟踪应用日志
make status                                       # 查看项目概览和统计

# Sprint 9 quick launcher
./scripts/sprint9_launcher.sh                     # 一键启动完整开发环境
```

### CI/CD and Monitoring
```bash
make ci-status           # 查看CI运行状态
make ci-monitor          # 实时监控CI执行
```

## Architecture Overview

### Core Architecture Pattern
**Service Layer v2.0 + ML Inference + Docker Containerization**

The system implements modern Service Layer architecture with ML integration:

```mermaid
graph TB
    subgraph "客户端层"
        CLI[CLI工具<br/>predict_match_v2.py]
        WEB[Web界面<br/>FastAPI Docs]
        API[外部API客户端]
    end

    subgraph "服务层 v2.0"
        SVC1[InferenceService<br/>预测服务]
        SVC2[CollectionService<br/>数据收集服务]
        SVC3[ExplainabilityService<br/>可解释性服务]
    end

    subgraph "ML推理层"
        MODEL[ModelLoader<br/>模型加载器]
        PREDICTOR[Predictor<br/>预测器]
        CACHE[CacheManager<br/>缓存管理器]
    end

    subgraph "数据层"
        PG[(PostgreSQL<br/>主数据库)]
        REDIS[(Redis<br/>缓存/队列)]
        FILES[文件系统<br/>模型存储]
        EXTERNAL[外部API<br/>FotMob]
    end

    subgraph "监控层"
        PROM[Prometheus<br/>指标收集]
        GRAFANA[Grafana<br/>可视化]
        ALERT[Alertmanager<br/>报警]
    end

    CLI --> SVC1
    WEB --> SVC1
    API --> SVC2

    SVC1 --> MODEL
    SVC1 --> PREDICTOR
    SVC1 --> CACHE

    SVC2 --> REDIS
    SVC2 --> EXTERNAL

    SVC3 --> MODEL
    SVC3 --> CACHE

    MODEL --> FILES
    PREDICTOR --> PG
    CACHE --> REDIS

    SVC1 -.->|指标暴露| PROM
    SVC2 -.->|指标暴露| PROM
    SVC3 -.->|指标暴露| PROM

    PROM --> GRAFANA
    PROM --> ALERT

    style CLI fill:#e1f5fe
    style WEB fill:#e1f5fe
    style API fill:#e1f5fe
    style SVC1 fill:#f3e5f5
    style SVC2 fill:#f3e5f5
    style SVC3 fill:#f3e5f5
    style MODEL fill:#e8f5e8
    style PREDICTOR fill:#e8f5e8
    style CACHE fill:#e8f5e8
```

### Key Architectural Components

#### Machine Learning Pipeline
- **Models**: XGBoost 2.0+ classifier in `src/ml/models/`
- **Feature Engineering**: Advanced feature extraction in `src/ml/features/`
- **Training Pipeline**: Model training workflow in `src/ml/training/`
- **Data Processing**: PostgreSQL data loaders in `src/ml/data/`

#### API Architecture
- **FastAPI Application**: High-performance async web framework
- **Health Checks**: System health monitoring in `src/api/health.py`
- **Model Management**: Model lifecycle management in `src/api/model_management.py`
- **Predictions**: Prediction endpoints in `src/api/predictions/`
- **Monitoring**: System metrics and monitoring in `src/api/monitoring.py`

#### Database Architecture
- **PostgreSQL Integration**: Async database operations
- **Data Loaders**: Specialized data extraction from `src/ml/data/postgres_loader.py`
- **Connection Management**: Async connection pooling and health checks

#### Configuration System
- **Centralized Config**: Complete configuration in `src/config.py` (461 lines)
- **Environment Management**: Multi-environment support (.env.dev, .env.ci, .env.production)
- **API Configuration**: External API (FotMob) settings and headers

## Project Structure

```
FootballPrediction/
├── src/
│   ├── api/                      # FastAPI routers and HTTP endpoints
│   ├── services/                 # 服务层 v2.0 (核心业务逻辑)
│   ├── ml/               # Machine learning models and feature engineering
│   │   ├── inference/            # 推理层 (v2.0新增)
│   │   ├── features/             # 特征工程模块
│   │   ├── models/               # ML模型
│   │   ├── training/             # 训练流水线
│   │   ├── data/                 # 数据加载和处理
│   │   └── dataset/              # 数据集生成
│   ├── database/                 # 数据库相关
│   ├── utils/            # Shared utilities
│   ├── config.py         # Centralized configuration (461 lines)
│   └── inference.py      # Main inference engine
├── scripts/              # Data collectors and development scripts
│   ├── predict_match_v2.py             # v2.0 预测CLI工具
│   ├── docker-manager.sh               # Docker容器管理脚本 (440行)
│   ├── sprint9_launcher.sh             # Sprint 9一键启动脚本
│   ├── collectors/       # External API data collectors
│   └── ci_monitor.py                    # CI状态监控
├── tests/                # Comprehensive test suite (630 tests)
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   ├── e2e/            # End-to-end tests
│   ├── performance/    # Performance tests
│   └── v2/             # v2.0架构测试
├── mcp_servers/         # MCP服务器 (5个服务器)
├── monitoring/          # Monitoring configuration
├── deploy/              # Deployment configuration
├── docker-compose.yml   # Container orchestration
├── Dockerfile           # Container image
├── Makefile            # Development toolchain (27 commands)
└── ci-verify.sh        # Local CI verification (141 lines)
```

## Development Guidelines

### Code Organization
- All code must follow async-first design patterns
- Use centralized configuration through `src/config.py`
- Machine learning components organized in `src/ml/` with clear separation
- Data collection handled through specialized collectors in `scripts/collectors/`
- External API integration using adapter pattern

### Testing Strategy
- Unit tests for all business logic in `tests/unit/`
- Integration tests for database and external APIs in `tests/integration/`
- End-to-end tests for complete workflows in `tests/e2e/`
- Performance tests in `tests/performance/`
- **Current Test Count**: 630 tests across multiple test files
- Test coverage target: 80%+ (current: 96.35%)

### Configuration Management
- Centralized configuration in `src/config.py` (461 lines)
- Environment-specific configs: `.env.dev`, `.env.ci`, `.env.production`
- FotMob API configuration for external data sources
- Database connection settings with async support

### Error Handling
- Comprehensive error handling in API layer
- Structured logging for debugging and monitoring
- Graceful degradation for external API failures
- Health checks for system status monitoring

## Monitoring and Observability

### Monitoring Stack
The system includes comprehensive monitoring and observability:

- **Prometheus** (http://localhost:9090): Metrics collection and storage
- **Grafana** (http://localhost:3000): Visualization dashboard (admin/admin123)
- **Alertmanager**: Alert routing and notification

### Key Metrics

| Metric Type | Description | Dashboard Location |
|-------------|-------------|-------------------|
| **API Performance** | QPS, P95 latency, error rate | Grafana → API Performance |
| **Business Metrics** | Prediction request rate, model inference time, accuracy | Grafana → Business Metrics |
| **System Resources** | CPU, memory, disk usage | Grafana → System Overview |
| **Cache Health** | Redis hit rate, memory usage | Grafana → Cache Health |

### Alert Rules
- **API error rate > 5%**: Triggers warning after 2 minutes
- **P95 latency > 1s**: Triggers warning after 5 minutes
- **System resources > 80%**: Triggers warning after 10 minutes
- **Redis hit rate < 50%**: Triggers warning after 15 minutes

### Accessing Monitoring
```bash
# Via Docker
docker-compose exec app python scripts/predict_match_v2.py --home "Man Utd" --away "Arsenal"

# Grafana Dashboard
open http://localhost:3000  # admin/admin123

# Prometheus Metrics
open http://localhost:9090
```

## Key Technologies

- **FastAPI**: High-performance async web framework
- **PostgreSQL**: Primary database with JSON support
- **XGBoost 2.0+**: Machine learning models for prediction
- **SHAP 0.50+**: Model explainability and interpretation
- **Docker**: Containerization and orchestration
- **pytest 7.4+**: Testing framework with high coverage
- **Python 3.11+**: Modern Python with async support
- **Prometheus**: Metrics collection
- **Grafana**: Visualization
- **Redis**: Caching and queue management
- **MCP (Model Context Protocol)**: 5 core servers for enhanced database and system integration
- **Claude Skills**: Professional-grade Python code quality and machine learning engineering tools

## Data Sources and Integration

### FotMob API Integration
- **Enhanced Collector**: L2级别数据提取 in `scripts/collectors/enhanced_fotmob_collector.py`
- **Data Types**: Odds数据, 球员评分, 深度统计
- **Authentication**: Configurable headers for API access
- **Rate Limiting**: Built-in request throttling

### Data Processing Pipeline
- **Feature Engineering**: Advanced statistical calculations
- **Historical Analysis**: Head-to-head (H2H) calculations
- **Venue Separation**: Home/away performance analysis
- **Real-time Processing**: Async data collection and processing

## Machine Learning Features

### Phase 5 Advanced Features
- **Current Development**: Focused on advanced feature engineering
- **Key Problems Solved**:
  - Venue-separated rolling statistics (解决主客场偏见)
  - Historical head-to-head statistics (H2H记录和"克星"效应)
  - League form analysis (联赛形态特征 - 积分替代进球数)

### Model Performance
- **Target Accuracy**: 65%+ (from current 67.2% in v2.0)
- **Response Time**: <100ms (single prediction)
- **Cache Hit Rate**: >80%
- **Feature Dimensions**: 12+ professional features
- **Current Architecture**: Service Layer v2.0 + ML Inference Layer (production ready)

## Quality Assurance

### Testing Infrastructure
- **Coverage**: 96.35% target coverage (630 tests passing)
- **CI/CD**: GitHub Actions with local verification via `ci-verify.sh`
- **Quality Tools**: black, flake8, mypy, bandit, radon, vulture
- **Security**: Automated vulnerability scanning

### Development Workflow
- **Pre-commit Checks**: `make ci` for quality validation
- **Local Verification**: `./ci-verify.sh` for CI simulation
- **Docker Support**: Complete containerized development environment
- **Monitoring**: Real-time CI status monitoring

## Testing and Quality Assurance

### Test Execution
```bash
# Run tests with coverage
make test                    # Run unit tests (fast)
make coverage               # Run tests with coverage report
make ci                     # Complete quality check + tests

# Docker-based testing (v2.0)
./scripts/docker-manager.sh test              # Run tests in containers
./scripts/docker-manager.sh quality           # Run quality checks

# Individual test execution
pytest tests/v2/test_inference_logic.py::test_single_match_prediction -v
pytest tests/v2/test_health_schema.py::test_health_check_response -v
pytest tests/ -k "smoke" -v

# Run specific test categories
pytest tests/v2/ -v             # V2 tests only
pytest tests/unit/ -v           # Unit tests only
pytest tests/integration/ -v    # Integration tests only
pytest tests/e2e/ -v            # End-to-end tests only
pytest tests/performance/ -v    # Performance tests only

# Python testing with skills integration
python -m pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
```

### Quality Checks
```bash
make format                 # Format code with black
make lint                   # Run flake8 linting
make typecheck              # Run mypy type checking
make security               # Run bandit security scan
make quality                # Run all quality checks

# Advanced quality tools
make complexity             # Code complexity analysis with radon
make deadcode               # Dead code detection with vulture

# Python code quality Claude Skills
make python-quality-check   # Run comprehensive code quality analysis
make python-quality-format  # Auto-format code with quality standards
make python-quality-fix     # Auto-fix common code quality issues
make python-quality-score   # Get code quality score and recommendations
```

### Local CI Validation
```bash
./ci-verify.sh             # Complete local CI verification (141 lines)
# Includes: venv rebuild, Docker stack startup, test execution with coverage validation
```

## Working with the Codebase

### Development Workflow
```bash
# Quick start
make dev                   # Complete development environment setup
make test                  # Verify tests pass
make ci                    # Run quality checks before committing
```

### Adding New Features
1. **ML Features**: Add feature engineering in `src/ml/features/`
2. **API Endpoints**: Create new routes in `src/api/`
3. **Data Collection**: Add collectors in `scripts/collectors/`
4. **Configuration**: Update settings in `src/config.py`
5. **Testing**: Add tests in appropriate `tests/` subdirectory
6. **Validation**: Run `make ci` before submitting
7. **PR**: Use `.github/PULL_REQUEST_TEMPLATE.md` for structured PRs

### Machine Learning Development
1. **Feature Engineering**: Work with `src/ml/features/`
2. **Model Updates**: Modify models in `src/ml/models/`
3. **Training**: Use `scripts/process_offline_features_full.py`
4. **Validation**: Run `scripts/canary_simple.py` for testing

### Data Collection and Processing
```bash
# Data collection scripts
python scripts/collectors/enhanced_fotmob_collector.py  # L2 data extraction
python scripts/collectors/odds_collector.py             # Odds data
python scripts/process_offline_features_full.py         # Feature processing

# Model management scripts
python scripts/train_model_from_csv.py                  # Train model from CSV data
python scripts/test_real_model.py                       # Test real model performance
```

### Environment Setup

#### 环境文件说明
项目提供多个环境配置文件：
- `.env.example` - 配置模板和说明
- `.env.dev` - 本地开发环境配置
- `.env.ci` - CI/CD环境配置
- `.env.production` - 生产环境配置

#### 核心环境变量
```bash
# Database Configuration
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=football_prediction_dev
export DB_USER=football_user
export DB_PASSWORD=football_pass

# Redis Configuration (v2.0)
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=0

# FotMob API (production)
export FOTMOB_X_MAS_HEADER="your_header"
export FOTMOB_X_FOO_HEADER="your_header"

# Service Configuration (v2.0)
export INFERENCE_SERVICE_V2_ENABLED=true
export COLLECTION_SERVICE_ENABLED=true
export EXPLAINABILITY_SERVICE_ENABLED=true
```

### Dependency Management
```bash
# Install dependencies
make install                    # Install all dependencies including dev deps
make lock                       # Generate dependency lock file
pip install -r requirements.txt                # Production dependencies
pip install -r requirements-dev.txt           # Development dependencies

# Development dependencies include:
# - pytest 7.4+ (testing)
# - black, flake8, mypy, bandit (code quality)
# - coverage (test coverage)
# - pre-commit (git hooks)
```

## CLI Tools and Usage

### v2.0 Prediction CLI
```bash
# Single match prediction
python scripts/predict_match_v2.py --home "Manchester United" --away "Arsenal"

# Batch prediction
python scripts/predict_match_v2.py --batch matches.json

# Use specific model version
python scripts/predict_match_v2.py --home "Chelsea" --away "Liverpool" --model xgboost_v2

# Example output:
🏟️  比赛: Manchester United vs Arsenal
📅  日期: 2024-01-15

📊 预测概率:
主胜 (HOME) : 65.2% |███████████████████████████████████░░░|
平局 (DRAW) : 22.1% |███████████████░░░░░░░░░░░░░░░░░░░░░░|
客胜 (AWAY) : 12.7% |███████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░|

🎯 预测结果: HOME_WIN
💡 置信度: 65.2%
📈 模型版本: xgboost_v2
```

### Docker Management Script (v2.0)
```bash
# Environment management
./scripts/docker-manager.sh dev                    # Start development environment
./scripts/docker-manager.sh prod                   # Start production environment
./scripts/docker-manager.sh health                 # Health check all services

# Development features
./scripts/docker-manager.sh dev --collectors       # Start with data collectors
./scripts/docker-manager.sh dev --debug           # Enable debug mode
./scripts/docker-manager.sh dev --reload          # Enable hot reload

# Service management
./scripts/docker-manager.sh logs -f app           # Follow application logs
./scripts/docker-manager.sh shell                 # Enter container shell
./scripts/docker-manager.sh restart               # Restart all services

# Testing and quality
./scripts/docker-manager.sh test                  # Run test suite
./scripts/docker-manager.sh quality               # Run quality checks

# Cleanup
./scripts/docker-manager.sh clean                 # Clean unused resources
./scripts/docker-manager.sh clean --all           # Clean all resources
```

### Model Performance and Features

#### Current Performance Metrics
- **Target Accuracy**: 65%+ (from current 67.2% in v2.0)
- **Response Time**: <100ms (single prediction)
- **Cache Hit Rate**: >80%
- **Feature Dimensions**: 12+ professional features

#### Advanced Feature Engineering (v2.0)
- **Venue-separated rolling statistics**: 解决主客场偏见
- **Historical head-to-head (H2H) analysis**: H2H记录和"克星"效应
- **League form analysis**: 联赛形态特征 - 积分替代进球数
- **Real-time feature processing**: 异步特征计算和缓存

## Contribution Workflow

### Pull Request Process
This project uses a structured PR template (`.github/PULL_REQUEST_TEMPLATE.md`):

1. **PR Types**: feat, fix, docs, style, refactor, perf, test, build/ci, security, chore
2. **Required Checks**:
   - Unit tests passed
   - Integration tests passed
   - Manual testing completed
   - Test coverage ≥ 80%
   - Documentation updated
   - No merge conflicts
   - All CI checks passed
   - Self-review completed

3. **Review Process**:
   - Use PR template for structured descriptions
   - Include implementation details
   - Add performance impact assessment
   - Document security considerations
   - Update relevant documentation

### CI/CD Pipeline
The project uses GitHub Actions for CI/CD (see `.github/workflows/`):
- Automated testing on PR
- Code quality checks
- Security scanning
- Coverage reporting
- Docker build and push

## Code Examples

### Configuration Usage
```python
# 推荐使用新的安全配置系统
from src.config_secure import get_settings

settings = get_settings()
db_url = settings.database.get_connection_string()
headers = settings.fotmob_api.get_headers()
```

### ML Feature Engineering
```python
from src.ml.features.advanced_feature_transformer import AdvancedFeatureTransformer

transformer = AdvancedFeatureTransformer()
features = transformer.transform_match_features(match_data)
h2h_features = transformer.calculate_h2h_features(team_a_id, team_b_id)
```

### Service Layer Usage
```python
from src.services.inference_service_v2 import InferenceServiceV2

service = InferenceServiceV2()
result = await service.predict_single_match(home_team, away_team)
```

### MCP Database Access
```python
# Direct MCP tool usage (automatic routing through mcp_servers/)
from mcp_context7 import execute_sql

result = await execute_sql("SELECT * FROM matches LIMIT 10")

# Enhanced MCP operations
from mcp_postgres import execute_sql, get_table_info
from mcp_redis import redis_get, redis_set

# Database operations
matches = await execute_sql("SELECT * FROM matches WHERE date > '2024-01-01'")
table_schema = await get_table_info("teams")

# Redis caching operations
cache_result = await redis_get("prediction:cache:123")
await redis_set("prediction:cache:123", json.dumps(prediction_data), ttl=3600)
```

## Common Issues

### Database Connection
```bash
docker-compose exec db pg_isready -U football_user
docker-compose down && docker-compose up -d
docker-compose logs db
```

### Test Failures
```bash
pytest tests/unit/api/test_simple_api.py::test_health_check -v -s
make clean && make install
```

### Docker Issues
```bash
docker system prune -f
docker-compose down --rmi all
docker-compose up --build
```

### Environment Issues
```bash
make env-check    # Check environment setup
make clean && make install  # Reset environment

# MCP server issues
./scripts/mcp_manager.sh restart                   # Restart MCP servers
./scripts/test_mcp_servers.sh                      # Test MCP connectivity
./scripts/mcp_validation_report.py                 # Generate MCP validation report

# Python quality issues
make python-quality-check                          # Run comprehensive quality analysis
make python-quality-fix                            # Auto-fix common issues
```

## MCP (Model Context Protocol) Integration

### Available MCP Servers
The project includes 5 core MCP servers for enhanced functionality:

1. **PostgreSQL MCP Server**: Database operations and schema management
2. **Redis MCP Server**: Caching and queue operations
3. **Filesystem MCP Server**: File operations and project structure management
4. **Context7 MCP Server**: Documentation and library integration
5. **System Monitor MCP Server**: Performance monitoring and metrics

### MCP Usage Examples
```bash
# Start MCP servers
./scripts/mcp_manager.sh start

# Development mode with MCP
./scripts/enhanced_mcp_manager.sh dev

# Test MCP functionality
./scripts/test_mcp_functionality.py

# Validate MCP configuration
python scripts/mcp_validation_report.py
```

---

**更新时间**: 2025-01-18 | **分支**: main | **版本**: v2.0.0-Stable

**重要说明**:
- 项目已升级到v2.0稳定版本，采用全新Service Layer架构，完全容器化部署，生产就绪
- 新增了MCP (Model Context Protocol) 集成，提供5个核心MCP服务器
- 集成了完整的Prometheus/Grafana监控栈
- 实现了凯利公式金融级风控系统
- 测试覆盖率达到96.35%，系统性能优异