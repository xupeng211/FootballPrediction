# 📋 足球预测系统测试策略文档

## 📖 文档信息

### 文档目的
本文档定义了足球预测系统的完整测试策略，确保数据采集、清洗、存储、特征工程、模型预测全链路的正确性和可靠性。通过分层测试架构和自动化CI/CD流程，保障系统的可维护性、可扩展性和稳定性。

### 适用范围
- **项目名称**: FootballPrediction - 足球预测系统
- **技术栈**: FastAPI + PostgreSQL + Redis + MLflow + Prometheus + Grafana
- **架构模式**: Bronze→Silver→Gold数据分层 + 特征仓库 + ML预测服务
- **部署方式**: Docker容器化 + GitHub Actions CI/CD

### 版本信息
- **文档版本**: v1.0
- **创建日期**: 2025-09-11
- **最后更新**: 2025-09-11
- **责任人**: 数据架构优化工程师
- **审核人**: 测试架构师

---

## 🎯 测试总体目标

### 核心质量目标
1. **数据完整性保障**: 确保数据采集、清洗、存储、预测全链路的正确性
2. **系统稳定性确保**: 保证系统的可维护性、可扩展性和7x24小时稳定运行
3. **CI/CD质量提升**: 提高CI/CD流程中的代码质量和发布可靠性
4. **性能指标达成**: 确保系统满足预期的性能和响应时间要求

### 测试质量指标
| 质量维度 | 目标指标 | 监控方法 | 责任人 |
|---------|---------|---------|--------|
| **代码覆盖率** | ≥80% | pytest-cov + CI检查 | 开发团队 |
| **关键路径覆盖率** | ≥95% | 专项覆盖率检查 | 架构师 |
| **API可用性** | ≥99.5% | Prometheus监控 | 运维团队 |
| **数据质量正确率** | ≥95% | Great Expectations | 数据团队 |
| **预测准确率** | ≥基准线 | MLflow模型监控 | ML团队 |

---

## 🗂️ 测试套件分类与执行

- **单元测试目录**: `tests/unit/`
- **集成测试目录**: `tests/integration/`
- **标记约定**: `unit` 代表纯单测（无外部依赖），`integration` 代表依赖数据库/API/Kafka 等外部服务，`slow` 用于标记 >100ms 的慢测试。
- **Slow 场景说明**: Redis 健康检查相关用例（如 `tests/unit/api/test_api_health_enhanced.py`）由于真实等待成本，已标记为 `@pytest.mark.slow`，默认不随快速单测一起执行。

```bash
# 快速单测（排除 slow）
pytest tests/unit -m "unit and not slow"

# 单独运行慢测试（包括 Redis 健康检查等）
pytest tests/unit -m "slow"
```


```bash
# 仅跑单元测试（快速反馈）
pytest tests/unit -m "unit and not slow"

# 跑集成测试
pytest tests/integration -m "integration"
```

## CI/CD 流程

- **Pull Request（Fast）**: GitHub Actions 触发 `unit-fast` job，执行 `make check-deps` + 安装依赖，并运行 `pytest tests/unit -m "unit and not slow" --maxfail=1 --disable-warnings --cov=src --cov-report=term --cov-report=xml --cov-fail-under=0`，聚焦快速反馈，不对覆盖率设门槛。
- **Push 到 main（Slow）**: 触发 `slow-suite` job，复用相同的依赖初始化后运行慢测试 (`pytest tests/unit -m "slow" --cov=src --cov-append --cov-fail-under=0`) 与集成测试 (`pytest tests/integration -m "integration" --cov=src --cov-append --cov-fail-under=0`)，仅验证逻辑完整性，不检查覆盖率红线。
- **定时 Nightly**: 同样由 `slow-suite` job 在 `schedule` 触发，自动将 `--cov-fail-under` 切换回 `70` 并生成 `coverage.txt` + `docs/CI_REPORT.md`，严格卡住覆盖率门槛并回写报告。
- **本地复现**: 与 CI 保持一致，先执行 `make check-deps` + `pip install -r requirements.txt -r requirements-dev.txt`，随后按需运行快速或慢测试命令。

