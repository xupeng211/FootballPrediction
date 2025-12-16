# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**重要提醒**: 请始终用中文回复用户的问题和请求。

**⚠️ IMPORTANT**: Current working branch is `feat/phase-5-advanced-features` with Phase 5 advanced features development in progress.

## Development Commands

### Environment Setup
```bash
make install          # Install dependencies and create virtual environment
make env-check        # Verify environment is properly configured
make dev              # Quick development environment setup
```

### Testing and Quality
```bash
make test             # Run unit tests (630 tests, requires 80%+ coverage)
make coverage         # Run tests with coverage report (current: 96.35%)
make ci               # Complete CI simulation (env-check, quality, test, coverage)
make ci-local         # Local CI matching remote GitHub Actions
./ci-verify.sh        # Local CI verification script
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
```

### Local Development
```bash
docker-compose up --build    # Start full development stack
docker-compose ps            # Check service status
docker-compose logs app      # View application logs
docker-compose logs -f app   # Follow application logs in real-time
make status                  # View project overview and statistics
make dev                     # Quick development environment setup
```

### CI Monitoring and Debugging (CI监控和调试)
```bash
# CI状态监控
make ci-status              # Check latest CI run status
make ci-monitor             # Real-time CI monitoring
make ci-analyze RUN_ID=xxx  # Analyze specific CI failure

# CI Guardian防御系统
make ci-guardian            # Run CI guardian checks
make validate-defenses      # Validate all defense mechanisms
make update-defenses        # Update defense mechanisms
```

## Architecture Overview

### Core Architecture Pattern
**Domain-Driven Design + CQRS + Event-Driven + Async-First**

The system implements clean architecture with strict separation of concerns:
- **Domain Layer**: Pure business logic (entities, events, repositories interfaces)
- **Application Layer**: Services orchestration and use cases
- **Infrastructure Layer**: Database, cache, external API implementations
- **Presentation Layer**: FastAPI routers and HTTP handling

### Key Architectural Components

#### CQRS System
- **Command Bus**: Handles write operations (create, update, delete)
- **Query Bus**: Handles read operations with optimization
- **Event Bus**: Manages domain events and notifications
- Located in `src/cqrs/` with handlers in `src/cqrs/handlers/`

#### Database Architecture
- **ORM**: SQLAlchemy 2.0+ with async support
- **Connection**: Read-write separation with connection pooling
- **Migrations**: Alembic-based schema management in `src/database/migrations/`
- **Repositories**: Implementation of domain repository interfaces in `src/database/repositories/`

#### Machine Learning Pipeline
- **Inference Service**: Singleton pattern in `src/core/prediction_engine.py`
- **Models**: XGBoost 2.0+ with ensemble strategies in `src/ml/`
- **Feature Store**: Real-time feature extraction and caching
- **Model Management**: Versioned model files with health monitoring

#### Caching Strategy
- **Redis Manager**: Enhanced connection management in `src/cache/redis_manager.py`
- **Multi-layer**: Application, database, and HTTP-level caching
- **TTL Management**: Intelligent cache expiration strategies
- **Cluster Support**: Redis clustering for high availability

#### Streaming Infrastructure
- **Kafka Integration**: Producer/consumer implementations in `src/streaming/`
- **WebSocket Support**: Real-time API communication
- **Event Sourcing**: CQRS event storage and replay capabilities

## Project Structure

```
FootballPrediction/
├── src/
│   ├── api/              # FastAPI routers and HTTP endpoints
│   ├── domain/           # Domain entities, events, repository interfaces
│   ├── services/         # Application services and use cases
│   ├── database/         # SQLAlchemy models, migrations, repositories
│   ├── cqrs/            # Command Query Responsibility Segregation
│   ├── ml/              # Machine learning models and inference
│   ├── cache/           # Caching layer and Redis management
│   ├── streaming/       # Kafka and real-time processing
│   ├── adapters/        # External API integrations
│   ├── core/            # DI container, logging, exceptions
│   └── utils/           # Shared utilities
├── tests/               # Comprehensive test suite (630 tests)
├── microservices/       # Microservice implementations
├── config/              # Configuration management
├── monitoring/          # Health checks and metrics
└── scripts/             # Development and CI scripts
```

