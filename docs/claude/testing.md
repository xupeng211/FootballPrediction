# 测试体系详解

本文档详细介绍FootballPrediction项目的完整测试体系，包括47个标准化测试标记、Smart Tests策略和测试最佳实践。

---

## 📋 目录

- [🧪 测试架构概览](#-测试架构概览)
- [🎯 Smart Tests策略](#-smart-tests策略)
- [🏷️ 47个标准化测试标记](#️-47个标准化测试标记)
- [📊 测试类型详解](#-测试类型详解)
- [🛠️ 测试工具链](#️-测试工具链)
- [📈 覆盖率管理](#-覆盖率管理)
- [🚀 测试执行策略](#-测试执行策略)
- [🔧 测试配置详解](#-测试配置详解)
- [🐛 测试调试技巧](#-测试调试技巧)
- [📝 测试最佳实践](#-测试最佳实践)

---

## 🧪 测试架构概览

### 测试目录结构

```
tests/
├── unit/                    # 单元测试 (85%)
│   ├── api/                # API层测试
│   ├── core/               # 核心模块测试
│   ├── domain/             # 领域逻辑测试
│   ├── services/           # 应用服务测试
│   ├── database/           # 数据访问层测试
│   ├── cache/              # 缓存测试
│   ├── utils/              # 工具类测试
│   └── fixtures/           # 测试数据
├── integration/             # 集成测试 (12%)
│   ├── api/                # API集成测试
│   ├── database/           # 数据库集成测试
│   ├── cache/              # 缓存集成测试
│   └── external/           # 外部服务集成测试
├── e2e/                     # 端到端测试 (2%)
│   ├── api/                # API端到端测试
│   └── workflows/          # 业务流程测试
├── performance/             # 性能测试 (1%)
│   ├── load/               # 负载测试
│   ├── stress/             # 压力测试
│   └── benchmarks/         # 基准测试
└── conftest.py              # pytest配置文件
```

### 测试比例和执行时间

| 测试类型 | 比例 | 执行时间 | 并发度 | 优先级 |
|---------|------|----------|--------|--------|
| 单元测试 | 85% | <5分钟 | 高 | 🔥 critical |
| 集成测试 | 12% | <15分钟 | 中 | ⚡ important |
| 端到端测试 | 2% | <30分钟 | 低 | 💡 optional |
| 性能测试 | 1% | >30分钟 | 串行 | 🎯 special |

---

## 🎯 Smart Tests策略

### 核心理念

**Smart Tests** 是一个基于稳定性和执行时间的智能测试优化策略，旨在：

1. **提高开发效率** - 优先执行快速稳定的测试
2. **降低反馈延迟** - 快速发现和修复问题
3. **优化CI/CD流水线** - 分阶段执行不同类型的测试
4. **保障测试质量** - 确保核心功能的测试覆盖率

### 策略配置（pytest.ini）

```ini
[tool:pytest]
# Smart Tests 配置
addopts =
    --strict-markers
    --strict-config
    --tb=short
    -ra
    --cov=src
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=40

# Smart Tests 核心模块（快速稳定）
testpaths =
    tests/unit/utils
    tests/unit/cache
    tests/unit/core

# 自动排除的问题测试文件
norecursedirs =
    tests/unit/services/test_prediction_service.py
    tests/unit/core/test_di.py
    tests/unit/core/test_path_manager_enhanced.py
    tests/unit/scripts/test_create_service_tests.py
```

### Smart Tests 执行命令

```bash
# 核心稳定测试（执行时间<2分钟，通过率>90%）
make test.smart              # 智能测试组合
pytest tests/unit/utils tests/unit/cache tests/unit/core

# 快速验证（<5分钟）
make test.smart-extended     # 扩展智能测试

# 完整验证（<30分钟）
make test.unit              # 所有单元测试
make test.integration       # 集成测试
```

### 核心稳定测试模块

**1. utils模块** - 最稳定的工具类测试
```bash
tests/unit/utils/
├── test_date_utils.py      # 日期工具函数
├── test_string_utils.py    # 字符串处理工具
├── test_validation_utils.py # 数据验证工具
├── test_formatting_utils.py # 格式化工具
└── test_calculation_utils.py # 计算工具
```

**2. cache模块** - 依赖少、执行快
```bash
tests/unit/cache/
├── test_decorators.py      # 缓存装饰器
├── test_redis_client.py    # Redis客户端
├── test_cache_manager.py   # 缓存管理器
└── test_cache_strategies.py # 缓存策略
```

**3. core模块** - 基础功能测试
```bash
tests/unit/core/
├── test_config.py          # 配置管理
├── test_exceptions.py      # 异常处理
├── test_logger.py          # 日志系统
└── test_base_classes.py    # 基础类测试
```

### 自动排除的问题文件

**复杂依赖测试**
- `test_prediction_service.py` - 服务层复杂依赖
- `test_di.py` - 依赖注入测试
- `test_path_manager_enhanced.py` - 路径管理测试
- `test_create_service_tests.py` - 脚本测试

**排除原因**
- 🔧 **依赖复杂** - 需要大量Mock和配置
- ⏱️ **执行缓慢** - 单个测试耗时过长
- 🔄 **不稳定** - 偶发性失败影响CI稳定性
- 🏗️ **架构变更** - 频繁重构导致测试失效

---

## 🏷️ 47个标准化测试标记

### 核心类型标记（8个）

```bash
pytest -m "unit"              # 单元测试 - 单个函数/类测试
pytest -m "integration"       # 集成测试 - 多组件交互测试
pytest -m "e2e"              # 端到端测试 - 完整用户流程测试
pytest -m "performance"       # 性能测试 - 基准和性能分析
pytest -m "smoke"            # 冒烟测试 - 基础功能验证
pytest -m "regression"       # 回归测试 - 防止功能回退
pytest -m "security"         # 安全测试 - 安全漏洞检测
pytest -m "compatibility"    # 兼容性测试 - 版本兼容性
```

### 执行特征标记（12个）

```bash
# 时间相关标记
pytest -m "slow"             # 慢速测试 (>30s)
pytest -m "fast"             # 快速测试 (<1s)
pytest -m "medium"           # 中等速度测试 (1s-30s)

# 稳定性标记
pytest -m "stable"           # 稳定测试 (通过率>95%)
pytest -m "flaky"            # 不稳定测试 (偶发性失败)
pytest -m "critical"         # 关键功能测试 (必须通过)
pytest -m "optional"         # 可选测试 (允许失败)

# 执行环境标记
pytest -m "local"            # 仅本地环境执行
pytest -m "ci"               # 仅CI环境执行
pytest -m "production"       # 生产环境测试
pytest -m "debug"            # 调试测试
```

### 功能域标记（15个）

```bash
# 业务功能标记
pytest -m "api"              # API接口测试
pytest -m "domain"           # 领域逻辑测试
pytest -m "services"         # 应用服务测试
pytest -m "database"         # 数据库相关测试
pytest -m "cache"            # 缓存相关测试
pytest -m "ml"               # 机器学习模块测试
pytest -m "utils"            # 工具类测试
pytest -m "decorators"       # 装饰器测试
pytest -m "config"           # 配置相关测试
pytest -m "di"               # 依赖注入测试
pytest -m "cqrs"             # CQRS模式测试
pytest -m "events"           # 事件系统测试
pytest -m "strategies"       # 策略模式测试
pytest -m "adapters"         # 适配器模式测试
pytest -m "monitoring"       # 监控相关测试
```

### 依赖环境标记（8个）

```bash
pytest -m "docker"           # 需要Docker环境
pytest -m "network"          # 需要网络连接
pytest -m "external_api"     # 需要外部API调用
pytest -m "database"         # 需要数据库连接
pytest -m "redis"            # 需要Redis连接
pytest -m "filesystem"       # 需要文件系统访问
pytest -m "memory"           # 需要大量内存
pytest -m "gpu"              # 需要GPU支持
```

### 数据状态标记（4个）

```bash
pytest -m "requires_data"    # 需要测试数据
pytest -m "generates_data"   # 生成测试数据
pytest -m "cleanup_required" # 需要清理数据
pytest -m "stateful"         # 状态相关测试
```

### 使用示例

```bash
# 复合标记查询
pytest -m "unit and api and critical"          # API关键功能单元测试
pytest -m "integration and database"           # 数据库集成测试
pytest -m "slow or external_api"               # 慢速或外部API测试
pytest -m "unit and not slow and stable"      # 稳定快速单元测试

# 排除特定标记
pytest -m "unit and not slow"                  # 排除慢速测试
pytest -m "not docker and not network"         # 排除依赖外部服务的测试
```

---

## 📊 测试类型详解

### 单元测试（Unit Tests - 85%）

**定义**：测试单个函数、方法或类的功能

**特点**：
- ⚡ 执行快速（<1秒）
- 🔧 依赖隔离（使用Mock）
- 🎯 职责单一
- 📈 覆盖率驱动

**示例**：
```python
# tests/unit/utils/test_date_utils.py
import pytest
from src.utils.date_utils import DateUtils

class TestDateUtils:
    def test_format_date_success(self):
        """测试日期格式化成功场景"""
        date_str = "2023-12-25"
        result = DateUtils.format_date(date_str, "%Y-%m-%d")
        assert result == "2023-12-25"

    def test_format_date_invalid_input(self):
        """测试日期格式化失败场景"""
        with pytest.raises(ValueError):
            DateUtils.format_date("invalid-date", "%Y-%m-%d")

    @pytest.mark.parametrize("date_str,expected", [
        ("2023-01-01", "2023-01-01"),
        ("2023/01/01", "2023-01-01"),
        ("01-01-2023", "2023-01-01"),
    ])
    def test_parse_date_various_formats(self, date_str, expected):
        """参数化测试多种日期格式"""
        result = DateUtils.parse_date(date_str)
        assert result.strftime("%Y-%m-%d") == expected
```

### 集成测试（Integration Tests - 12%）

**定义**：测试多个组件之间的交互

**特点**：
- 🔗 组件交互测试
- 🌐 真实环境配置
- 📊 端到端数据流
- ⏱️ 执行时间中等（1-30秒）

**示例**：
```python
# tests/integration/database/test_prediction_repository.py
import pytest
from src.database.repositories.prediction_repository import PredictionRepository
from src.database.adapters.postgresql_adapter import PostgreSQLAdapter

@pytest.mark.integration
@pytest.mark.database
class TestPredictionRepositoryIntegration:
    @pytest.fixture
    async def repository(self):
        """设置集成测试环境"""
        adapter = PostgreSQLAdapter("postgresql://test:test@localhost/test_db")
        await adapter.connect()
        return PredictionRepository(adapter)

    async def test_create_and_retrieve_prediction(self, repository):
        """测试创建和获取预测"""
        # 创建测试数据
        prediction = Prediction(
            id="test-pred-123",
            match_id="test-match-456",
            strategy_type="ml_model",
            prediction_data={"home_win": 0.6, "draw": 0.3, "away_win": 0.1}
        )

        # 测试创建
        created = await repository.create(prediction)
        assert created.id == prediction.id

        # 测试获取
        retrieved = await repository.get_by_id(prediction.id)
        assert retrieved.id == prediction.id
        assert retrieved.prediction_data == prediction.prediction_data
```

### 端到端测试（E2E Tests - 2%）

**定义**：测试完整的用户场景和业务流程

**特点**：
- 🎭 真实用户场景
- 🌍 完整系统测试
- ⏱️ 执行时间长（>30秒）
- 💡 业务价值驱动

**示例**：
```python
# tests/e2e/api/test_prediction_workflow.py
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.e2e
@pytest.mark.api
class TestPredictionWorkflowE2E:
    async def test_complete_prediction_workflow(self):
        """测试完整的预测工作流"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 1. 获取比赛列表
            response = await client.get("/api/matches")
            assert response.status_code == 200
            matches = response.json()
            assert len(matches) > 0

            # 2. 选择比赛创建预测
            match_id = matches[0]["id"]
            prediction_request = {
                "match_id": match_id,
                "strategy_type": "ml_model"
            }

            response = await client.post("/api/predictions", json=prediction_request)
            assert response.status_code == 201
            prediction = response.json()
            assert prediction["match_id"] == match_id

            # 3. 获取预测结果
            prediction_id = prediction["id"]
            response = await client.get(f"/api/predictions/{prediction_id}")
            assert response.status_code == 200
            result = response.json()
            assert "prediction_data" in result
```

### 性能测试（Performance Tests - 1%）

**定义**：测试系统性能指标

**特点**：
- ⚡ 性能基准测试
- 📊 负载和压力测试
- 📈 性能监控
- 🔍 性能回归检测

**示例**：
```python
# tests/performance/load/test_prediction_api.py
import pytest
import asyncio
import time
from httpx import AsyncClient

@pytest.mark.performance
@pytest.mark.load
class TestPredictionAPILoad:
    async def test_concurrent_prediction_requests(self):
        """测试并发预测请求性能"""
        async def make_request(client):
            start_time = time.time()
            response = await client.post(
                "/api/predictions",
                json={
                    "match_id": "test-match",
                    "strategy_type": "ml_model"
                }
            )
            end_time = time.time()
            return {
                "status": response.status_code,
                "response_time": end_time - start_time
            }

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 并发执行100个请求
            tasks = [make_request(client) for _ in range(100)]
            results = await asyncio.gather(*tasks)

            # 性能断言
            successful_requests = [r for r in results if r["status"] == 200]
            avg_response_time = sum(r["response_time"] for r in successful_requests) / len(successful_requests)

            assert len(successful_requests) >= 95  # 95%成功率
            assert avg_response_time < 1.0         # 平均响应时间<1秒
```

---

## 🛠️ 测试工具链

### 核心测试框架

**pytest** - 主要测试框架
```bash
# 安装
pip install pytest pytest-asyncio pytest-cov pytest-mock

# 基本使用
pytest                           # 运行所有测试
pytest -v                        # 详细输出
pytest -x                        # 首次失败后停止
pytest --maxfail=5              # 最多允许5个失败
pytest -k "test_prediction"      # 运行名称匹配的测试
```

**pytest-asyncio** - 异步测试支持
```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_async_prediction_service():
    service = PredictionService()
    prediction = await service.create_prediction(match_data)
    assert prediction is not None
```

**pytest-mock** - Mock和Patch支持
```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_prediction_service_with_mock():
    with patch('src.services.prediction_service.PredictionStrategy') as mock_strategy:
        mock_strategy.predict.return_value = {"home_win": 0.7}

        service = PredictionService()
        result = await service.make_prediction(match_data)

        assert result["home_win"] == 0.7
        mock_strategy.predict.assert_called_once_with(match_data)
```

### 覆盖率工具

**pytest-cov** - 覆盖率测量
```bash
# 生成覆盖率报告
pytest --cov=src --cov-report=term-missing
pytest --cov=src --cov-report=html:htmlcov

# 覆盖率配置
# pytest.ini
[tool:pytest]
addopts = --cov=src --cov-fail-under=40
```

**Coverage.py** - 覆盖率分析
```bash
# 详细覆盖率分析
coverage run -m pytest
coverage report -m                    # 显示未覆盖行
coverage html                         # 生成HTML报告
coverage xml                          # 生成XML报告（CI集成）
```

### Mock工具

**unittest.mock** - Python标准Mock库
```python
from unittest.mock import Mock, patch, AsyncMock

# Mock对象
mock_service = Mock()
mock_service.get_prediction.return_value = {"id": "123"}

# 异步Mock
async_mock = AsyncMock()
async_mock.create_prediction.return_value = prediction

# Patch装饰器
@patch('src.repositories.prediction_repository.PredictionRepository')
async def test_with_patch(mock_repo_class):
    mock_repo = mock_repo_class.return_value
    mock_repo.create.return_value = prediction

    service = PredictionService(mock_repo)
    result = await service.create_prediction(data)

    mock_repo.create.assert_called_once_with(data)
```

**responses** - HTTP请求Mock
```python
import responses
import requests

@responses.activate
def test_api_call():
    responses.add(
        responses.GET,
        "https://api.football-data.org/matches",
        json={"matches": []},
        status=200
    )

    response = requests.get("https://api.football-data.org/matches")
    assert response.json() == {"matches": []}
```

### 测试数据管理

**factory-boy** - 测试数据工厂
```python
import factory
from src.domain.entities import Match, Team

class TeamFactory(factory.Factory):
    class Meta:
        model = Team

    id = factory.Faker('uuid4')
    name = factory.Faker('company')

class MatchFactory(factory.Factory):
    class Meta:
        model = Match

    id = factory.Faker('uuid4')
    home_team = factory.SubFactory(TeamFactory)
    away_team = factory.SubFactory(TeamFactory)
    match_date = factory.Faker('date_time')

# 使用示例
def test_with_factory():
    match = MatchFactory()
    assert match.home_team.name is not None
```

**pytest fixtures** - 测试数据和设置
```python
@pytest.fixture
def sample_match():
    """提供示例比赛数据"""
    return Match(
        id="test-match-123",
        home_team=Team(id="team-1", name="Team A"),
        away_team=Team(id="team-2", name="Team B"),
        match_date=datetime.now()
    )

@pytest.fixture
async def prediction_service():
    """提供预测服务实例"""
    return PredictionService()

def test_with_fixtures(sample_match, prediction_service):
    prediction = prediction_service.create_prediction(sample_match)
    assert prediction.match_id == sample_match.id
```

---

## 📈 覆盖率管理

### 覆盖率目标策略

**渐进式覆盖率提升**
```bash
# 当前状态：29% → 目标状态：40%
# 阶段1：达到30%（Smart Tests核心模块）
# 阶段2：达到35%（扩展到主要业务逻辑）
# 阶段3：达到40%（全面覆盖）
```

### 覆盖率配置详解

**pytest.ini 配置**
```ini
[tool:pytest]
# 覆盖率配置
addopts = --cov=src --cov-report=term-missing --cov-report=html:htmlcov

# 覆盖率阈值
--cov-fail-under=40

# 包含的源码目录
--cov-branch

# 忽略的文件
--cov-ignore-errors

# 覆盖率报告格式
--cov-report=term-missing:skip-covered
--cov-report=html:htmlcov
--cov-report=xml
```

### 覆盖率分析命令

**基础覆盖率报告**
```bash
make coverage                # 生成基础覆盖率报告
make coverage-unit          # 单元测试覆盖率
make coverage-integration   # 集成测试覆盖率
make cov.html               # HTML详细报告
```

**增强覆盖率分析**
```bash
make test-enhanced-coverage    # 增强覆盖率分析
make test-coverage-monitor     # 覆盖率趋势监控
make cov.enforce              # 强制执行覆盖率阈值
```

### 覆盖率优化策略

**1. 智能覆盖率报告**
```bash
# 按模块分析覆盖率
pytest --cov=src.domain --cov-report=term-missing
pytest --cov=src.api --cov-report=term-missing

# 按文件分析覆盖率
pytest --cov=src/utils/date_utils.py --cov-report=term-missing
```

**2. 覆盖率趋势监控**
```bash
# 生成覆盖率趋势报告
python3 scripts/coverage_trend_analyzer.py

# 设置覆盖率监控
make test-coverage-monitor
```

**3. 覆盖率门槛执行**
```bash
# 严格执行覆盖率阈值
make cov.enforce

# 渐进式提升覆盖率
make improve-coverage
```

---

## 🚀 测试执行策略

### 开发阶段测试

**快速反馈循环（<2分钟）**
```bash
# Smart Tests - 核心稳定测试
make test.smart

# 增量测试 - 仅运行变更相关测试
pytest --testmon               # 基于代码变更运行测试

# 最小验证 - 关键功能测试
pytest -m "critical and unit and fast"
```

**功能验证（<5分钟）**
```bash
# 扩展智能测试
make test.smart-extended

# API核心功能测试
pytest -m "api and critical"

# 业务逻辑测试
pytest -m "domain or services"
```

### 代码提交前测试

**完整验证（<15分钟）**
```bash
# 完整单元测试
make test.unit

# 代码质量检查
make check-quality

# 覆盖率验证
make coverage

# 完整CI模拟
make prepush
```

### CI/CD流水线测试

**并行执行策略**
```yaml
# .github/workflows/test.yml
jobs:
  test-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run unit tests
        run: make test.unit

  test-integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
    steps:
      - uses: actions/checkout@v3
      - name: Run integration tests
        run: make test.integration

  test-coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Generate coverage report
        run: make coverage
      - name: Upload to codecov
        uses: codecov/codecov-action@v3
```

### 性能测试策略

**定期性能测试**
```bash
# 每日性能基准测试
make test-performance-daily

# 性能回归检测
make test-performance-regression

# 负载测试
make test-load
```

---

## 🔧 测试配置详解

### pytest.ini 完整配置

```ini
[tool:pytest]
# 基础配置
minversion = 6.0
addopts =
    --strict-markers
    --strict-config
    --tb=short
    -ra
    --cov=src
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=40
    --import-mode=importlib

# 测试目录
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*

# 标记定义
markers =
    # 测试类型标记
    unit: 单元测试
    integration: 集成测试
    e2e: 端到端测试
    performance: 性能测试
    smoke: 冒烟测试
    regression: 回归测试
    security: 安全测试
    compatibility: 兼容性测试

    # 执行特征标记
    slow: 慢速测试 (>30s)
    fast: 快速测试 (<1s)
    medium: 中等速度测试 (1s-30s)
    stable: 稳定测试 (通过率>95%)
    flaky: 不稳定测试 (偶发性失败)
    critical: 关键功能测试 (必须通过)
    optional: 可选测试 (允许失败)
    local: 仅本地环境执行
    ci: 仅CI环境执行
    production: 生产环境测试
    debug: 调试测试

    # 功能域标记
    api: API接口测试
    domain: 领域逻辑测试
    services: 应用服务测试
    database: 数据库相关测试
    cache: 缓存相关测试
    ml: 机器学习模块测试
    utils: 工具类测试
    decorators: 装饰器测试
    config: 配置相关测试
    di: 依赖注入测试
    cqrs: CQRS模式测试
    events: 事件系统测试
    strategies: 策略模式测试
    adapters: 适配器模式测试
    monitoring: 监控相关测试

    # 依赖环境标记
    docker: 需要Docker环境
    network: 需要网络连接
    external_api: 需要外部API调用
    filesystem: 需要文件系统访问
    memory: 需要大量内存
    gpu: 需要GPU支持

    # 数据状态标记
    requires_data: 需要测试数据
    generates_data: 生成测试数据
    cleanup_required: 需要清理数据
    stateful: 状态相关测试

# 异步测试配置
asyncio_mode = auto

# 日志配置
log_cli = true
log_cli_level = INFO
log_cli_format = %(asctime)s [%(levelname)8s] %(name)s: %(message)s

# 过滤警告
filterwarnings =
    ignore::UserWarning
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

### conftest.py 配置

```python
# tests/conftest.py
import pytest
import asyncio
from unittest.mock import AsyncMock
from src.database.adapters.postgresql_adapter import PostgreSQLAdapter
from src.cache.redis_client import RedisClient

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def test_database():
    """测试数据库连接"""
    adapter = PostgreSQLAdapter("postgresql://test:test@localhost/test_db")
    await adapter.connect()
    yield adapter
    await adapter.disconnect()

@pytest.fixture
async def test_redis():
    """测试Redis连接"""
    redis_client = RedisClient("redis://localhost:6379/1")
    await redis_client.connect()
    yield redis_client
    await redis_client.disconnect()

@pytest.fixture
def mock_prediction_service():
    """Mock预测服务"""
    return AsyncMock()

@pytest.fixture
def sample_prediction_data():
    """示例预测数据"""
    return {
        "match_id": "test-match-123",
        "strategy_type": "ml_model",
        "prediction_data": {
            "home_win": 0.6,
            "draw": 0.3,
            "away_win": 0.1
        }
    }
```

---

## 🐛 测试调试技巧

### 调试命令

**详细调试输出**
```bash
# 显示详细输出
pytest -v -s

# 显示最长10个失败测试的详细信息
pytest --tb=long --maxfail=10

# 进入调试器
pytest --pdb

# 仅在失败时进入调试器
pytest --pdb -x
```

**选择性测试执行**
```bash
# 运行特定测试文件
pytest tests/unit/api/test_predictions.py

# 运行特定测试函数
pytest tests/unit/api/test_predictions.py::test_create_prediction

# 运行特定测试类
pytest tests/unit/api/test_predictions.py::TestPredictionAPI

# 基于名称模式运行测试
pytest -k "prediction"
```

### 调试技巧

**1. 使用print调试**
```python
def test_complex_logic():
    data = get_complex_data()
    print(f"Debug: data = {data}")  # 添加调试输出
    result = process_data(data)
    print(f"Debug: result = {result}")
    assert result["status"] == "success"
```

**2. 使用pytest hooks**
```python
# conftest.py
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """在测试失败时执行额外调试"""
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed:
        # 执行调试逻辑
        print(f"Test failed: {item.name}")
        print(f"Error: {rep.longrepr}")
```

**3. 条件断点**
```python
def test_with_conditional_breakpoint():
    for i, data in enumerate(test_data):
        result = process_data(data)
        if i == 42:  # 在第43次迭代时中断
            import pdb; pdb.set_trace()
        assert result is not None
```

### 常见问题解决

**1. 异步测试问题**
```python
# 问题：异步函数未正确执行
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()  # 确保使用await
    assert result is not None
```

**2. Mock问题**
```python
# 问题：Mock未正确替换
@patch('module.ClassName')  # 确保路径正确
def test_with_mock(mock_class):
    instance = mock_class.return_value
    instance.method.return_value = "mocked_value"

    result = function_that_uses_class()
    assert result == "mocked_value"
```

**3. 异常测试**
```python
# 问题：异常未正确捕获
def test_exception_raised():
    with pytest.raises(ValueError, match="specific error message"):
        function_that_raises_value_error()
```

---

## 📝 测试最佳实践

### 1. 测试命名规范

**描述性测试名称**
```python
def test_prediction_service_creates_prediction_successfully():
    """测试预测服务成功创建预测"""
    pass

def test_prediction_service_raises_error_when_match_data_invalid():
    """测试当比赛数据无效时预测服务抛出错误"""
    pass

def test_prediction_service_returns_correct_confidence_score():
    """测试预测服务返回正确的置信度分数"""
    pass
```

### 2. 测试结构（AAA模式）

**Arrange - Act - Assert**
```python
def test_prediction_creation():
    # Arrange - 准备测试数据和环境
    match_data = {
        "home_team": "Team A",
        "away_team": "Team B",
        "match_date": "2023-12-25"
    }
    service = PredictionService()

    # Act - 执行被测试的操作
    prediction = service.create_prediction(match_data)

    # Assert - 验证结果
    assert prediction is not None
    assert prediction.home_team == "Team A"
    assert prediction.away_team == "Team B"
```

### 3. 测试数据管理

**使用工厂模式**
```python
class PredictionFactory:
    @staticmethod
    def create_basic():
        return Prediction(
            id="test-123",
            match=MatchFactory.create_basic(),
            strategy_type="ml_model",
            prediction_data={"home_win": 0.6}
        )

    @staticmethod
    def create_with_high_confidence():
        prediction = PredictionFactory.create_basic()
        prediction.confidence_score = 0.95
        return prediction
```

### 4. 测试隔离

**每个测试独立**
```python
@pytest.fixture
async def isolated_database():
    """为每个测试提供独立的数据库"""
    # 创建临时数据库
    temp_db_name = f"test_db_{uuid.uuid4().hex[:8]}"

    # 设置数据库
    await setup_temp_database(temp_db_name)

    yield temp_db_name

    # 清理数据库
    await cleanup_temp_database(temp_db_name)
```

### 5. 测试覆盖策略

**核心路径优先**
```python
# 优先测试核心业务流程
def test_prediction_workflow_core():
    """测试预测核心工作流"""
    # 1. 获取比赛数据
    # 2. 选择预测策略
    # 3. 生成预测
    # 4. 保存预测结果
    # 5. 返回预测结果
    pass

# 其次测试边界条件
def test_prediction_with_edge_cases():
    """测试边界条件"""
    # 1. 空数据
    # 2. 无效格式
    # 3. 极端值
    # 4. 并发场景
    pass
```

### 6. 测试性能优化

**避免重复设置**
```pytest
@pytest.fixture(scope="module")
def expensive_service():
    """模块级别的昂贵服务设置"""
    return ExpensiveService()

def test1(expensive_service):
    result1 = expensive_service.method1()
    assert result1 is not None

def test2(expensive_service):
    result2 = expensive_service.method2()
    assert result2 is not None
```

### 7. 测试文档化

**文档字符串**
```python
def test_ml_prediction_strategy():
    """测试ML预测策略

    验证ML策略能够：
    1. 正确提取特征
    2. 调用模型进行预测
    3. 返回格式化的预测结果
    4. 处理模型预测失败的情况

    Args:
        None

    Returns:
        None

    Raises:
        AssertionError: 当预测结果不符合预期时
    """
    pass
```

---

## 🎯 测试策略总结

### 开发阶段建议

**1. 日常开发**
```bash
# 快速验证（<2分钟）
make test.smart

# 功能验证（<5分钟）
pytest -m "critical and fast"
```

**2. 提交前**
```bash
# 完整验证（<15分钟）
make prepush

# 质量检查
make check-quality
```

**3. 发布前**
```bash
# 全面测试（<1小时）
make test.ci-full

# 性能测试
make test.performance-release
```

### 质量保证策略

**1. 覆盖率目标**
- 当前：29%
- 短期目标：35%
- 长期目标：40%

**2. 测试稳定性**
- 目标通过率：>95%
- 关键测试通过率：100%

**3. 执行效率**
- Smart Tests：<2分钟
- 完整单元测试：<10分钟
- 全套测试：<30分钟

---

*文档版本: v1.0 | 更新时间: 2025-11-16*