- **Nightly 报告**: Nightly job 会解析测试日志并更新 `docs/CI_REPORT.md`，并自动提交到仓库；报告包含最新的快/慢测试覆盖率总览（TOTAL 覆盖率）、趋势表与折线图，并附带覆盖率一致性验证结果，若覆盖率低于 70% 即失败。

## ⚡ 测试性能优化

- Mock 掉阻塞性的 `asyncio.sleep` / `time.sleep` 调用，覆盖 `tests/unit/utils/test_retry.py`, `tests/unit/cache/test_ttl_cache.py`, `tests/unit/models/test_prediction_service_caching.py` 等核心耗时用例，保持原有断言逻辑不变。
- 单元测试套件运行时间显著下降（`pytest tests/unit -m "unit and not slow"`），CI 沙箱环境下可稳定完成，无需额外等待窗口。

## 🧩 依赖校验

- 在本地或 CI 执行测试前运行 `make check-deps`，快速确认当前环境已安装 `requirements*.txt` 中声明的依赖。
- 脚本会列出缺失项并提示安装命令（例如 `[MISSING DEP] prometheus_client is not installed. Run: pip install prometheus_client`），修复后再次运行即可通过校验。

### 依赖管理规范

- 运行时依赖（生产环境需要的库）统一维护在 `requirements.txt`，例如 `fastapi`, `openlineage-python`, `openlineage-sql`。
- 开发与测试依赖（pytest、coverage、prometheus_client 等）统一维护在 `requirements-dev.txt`，保持与 CI/CD、Dockerfile 中 `pip install -r requirements.txt -r requirements-dev.txt` 的流程一致。
- 新增依赖时同步更新上述文件，并通过 `make check-deps` 进行验证。

### 慢测试分层

- 将执行时间 ≥5 秒的用例标记为 `@pytest.mark.slow`（如 `tests/unit/test_data_collection_tasks_comprehensive.py`、`tests/unit/api/test_health_core.py`），确保默认单测集合保持快速。
- 快速单元测试：`pytest tests/unit -m "unit and not slow"`
- 专门运行慢测试：`pytest tests/unit -m "slow"`

### CI/CD 执行顺序

1. 运行 `make check-deps` 校验依赖是否完整。
2. 执行 `pip install -r requirements.txt -r requirements-dev.txt` 安装运行时与测试依赖。
3. 按需运行快速单测或慢测试套件，保证与本地体验一致。

## 🏗️ 测试分层设计

### 1️⃣ 单元测试（Unit Test）- 基础保障层

#### 测试目标
验证个别模块和函数的逻辑正确性，确保每个组件独立工作正常。

#### 重点覆盖模块
- **数据采集器** (`src/data/collectors/`)
  - `DataCollector.collect_fixtures()` - 赛程数据采集
  - `DataCollector.collect_odds()` - 赔率数据采集
  - `DataCollector.collect_live_scores()` - 实时比分采集
  - 防重复机制和防丢失策略验证

- **数据清洗器** (`src/data/processing/`)
  - `FootballDataCleaner.clean_match_data()` - 比赛数据清洗
  - `FootballDataCleaner.clean_odds_data()` - 赔率数据清洗
  - `MissingDataHandler.handle_missing_values()` - 缺失值处理
  - 数据质量规则验证

- **数据库管理器** (`src/database/`)
  - `DatabaseManager` 连接池管理
  - `BaseModel` ORM模型基类
  - 数据库操作CRUD验证
  - 事务管理和异常处理

- **模型训练器** (`src/models/`)
  - `BaselineModelTrainer.train_baseline_model()` - 模型训练
  - `PredictionService.predict_match()` - 预测服务
  - `FeatureCalculator` 特征计算逻辑
  - MLflow集成验证