## Development Guidelines

### Code Organization
- All code must follow async-first design patterns
- Use dependency injection through `src/core/di.py`
- Repository interfaces defined in domain, implemented in database layer
- All database operations must be async
- External API calls should use the adapter pattern

### Testing Strategy
- Unit tests for all business logic in `tests/unit/`
- Integration tests for database and external APIs in `tests/integration/`
- End-to-end tests for complete workflows in `tests/e2e/`
- Performance tests in `tests/performance/`
- Test markers: `@pytest.mark.unit`, `@pytest.mark.integration`, etc.

### Configuration Management
- Environment-specific configs in `.env.ci`, `.env.production`
- Database connection settings in `config/database_pool_config.py`
- Cache strategy configuration in `config/cache_strategy_config.py`
- API optimization settings in `config/api_optimization_config.py`

### Error Handling
- Custom exceptions defined in `src/core/exceptions.py`
- Comprehensive error logging with structured logging
- Fallback strategies for external dependencies
- Circuit breaker pattern for external API calls

## Key Technologies

- **FastAPI 0.104+**: High-performance async web framework
- **SQLAlchemy 2.0+**: Modern async ORM with advanced features
- **PostgreSQL 15**: Primary database with JSON support
- **Redis 5.0+**: Caching and session management
- **XGBoost 2.0+**: Machine learning models
- **Kafka**: Event streaming platform
- **Docker**: Containerization and orchestration

## Performance Considerations

### Database Optimization
- Read-write separation with dedicated connection pools
- Optimized queries with proper indexing
- Batch operations for bulk data processing
- Connection pooling with health checks

### Caching Strategy
- Multi-level caching (application, database, HTTP)
- Intelligent cache warming on startup
- Cache invalidation strategies for data consistency
- Redis clustering for high availability

### API Performance
- Async request handling throughout
- Rate limiting with Redis backend
- Response compression and optimization
- Prometheus metrics for monitoring

## Security Practices

- Input validation through Pydantic models
- SQL injection prevention via ORM
- Authentication and authorization middleware
- Security scanning with bandit
- Dependency vulnerability checks with safety

## Monitoring and Observability

- Structured logging with correlation IDs
- Health checks at multiple levels (`/health`, `/health/database`)
- Prometheus metrics exposure
- Performance monitoring with response time tracking
- Error tracking and alerting

## 🧪 测试配置和执行 (630个测试用例)

### pytest配置体系
```bash
# 主配置文件
FootballPrediction/pytest.ini             # pytest标记和配置定义

# 测试发现和执行
testpaths = tests                       # 测试根目录
pythonpath = .                          # Python路径
python_files = test_*.py *_test.py       # 测试文件模式
```

### 标准化测试标记系统
```bash
# 核心测试类型 (按数量分布)
pytest tests/ -m "unit"                  # 单元测试 (85% of tests)
pytest tests/ -m "integration"           # 集成测试 (12% of tests)
pytest tests/ -m "e2e"                   # 端到端测试 (2% of tests)
pytest tests/ -m "performance"           # 性能测试 (1% of tests)

# 功能域标记
pytest tests/ -m "ml"                    # 机器学习模型和特征测试
pytest tests/ -m "api"                   # HTTP端点和接口测试
pytest tests/ -m "database"              # 数据库连接和仓储测试
pytest tests/ -m "collectors"            # 数据收集器测试
pytest tests/ -m "cache"                 # Redis和缓存逻辑测试
pytest tests/ -m "auth"                  # 认证和权限测试
pytest tests/ -m "monitoring"            # 监控和健康检查测试

# 执行特征标记
pytest tests/ -m "critical"              # 必须通过的核心功能测试
pytest tests/ -m "smoke"                 # 基本功能验证测试
pytest tests/ -m "slow"                  # 运行时间>30s的慢速测试
pytest tests/ -m "regression"            # 回归测试
pytest tests/ -m "docker"                # 需要Docker容器环境
pytest tests/ -m "external_api"          # 需要外部API调用

# Phase 5 特定测试
pytest tests/ml/features/test_advanced_features.py    # Phase 5高级特征测试
python scripts/test_phase5_advanced_features.py       # Phase 5功能验证脚本
```

