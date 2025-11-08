# 测试综合指南

## 📋 概述

足球比赛结果预测系统的完整测试指南，涵盖单元测试、集成测试、端到端测试和性能测试的最佳实践。

## 🧪 测试架构

### 测试金字塔

```
    /\
   /  \     E2E Tests (2%)
  /____\
 /      \   Integration Tests (12%)
/________\  Unit Tests (85%)
```

### 测试分类

| 类型 | 占比 | 目标 | 工具 |
|------|------|------|------|
| **单元测试** | 85% | 测试单个函数/类 | pytest, unittest.mock |
| **集成测试** | 12% | 测试组件交互 | pytest, testcontainers |
| **端到端测试** | 2% | 完整用户流程 | Playwright, Selenium |
| **性能测试** | 1% | 基准测试和性能分析 | pytest-benchmark, locust |

## 🏗️ 测试项目结构

```
tests/
├── unit/                    # 单元测试 (85%)
│   ├── api/                # API层测试
│   ├── core/               # 核心模块测试
│   ├── database/           # 数据库测试
│   ├── domain/             # 领域逻辑测试
│   ├── services/           # 业务服务测试
│   └── utils/              # 工具类测试
├── integration/            # 集成测试 (12%)
│   ├── api/                # API集成测试
│   ├── database/           # 数据库集成测试
│   └── external/           # 外部服务集成测试
├── e2e/                    # 端到端测试 (2%)
│   ├── user_workflows/     # 用户工作流测试
│   └── api_workflows/      # API工作流测试
├── performance/            # 性能测试 (1%)
│   ├── benchmarks/         # 基准测试
│   └── load/               # 负载测试
├── fixtures/               # 测试数据夹具
├── conftest.py            # pytest配置
└── requirements-test.txt   # 测试依赖
```

## 🚀 快速开始

### 环境准备

```bash
# 1. 安装测试依赖
make install

# 2. 环境检查
make env-check

# 3. 智能修复（解决环境问题）
python3 scripts/smart_quality_fixer.py

# 4. 验证测试环境
pytest tests/unit/utils/test_date_utils.py::test_format_date_iso -v
```

### 常用测试命令

```bash
# 运行所有单元测试
make test.unit

# 运行特定模块测试
pytest tests/unit/utils/ -v

# 运行单个测试文件
pytest tests/unit/core/test_di.py -v

# 运行单个测试方法
pytest tests/unit/api/test_health.py::test_health_check_basic -v

# 查看覆盖率报告
make coverage

# 运行性能测试
pytest tests/performance/ -v

# 运行集成测试
pytest tests/integration/ -v
```

## 📊 测试标记系统

项目使用47个标准化测试标记，支持精确的测试选择：

### 核心标记

```bash
# 按测试类型
pytest -m "unit"              # 单元测试 (85%)
pytest -m "integration"       # 集成测试 (12%)
pytest -m "e2e"               # 端到端测试 (2%)
pytest -m "performance"       # 性能测试 (1%)

# 按优先级
pytest -m "critical"          # 关键功能测试
pytest -m "high"              # 高优先级测试
pytest -m "medium"            # 中等优先级测试
pytest -m "low"               # 低优先级测试

# 按功能域
pytest -m "api and critical"  # API关键功能测试
pytest -m "domain or services" # 业务逻辑测试
pytest -m "database"           # 数据库相关测试
pytest -m "cache"              # 缓存相关测试
pytest -m "auth"               # 认证相关测试
pytest -m "utils"              # 工具模块测试
pytest -m "core"               # 核心模块测试
```

### Smart Tests组合

```bash
# 核心稳定测试 - 执行时间<2分钟，通过率>90%
pytest tests/unit/utils tests/unit/cache tests/unit/core -v --maxfail=20
```

## 🎯 单元测试最佳实践

### 测试命名规范