#### 测试工具与框架
- **主框架**: pytest + pytest-asyncio
- **Mock工具**: pytest-mock + unittest.mock
- **数据工厂**: factory_boy + Faker
- **异步测试**: pytest-asyncio
- **数据库测试**: pytest-postgresql + SQLAlchemy

#### 覆盖率目标
- **总体覆盖率**: ≥80%
- **核心业务逻辑**: ≥95%
- **API端点**: ≥90%
- **数据处理模块**: ≥85%

#### 单元测试示例
```python
# tests/unit/test_data_collectors.py
import pytest
from unittest.mock import AsyncMock, patch
from src.data.collectors.base_collector import DataCollector

class TestDataCollector:
    @pytest.mark.asyncio
    async def test_collect_fixtures_success(self):
        """测试赛程数据采集成功场景"""
        collector = DataCollector()

        # Mock外部API响应
        mock_api_response = {
            "fixtures": [
                {
                    "id": 12345,
                    "home_team": "Arsenal",
                    "away_team": "Chelsea",
                    "date": "2025-09-15T15:00:00Z"
                }
            ]
        }

        with patch.object(collector, '_fetch_from_api', return_value=mock_api_response):
            result = await collector.collect_fixtures()

        assert result.success is True
        assert result.records_collected == 1
        assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_collect_fixtures_duplicate_prevention(self):
        """测试赛程数据采集防重复机制"""
        collector = DataCollector()

        # 模拟数据库中已存在相同数据
        with patch.object(collector, '_check_existing_data', return_value=True):
            result = await collector.collect_fixtures()

        assert result.duplicate_count > 0
        assert "duplicate prevention" in result.notes
```

---

### 2️⃣ 集成测试（Integration Test）- 系统协同层

#### 测试目标
验证跨模块协同逻辑和关键数据流，确保各组件之间正确协作。

#### 重点覆盖场景

##### 数据流集成测试
- **Bronze→Silver→Gold数据流**
  ```python
  # tests/integration/test_data_pipeline.py
  @pytest.mark.asyncio
  async def test_complete_data_pipeline():
      """测试完整数据处理管道"""
      # 1. Bronze层: 原始数据采集
      raw_data = await data_collector.collect_fixtures()
      assert raw_data.success

      # 2. Silver层: 数据清洗
      cleaned_data = await data_processor.process_bronze_to_silver()
      assert cleaned_data['processed_count'] > 0

      # 3. Gold层: 特征计算
      features = await feature_calculator.calculate_match_features()
      assert features is not None

      # 4. 验证数据一致性
      assert_data_consistency()
  ```

##### 任务调度集成测试
- **Celery任务编排验证**
  ```python
  # tests/integration/test_scheduler.py
  @pytest.mark.asyncio
  async def test_celery_task_dependencies():
      """测试Celery任务依赖关系"""
      # 触发赛程采集任务
      fixtures_task = collect_fixtures_task.delay()

      # 等待完成后触发赔率采集
      odds_task = collect_odds_task.delay()

      # 验证任务执行顺序和结果
      assert fixtures_task.get() is True
      assert odds_task.get() is True
  ```

##### 缓存一致性测试
- **Redis↔PostgreSQL数据一致性**
  ```python
  # tests/integration/test_cache_consistency.py
  @pytest.mark.asyncio
  async def test_redis_postgres_consistency():
      """测试Redis缓存与PostgreSQL数据一致性"""
      # 写入PostgreSQL
      match_data = await db_manager.create_match(match_info)

      # 检查Redis缓存更新
      cached_data = await redis_manager.get_match(match_id)

      assert match_data.id == cached_data['id']
      assert match_data.home_team_id == cached_data['home_team_id']
  ```

#### 测试工具与环境
- **框架**: pytest + docker-compose
- **数据库**: 专用测试PostgreSQL实例
- **缓存**: 专用测试Redis实例
- **消息队列**: 测试环境Celery + Redis broker
- **容器编排**: docker-compose.test.yml

