from typing import List
from typing import Dict
from typing import Optional
from typing import Any
"""测试辅助工具 - 统一管理测试数据和Mock对象"""

from __future__ import annotations


import pytest

from tests.factories.data_factory import DataFactory

# # from tests.factories.mock_factory import MockFactory  # TODO: 创建MockFactory  # TODO: 创建MockFactory


class TestDataManager:
    """测试数据管理器"""

    def __init__(self):
        self.users: List[Any] = []
        self.matches: List[Any] = []
        self.predictions: List[Any] = []
        self.custom_data: Dict[str, Any] = {}

    def create_test_user(self, **overrides) -> Any:
        """创建测试用户"""
        from tests.factories import UserFactory

        _user = UserFactory.create(**overrides)
        self.users.append(user)
        return user

    def create_test_users(self, count: int, **overrides) -> List[Any]:
        """批量创建测试用户"""
        from tests.factories import UserFactory

        users = UserFactory.create_batch(count, **overrides)
        self.users.extend(users)
        return users

    def create_test_match(self, **overrides) -> Any:
        """创建测试比赛"""
        from tests.factories import MatchFactory

        match = MatchFactory.create(**overrides)
        self.matches.append(match)
        return match

    def create_test_prediction(self, **overrides) -> Any:
        """创建测试预测"""
        from tests.factories import PredictionFactory

        _prediction = PredictionFactory.create(**overrides)
        self.predictions.append(prediction)
        return prediction

    def get_user_by_username(self, username: str) -> Optional[Any]:
        """根据用户名获取用户"""
        for user in self.users:
            if hasattr(user, "username") and user.username == username:
                return user
        return None

    def clear_all(self):
        """清除所有数据"""
        self.users.clear()
        self.matches.clear()
        self.predictions.clear()
        self.custom_data.clear()


class MockManager:
    """Mock对象管理器"""

    def __init__(self):
        self.mocks: Dict[str, Mock] = {}
        self.data_manager = TestDataManager()

    def get_mock_user(self, name: str = "default", **overrides) -> Mock:
        """获取Mock用户"""
        key = f"user_{name}"
        if key not in self.mocks:
            self.mocks[key] = MockFactory.mock_user(**overrides)
        return self.mocks[key]

    def get_mock_repository(self, name: str = "default") -> Mock:
        """获取Mock仓储"""
        key = f"repository_{name}"
        if key not in self.mocks:
            self.mocks[key] = MockFactory.mock_repository()
        return self.mocks[key]

    def get_mock_db(self, name: str = "default") -> Mock:
        """获取Mock数据库连接"""
        key = f"db_{name}"
        if key not in self.mocks:
            self.mocks[key] = MockFactory.mock_database_connection()
        return self.mocks[key]

    def get_mock_redis(self, name: str = "default") -> Mock:
        """获取Mock Redis客户端"""
        key = f"redis_{name}"
        if key not in self.mocks:
            self.mocks[key] = MockFactory.mock_redis_client()
        return self.mocks[key]

    def get_mock_api_client(self, name: str = "default") -> Mock:
        """获取Mock API客户端"""
        key = f"api_{name}"
        if key not in self.mocks:
            self.mocks[key] = MockFactory.mock_api_client()
        return self.mocks[key]

    def get_mock_cache(self, name: str = "default") -> Mock:
        """获取Mock缓存服务"""
        key = f"cache_{name}"
        if key not in self.mocks:
            self.mocks[key] = MockFactory.mock_cache_service()
        return self.mocks[key]

    def get_mock_logger(self, name: str = "default") -> Mock:
        """获取Mock日志器"""
        key = f"logger_{name}"
        if key not in self.mocks:
            self.mocks[key] = MockFactory.mock_logger()
        return self.mocks[key]

    def get_mock_event_bus(self, name: str = "default") -> Mock:
        """获取Mock事件总线"""
        key = f"event_bus_{name}"
        if key not in self.mocks:
            self.mocks[key] = MockFactory.mock_event_bus()
        return self.mocks[key]

    def get_mock_scheduler(self, name: str = "default") -> Mock:
        """获取Mock任务调度器"""
        key = f"scheduler_{name}"
        if key not in self.mocks:
            self.mocks[key] = MockFactory.mock_scheduler()
        return self.mocks[key]

    def get_mock_email_service(self, name: str = "default") -> Mock:
        """获取Mock邮件服务"""
        key = f"email_{name}"
        if key not in self.mocks:
            self.mocks[key] = MockFactory.mock_email_service()
        return self.mocks[key]

    def clear_all_mocks(self):
        """清除所有Mock对象"""
        self.mocks.clear()
        self.data_manager.clear_all()


