#!/usr/bin/env python3
"""
测试框架自动化构建脚本
快速生成基础测试文件和配置
"""

import json
from pathlib import Path


class TestFrameworkBuilder:
    """测试框架构建器"""

    def __init__(self):
        self.project_root = Path.cwd()
        self.src_dir = self.project_root / "src"
        self.tests_dir = self.project_root / "tests"
        self.fixtures_dir = self.tests_dir / "fixtures"
        self.factories_dir = self.tests_dir / "factories"

        # 测试目录结构
        self.test_structure = {
            "unit": {
                "api": ["test_health.py", "test_auth.py", "test_predictions.py"],
                "services": ["test_prediction_service.py", "test_user_service.py"],
                "models": ["test_match.py", "test_prediction.py", "test_user.py"],
                "utils": ["test_crypto_utils.py", "test_i18n.py", "test_validators.py"],
                "database": ["test_config.py", "test_connections.py"],
                "middleware": ["test_i18n.py", "test_security.py", "test_performance.py"]
            },
            "integration": {
                "api": ["test_api_db_integration.py", "test_api_cache_integration.py"],
                "database": ["test_migrations.py", "test_relationships.py"],
                "cache": ["test_redis_integration.py", "test_cache_strategies.py"],
                "external": ["test_mlflow_integration.py", "test_external_apis.py"]
            },
            "e2e": {
                "scenarios": ["test_user_journey.py", "test_prediction_flow.py"],
                "performance": ["test_load.py", "test_stress.py"],
                "security": ["test_authentication_flow.py", "test_authorization.py"]
            }
        }

    def create_directory_structure(self):
        """创建测试目录结构"""
        print("📁 创建测试目录结构...")

        for test_type, modules in self.test_structure.items():
            test_path = self.tests_dir / test_type
            test_path.mkdir(parents=True, exist_ok=True)

            # 创建__init__.py
            (test_path / "__init__.py").touch(exist_ok=True)

            for module_name, test_files in modules.items():
                module_path = test_path / module_name
                module_path.mkdir(exist_ok=True)

                # 创建__init__.py
                (module_path / "__init__.py").touch(exist_ok=True)

        # 创建固定目录
        self.fixtures_dir.mkdir(exist_ok=True)
        self.factories_dir.mkdir(exist_ok=True)

        print("✅ 目录结构创建完成")

    def create_pytest_config(self):
        """创建pytest配置文件"""
        print("\n⚙️  创建pytest配置...")

        # pytest.ini
        pytest_ini = """[tool:pytest]
# pytest配置文件

# 测试目录
testpaths = tests

# Python路径
python_paths = src

# 测试文件模式
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*

# 标记
markers =
    unit: 单元测试
    integration: 集成测试
    e2e: 端到端测试
    smoke: 冒烟测试
    slow: 慢速测试
    security: 安全测试
    performance: 性能测试
    api: API测试
    database: 数据库测试
    cache: 缓存测试

# 最小版本
minversion = 8.0

# 添加选项
addopts =
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=20
    --durations=10
    --maxfail=5

# 过滤警告
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
    ignore::UserWarning
"""

        with open("pytest.ini", "w", encoding="utf-8") as f:
            f.write(pytest_ini)

        # pyproject.toml pytest配置
        pyproject_content = """
[tool.pytest.ini_options]
# 现代pytest配置
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

markers = [
    "unit: 单元测试",
    "integration: 集成测试",
    "e2e: 端到端测试",
    "smoke: 冒烟测试",
    "slow: 慢速测试",
    "security: 安全测试",
    "performance: 性能测试",
    "api: API测试",
    "database: 数据库测试",
    "cache: 缓存测试"
]

addopts = [
    "--strict-markers",
    "--strict-config",
    "--verbose",
    "--tb=short",
    "--cov=src",
    "--cov-report=html",
    "--cov-report=term-missing",
    "--cov-fail-under=20",
    "--durations=10",
    "--maxfail=5"
]

filterwarnings = [
    "ignore::DeprecationWarning",
    "ignore::PendingDeprecationWarning",
    "ignore::UserWarning"
]
"""

        # 读取现有pyproject.toml
        if Path("pyproject.toml").exists():
            with open("pyproject.toml", "r", encoding="utf-8") as f:
                content = f.read()

            # 检查是否已有pytest配置
            if "[tool.pytest.ini_options]" not in content:
                with open("pyproject.toml", "a", encoding="utf-8") as f:
                    f.write(pyproject_content)

        print("✅ pytest配置创建完成")

    def create_conftest_files(self):
        """创建conftest.py文件"""
        print("\n📝 创建conftest.py文件...")

        # 根目录conftest.py
        root_conftest = '''"""pytest配置文件"""

import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_redis():
    """模拟Redis客户端"""
    from unittest.mock import MagicMock
    redis_mock = MagicMock()
    redis_mock.ping.return_value = True
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = 1
    return redis_mock


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    from sqlalchemy.ext.asyncio import AsyncSession

    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = AsyncMock()
    session.commit.return_value = None
    session.rollback.return_value = None
    session.close.return_value = None
    return session


@pytest.fixture
def test_client():
    """测试客户端"""
    from src.main import app

    client = TestClient(app)
    return client


@pytest.fixture
async def async_client():
    """异步测试客户端"""
    from src.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_user_data():
    """示例用户数据"""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPassword123!",
        "full_name": "Test User"
    }


@pytest.fixture
def sample_prediction_data():
    """示例预测数据"""
    return {
        "match_id": 12345,
        "home_team": "Team A",
        "away_team": "Team B",
        "predicted_home_score": 2,
        "predicted_away_score": 1,
        "confidence": 0.75
    }


@pytest.fixture
def auth_headers():
    """认证头"""
    return {
        "Authorization": "Bearer test_token_here",
        "Content-Type": "application/json"
    }


# 测试标记
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line(
        "markers", "slow: 标记测试为慢速测试"
    )
    config.addinivalue_line(
        "markers", "integration: 标记为集成测试"
    )
    config.addinivalue_line(
        "markers", "e2e: 标记为端到端测试"
    )


# 测试收集钩子
def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    for item in items:
        # 自动添加标记
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
'''
        with open(self.tests_dir / "conftest.py", "w", encoding="utf-8") as f:
            f.write(root_conftest)

        # API目录conftest.py
        api_conftest = '''"""API测试配置"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture
def api_client():
    """API测试客户端"""
    from src.main import app

    # 测试配置
    app.dependency_overrides = {}

    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_auth_service():
    """模拟认证服务"""
    with patch("src.api.auth.AuthService") as mock:
        mock.verify_token.return_value = {"user_id": 1, "email": "test@example.com"}
        yield mock


@pytest.fixture
def mock_prediction_service():
    """模拟预测服务"""
    with patch("src.api.predictions.PredictionService") as mock:
        mock.create_prediction.return_value = {"id": 1, "status": "success"}
        mock.get_prediction.return_value = {"id": 1, "result": "2-1"}
        yield mock
'''
        api_dir = self.tests_dir / "unit" / "api"
        with open(api_dir / "conftest.py", "w", encoding="utf-8") as f:
            f.write(api_conftest)

        print("✅ conftest.py文件创建完成")

    def create_test_templates(self):
        """创建测试模板文件"""
        print("\n📄 创建测试模板...")

        # API测试模板
        api_test_template = '''"""API测试模板"""

import pytest
from fastapi import status
from unittest.mock import patch, MagicMock


class TestHealthAPI:
    """健康检查API测试"""

    def test_health_check_success(self, api_client):
        """测试健康检查成功"""
        response = api_client.get("/api/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    def test_health_check_with_database(self, api_client, mock_db_session):
        """测试带数据库检查的健康检查"""
        with patch("src.api.health.database.check") as mock_check:
            mock_check.return_value = True

            response = api_client.get("/api/health?check_db=true")

            assert response.status_code == status.HTTP_200_OK
            assert response.json()["database"] == "connected"

    @pytest.mark.parametrize("endpoint", ["/api/health", "/api/health/", "/health"])
    def test_health_check_endpoints(self, api_client, endpoint):
        """测试多个健康检查端点"""
        response = api_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK


class TestPredictionAPI:
    """预测API测试"""

    def test_create_prediction_success(self, api_client, auth_headers, sample_prediction_data):
        """测试创建预测成功"""
        with patch("src.api.predictions.PredictionService") as mock_service:
            mock_service.create_prediction.return_value = {
                "id": 1,
                **sample_prediction_data,
                "status": "pending"
            }

            response = api_client.post(
                "/api/predictions",
                json=sample_prediction_data,
                headers=auth_headers
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["id"] == 1
            assert data["status"] == "pending"

    def test_create_prediction_unauthorized(self, api_client, sample_prediction_data):
        """测试未授权创建预测"""
        response = api_client.post("/api/predictions", json=sample_prediction_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_prediction_invalid_data(self, api_client, auth_headers):
        """测试无效数据创建预测"""
        invalid_data = {"match_id": "invalid"}

        response = api_client.post(
            "/api/predictions",
            json=invalid_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_prediction_success(self, api_client, auth_headers):
        """测试获取预测成功"""
        with patch("src.api.predictions.PredictionService") as mock_service:
            mock_service.get_prediction.return_value = {
                "id": 1,
                "result": "2-1",
                "confidence": 0.75
            }

            response = api_client.get("/api/predictions/1", headers=auth_headers)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == 1

    def test_get_prediction_not_found(self, api_client, auth_headers):
        """测试获取不存在的预测"""
        with patch("src.api.predictions.PredictionService") as mock_service:
            mock_service.get_prediction.return_value = None

            response = api_client.get("/api/predictions/999", headers=auth_headers)

            assert response.status_code == status.HTTP_404_NOT_FOUND
'''
        api_test_path = self.tests_dir / "unit" / "api" / "test_health.py"
        with open(api_test_path, "w", encoding="utf-8") as f:
            f.write(api_test_template)

        # Service测试模板
        service_test_template = '''"""服务层测试模板"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime


class TestPredictionService:
    """预测服务测试"""

    @pytest.fixture
    def service(self, mock_db_session, mock_redis):
        """创建服务实例"""
        from src.services.prediction_service import PredictionService
        return PredictionService(db=mock_db_session, redis=mock_redis)

    @pytest.mark.asyncio
    async def test_create_prediction_success(self, service, sample_prediction_data):
        """测试创建预测成功"""
        # 模拟数据库保存
        service.db.add = MagicMock()
        service.db.commit = AsyncMock()
        service.db.refresh = AsyncMock()

        # 模拟Redis缓存
        service.redis.set = AsyncMock(return_value=True)

        result = await service.create_prediction(sample_prediction_data)

        assert result is not None
        assert result["status"] == "success"
        service.db.add.assert_called_once()
        service.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_prediction_duplicate(self, service, sample_prediction_data):
        """测试创建重复预测"""
        # 模拟已存在预测
        service.redis.get = AsyncMock(return_value=b'{"exists": true}')

        with pytest.raises(ValueError, match="Prediction already exists"):
            await service.create_prediction(sample_prediction_data)

    @pytest.mark.asyncio
    async def test_get_prediction_success(self, service):
        """测试获取预测成功"""
        # 模拟Redis缓存
        service.redis.get = AsyncMock(return_value=b'{"id": 1, "result": "2-1"}')

        result = await service.get_prediction(1)

        assert result is not None
        assert result["id"] == 1
        assert result["result"] == "2-1"

    @pytest.mark.asyncio
    async def test_get_prediction_not_found(self, service):
        """测试获取不存在的预测"""
        # 模拟Redis无数据
        service.redis.get = AsyncMock(return_value=None)

        # 模拟数据库查询
        service.db.execute = AsyncMock()
        service.db.fetch_one = AsyncMock(return_value=None)

        result = await service.get_prediction(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_prediction_confidence(self, service):
        """测试更新预测置信度"""
        # 模拟更新操作
        service.db.execute = AsyncMock()
        service.db.commit = AsyncMock()

        result = await service.update_prediction_confidence(1, 0.85)

        assert result is True
        service.db.execute.assert_called_once()
        service.db.commit.assert_called_once()
'''
        service_test_path = self.tests_dir / "unit" / "services" / "test_prediction_service.py"
        with open(service_test_path, "w", encoding="utf-8") as f:
            f.write(service_test_template)

        # 集成测试模板
        integration_test_template = '''"""集成测试模板"""

import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


@pytest.mark.integration
class TestAPIIntegration:
    """API集成测试"""

    @pytest.fixture
    async def test_db(self):
        """测试数据库连接"""
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False
        )

        # 创建表
        from src.database.models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield engine
        await engine.dispose()

    @pytest.fixture
    async def db_session(self, test_db):
        """数据库会话"""
        async_session = sessionmaker(
            test_db, class_=AsyncSession, expire_on_commit=False
        )

        async with async_session() as session:
            yield session

    async def test_create_user_and_prediction_flow(self, async_client, db_session):
        """测试创建用户和预测的完整流程"""
        # 1. 创建用户
        user_data = {
            "email": "integration@test.com",
            "username": "integration_user",
            "password": "TestPass123!"
        }

        response = await async_client.post("/api/users", json=user_data)
        assert response.status_code == 201
        user_id = response.json()["id"]

        # 2. 用户登录
        login_data = {
            "username": "integration_user",
            "password": "TestPass123!"
        }

        response = await async_client.post("/api/auth/login", json=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]

        # 3. 创建预测
        headers = {"Authorization": f"Bearer {token}"}
        prediction_data = {
            "match_id": 54321,
            "home_team": "Integration Team A",
            "away_team": "Integration Team B",
            "predicted_home_score": 2,
            "predicted_away_score": 1
        }

        response = await async_client.post(
            "/api/predictions",
            json=prediction_data,
            headers=headers
        )
        assert response.status_code == 201
        prediction_id = response.json()["id"]

        # 4. 获取预测
        response = await async_client.get(
            f"/api/predictions/{prediction_id}",
            headers=headers
        )
        assert response.status_code == 200
        assert response.json()["id"] == prediction_id

        # 5. 验证数据库中的数据
        from src.database.models import User, Prediction
        result = await db_session.get(User, user_id)
        assert result is not None
        assert result.email == "integration@test.com"

        result = await db_session.get(Prediction, prediction_id)
        assert result is not None
        assert result.match_id == 54321


@pytest.mark.integration
@pytest.mark.slow
class TestCacheIntegration:
    """缓存集成测试"""

    async def test_prediction_caching(self, async_client, mock_redis):
        """测试预测缓存"""
        # 模拟Redis
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        # 创建预测
        prediction_data = {
            "match_id": 12345,
            "home_team": "Cache Test A",
            "away_team": "Cache Test B",
            "predicted_home_score": 3,
            "predicted_away_score": 1
        }

        response = await async_client.post("/api/predictions", json=prediction_data)
        assert response.status_code == 201

        # 验证缓存设置
        mock_redis.set.assert_called()

        # 再次获取预测
        mock_redis.get.return_value = b'{"id": 1, "result": "3-1"}'

        response = await async_client.get("/api/predictions/1")
        assert response.status_code == 200
'''
        integration_test_path = self.tests_dir / "integration" / "api" / "test_api_db_integration.py"
        with open(integration_test_path, "w", encoding="utf-8") as f:
            f.write(integration_test_template)

        print("✅ 测试模板创建完成")

    def create_test_factories(self):
        """创建测试数据工厂"""
        print("\n🏭 创建测试数据工厂...")

        # factory_base.py
        factory_base = '''"""测试工厂基类"""

import factory
from factory import fuzzy
import uuid
from datetime import datetime, timedelta
import faker

fake = faker.Faker()


class BaseFactory(factory.alchemy.SQLAlchemyModelFactory):
    """基础工厂类"""

    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "flush"
'''
        with open(self.factories_dir / "__init__.py", "w", encoding="utf-8") as f:
            f.write('"""测试数据工厂包"""\n')
        with open(self.factories_dir / "base.py", "w", encoding="utf-8") as f:
            f.write(factory_base)

        # user_factory.py
        user_factory = '''"""用户工厂"""

import factory
from factory import fuzzy
from .base import BaseFactory


class UserFactory(BaseFactory):
    """用户工厂"""

    class Meta:
        model = None  # 需要导入实际模型
        sqlalchemy_session = None

    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    username = factory.Faker("user_name")
    full_name = factory.Faker("name")
    hashed_password = factory.LazyFunction(lambda: "hashed_password_here")
    is_active = True
    is_verified = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        """设置密码"""
        if extracted:
            self.set_password(extracted)


class AdminUserFactory(UserFactory):
    """管理员用户工厂"""

    is_admin = True
    is_verified = True
    email = factory.LazyAttribute(lambda o: f"admin.{o.username}@example.com")
'''
        with open(self.factories_dir / "user_factory.py", "w", encoding="utf-8") as f:
            f.write(user_factory)

        # prediction_factory.py
        prediction_factory = '''"""预测工厂"""

import factory
from factory import fuzzy
from datetime import datetime, timedelta
from .base import BaseFactory


class MatchFactory(BaseFactory):
    """比赛工厂"""

    class Meta:
        model = None  # 需要导入实际模型
        sqlalchemy_session = None

    home_team = factory.Faker("company")
    away_team = factory.Faker("company")
    match_date = factory.LazyFunction(lambda: datetime.now() + timedelta(days=fuzzy.FuzzyInteger(1, 30).fuzz()))
    league = factory.Faker("word")
    season = factory.LazyFunction(lambda: datetime.now().year)
    is_finished = False
    home_score = None
    away_score = None


class PredictionFactory(BaseFactory):
    """预测工厂"""

    class Meta:
        model = None  # 需要导入实际模型
        sqlalchemy_session = None

    match_id = 1
    predicted_home_score = fuzzy.FuzzyInteger(0, 5)
    predicted_away_score = fuzzy.FuzzyInteger(0, 5)
    confidence = fuzzy.FuzzyFloat(0.5, 1.0)
    created_at = factory.LazyFunction(datetime.now)
    status = fuzzy.FuzzyChoice(["pending", "processing", "completed", "failed"])
    result = None

    @factory.post_generation
    def set_result(self, create, extracted, **kwargs):
        """设置结果"""
        if self.status == "completed" and not self.result:
            self.result = f"{self.predicted_home_score}-{self.predicted_away_score}"
'''
        with open(self.factories_dir / "prediction_factory.py", "w", encoding="utf-8") as f:
            f.write(prediction_factory)

        print("✅ 测试数据工厂创建完成")

    def create_test_data_fixtures(self):
        """创建测试数据fixtures"""
        print("\n📦 创建测试数据fixtures...")

        # sample_data.py
        sample_data = '''"""示例测试数据"""

# 用户数据
SAMPLE_USERS = [
    {
        "email": "john.doe@example.com",
        "username": "johndoe",
        "full_name": "John Doe",
        "password": "SecurePass123!",
        "is_active": True,
        "is_verified": True
    },
    {
        "email": "jane.smith@example.com",
        "username": "janesmith",
        "full_name": "Jane Smith",
        "password": "SecurePass456!",
        "is_active": True,
        "is_verified": False
    },
    {
        "email": "admin@example.com",
        "username": "admin",
        "full_name": "Admin User",
        "password": "AdminPass789!",
        "is_active": True,
        "is_verified": True,
        "is_admin": True
    }
]

# 比赛数据
SAMPLE_MATCHES = [
    {
        "id": 1001,
        "home_team": "Manchester United",
        "away_team": "Liverpool",
        "match_date": "2025-10-10T20:00:00Z",
        "league": "Premier League",
        "season": 2025
    },
    {
        "id": 1002,
        "home_team": "Barcelona",
        "away_team": "Real Madrid",
        "match_date": "2025-10-12T21:00:00Z",
        "league": "La Liga",
        "season": 2025
    },
    {
        "id": 1003,
        "home_team": "Bayern Munich",
        "away_team": "Paris Saint-Germain",
        "match_date": "2025-10-15T19:45:00Z",
        "league": "Champions League",
        "season": 2025
    }
]

# 预测数据
SAMPLE_PREDICTIONS = [
    {
        "match_id": 1001,
        "predicted_home_score": 2,
        "predicted_away_score": 1,
        "confidence": 0.75,
        "reasoning": "Home team advantage"
    },
    {
        "match_id": 1002,
        "predicted_home_score": 1,
        "predicted_away_score": 1,
        "confidence": 0.60,
        "reasoning": "Even match"
    },
    {
        "match_id": 1003,
        "predicted_home_score": 3,
        "predicted_away_score": 2,
        "confidence": 0.80,
        "reasoning": "Strong attack"
    }
]

# API测试载荷
API_REQUESTS = {
    "create_user": {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPass123!",
        "full_name": "Test User"
    },
    "login": {
        "username": "testuser",
        "password": "TestPass123!"
    },
    "create_prediction": {
        "match_id": 1001,
        "home_team": "Team A",
        "away_team": "Team B",
        "predicted_home_score": 2,
        "predicted_away_score": 1,
        "confidence": 0.75
    },
    "update_prediction": {
        "predicted_home_score": 3,
        "predicted_away_score": 1,
        "confidence": 0.85
    }
}
'''
        with open(self.fixtures_dir / "sample_data.py", "w", encoding="utf-8") as f:
            f.write(sample_data)

        # json_fixtures.py
        json_fixtures = '''"""JSON格式测试fixtures"""

import json
from pathlib import Path


def load_json_fixture(filename):
    """加载JSON fixture"""
    fixture_path = Path(__file__).parent / "json" / filename
    if fixture_path.exists():
        with open(fixture_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# 预定义的JSON响应
API_RESPONSES = {
    "health_check": {
        "status": "healthy",
        "timestamp": "2025-10-04T10:00:00Z",
        "version": "1.0.0",
        "database": "connected",
        "cache": "connected"
    },
    "error_response": {
        "detail": "Validation error",
        "errors": [
            {
                "field": "email",
                "message": "Invalid email format"
            }
        ]
    },
    "prediction_created": {
        "id": 1,
        "status": "pending",
        "created_at": "2025-10-04T10:00:00Z"
    }
}
'''
        with open(self.fixtures_dir / "json_fixtures.py", "w", encoding="utf-8") as f:
            f.write(json_fixtures)

        # 创建json目录
        json_dir = self.fixtures_dir / "json"
        json_dir.mkdir(exist_ok=True)

        # health_response.json
        health_response = {
            "status": "healthy",
            "timestamp": "2025-10-04T10:00:00Z",
            "version": "1.0.0",
            "database": "connected",
            "cache": "connected"
        }
        with open(json_dir / "health_response.json", "w", encoding="utf-8") as f:
            json.dump(health_response, f, indent=2)

        print("✅ 测试数据fixtures创建完成")

    def create_makefile_commands(self):
        """创建Makefile测试命令"""
        print("\n📋 创建Makefile测试命令...")

        makefile_commands = """
# 测试命令
test:
	@echo "运行所有测试"
	pytest tests/ -v

test-unit:
	@echo "运行单元测试"
	pytest tests/unit/ -v -m "unit"

test-integration:
	@echo "运行集成测试"
	pytest tests/integration/ -v -m "integration"

test-e2e:
	@echo "运行端到端测试"
	pytest tests/e2e/ -v -m "e2e"

test-smoke:
	@echo "运行冒烟测试"
	pytest tests/ -v -m "smoke"

test-coverage:
	@echo "运行测试并生成覆盖率报告"
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

test-watch:
	@echo "监视文件变化并运行测试"
	pytest-watch tests/

test-parallel:
	@echo "并行运行测试"
	pytest tests/ -n auto

test-failed:
	@echo "只运行失败的测试"
	pytest tests/ --lf

test-debug:
	@echo "调试模式运行测试"
	pytest tests/ -v -s --tb=long

test-performance:
	@echo "运行性能测试"
	pytest tests/e2e/performance/ -v -m "performance"

test-security:
	@echo "运行安全测试"
	pytest tests/ -v -m "security"

# 清理测试数据
clean-test:
	@echo "清理测试数据"
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# 生成测试报告
test-report:
	@echo "生成测试报告"
	pytest tests/ --html=test-report.html --self-contained-html
"""

        # 读取现有Makefile
        makefile_path = Path("Makefile")
        if makefile_path.exists():
            with open(makefile_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 检查是否已有测试命令
            if "test-unit:" not in content:
                with open(makefile_path, "a", encoding="utf-8") as f:
                    f.write("\n" + makefile_commands)

        print("✅ Makefile测试命令添加完成")

    def build_complete_framework(self):
        """构建完整测试框架"""
        print("🚀 构建测试框架...")
        print("=" * 60)

        self.create_directory_structure()
        self.create_pytest_config()
        self.create_conftest_files()
        self.create_test_templates()
        self.create_test_factories()
        self.create_test_data_fixtures()
        self.create_makefile_commands()

        print("\n" + "=" * 60)
        print("✅ 测试框架构建完成!")
        print("\n📌 下一步操作:")
        print("1. 运行测试: make test-unit")
        print("2. 查看覆盖率: make test-coverage")
        print("3. 监视模式: make test-watch")
        print("4. 清理数据: make clean-test")
        print("\n📊 预期覆盖率增长:")
        print("  - Week 1: 20% (基础测试)")
        print("  - Week 2: 50% (核心功能)")
        print("  - Week 3: 70% (业务逻辑)")
        print("  - Week 4: 85% (集成和E2E)")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="测试框架构建工具")
    parser.add_argument(
        "--only-config",
        action="store_true",
        help="仅创建配置文件"
    )
    parser.add_argument(
        "--only-templates",
        action="store_true",
        help="仅创建测试模板"
    )

    args = parser.parse_args()

    builder = TestFrameworkBuilder()

    if args.only_config:
        builder.create_pytest_config()
        builder.create_conftest_files()
    elif args.only_templates:
        builder.create_test_templates()
    else:
        builder.build_complete_framework()


if __name__ == "__main__":
    main()