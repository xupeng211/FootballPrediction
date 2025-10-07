# 测试覆盖率提升执行计划

## 概述

本文档详细说明了如何按照系统性方案执行测试覆盖率提升计划，从当前的16%提升到80%的目标。

## 第一阶段：基础设施改进（第1周）

### Day 1-2: 环境配置

#### 1.1 配置TestContainers

创建 `tests/conftest.py` 的增强版本：

```python
# tests/conftest.py
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="session")
def postgres_container():
    """创建PostgreSQL测试容器"""
    with PostgresContainer("postgres:14-alpine") as postgres:
        yield postgres

@pytest.fixture(scope="session")
def redis_container():
    """创建Redis测试容器"""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis

@pytest.fixture
def test_database(postgres_container):
    """创建测试数据库连接"""
    engine = create_engine(postgres_container.get_connection_url())
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()

@pytest.fixture
def test_session(test_database):
    """创建测试会话"""
    Session = sessionmaker(bind=test_database)
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
```

#### 1.2 环境变量管理

创建 `.env.test`：

```bash
# .env.test
ENVIRONMENT=test
TESTING=true
DEBUG=true
LOG_LEVEL=DEBUG

# 数据库配置（由TestContainers动态设置）
DATABASE_URL=postgresql://test:test@localhost:5432/test_db

# Redis配置（由TestContainers动态设置）
REDIS_URL=redis://localhost:6379/1

# 外部服务Mock
ENABLE_FEAST=false
ENABLE_KAFKA=false
ENABLE_MLFLOW=false

# API配置
API_HOST=127.0.0.1
API_PORT=8001
```

#### 1.3 依赖问题修复

创建 `scripts/fix_dependencies.py`：

```python
#!/usr/bin/env python3
"""
修复循环导入和依赖问题
"""

import os
import re
from pathlib import Path

def fix_circular_imports():
    """修复循环导入"""
    # 检测循环导入
    circular_imports = detect_circular_imports()

    # 生成报告
    report = []
    for cycle in circular_imports:
        report.append(f"发现循环导入: {' -> '.join(cycle)}")

    # 修复策略
    fixes = generate_fixes(circular_imports)

    return report, fixes

def detect_circular_imports():
    """检测循环导入"""
    # 实现循环导入检测逻辑
    pass

def generate_fixes(cycles):
    """生成修复建议"""
    fixes = []
    for cycle in cycles:
        # 建议引入依赖注入
        if len(cycle) == 2:
            fixes.append({
                "type": "dependency_injection",
                "modules": cycle,
                "solution": "使用配置或工厂模式解耦"
            })
        # 建议重构模块
        elif len(cycle) > 2:
            fixes.append({
                "type": "refactor",
                "modules": cycle,
                "solution": "将共同依赖提取到新模块"
            })
    return fixes

if __name__ == "__main__":
    report, fixes = fix_circular_imports()
    print("循环导入检测报告:")
    for item in report:
        print(f"  - {item}")

    print("\n修复建议:")
    for fix in fixes:
        print(f"  - {fix}")
```

### Day 3-4: CI/CD流水线

#### 1.4 GitHub Actions配置

创建 `.github/workflows/coverage.yml`：

```yaml
name: Test Coverage

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11]

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Cache pip dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements/dev.lock
        pip install pytest-cov pytest-benchmark pytest-mock

    - name: Run tests with coverage
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        REDIS_URL: redis://localhost:6379/1
        TESTING: true
      run: |
        pytest --cov=src --cov-report=xml --cov-report=html --cov-report=term-missing --cov-fail-under=20

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

    - name: Archive coverage HTML
      uses: actions/upload-artifact@v3
      with:
        name: coverage-report
        path: htmlcov/
```

#### 1.5 质量门禁

创建 `.github/workflows/quality-gate.yml`：