# 全局实例
test_data_manager = TestDataManager()
mock_manager = MockManager()


# pytest fixtures
@pytest.fixture
def data_manager():
    """提供测试数据管理器"""
    manager = TestDataManager()
    yield manager
    manager.clear_all()


@pytest.fixture
def manager():
    """提供Mock管理器"""
    manager = MockManager()
    yield manager
    manager.clear_all_mocks()


@pytest.fixture
def mock_user():
    """提供Mock用户"""
    return MockFactory.mock_user()


@pytest.fixture
def mock_repository():
    """提供Mock仓储"""
    return MockFactory.mock_repository()


@pytest.fixture
def mock_db():
    """提供Mock数据库连接"""
    return MockFactory.mock_database_connection()


@pytest.fixture
def mock_redis():
    """提供Mock Redis客户端"""
    return MockFactory.mock_redis_client()


@pytest.fixture
def mock_api_client():
    """提供Mock API客户端"""
    return MockFactory.mock_api_client()


@pytest.fixture
def mock_cache():
    """提供Mock缓存服务"""
    return MockFactory.mock_cache_service()


@pytest.fixture
def mock_logger():
    """提供Mock日志器"""
    return MockFactory.mock_logger()


@pytest.fixture
def mock_event_bus():
    """提供Mock事件总线"""
    return MockFactory.mock_event_bus()


@pytest.fixture
def mock_scheduler():
    """提供Mock任务调度器"""
    return MockFactory.mock_scheduler()


@pytest.fixture
def mock_email_service():
    """提供Mock邮件服务"""
    return MockFactory.mock_email_service()


# 便捷函数
def create_test_context():
    """创建测试上下文"""
    return {
        "data": test_data_manager,
        "mocks": mock_manager,
        "factory": DataFactory,
    }


def setup_test_mocks(required_mocks: List[str]) -> Dict[str, Mock]:
    """设置所需的Mock对象"""
    mocks = {}
    for mock_name in required_mocks:
        if mock_name == "user":
            mocks["user"] = mock_manager.get_mock_user()
        elif mock_name == "repository":
            mocks["repository"] = mock_manager.get_mock_repository()
        elif mock_name == "db":
            mocks["db"] = mock_manager.get_mock_db()
        elif mock_name == "redis":
            mocks["redis"] = mock_manager.get_mock_redis()
        elif mock_name == "api":
            mocks["api"] = mock_manager.get_mock_api_client()
        elif mock_name == "cache":
            mocks["cache"] = mock_manager.get_mock_cache()
        elif mock_name == "logger":
            mocks["logger"] = mock_manager.get_mock_logger()
        elif mock_name == "event_bus":
            mocks["event_bus"] = mock_manager.get_mock_event_bus()
        elif mock_name == "scheduler":
            mocks["scheduler"] = mock_manager.get_mock_scheduler()
        elif mock_name == "email":
            mocks["email"] = mock_manager.get_mock_email_service()
    return mocks


# 测试数据生成器装饰器
def with_test_data(**data_overrides):
    """装饰器：为测试函数提供测试数据"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            context = create_test_context()
            # 添加自定义数据
            for key, value in data_overrides.items():
                context["data"].custom_data[key] = value
            # 将context作为第一个参数传入
            return func(context, *args, **kwargs)

        return wrapper

    return decorator


# Mock环境装饰器
def with_mocks(required_mocks: List[str]):
    """装饰器：为测试函数提供Mock对象"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            mocks = setup_test_mocks(required_mocks)
            kwargs["mocks"] = mocks
            return func(*args, **kwargs)

        return wrapper

    return decorator
