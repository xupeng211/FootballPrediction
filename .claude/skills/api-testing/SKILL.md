---
name: api-testing
description: Comprehensive API testing including unit tests, integration tests, performance testing, and automated test pipelines. Use when testing REST endpoints, validating API responses, load testing, or setting up test automation.
---

# API Testing Skill

## 技能概述
专业的API测试技能模块，专注于全面测试策略、性能测试和自动化测试流水线。

## 核心能力
- **功能测试**: 单元测试、集成测试、端到端测试
- **性能测试**: 负载测试、压力测试、并发测试
- **安全测试**: 认证授权、输入验证、SQL注入防护
- **API文档**: 自动化文档生成、API契约测试
- **测试自动化**: CI/CD集成、测试报告、质量门禁
- **监控测试**: 生产环境监控、混沌工程

## 当前应用场景：足球预测API测试
- **测试框架**: pytest + pytest-asyncio
- **API测试**: FastAPI TestClient + httpx
- **性能测试**: locust + k6
- **覆盖率**: pytest-cov
- **当前测试数**: 279个测试函数

## 工具和库
- **pytest**: 测试框架
- **httpx**: 异步HTTP客户端
- **locust**: 负载测试
- **pytest-cov**: 覆盖率测试
- **factory-boy**: 测试数据工厂
- **pytest-mock**: Mock和Stub
- **requests-mock**: HTTP请求Mock

## 快速开始（第一层）

### 基础API测试
```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    """健康检查测试"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_prediction_endpoint():
    """预测端点测试"""
    response = client.post(
        "/api/predict",
        json={
            "home_team": "Manchester United",
            "away_team": "Arsenal"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert "confidence" in data
```

## 深入测试（第二层）

### 异步测试和集成测试
```python
import pytest
import asyncio
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_async_prediction():
    """异步预测测试"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/predict",
            json={"home_team": "Team A", "away_team": "Team B"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["prediction"] in ["HOME", "DRAW", "AWAY"]
        assert 0 <= data["confidence"] <= 1

@pytest.mark.asyncio
async def test_database_integration():
    """数据库集成测试"""
    # 设置测试数据库
    test_db = await setup_test_database()

    try:
        # 测试数据存储
        result = await save_prediction_to_db(test_prediction)
        assert result["success"] is True

        # 测试数据检索
        saved = await get_prediction_from_db(result["id"])
        assert saved["prediction"] == test_prediction["prediction"]

    finally:
        # 清理测试数据
        await cleanup_test_database(test_db)
```

## 高级应用（第三层）

### 性能测试
```python
from locust import HttpUser, task, between

class FootballAPIUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def predict_match(self):
        """预测比赛任务"""
        self.client.post("/api/predict", json={
            "home_team": "Team A",
            "away_team": "Team B"
        })

    @task(1)
    def get_predictions(self):
        """获取预测历史任务"""
        self.client.get("/api/predictions")

    @task(1)
    def health_check(self):
        """健康检查任务"""
        self.client.get("/health")

# 运行性能测试
# locust -f performance_test.py --host=http://localhost:8000
```

## 测试策略

### 1. 测试金字塔
- **单元测试 (70%)**: 测试单个函数和类
- **集成测试 (20%)**: 测试组件间交互
- **端到端测试 (10%)**: 测试完整工作流

### 2. 测试分类
- **功能测试**: 验证API功能正确性
- **性能测试**: 验证API性能指标
- **安全测试**: 验证API安全防护
- **兼容性测试**: 验证API向后兼容性

## 覆盖率优化

### 目标覆盖率: 80%+
```bash
# 运行覆盖率测试
pytest --cov=src --cov-report=html --cov-report=term

# 生成覆盖率报告
coverage html
coverage report
```

### 覆盖率配置
```ini
# .coveragerc
[run]
source = src
omit =
    */tests/*
    */migrations/*
    */venv/*
    */__pycache__/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
```

## 自动化测试流水线

### GitHub Actions配置
```yaml
# .github/workflows/test.yml
name: API Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11]

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: testdb
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
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Run linting
      run: |
        flake8 src tests
        black --check src tests
        mypy src

    - name: Run tests with coverage
      env:
        DATABASE_URL: postgresql://postgres:testpass@localhost/testdb
        REDIS_URL: redis://localhost:6379
      run: |
        pytest --cov=src --cov-report=xml --cov-report=html

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3

    - name: Run performance tests
      run: |
        locust -f tests/performance/locustfile.py \
          --headless \
          --users 10 \
          --spawn-rate 2 \
          --run-time 30s \
          --host http://localhost:8000
```

## 最佳实践

1. **测试命名**: 使用描述性的测试名称
2. **测试隔离**: 确保测试之间相互独立
3. **测试数据**: 使用工厂模式生成测试数据
4. **Mock使用**: 合理使用Mock避免外部依赖
5. **断言清晰**: 使用清晰的断言信息
6. **测试维护**: 定期更新和重构测试

## Related Skills
- `fastapi-development`: FastAPI async API development
- `code-quality`: Code quality management
- `performance-monitoring`: System performance monitoring
- `football-prediction`: Football prediction system

---
*Last updated: 2025-12-28*
*Target: API测试覆盖率和质量提升*