#### 集成测试策略
- **数据隔离**: 每个测试使用独立数据库schema
- **服务隔离**: Docker容器化确保环境一致性
- **状态清理**: 测试前后自动清理数据和状态
- **并发测试**: 验证多用户并发场景

---

### 3️⃣ 端到端测试（E2E Test）- 业务场景层

#### 测试目标
模拟真实用户场景，验证完整业务流程的端到端正确性。

#### 核心测试场景

##### API功能测试
```python
# tests/e2e/test_prediction_api.py
@pytest.mark.asyncio
async def test_match_prediction_workflow():
    """测试完整比赛预测工作流"""
    # 1. 创建比赛数据
    match_data = await create_test_match()

    # 2. 调用预测API
    response = await client.get(f"/predictions/{match_data.id}")

    # 3. 验证响应格式和概率
    assert response.status_code == 200
    prediction = response.json()["data"]

    # 验证概率和为1（±0.05容差）
    total_prob = (
        prediction["home_win_probability"] +
        prediction["draw_probability"] +
        prediction["away_win_probability"]
    )
    assert 0.95 <= total_prob <= 1.05

    # 4. 验证预测结果存储
    stored_prediction = await db.get_prediction(match_data.id)
    assert stored_prediction is not None
```

##### 数据血缘测试
```python
# tests/e2e/test_data_lineage.py
@pytest.mark.asyncio
async def test_data_lineage_tracking():
    """验证数据血缘在元数据管理系统中完整追踪"""
    # 1. 触发数据采集
    collection_result = await trigger_data_collection()

    # 2. 检查Marquez中的血缘记录
    lineage_data = await marquez_client.get_dataset_lineage(
        namespace="football_db.bronze",
        name="raw_match_data"
    )

    # 3. 验证血缘完整性
    assert lineage_data["upstream_datasets"] != []
    assert "api_football" in lineage_data["data_sources"]

    # 4. 验证下游血缘
    downstream = await marquez_client.get_downstream_lineage("raw_match_data")
    assert "matches" in [ds["name"] for ds in downstream]
```

##### 回测验证测试
```python
# tests/e2e/test_backtesting.py
@pytest.mark.asyncio
async def test_prediction_backtesting():
    """历史比赛预测结果的准确率回测验证"""
    # 1. 获取历史已完成比赛
    historical_matches = await get_completed_matches(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 12, 31)
    )

    # 2. 批量预测历史比赛
    predictions = []
    for match in historical_matches:
        pred_result = await prediction_service.predict_match(match.id)
        predictions.append(pred_result)

    # 3. 计算准确率
    correct_predictions = sum(
        1 for pred in predictions
        if pred.predicted_result == pred.actual_result
    )
    accuracy = correct_predictions / len(predictions)

    # 4. 验证准确率达到基准线
    BASELINE_ACCURACY = 0.55  # 55%基准准确率
    assert accuracy >= BASELINE_ACCURACY, f"准确率{accuracy:.2%}低于基准{BASELINE_ACCURACY:.2%}"
```

#### 测试工具与框架
- **框架**: pytest + requests + pytest-asyncio
- **API测试**: httpx + FastAPI TestClient
- **数据验证**: pandas + numpy用于结果分析
- **性能测试**: locust用于负载测试

---

## 📊 测试覆盖范围

### 功能覆盖率

#### 核心业务模块 (95%+ 覆盖要求)
- **数据采集**: 外部API调用、数据解析、存储入库
- **数据清洗**: 质量检查、格式标准化、异常处理
- **特征工程**: 特征计算、特征存储、特征检索
- **模型预测**: 模型加载、预测计算、结果存储
- **监控告警**: 指标收集、异常检测、告警触发