```yaml
name: Quality Gate

on:
  pull_request:
    branches: [ main ]

jobs:
  quality-check:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install black flake8 mypy bandit safety

    - name: Code formatting check
      run: black --check --diff src/ tests/

    - name: Lint
      run: flake8 src/ tests/

    - name: Type check
      run: mypy src --ignore-missing-imports

    - name: Security check
      run: bandit -r src/ -f json -o bandit-report.json

    - name: Dependency check
      run: safety check --json --output safety-report.json

    - name: Coverage trend check
      run: |
        # 获取当前覆盖率
        pytest --cov=src --cov-report=term-missing --tb=no -q > coverage.log
        COVERAGE=$(grep "TOTAL" coverage.log | awk '{print $4}' | sed 's/%//')

        # 获取基准覆盖率
        BASE_COVERAGE=$(jq -r '.coverage' .coverage-baseline.json)

        # 检查是否下降
        if (( $(echo "$COVERAGE < $BASE_COVERAGE" | bc -l) )); then
          echo "Coverage decreased from ${BASE_COVERAGE}% to ${COVERAGE}%"
          exit 1
        fi
```

### Day 5: 测试数据管理

#### 1.6 创建测试数据工厂

创建 `tests/factories.py`：

```python
import factory
from factory import fuzzy
from datetime import datetime, timedelta
import random

from src.database.models.team import Team
from src.database.models.league import League
from src.database.models.match import Match
from src.database.models.odds import Odds

class TeamFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Team
        sqlalchemy_session_persistence = "commit"

    name = factory.Faker('company')
    short_name = factory.LazyAttribute(lambda obj: obj.name[:3].upper())
    country = factory.Faker('country_code')
    founded_year = fuzzy.FuzzyInteger(1900, 2020)
    stadium_capacity = fuzzy.FuzzyInteger(1000, 100000)

class LeagueFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = League
        sqlalchemy_session_persistence = "commit"

    name = factory.Faker('company')
    country = factory.Faker('country_code')
    level = fuzzy.FuzzyInteger(1, 5)
    season_start = fuzzy.FuzzyDate(datetime(2023, 1, 1), datetime(2023, 8, 1))
    season_end = fuzzy.FuzzyDate(datetime(2023, 8, 1), datetime(2024, 6, 1))

class MatchFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Match
        sqlalchemy_session_persistence = "commit"

    home_team = factory.SubFactory(TeamFactory)
    away_team = factory.SubFactory(TeamFactory)
    league = factory.SubFactory(LeagueFactory)
    match_time = fuzzy.FuzzyDateTime(datetime.now(), datetime.now() + timedelta(days=30))
    status = fuzzy.FuzzyChoice(['scheduled', 'live', 'finished', 'postponed'])
    home_score = fuzzy.FuzzyInteger(0, 5)
    away_score = fuzzy.FuzzyInteger(0, 5)

class OddsFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Odds
        sqlalchemy_session_persistence = "commit"

    match = factory.SubFactory(MatchFactory)
    bookmaker = factory.Faker('company')
    home_win_odds = fuzzy.FuzzyFloat(1.0, 10.0)
    draw_odds = fuzzy.FuzzyFloat(2.0, 5.0)
    away_win_odds = fuzzy.FuzzyFloat(1.0, 10.0)
    updated_at = factory.LazyFunction(datetime.now)

# 创建测试数据生成器
class TestDataGenerator:
    @staticmethod
    def create_test_league_with_teams(session, num_teams=20):
        """创建包含球队的测试联赛"""
        league = LeagueFactory()
        teams = [TeamFactory() for _ in range(num_teams)]

        # 添加球队到联赛
        for team in teams:
            league.teams.append(team)

        session.commit()
        return league, teams

    @staticmethod
    def create_test_matches(session, league, teams, num_matches=100):
        """创建测试比赛"""
        matches = []
        for _ in range(num_matches):
            home_team = random.choice(teams)
            away_team = random.choice([t for t in teams if t != home_team])
            match = MatchFactory(
                home_team=home_team,
                away_team=away_team,
                league=league
            )
            matches.append(match)

        session.commit()
        return matches

    @staticmethod
    def create_test_season(session):
        """创建完整的测试赛季数据"""
        # 创建联赛
        league, teams = TestDataGenerator.create_test_league_with_teams(session)

        # 创建比赛
        matches = TestDataGenerator.create_test_matches(session, league, teams)

        # 创建赔率
        for match in matches:
            OddsFactory(match=match)

        session.commit()
        return league, teams, matches
```

## 第二阶段：核心模块覆盖（第2周）

### Day 6-7: API层测试

#### 2.1 创建API测试基类

创建 `tests/base_api_test.py`：

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