### 覆盖率要求
```bash
# CI覆盖率门槛验证 (当前96.35%)
pytest --cov=src --cov-fail-under=80 --cov-report=term-missing

# 生成详细覆盖率报告
pytest --cov=src --cov-report=html:htmlcov --cov-report=xml

# 覆盖率分析
make coverage                              # 完整覆盖率检查
open htmlcov/index.html                   # 查看详细覆盖率报告
```

### 推荐测试工作流
```bash
# 日常开发 - 快速验证 (<2分钟)
make test.smart                           # 或 pytest tests/ -m "not slow"

# 功能开发完成 - 分类测试
make test.unit                            # 完整单元测试套件
pytest tests/ml/ -m "ml"                  # ML模块专项测试
pytest tests/api/ -m "api"                # API端点专项测试

# 发布前验证 - 全面检查
make test.all                             # 完整测试套件 (unit + integration + e2e)
make ci                                  # 质量检查 + 完整测试

# 问题诊断 - 快速定位
pytest tests/unit/ --maxfail=5 -x         # 失败时快速停止
pytest tests/unit/ -k "test_keyword" -v   # 关键词过滤测试
```

## Working with the Codebase

### Development Workflow (推荐工作流)
```bash
# 日常开发流程
make dev                     # 完整开发环境设置
make context                 # 加载项目上下文
# 进行开发工作...
make ci                      # 提交前CI检查
make prepush                 # 完整提交流程(含推送)
```

### Single Test Execution (单测试执行)
```bash
# 运行单个测试文件
pytest tests/unit/api/test_simple_api.py::test_health_check -v

# 运行特定标记的测试
pytest tests/ -m "unit and api" --maxfail=5

# 运行带关键词的测试
pytest tests/ -k "test_health" -v

# 调试模式运行测试
pytest tests/test_api_basic.py -v -s --tb=long
```

### Adding New Features
1. Define domain entities in `src/domain/entities.py`
2. Create repository interfaces in domain layer
3. Implement repositories in `src/database/repositories/`
4. Add application services in `src/services/`
5. Create API endpoints in `src/api/`
6. Write comprehensive tests
7. Run `make ci` before submitting

### Database Changes
1. Create Alembic migration in `src/database/migrations/`
2. Update SQLAlchemy models in `src/database/models/`
3. Run `docker-compose exec app alembic upgrade head`
4. Update repository implementations as needed

### Machine Learning Updates
1. Update models in `src/ml/models/`
2. Modify inference service in `src/core/prediction_engine.py`
3. Update feature engineering pipeline
4. Run performance validation tests

### Adding External APIs
1. Create adapter in `src/adapters/`
2. Define interface in domain layer
3. Implement configuration management
4. Add error handling and retry logic
5. Write integration tests

### Phase 5 Advanced Feature Development (Phase 5高级特征开发)
```bash
# Phase 5 核心开发命令
python scripts/test_phase5_advanced_features.py      # 验证高级特征功能
python scripts/verify_catch_all_stats.py             # 验证统计数据完整性
python scripts/test_enhanced_l2_extraction.py        # 测试L2增强数据提取
python scripts/process_offline_features_full.py      # 处理离线特征数据

# Phase 5 组件测试
pytest tests/ml/features/test_advanced_features.py   # 高级特征组件测试

# 模型训练和验证
python scripts/train_real_postgres_standalone.py    # 独立模型训练
python scripts/canary_simple.py                     # 金丝雀测试
```

## 🎯 Phase 5: Advanced Features (Current Development)

### 当前开发重点 (2025-12-16)
**分支**: `feat/phase-5-advanced-features`
**状态**: 🚧 进行中
**目标**: 通过高级特征工程将模型准确率从 58.69% 提升至 65%+