#### 支撑功能模块 (80%+ 覆盖要求)
- **数据库操作**: CRUD操作、连接管理、事务处理
- **缓存管理**: Redis操作、缓存策略、过期处理
- **API接口**: 请求处理、响应格式、错误处理
- **权限认证**: 用户验证、权限检查、会话管理

### 代码覆盖率

#### 按文件类型分类
| 文件类型 | 覆盖率目标 | 检查工具 | 备注 |
|---------|-----------|---------|------|
| **API模块** | ≥90% | pytest-cov | 所有端点必须测试 |
| **业务逻辑** | ≥95% | pytest-cov | 核心算法完全覆盖 |
| **数据模型** | ≥85% | pytest-cov | ORM模型和验证 |
| **工具函数** | ≥80% | pytest-cov | 通用功能模块 |
| **配置文件** | ≥70% | pytest-cov | 配置加载和验证 |

#### 覆盖率监控策略
```bash
# 生成覆盖率报告
make coverage

# 覆盖率检查 (CI中强制执行)
pytest --cov=src --cov-min=60 --cov-fail-under=60 --maxfail=5 --disable-warnings

# 生成HTML报告
pytest --cov=src --cov-report=html
```

### 业务场景覆盖率

#### 数据处理场景
- ✅ 正常数据采集和处理流程
- ✅ 网络异常和API错误处理
- ✅ 数据格式异常和清洗逻辑
- ✅ 大批量数据处理性能
- ✅ 并发采集和竞态条件
- ✅ 断点续传和增量采集

#### 预测服务场景
- ✅ 标准比赛预测流程
- ✅ 缺失特征数据处理
- ✅ 模型版本更新切换
- ✅ 高并发预测请求
- ✅ 预测结果缓存策略
- ✅ 异常比赛数据处理

#### 系统运维场景
- ✅ 服务启动和关闭
- ✅ 数据库连接异常恢复
- ✅ Redis连接中断处理
- ✅ 磁盘空间不足处理
- ✅ 内存泄漏监控
- ✅ 日志轮转和清理

---

## ⚙️ 测试执行与自动化

### CI/CD流程中的测试

#### GitHub Actions工作流
```yaml
# .github/workflows/test.yml (简化版)
name: Test Pipeline
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test_password
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run linting
        run: |
          black --check src tests
          flake8 src tests
          mypy src

      - name: Run unit tests
        run: |
          pytest tests/unit/ -v --cov=src --cov-min=80

      - name: Run integration tests
        run: |
          pytest tests/integration/ -v

      - name: Run E2E tests
        run: |
          pytest tests/e2e/ -v

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
```

#### 本地Docker CI模拟
```bash
# ci-verify.sh - 本地CI环境完整模拟
#!/bin/bash
set -e

echo "🐳 启动测试环境..."
docker-compose -f docker-compose.test.yml up -d

echo "📦 安装依赖..."
docker-compose -f docker-compose.test.yml exec app pip install -r requirements.txt

echo "🧪 运行完整测试套件..."
docker-compose -f docker-compose.test.yml exec app make test

echo "📊 生成覆盖率报告..."
docker-compose -f docker-compose.test.yml exec app make coverage

echo "🧹 清理环境..."
docker-compose -f docker-compose.test.yml down

echo "✅ 所有测试通过！代码可以推送。"
```

### 自动化测试调度

#### 每次提交必须执行
- **单元测试**: 快速验证基础功能 (~2分钟)
- **集成测试**: 验证模块协同 (~5分钟)
- **代码质量检查**: 风格、类型、安全检查 (~1分钟)
- **覆盖率检查**: 确保覆盖率达标 (~30秒)

#### 每日定时执行
- **完整E2E测试**: 端到端业务流程验证 (~15分钟)
- **性能回归测试**: 关键API性能基准检查 (~10分钟)
- **数据一致性检查**: 验证各层数据一致性 (~5分钟)