```python
class TestClassName:
    def test_method_scenario_expected_result(self):
        """测试方法_场景_期望结果"""
        pass

# 示例
class TestPredictionService:
    def test_create_prediction_valid_data_success(self):
        """测试创建预测_有效数据_成功"""
        pass

    def test_create_prediction_invalid_data_raises_validation_error(self):
        """测试创建预测_无效数据_抛出验证错误"""
        pass
```

### 测试结构 (AAA模式)

```python
def test_user_service_create_user_success():
    # Arrange (准备)
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "SecurePass123!"
    }
    user_service = UserService()

    # Act (执行)
    result = user_service.create_user(user_data)

    # Assert (断言)
    assert result["email"] == user_data["email"]
    assert result["username"] == user_data["username"]
    assert "id" in result
    assert "password" not in result  # 密码不应返回
```

### Mock和Fixture使用

```python
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def mock_database():
    """模拟数据库连接"""
    return Mock()

@pytest.fixture
def user_service(mock_database):
    """创建用户服务实例"""
    return UserService(database=mock_database)

def test_get_user_by_id_found(user_service, mock_database):
    # 设置mock返回值
    mock_database.get_user.return_value = {
        "id": 1,
        "email": "test@example.com",
        "username": "testuser"
    }

    # 执行测试
    result = user_service.get_user_by_id(1)

    # 验证结果和mock调用
    assert result["id"] == 1
    mock_database.get_user.assert_called_once_with(1)

# 使用patch装饰器
@patch('src.services.external.weather_api.get_weather')
def test_prediction_service_with_weather(mock_weather_api):
    mock_weather_api.return_value = {"temperature": 25, "humidity": 60}

    service = PredictionService()
    result = service.create_prediction_with_weather(match_data)

    assert "weather" in result
    mock_weather_api.assert_called_once()
```

### 异步测试

```python
import pytest
import asyncio
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_async_service_process_data():
    # 准备
    async_service = AsyncService()
    test_data = {"value": 42}

    # 执行
    result = await async_service.process_data(test_data)

    # 断言
    assert result["processed"] is True
    assert result["original_value"] == 42

@pytest.mark.asyncio
async def test_async_service_with_mock():
    # 准备
    mock_async_client = AsyncMock()
    mock_async_client.fetch.return_value = {"status": "success"}

    service = AsyncService(client=mock_async_client)

    # 执行
    result = await service.fetch_external_data()

    # 断言
    assert result["status"] == "success"
    mock_async_client.fetch.assert_called_once()
```

## 🔗 集成测试最佳实践

### 数据库集成测试

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.base import Base
from src.services.prediction import PredictionService