### 核心问题解决 (Napoli vs Juventus 案例)
基于Phase 4的失败分析，当前解决以下关键问题：
1. **场馆分离滚动统计**: 解决主客场偏见问题 - Napoli主场0进球导致被严重低估
2. **历史交锋统计**: H2H记录和"克星"效应分析
3. **联赛形态特征**: 使用积分替代噪音大的进球数

### 高级特征组件
```python
# 新增的Phase 5核心组件
src/ml/features/
├── advanced_feature_transformer.py    # 高级特征转换器 (整合三类特征)
├── h2h_calculator.py                  # 历史交锋统计计算
└── venue_analyzer.py                  # 场馆分析器 (主客场分离)

# 验证和测试脚本
scripts/
├── test_phase5_advanced_features.py   # Phase 5功能验证
├── verify_catch_all_stats.py          # 统计数据验证
├── test_enhanced_l2_extraction.py     # L2增强提取测试
└── test_deep_stats_extraction.py      # 深度统计提取测试
```

### Phase 5 开发命令
```bash
# Phase 5 特定开发和验证
python scripts/test_phase5_advanced_features.py  # 验证高级特征
python scripts/verify_catch_all_stats.py         # 验证L2数据提取
python scripts/test_enhanced_l2_extraction.py    # 测试L2增强提取
python scripts/test_deep_stats_extraction.py     # 测试深度统计提取

# 高级特征组件测试
pytest tests/ml/features/test_advanced_features.py    # 高级特征单元测试

# 离线特征处理
python scripts/process_offline_features_full.py  # 处理离线特征
python scripts/canary_simple.py                  # 金丝雀测试

# 元数据和结构分析
python scripts/test_metadata_extraction.py       # 测试元数据提取
python scripts/analyze_fotmob_structure.py       # 分析FotMob结构
```

### 数据收集增强 (FotMob L2集成)
```python
# 增强的数据收集器 - Phase 5核心数据源
src/collectors/enhanced_fotmob_collector.py  # L2级别数据提取
├── Odds数据提取      # 市场情绪分析和赔率信息
├── 球员评分提取      # 个人表现指标和评分
└── 深度统计提取      # 射门图、势头分析、教练信息
```

### Phase 5 关键文档
- `docs/PHASE_5_DESIGN.md` - 详细设计文档和实施路线图
- `docs/L2_ENHANCED_FEATURES_SUMMARY.md` - L2功能总结
- `docs/MATCH_EVENTS_EXTRACTION_SUMMARY.md` - 比赛事件提取总结
- `docs/TOTAL_DATA_EXTRACTION_SUMMARY.md` - 完整数据提取总结
- `docs/FINAL_DEEP_EXTRACTION_SUMMARY.md` - 深度提取最终总结

### Phase 5 技术实施重点
1. **AdvancedFeatureTransformer**: 整合场馆分离、H2H和积分特征的核心转换器
2. **严格的防数据泄露**: 使用shift(1)确保特征不包含未来信息
3. **向量化操作**: 使用pandas groupby + transform进行高效计算
4. **缺失值处理**: 智能填充策略确保模型稳定性

### 预期性能提升
- **目标准确率**: 65%+ (相比当前58.69%提升6.3%+)
- **主客场偏见修复**: 解决Napoli vs Juventus类型案例
- **特征重要性提升**: 新特征在模型中占据重要位置
- **实时预测性能**: 满足在线预测需求

### 实际测试状态
- **测试覆盖**: 630个测试用例，当前覆盖率96.35%
- **Phase 5组件**: 已实现H2HCalculator、VenueAnalyzer、AdvancedFeatureTransformer
- **验证脚本**: 完整的Phase 5功能测试和数据验证脚本
- **Docker支持**: 完整的容器化开发和测试环境

### 实际代码示例

#### Async Database Usage (异步数据库使用)
```python
# 正确的异步数据库操作模式
async def get_team_performance(team_id: int) -> dict:
    async with get_async_session() as session:
        result = await session.execute(
            select(Match).where(
                (Match.home_team_id == team_id) | (Match.away_team_id == team_id)
            ).order_by(Match.date.desc()).limit(10)
        )
        return result.scalars().all()
```