#### 每周定时执行
```python
# scripts/weekly_test_suite.py
async def run_weekly_comprehensive_tests():
    """每周执行的综合测试套件"""

    # 1. 历史数据回测
    await run_backtesting_validation()

    # 2. 数据血缘完整性检查
    await verify_data_lineage_integrity()

    # 3. 模型性能回归测试
    await run_model_performance_regression()

    # 4. 系统负载测试
    await run_load_testing()

    # 5. 安全渗透测试
    await run_security_tests()
```

### 测试环境管理

#### 环境隔离策略
| 环境类型 | 数据库 | 缓存 | 用途 | 数据策略 |
|---------|-------|------|------|---------|
| **单元测试** | SQLite内存 | FakeRedis | 快速验证 | Mock数据 |
| **集成测试** | PostgreSQL测试库 | Redis测试实例 | 组件协同 | 测试数据 |
| **E2E测试** | PostgreSQL演示库 | Redis演示实例 | 完整流程 | 仿真数据 |
| **性能测试** | PostgreSQL性能库 | Redis集群 | 负载验证 | 大量数据 |

#### 测试数据管理
```python
# tests/fixtures/data_factory.py
import factory
from faker import Faker

class MatchFactory(factory.Factory):
    class Meta:
        model = Match

    home_team_id = factory.Sequence(lambda n: n)
    away_team_id = factory.Sequence(lambda n: n + 100)
    league_id = 1
    season = "2024-25"
    match_time = factory.Faker('future_datetime', end_date='+30d')
    match_status = "scheduled"

class OddsFactory(factory.Factory):
    class Meta:
        model = Odd

    match = factory.SubFactory(MatchFactory)
    bookmaker = factory.Faker('company')
    home_odds = factory.Faker('pydecimal', left_digits=1, right_digits=2, min_value=1.01, max_value=10.00)
    draw_odds = factory.Faker('pydecimal', left_digits=1, right_digits=2, min_value=1.01, max_value=10.00)
    away_odds = factory.Faker('pydecimal', left_digits=1, right_digits=2, min_value=1.01, max_value=10.00)
```

---

## 📈 改进计划

### 短期改进 (1-2个月)

#### 1. 补齐单元测试缺口
**目标**: 将当前覆盖率从约60%提升到80%+

**具体任务**:
- ✅ 完善数据采集器测试 (`tests/unit/test_collectors.py`)
- ✅ 补充数据清洗器测试 (`tests/unit/test_data_cleaning.py`)
- ✅ 增加特征计算器测试 (`tests/unit/test_feature_calculator.py`)
- ⏳ 完善API端点测试 (`tests/unit/test_api_endpoints.py`)
- ⏳ 增加异常处理测试用例

**执行计划**:
```bash
# 第1周: 数据层测试
Week 1: 完成Bronze/Silver/Gold层核心逻辑测试

# 第2周: 业务层测试
Week 2: 完成特征工程和预测服务测试

# 第3周: API层测试
Week 3: 完成所有API端点和边界条件测试

# 第4周: 集成和优化
Week 4: 集成测试优化，达到80%覆盖率目标
```

#### 2. 索引优化相关测试
**目标**: 确保数据库性能优化正确性

**测试内容**:
- 分区表查询性能验证
- 索引使用效果测试
- 大数据量场景压力测试
- 并发查询性能基准

```python
# tests/performance/test_database_optimization.py
@pytest.mark.performance
async def test_partitioned_table_query_performance():
    """测试分区表查询性能"""
    # 插入大量测试数据 (10万条记录)
    await insert_large_dataset(100000)

    # 测试分区查询
    start_time = time.time()
    results = await query_matches_by_date_range(
        start_date=datetime(2025, 9, 1),
        end_date=datetime(2025, 9, 30)
    )
    query_time = time.time() - start_time

    # 验证查询时间 < 200ms
    assert query_time < 0.2, f"查询时间{query_time:.3f}s超过200ms阈值"
    assert len(results) > 0
```

### 中期改进 (3-6个月)