class BaseAPITest:
    """API测试基类"""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        from src.main import app
        self.client = TestClient(app)

    @pytest.fixture
    def auth_headers(self):
        """认证头"""
        return {
            "Authorization": "Bearer test_token",
            "Content-Type": "application/json"
        }

    def assert_valid_response(self, response, expected_status=200):
        """验证响应格式"""
        assert response.status_code == expected_status
        assert "application/json" in response.headers["content-type"]

        data = response.json()
        assert isinstance(data, dict)

        if expected_status == 200:
            assert "success" in data or "data" in data

        return data

    def assert_error_response(self, response, expected_status, expected_error):
        """验证错误响应"""
        assert response.status_code == expected_status

        data = response.json()
        assert "error" in data or "detail" in data
        assert expected_error in str(data)
```

#### 2.2 健康检查API测试

创建 `tests/unit/api/test_health_enhanced.py`：

```python
import pytest
from unittest.mock import patch, MagicMock
from tests.base_api_test import BaseAPITest

class TestHealthAPIEnhanced(BaseAPITest):
    """增强的健康检查API测试"""

    def test_health_check_basic(self):
        """测试基本健康检查"""
        response = self.client.get("/api/health")
        data = self.assert_valid_response(response)

        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    @patch('src.api.health.redis_manager')
    def test_health_check_with_redis_unavailable(self, mock_redis):
        """测试Redis不可用时的健康检查"""
        mock_redis.ping.side_effect = Exception("Redis connection failed")

        response = self.client.get("/api/health")
        data = self.assert_valid_response(response)

        assert data["status"] == "degraded"
        assert "redis" in data["services"]
        assert data["services"]["redis"]["status"] == "error"

    @patch('src.api.health.DatabaseManager')
    def test_health_check_with_database_unavailable(self, mock_db):
        """测试数据库不可用时的健康检查"""
        mock_db.check_connection.side_effect = Exception("DB connection failed")

        response = self.client.get("/api/health")
        data = self.assert_valid_response(response, status=503)

        assert data["status"] == "unhealthy"
        assert "database" in data["services"]

    def test_health_check_detailed(self):
        """测试详细健康检查"""
        response = self.client.get("/api/health?detailed=true")
        data = self.assert_valid_response(response)

        # 验证详细信息
        assert "services" in data
        assert "system" in data

        # 系统信息
        system = data["system"]
        assert "cpu_usage" in system
        assert "memory_usage" in system
        assert "disk_usage" in system

    def test_health_check_with_components(self):
        """测试组件健康检查"""
        response = self.client.get("/api/health/components")
        data = self.assert_valid_response(response)

        # 验证各组件状态
        components = ["api", "database", "redis", "cache", "predictions"]
        for component in components:
            assert component in data
            assert "status" in data[component]
            assert "response_time" in data[component]
```

#### 2.3 配置API测试

创建 `tests/unit/api/test_config_api.py`：

```python
import pytest
import os
from unittest.mock import patch
from tests.base_api_test import BaseAPITest

class TestConfigAPI(BaseAPITest):
    """配置API测试"""

    def test_get_config_basic(self):
        """测试获取基本配置"""
        response = self.client.get("/api/config")
        data = self.assert_valid_response(response)

        # 验证公开配置
        assert "api_version" in data
        assert "environment" in data
        assert "features" in data

        # 确保敏感信息不暴露
        sensitive_keys = ["secret_key", "database_url", "api_key"]
        for key in sensitive_keys:
            assert key not in data

    @patch.dict(os.environ, {"FEATURE_FLAG_NEW_UI": "true"})
    def test_get_config_with_feature_flags(self):
        """测试功能开关配置"""
        response = self.client.get("/api/config?include_features=true")
        data = self.assert_valid_response(response)

        assert "features" in data
        features = data["features"]
        assert "new_ui" in features
        assert features["new_ui"] is True

    def test_update_config_unauthorized(self):
        """测试未授权更新配置"""
        response = self.client.post("/api/config", json={
            "debug": True
        })
        assert response.status_code == 401

    def test_update_config_authorized(self, auth_headers):
        """测试授权更新配置"""
        with patch('src.api.config.ConfigService.update_config') as mock_update:
            mock_update.return_value = {"debug": True, "updated": True}

            response = self.client.post(
                "/api/config",
                json={"debug": True},
                headers=auth_headers
            )
            data = self.assert_valid_response(response)

            assert data["debug"] is True
            assert data["updated"] is True