@pytest.fixture(scope="function")
def test_db():
    """创建测试数据库"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.mark.integration
def test_prediction_service_crud_operations(test_db):
    """测试预测服务的CRUD操作"""
    service = PredictionService(db_session=test_db)

    # 创建
    prediction_data = {
        "match_id": 1,
        "predicted_result": "home_win",
        "confidence": 0.75
    }
    created = service.create_prediction(prediction_data)
    assert created.id is not None

    # 读取
    retrieved = service.get_prediction(created.id)
    assert retrieved.predicted_result == "home_win"

    # 更新
    updated = service.update_prediction(created.id, {"confidence": 0.80})
    assert updated.confidence == 0.80

    # 删除
    service.delete_prediction(created.id)
    with pytest.raises(Exception):
        service.get_prediction(created.id)
```

### API集成测试

```python
import pytest
from fastapi.testclient import TestClient
from src.main import app

@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)

@pytest.mark.integration
def test_prediction_api_full_workflow(client):
    """测试预测API的完整工作流"""
    # 创建预测
    prediction_data = {
        "match_id": 123,
        "predicted_result": "draw",
        "confidence": 0.65
    }
    response = client.post("/api/v1/predictions", json=prediction_data)
    assert response.status_code == 201
    created_prediction = response.json()

    # 获取预测
    response = client.get(f"/api/v1/predictions/{created_prediction['id']}")
    assert response.status_code == 200
    retrieved = response.json()
    assert retrieved["predicted_result"] == "draw"

    # 更新预测
    update_data = {"confidence": 0.70}
    response = client.patch(f"/api/v1/predictions/{created_prediction['id']}", json=update_data)
    assert response.status_code == 200
    updated = response.json()
    assert updated["confidence"] == 0.70

    # 删除预测
    response = client.delete(f"/api/v1/predictions/{created_prediction['id']}")
    assert response.status_code == 204

    # 验证删除
    response = client.get(f"/api/v1/predictions/{created_prediction['id']}")
    assert response.status_code == 404
```

## 🚀 端到端测试最佳实践

### 用户工作流测试

```python
import pytest
from playwright.sync_api import Page, expect

@pytest.mark.e2e
def test_user_prediction_workflow(page: Page):
    """测试用户完整预测工作流"""
    # 1. 用户登录
    page.goto("/login")
    page.fill("[data-testid=email]", "user@example.com")
    page.fill("[data-testid=password]", "password123")
    page.click("[data-testid=login-button]")

    # 2. 导航到预测页面
    page.click("[data-testid=predictions-nav]")
    expect(page).to_have_url("/predictions")

    # 3. 创建预测
    page.click("[data-testid=new-prediction-button]")
    page.select_option("[data-testid=match-select]", "123")
    page.select_option("[data-testid=result-select]", "home_win")
    page.fill("[data-testid=confidence-input]", "75")
    page.click("[data-testid=save-prediction-button]")

    # 4. 验证预测已创建
    expect(page.locator("[data-testid=prediction-success]")).to_be_visible()
    expect(page.locator("[data-testid=prediction-list]")).to_contain_text("home_win")
```

### API工作流测试

```python
import pytest
import requests

@pytest.mark.e2e
def test_complete_prediction_api_workflow():
    """测试完整的预测API工作流"""
    base_url = "http://localhost:8000"

    # 1. 用户认证
    auth_response = requests.post(f"{base_url}/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    token = auth_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. 获取可用比赛
    matches_response = requests.get(f"{base_url}/api/v1/matches", headers=headers)
    matches = matches_response.json()
    assert len(matches) > 0

    # 3. 创建预测
    prediction_data = {
        "match_id": matches[0]["id"],
        "predicted_result": "home_win",
        "confidence": 0.75
    }
    prediction_response = requests.post(
        f"{base_url}/api/v1/predictions",
        json=prediction_data,
        headers=headers
    )
    assert prediction_response.status_code == 201
    prediction = prediction_response.json()

    # 4. 获取用户所有预测
    user_predictions = requests.get(f"{base_url}/api/v1/predictions/my", headers=headers)
    predictions = user_predictions.json()
    assert any(p["id"] == prediction["id"] for p in predictions)
```

## ⚡ 性能测试最佳实践

### 基准测试

```python
import pytest
from src.services.prediction import PredictionService

@pytest.mark.performance
def test_prediction_service_performance_benchmark():
    """测试预测服务性能基准"""
    service = PredictionService()
    test_data = {
        "match_id": 123,
        "predicted_result": "home_win",
        "confidence": 0.75
    }

    # 使用pytest-benchmark
    result = service.create_prediction(test_data)

    assert result["id"] is not None

    # 测试响应时间
    start_time = time.time()
    for i in range(100):
        service.create_prediction({
            **test_data,
            "match_id": test_data["match_id"] + i
        })
    end_time = time.time()

    # 100次操作应在1秒内完成
    assert (end_time - start_time) < 1.0
```

### 负载测试

```python
import pytest
import asyncio
import aiohttp

@pytest.mark.performance
async def test_api_concurrent_requests():
    """测试API并发请求性能"""
    base_url = "http://localhost:8000"

    async def make_request(session, url):
        async with session.get(url) as response:
            return await response.json()

    async with aiohttp.ClientSession() as session:
        # 并发执行50个请求
        tasks = [
            make_request(session, f"{base_url}/health")
            for _ in range(50)
        ]
        results = await asyncio.gather(*tasks)

        # 验证所有请求都成功
        assert len(results) == 50
        for result in results:
            assert result["status"] == "healthy"
```

## 📈 覆盖率管理

### 覆盖率配置

pytest.ini 配置：

```ini
[tool:pytest]
addopts =
    --cov=src
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=30
    --cov-config=pyproject.toml
```

pyproject.toml 配置：

```toml
[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/migrations/*",
    "*/__pycache__/*",
    "*/venv/*",
    "*/env/*"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError"
]
```

### 覆盖率命令

```bash
# 生成覆盖率报告
make coverage

# 查看HTML报告
open htmlcov/index.html

# 检查特定模块覆盖率
pytest tests/unit/utils/ --cov=src.utils --cov-report=term-missing

# 设置最低覆盖率要求
pytest --cov=src --cov-fail-under=30
```

## 🛠️ 测试工具和配置

### pytest配置 (conftest.py)

```python
import pytest
import asyncio
from unittest.mock import AsyncMock

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_redis():
    """模拟Redis连接"""
    redis_mock = AsyncMock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = 1
    return redis_mock

@pytest.fixture
def mock_database_session():
    """模拟数据库会话"""
    session_mock = AsyncMock()
    session_mock.add.return_value = None
    session_mock.commit.return_value = None
    session_mock.refresh.return_value = None
    return session_mock
```

### 常用测试工具

```bash
# 测试数据生成
pip install factory_boy faker

# HTTP测试
pip install httpx

# 异步测试
pip install pytest-asyncio

# 性能测试
pip install pytest-benchmark

# Mock工具
pip install responses pytest-mock

# 测试覆盖率
pip install pytest-cov
```

## 🔍 测试调试

### 调试失败的测试

```bash
# 详细输出
pytest tests/unit/core/test_di.py::TestDI::test_container_resolve -v -s

# 进入调试器
pytest tests/unit/core/test_di.py::TestDI::test_container_resolve --pdb

# 只运行失败的测试
pytest --lf

# 停在第一个失败处
pytest -x

# 显示本地变量
pytest tests/unit/core/test_di.py -v --tb=short
```

### 测试性能分析

```bash
# 最慢的10个测试
pytest --durations=10

# 性能分析
pytest --profile-svg
```

## 📋 测试检查清单

### 单元测试检查清单

- [ ] 测试命名遵循 `test_method_scenario_expected_result` 格式
- [ ] 使用AAA模式（Arrange-Act-Assert）
- [ ] 每个测试只验证一个行为
- [ ] 使用描述性的断言消息
- [ ] Mock外部依赖
- [ ] 测试边界条件和异常情况
- [ ] 测试覆盖率满足要求

### 集成测试检查清单

- [ ] 使用真实的数据库连接（测试数据库）
- [ ] 测试组件间的交互
- [ ] 清理测试数据
- [ ] 测试事务回滚
- [ ] 验证数据一致性

### API测试检查清单

- [ ] 测试所有HTTP状态码
- [ ] 验证输入数据验证
- [ ] 测试认证和授权
- [ ] 测试错误处理
- [ ] 验证响应数据格式

## 🚨 常见问题和解决方案

### 问题1: 测试数据库连接失败

```python
# 解决方案：使用测试数据库配置
@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
```

### 问题2: 异步测试不执行

```python
# 解决方案：添加pytest标记
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### 问题3: Mock不生效

```python
# 解决方案：使用正确的patch路径
@patch('src.services.external.api_client.APIClient')
def test_service_with_mock(mock_api_client):
    # 使用服务相对于测试文件的路径
    pass
```

## 📚 参考资源

- [pytest官方文档](https://docs.pytest.org/)
- [pytest-asyncio文档](https://pytest-asyncio.readthedocs.io/)
- [pytest-mock文档](https://pytest-mock.readthedocs.io/)
- [测试覆盖率文档](https://coverage.readthedocs.io/)

---

*文档版本: v1.0 | 最后更新: 2025-11-08 | 维护者: Claude Code*