#### 1. 完善调度系统测试
**目标**: 确保Celery任务编排和调度系统稳定可靠

**测试策略**:
- **任务依赖测试**: 验证任务执行顺序和依赖关系
- **失败重试测试**: 模拟各种失败场景和重试机制
- **并发执行测试**: 验证多任务并发执行的正确性
- **资源消耗测试**: 监控任务执行的内存和CPU使用

```python
# tests/integration/test_celery_scheduler.py
@pytest.mark.asyncio
async def test_task_dependency_chain():
    """测试任务依赖链执行"""
    # 1. 触发数据采集任务链
    fixtures_task = collect_fixtures_task.delay()

    # 2. 等待赛程采集完成，触发赔率采集
    fixtures_result = fixtures_task.get(timeout=30)
    assert fixtures_result['success'] is True

    odds_task = collect_odds_task.delay(
        depends_on=fixtures_task.id
    )

    # 3. 验证赔率采集正确处理依赖
    odds_result = odds_task.get(timeout=60)
    assert odds_result['success'] is True
    assert odds_result['matches_processed'] > 0
```

#### 2. 数据质量监控测试
**目标**: 确保Great Expectations数据质量监控准确可靠

**测试范围**:
- **断言规则验证**: 确保数据质量规则正确定义
- **异常检测测试**: 验证异常数据能被正确识别
- **告警机制测试**: 确保质量问题能及时告警
- **修复策略测试**: 验证自动修复机制的有效性

```python
# tests/integration/test_data_quality_monitoring.py
@pytest.mark.asyncio
async def test_odds_data_quality_expectations():
    """测试赔率数据质量期望"""
    # 1. 插入包含异常的赔率数据
    test_odds = [
        {"home_odds": 1.50, "draw_odds": 3.20, "away_odds": 6.00},  # 正常
        {"home_odds": 0.80, "draw_odds": 2.50, "away_odds": 4.00},  # 异常: home_odds < 1.01
        {"home_odds": 1.10, "draw_odds": 1.10, "away_odds": 1.10},  # 异常: 总概率过高
    ]

    # 2. 运行Great Expectations验证
    validation_result = await run_ge_validation('odds', test_odds)

    # 3. 验证异常被正确识别
    assert validation_result['success'] is False
    assert validation_result['failed_expectations'] >= 2

    # 4. 验证告警已触发
    alerts = await get_recent_quality_alerts()
    assert len(alerts) >= 1
    assert any("odds" in alert['table'] for alert in alerts)
```

### 长期改进 (6-12个月)

#### 1. 增加性能测试
**目标**: 建立完整的性能基准和回归测试体系

**测试策略**:
- **API响应时间基准**: 建立各API端点的性能基准
- **数据库查询性能**: 监控关键查询的执行时间
- **并发负载测试**: 验证系统在高负载下的表现
- **内存泄漏检测**: 长期运行的内存使用监控

```python
# tests/performance/test_api_performance.py
@pytest.mark.performance
class TestAPIPerformance:

    @pytest.mark.parametrize("concurrent_users", [10, 50, 100])
    async def test_prediction_api_load(self, concurrent_users):
        """测试预测API负载性能"""
        import asyncio
        import aiohttp

        async def make_prediction_request(session, match_id):
            async with session.get(f"/predictions/{match_id}") as response:
                return await response.json(), response.headers

        # 创建并发请求
        async with aiohttp.ClientSession() as session:
            tasks = [
                make_prediction_request(session, i)
                for i in range(concurrent_users)
            ]

            start_time = time.time()
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time

        # 验证性能指标
        avg_response_time = total_time / concurrent_users
        assert avg_response_time < 1.0, f"平均响应时间{avg_response_time:.2f}s超过1秒"

        # 验证所有请求成功
        success_count = sum(1 for result, _ in results if result.get('success'))
        assert success_count == concurrent_users
```