```

### Day 8-9: 工具类测试

#### 2.4 时间工具测试

创建 `tests/unit/utils/test_time_utils_comprehensive.py`：

```python
import pytest
from datetime import datetime, timedelta, timezone
import pytz
from src.utils.time_utils import (
    format_datetime,
    parse_datetime,
    get_timezone_aware_time,
    calculate_duration,
    is_business_day,
    get_next_business_day
)

class TestTimeUtilsComprehensive:
    """时间工具综合测试"""

    @pytest.mark.parametrize("dt,fmt,expected", [
        (datetime(2025, 1, 1, 12, 0, 0), "%Y-%m-%d", "2025-01-01"),
        (datetime(2025, 1, 1, 12, 0, 0), "%H:%M:%S", "12:00:00"),
        (datetime(2025, 1, 1, 12, 0, 0), "%Y年%m月%d日", "2025年01月01日"),
    ])
    def test_format_datetime(self, dt, fmt, expected):
        """测试日期时间格式化"""
        result = format_datetime(dt, fmt)
        assert result == expected

    def test_format_datetime_with_timezone(self):
        """测试时区日期时间格式化"""
        dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = format_datetime(dt, "%Y-%m-%d %H:%M:%S %Z")
        assert "UTC" in result

    @pytest.mark.parametrize("date_str,fmt,expected", [
        ("2025-01-01", "%Y-%m-%d", datetime(2025, 1, 1)),
        ("12:00:00", "%H:%M:%S", datetime(1900, 1, 1, 12, 0, 0)),
        ("2025-01-01T12:00:00", "%Y-%m-%dT%H:%M:%S", datetime(2025, 1, 1, 12, 0, 0)),
    ])
    def test_parse_datetime(self, date_str, fmt, expected):
        """测试日期时间解析"""
        result = parse_datetime(date_str, fmt)
        assert result == expected

    def test_parse_iso_datetime(self):
        """测试ISO格式日期时间解析"""
        iso_str = "2025-01-01T12:00:00Z"
        result = parse_datetime(iso_str, "%Y-%m-%dT%H:%M:%SZ")
        assert result.tzinfo is not None

    def test_get_timezone_aware_time(self):
        """测试获取时区感知时间"""
        utc_time = get_timezone_aware_time("UTC")
        assert utc_time.tzinfo == pytz.UTC

        shanghai_time = get_timezone_aware_time("Asia/Shanghai")
        assert shanghai_time.tzinfo == pytz.timezone("Asia/Shanghai")

    @pytest.mark.parametrize("start,end,expected_hours", [
        (datetime(2025, 1, 1, 12, 0), datetime(2025, 1, 1, 15, 0), 3.0),
        (datetime(2025, 1, 1, 12, 0), datetime(2025, 1, 2, 12, 0), 24.0),
        (datetime(2025, 1, 1, 12, 30), datetime(2025, 1, 1, 13, 15), 0.75),
    ])
    def test_calculate_duration(self, start, end, expected_hours):
        """测试计算时间差"""
        duration = calculate_duration(start, end)
        assert duration == timedelta(hours=expected_hours)

    @pytest.mark.parametrize("date,is_business", [
        (datetime(2025, 1, 6), True),   # 周一
        (datetime(2025, 1, 7), True),   # 周二
        (datetime(2025, 1, 8), True),   # 周三
        (datetime(2025, 1, 9), True),   # 周四
        (datetime(2025, 1, 10), True),  # 周五
        (datetime(2025, 1, 11), False),  # 周六
        (datetime(2025, 1, 12), False),  # 周日
    ])
    def test_is_business_day(self, date, is_business):
        """测试工作日判断"""
        assert is_business_day(date) == is_business

    def test_get_next_business_day(self):
        """测试获取下一个工作日"""
        friday = datetime(2025, 1, 10)  # 周五
        next_day = get_next_business_day(friday)
        assert next_day.weekday() == 0  # 应该是周一

        wednesday = datetime(2025, 1, 8)  # 周三
        next_day = get_next_business_day(wednesday)
        assert next_day.weekday() == 3  # 应该是周四

    def test_edge_cases(self):
        """测试边界情况"""
        # 闰年2月29日
        leap_day = datetime(2024, 2, 29)
        formatted = format_datetime(leap_day, "%Y-%m-%d")
        assert formatted == "2024-02-29"

        # 时间戳转换
        timestamp = 1704067200  # 2024-01-01 00:00:00 UTC
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        assert dt.year == 2024
```

### Day 10: 服务基类测试

创建 `tests/unit/services/test_base_service_comprehensive.py`：

```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.services.base import BaseService
from src.core.config import get_settings