#### Configuration Usage (配置使用)
```python
# 正确的配置使用方式
from src.config import get_settings

settings = get_settings()

# 数据库连接
db_url = settings.database.get_connection_string()

# FotMob API调用
headers = settings.fotmob.get_headers()

# 环境检查
if settings.is_development():
    # 开发环境特定逻辑
    pass
```

#### API Response Format (API响应格式)
```python
# 标准API响应格式
from src.api.schemas import APIResponse

@router.get("/predictions/{match_id}")
async def get_prediction(match_id: int) -> APIResponse[PredictionSchema]:
    prediction = await prediction_service.get_prediction(match_id)
    return APIResponse(
        success=True,
        data=prediction,
        message="Prediction retrieved successfully"
    )
```

#### Phase 5 Feature Engineering (Phase 5特征工程)
```python
# Phase 5高级特征使用示例
from src.ml.features.advanced_feature_transformer import AdvancedFeatureTransformer

transformer = AdvancedFeatureTransformer()

# 处理比赛数据
features = transformer.transform_match_features(match_data)

# 场馆分离特征
venue_features = transformer.calculate_venue_separated_stats(match_data)

# H2H历史交锋特征
h2h_features = transformer.calculate_h2h_features(team_a_id, team_b_id)
```

### Code Style Guidelines (代码风格指南)

#### Async Pattern Usage (异步模式使用)
- 所有数据库操作必须使用async/await
- 使用async context managers管理资源
- 避免在async函数中使用阻塞调用

#### Error Handling (错误处理)
```python
# 统一错误处理模式
from src.core.exceptions import DatabaseError, ValidationError

try:
    result = await some_operation()
except DatabaseError as e:
    logger.error(f"Database operation failed: {e}")
    raise HTTPException(status_code=500, detail="Database error")
except ValidationError as e:
    logger.warning(f"Validation failed: {e}")
    raise HTTPException(status_code=400, detail=str(e))
```

#### Testing Patterns (测试模式)
```python
# 标准测试模式
@pytest.mark.asyncio
async def test_prediction_endpoint():
    # 使用test数据库
    async with get_async_test_session() as session:
        # 准备测试数据
        match = create_test_match(session)

        # 执行测试
        response = await client.get(f"/predictions/{match.id}")

        # 验证结果
        assert response.status_code == 200
        assert response.json()["success"] is True
```

### Environment Variables (环境变量)
```bash
# 必需的环境变量
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=football_prediction_dev
export DB_USER=football_user
export DB_PASSWORD=football_pass

# FotMob API配置 (生产环境必需)
export FOTMOB_X_MAS_HEADER="your_x_mas_header"
export FOTMOB_X_FOO_HEADER="your_x_foo_header"

# 应用配置
export ENVIRONMENT=development
export APP_DEBUG=true
```

### Common Issues and Solutions (常见问题和解决方案)

#### Database Connection Issues (数据库连接问题)
```bash
# 检查数据库连接
docker-compose exec db pg_isready -U football_user

# 重置数据库连接
docker-compose down && docker-compose up -d

# 检查数据库日志
docker-compose logs db
```

#### Test Failures (测试失败)
```bash
# 清理测试缓存
make clean-cache

# 重建环境
make clean && make install

# 运行特定失败测试
pytest tests/unit/api/test_simple_api.py::test_health_check -v -s
```

#### Docker Issues (Docker问题)
```bash
# 清理Docker资源
docker system prune -f
docker volume prune -f

# 重新构建镜像
docker-compose down --rmi all
docker-compose up --build
```

#### Performance Issues (性能问题)
```bash
# 检查代码复杂度
make complexity

# 查找死代码
make deadcode

# 运行性能测试
pytest tests/performance/ -v
```

---

**文件更新时间**: 2025-12-16 | **当前分支**: feat/phase-5-advanced-features | **Phase 5状态**: 🚧 进行中