#### 2. 增加压力测试
**目标**: 验证系统极限性能和故障恢复能力

**测试场景**:
- **数据库连接池耗尽**: 模拟连接池耗尽和恢复
- **Redis内存不足**: 测试缓存服务异常处理
- **磁盘空间不足**: 验证存储空间耗尽的处理
- **网络分区测试**: 模拟网络故障和恢复

```python
# tests/stress/test_system_limits.py
@pytest.mark.stress
class TestSystemLimits:

    async def test_database_connection_exhaustion(self):
        """测试数据库连接池耗尽场景"""
        # 1. 创建大量并发数据库连接
        connections = []
        try:
            for i in range(50):  # 超过连接池限制
                conn = await db_manager.get_connection()
                connections.append(conn)

            # 2. 尝试新连接应该优雅处理
            with pytest.raises(ConnectionPoolExhausted):
                await db_manager.get_connection()

        finally:
            # 3. 释放连接并验证恢复
            for conn in connections:
                await conn.close()

            # 验证连接池恢复正常
            test_conn = await db_manager.get_connection()
            assert test_conn is not None
            await test_conn.close()
```

---

## 📋 测试执行检查清单

### 每日检查项目 ✅
- [ ] 单元测试执行通过率 ≥ 98%
- [ ] 集成测试全部通过
- [ ] 代码覆盖率 ≥ 80%
- [ ] 关键API响应时间 < 500ms
- [ ] 数据质量检查无严重异常
- [ ] CI/CD管道运行正常

### 每周检查项目 ✅
- [ ] E2E测试全部通过
- [ ] 性能基准测试无回归
- [ ] 数据血缘验证完整
- [ ] 安全扫描无高危漏洞
- [ ] 测试环境数据同步
- [ ] 测试用例覆盖率审查

### 发布前检查项目 ✅
- [ ] 完整测试套件执行通过
- [ ] 代码覆盖率达到要求
- [ ] 性能测试通过基准
- [ ] 安全测试无阻塞问题
- [ ] 数据迁移测试验证
- [ ] 回滚方案测试验证

### 测试质量监控 📊

#### Prometheus监控指标
```python
# 测试执行监控指标
football_test_execution_total{test_type, status}
football_test_coverage_percentage{module}
football_test_duration_seconds{test_suite}
football_test_failure_rate{time_window}

# 测试环境健康指标
football_test_env_availability{environment}
football_test_data_freshness_hours{dataset}
```

#### Grafana监控看板
- **测试执行概览**: 测试通过率、执行时间趋势
- **覆盖率监控**: 模块覆盖率、趋势分析
- **性能基准**: API响应时间、数据库查询性能
- **环境健康**: 测试环境可用性、数据同步状态

---

## 📝 总结

### 测试策略核心价值

通过本测试策略的实施，足球预测系统将获得：

1. **质量保障**: 通过分层测试确保各个层级的代码质量
2. **稳定性提升**: 全面的集成测试保证系统稳定运行
3. **快速反馈**: 自动化CI/CD提供快速问题发现和反馈
4. **持续改进**: 基于监控数据的持续测试优化

### 成功指标

| 指标类型 | 目标值 | 当前状态 | 改进计划 |
|---------|-------|---------|---------|
| **代码覆盖率** | ≥80% | ~60% | 2个月内达标 |
| **API可用性** | ≥99.5% | ~95% | 强化集成测试 |
| **测试执行时间** | <10分钟 | ~8分钟 | 持续优化 |
| **缺陷发现率** | 75%在开发阶段 | ~60% | 加强单元测试 |

### 持续改进承诺

- **月度回顾**: 每月评估测试策略执行效果
- **季度优化**: 每季度更新测试策略和工具
- **年度规划**: 每年制定下一年度测试改进计划
- **技术跟进**: 持续跟进最新测试技术和最佳实践

---

*本文档将随着项目发展持续更新和完善，确保测试策略始终与业务需求和技术发展保持同步。*