class TestBaseServiceComprehensive:
    """基础服务综合测试"""

    def test_service_initialization(self):
        """测试服务初始化"""
        service = BaseService()
        assert service.settings is not None
        assert service.logger is not None
        assert service.service_name == "BaseService"

    def test_service_with_custom_name(self):
        """测试自定义服务名称"""
        service = BaseService(service_name="CustomService")
        assert service.service_name == "CustomService"

    @patch('src.services.base.redis_manager')
    def test_health_check_healthy(self, mock_redis):
        """测试健康检查 - 健康"""
        mock_redis.ping.return_value = True

        service = BaseService()
        health = service.health_check()

        assert health["status"] == "healthy"
        assert health["service"] == service.service_name
        assert "timestamp" in health

    @patch('src.services.base.redis_manager')
    def test_health_check_unhealthy(self, mock_redis):
        """测试健康检查 - 不健康"""
        mock_redis.ping.side_effect = Exception("Redis error")

        service = BaseService()
        health = service.health_check()

        assert health["status"] == "unhealthy"
        assert "error" in health

    def test_get_config_value(self):
        """测试获取配置值"""
        service = BaseService()

        # �存在的配置
        api_host = service.get_config("api_host")
        assert api_host is not None

        # 不存在的配置，返回默认值
        default_value = service.get_config("nonexistent_key", "default")
        assert default_value == "default"

    def test_log_info(self):
        """测试信息日志"""
        service = BaseService()
        with patch.object(service.logger, 'info') as mock_log:
            service.log_info("Test message", extra={"key": "value"})
            mock_log.assert_called_once_with("Test message", extra={"key": "value"})

    def test_log_error(self):
        """测试错误日志"""
        service = BaseService()
        with patch.object(service.logger, 'error') as mock_log:
            service.log_error("Error message", exc_info=True)
            mock_log.assert_called_once_with("Error message", exc_info=True)

    @pytest.mark.asyncio
    async def test_async_method(self):
        """测试异步方法"""
        service = BaseService()

        # 模拟异步操作
        with patch.object(service, '_async_operation', AsyncMock(return_value="result")):
            result = await service.execute_async()
            assert result == "result"

    def test_service_metrics(self):
        """测试服务指标"""
        service = BaseService()

        # 记录指标
        service.record_metric("requests", 1)
        service.record_metric("errors", 0)

        metrics = service.get_metrics()
        assert metrics["requests"] == 1
        assert metrics["errors"] == 0
```

## 第三阶段：服务层集成（第3周）

### Day 11-13: 数据处理服务测试

### Day 14-15: 缓存服务测试

## 第四阶段：端到端测试（第4周）

### Day 16-18: 集成测试场景

### Day 19-20: E2E测试框架

## 持续改进

### 每日任务

1. **运行测试套件**
   ```bash
   make test-quick
   make coverage
   ```

2. **检查覆盖率报告**
   ```bash
   open htmlcov/index.html
   ```

3. **更新任务板**
   - 标记完成的任务
   - 记录遇到的问题
   - 更新覆盖率数据

### 每周回顾

1. **覆盖率趋势分析**
   - 生成趋势报告
   - 识别改进点
   - 调整下周计划

2. **代码质量审查**
   - 检查新增测试质量
   - 审查Mock使用是否合理
   - 确保测试数据管理规范

## 最佳实践总结

### 测试编写原则

1. **AAA模式**：Arrange（准备）、Act（执行）、Assert（断言）
2. **单一职责**：每个测试只验证一个功能点
3. **独立性**：测试之间不应相互依赖
4. **可读性**：测试名称应清楚表达测试意图

### Mock使用原则

1. **只Mock外部依赖**：数据库、网络、文件系统等
2. **不Mock业务逻辑**：核心逻辑应该被真实测试
3. **验证Mock交互**：确保Mock被正确调用

### 测试数据管理

1. **使用Factory模式**：生成测试数据
2. **隔离测试数据**：每个测试使用独立数据
3. **清理机制**：测试后清理数据

---

*本执行计划将根据实际情况持续更新和优化*