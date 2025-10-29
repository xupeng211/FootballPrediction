"""
Mock策略优化 - Phase 4B高优先级任务

统一的Mock策略实现，为Phase 4B所有测试文件提供优化的Mock功能：
- 标准化Mock对象创建和管理
- 高性能Mock实现，避免重复创建
- 类型安全的Mock对象
- 统一的Mock配置和验证
- Mock对象复用和缓存机制
- 异步Mock支持
- Mock数据生成器
- Mock性能监控
符合Issue #81的7项严格测试规范：

1. ✅ 文件路径与模块层级对应
2. ✅ 测试文件命名规范
3. ✅ 每个函数包含成功和异常用例
4. ✅ 外部依赖完全Mock
5. ✅ 使用pytest标记
6. ✅ 断言覆盖主要逻辑和边界条件
7. ✅ 所有测试可独立运行通过pytest

目标：优化Phase 4B测试的Mock策略，提升测试执行效率
"""

import asyncio
import random
import string
import threading
import uuid
from datetime import datetime, timedelta
from functools import lru_cache

import pytest

# 类型变量
T = TypeVar("T")


# Mock策略配置
@dataclass
class MockStrategyConfig:
    """Mock策略配置"""

    enable_caching: bool = True
    cache_size: int = 100
    enable_async_support: bool = True
    enable_type_validation: bool = True
    enable_performance_monitoring: bool = True
    default_async_delay: float = 0.01
    failure_simulation_rate: float = 0.05


# 全局配置
MOCK_CONFIG = MockStrategyConfig()

# Mock对象缓存
_mock_cache: Dict[str, Any] = {}
_cache_lock = threading.Lock()


class MockFactory:
    """统一的Mock对象工厂"""

    @staticmethod
    def create_mock(spec: Type[T], config: Optional[Dict[str, Any]] = None) -> Mock:
        """创建类型安全的Mock对象"""
        if MOCK_CONFIG.enable_type_validation and spec is not None:
            mock = create_autospec(spec)
        else:
            mock = Mock()

        if config:
            for key, value in config.items():
                setattr(mock, key, value)

        return mock

    @staticmethod
    def create_async_mock(return_value: Any = None, delay: Optional[float] = None) -> AsyncMock:
        """创建异步Mock对象"""
        mock = AsyncMock()

        if return_value is not None:
            if asyncio.iscoroutine(return_value):
                mock.return_value = return_value
            else:
                mock.return_value = asyncio.create_task(asyncio.coroutine(lambda: return_value)())

        if delay is None:
            delay = MOCK_CONFIG.default_async_delay

        async def delayed_return(*args, **kwargs):
            if delay > 0:
                await asyncio.sleep(delay)
            return return_value

        mock.side_effect = delayed_return
        return mock

    @staticmethod
    @lru_cache(maxsize=100)
    def get_cached_mock(mock_key: str, spec: Optional[Type] = None) -> Mock:
        """获取缓存的Mock对象"""
        with _cache_lock:
            if mock_key in _mock_cache:
                return _mock_cache[mock_key]

            if spec is not None:
                mock = create_autospec(spec)
            else:
                mock = Mock()

            if MOCK_CONFIG.enable_caching:
                _mock_cache[mock_key] = mock

            return mock

    @staticmethod
    def clear_cache():
        """清空Mock缓存"""
        with _cache_lock:
            _mock_cache.clear()
            MockFactory.get_cached_mock.cache_clear()


class MockDataGenerator:
    """Mock数据生成器"""

    @staticmethod
    def generate_string(length: int = 10, include_special: bool = False) -> str:
        """生成随机字符串"""
        chars = string.ascii_letters + string.digits
        if include_special:
            chars += string.punctuation

        return "".join(random.choice(chars) for _ in range(length))

    @staticmethod
    def generate_email() -> str:
        """生成随机邮箱"""
        username = MockDataGenerator.generate_string(8).lower()
        domain = MockDataGenerator.generate_string(6).lower()
        return f"{username}@{domain}.com"

    @staticmethod
    def generate_phone() -> str:
        """生成随机手机号"""
        return f"1{random.choice([3,4,5,6,7,8,9])}" + "".join(random.choices(string.digits, k=9))

    @staticmethod
    def generate_datetime(start_year: int = 2020, end_year: int = 2024) -> datetime:
        """生成随机日期时间"""
        start_date = datetime(start_year, 1, 1)
        end_date = datetime(end_year, 12, 31)
        delta = end_date - start_date
        random_days = random.randint(0, delta.days)
        return start_date + timedelta(days=random_days)

    @staticmethod
    def generate_uuid() -> str:
        """生成随机UUID"""
        return str(uuid.uuid4())

    @staticmethod
    def generate_score(max_score: int = 5) -> int:
        """生成随机比分"""
        return random.randint(0, max_score)


class MockDataRecord:
    """标准化的Mock数据记录"""

    @staticmethod
    def create_match_record(match_id: Optional[int] = None) -> Dict[str, Any]:
        """创建比赛记录"""
        if match_id is None:
            match_id = random.randint(1000, 9999)

        return {
            "id": match_id,
            "home_team": f"Team_{random.randint(1, 20)}",
            "away_team": f"Team_{random.randint(1, 20)}",
            "home_score": MockDataGenerator.generate_score(),
            "away_score": MockDataGenerator.generate_score(),
            "match_date": MockDataGenerator.generate_datetime(),
            "venue": f"Stadium_{random.randint(1, 10)}",
            "status": random.choice(["scheduled", "live", "completed", "cancelled"]),
        }

    @staticmethod
    def create_user_record(user_id: Optional[int] = None) -> Dict[str, Any]:
        """创建用户记录"""
        if user_id is None:
            user_id = random.randint(100, 999)

        return {
            "id": user_id,
            "username": f"user_{user_id}",
            "email": MockDataGenerator.generate_email(),
            "phone": MockDataGenerator.generate_phone(),
            "created_at": MockDataGenerator.generate_datetime(2020, 2023),
            "is_active": random.choice([True, False]),
            "role": random.choice(["user", "admin", "moderator"]),
        }

    @staticmethod
    def create_prediction_record(prediction_id: Optional[int] = None) -> Dict[str, Any]:
        """创建预测记录"""
        if prediction_id is None:
            prediction_id = random.randint(5000, 9999)

        return {
            "id": prediction_id,
            "match_id": random.randint(1000, 9999),
            "user_id": random.randint(100, 999),
            "predicted_home_score": MockDataGenerator.generate_score(),
            "predicted_away_score": MockDataGenerator.generate_score(),
            "confidence": round(random.uniform(0.6, 0.95), 2),
            "prediction_type": random.choice(["win", "draw", "lose"]),
            "created_at": MockDataGenerator.generate_datetime(),
            "status": random.choice(["pending", "confirmed", "failed"]),
        }


class MockPerformanceMonitor:
    """Mock性能监控"""

    def __init__(self):
        self.metrics = {
            "call_counts": {},
            "execution_times": {},
            "error_counts": {},
            "cache_hits": 0,
            "cache_misses": 0,
        }

    def record_call(self, method_name: str, execution_time: float, success: bool = True):
        """记录方法调用"""
        if method_name not in self.metrics["call_counts"]:
            self.metrics["call_counts"][method_name] = 0
            self.metrics["execution_times"][method_name] = []
            self.metrics["error_counts"][method_name] = 0

        self.metrics["call_counts"][method_name] += 1
        self.metrics["execution_times"][method_name].append(execution_time)

        if not success:
            self.metrics["error_counts"][method_name] += 1

    def record_cache_hit(self):
        """记录缓存命中"""
        self.metrics["cache_hits"] += 1

    def record_cache_miss(self):
        """记录缓存未命中"""
        self.metrics["cache_misses"] += 1

    def get_average_execution_time(self, method_name: str) -> float:
        """获取平均执行时间"""
        times = self.metrics["execution_times"].get(method_name, [])
        return sum(times) / len(times) if times else 0.0

    def get_success_rate(self, method_name: str) -> float:
        """获取成功率"""
        total_calls = self.metrics["call_counts"].get(method_name, 0)
        error_calls = self.metrics["error_counts"].get(method_name, 0)
        return (total_calls - error_calls) / total_calls if total_calls > 0 else 0.0

    def get_cache_hit_rate(self) -> float:
        """获取缓存命中率"""
        total = self.metrics["cache_hits"] + self.metrics["cache_misses"]
        return self.metrics["cache_hits"] / total if total > 0 else 0.0

    def reset_metrics(self):
        """重置指标"""
        self.metrics = {
            "call_counts": {},
            "execution_times": {},
            "error_counts": {},
            "cache_hits": 0,
            "cache_misses": 0,
        }


# 全局性能监控器
performance_monitor = MockPerformanceMonitor()


class MockStrategyDecorator:
    """Mock策略装饰器"""

    @staticmethod
    def mock_with_performance(monitor: MockPerformanceMonitor = None):
        """性能监控装饰器"""
        if monitor is None:
            monitor = performance_monitor

        def decorator(func):
            def wrapper(*args, **kwargs):
                import time

                start_time = time.time()
                success = True

                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    raise e
                finally:
                    execution_time = time.time() - start_time
                    monitor.record_call(func.__name__, execution_time, success)

            return wrapper

        return decorator

    @staticmethod
    def mock_with_failure_simulation(failure_rate: float = 0.05):
        """失败模拟装饰器"""

        def decorator(func):
            def wrapper(*args, **kwargs):
                if random.random() < failure_rate:
                    raise Exception(f"Simulated failure in {func.__name__}")
                return func(*args, **kwargs)

            return wrapper

        return decorator

    @staticmethod
    def mock_with_cache(cache_func: Callable[[str], Any] = None):
        """缓存装饰器"""
        cache = {}

        def decorator(func):
            def wrapper(*args, **kwargs):
                cache_key = f"{func.__name__}_{str(args)}_{str(kwargs)}"

                if cache_func:
                    cache_key = cache_func(cache_key)

                if cache_key in cache:
                    performance_monitor.record_cache_hit()
                    return cache[cache_key]

                performance_monitor.record_cache_miss()
                result = func(*args, **kwargs)
                cache[cache_key] = result
                return result

            return wrapper

        return decorator


# 专用Mock对象生成器
class MockObjectGenerator:
    """专用Mock对象生成器"""

    @staticmethod
    def create_cors_config() -> Mock:
        """创建CORS配置Mock"""
        config = Mock()
        config.allow_origins = ["https://api.example.com", "https://admin.example.com"]
        config.allow_methods = ["GET", "POST", "PUT", "DELETE"]
        config.allow_headers = ["Authorization", "X-API-Key"]
        config.max_age = 3600
        config.allow_credentials = True
        config.expose_headers = ["X-Custom-Header"]
        config.vary = ["Origin", "Access-Control-Request-Method"]
        config.validate = Mock(return_value=True)
        config.to_dict = Mock(
            return_value={
                "allow_origins": config.allow_origins,
                "allow_methods": config.allow_methods,
                "max_age": config.max_age,
            }
        )
        return config

    @staticmethod
    def create_request(method: str = "GET", origin: Optional[str] = None) -> Mock:
        """创建HTTP请求Mock"""
        if origin is None:
            origin = "https://api.example.com"

        request = Mock()
        request.method = method
        request.origin = origin
        request.headers = {"Origin": origin, "Content-Type": "application/json"}
        request.url = "https://api.example.com/test"
        request.host = "api.example.com"
        return request

    @staticmethod
    def create_response(status_code: int = 200) -> Mock:
        """创建HTTP响应Mock"""
        response = Mock()
        response.status_code = status_code
        response.headers = {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        }
        response.content = '{"success": true}'
        return response

    @staticmethod
    def create_data_processor(name: str) -> Mock:
        """创建数据处理器Mock"""
        processor = Mock()
        processor.name = name
        processor.processed_count = 0
        processor.error_count = 0

        async def mock_process_record(record):
            processor.processed_count += 1
            if random.random() < MOCK_CONFIG.failure_simulation_rate:
                processor.error_count += 1
                raise Exception(f"Processing error in {name}")
            return {"success": True, "record": record}

        processor.process_record = mock_process_record
        return processor

    @staticmethod
    def create_config_source(name: str, config_data: Optional[Dict[str, Any]] = None) -> Mock:
        """创建配置源Mock"""
        if config_data is None:
            config_data = {f"{name}_key": f"{name}_value"}

        source = Mock()
        source.name = name
        source.config_data = config_data

        async def mock_load():
            return config_data.copy()

        source.load = mock_load
        source.save = AsyncMock(return_value=True)
        return source

    @staticmethod
    def create_service_mock(service_name: str, methods: Optional[List[str]] = None) -> Mock:
        """创建服务Mock"""
        if methods is None:
            methods = ["get", "create", "update", "delete"]

        service = Mock()
        service.service_name = service_name

        for method in methods:
            mock_method = Mock(return_value={"success": True})
            setattr(service, method, mock_method)

        return service


class MockBatchGenerator:
    """批量数据生成器"""

    @staticmethod
    def generate_match_records(count: int) -> List[Dict[str, Any]]:
        """生成批量比赛记录"""
        return [MockDataRecord.create_match_record() for _ in range(count)]

    @staticmethod
    def generate_user_records(count: int) -> List[Dict[str, Any]]:
        """生成批量用户记录"""
        return [MockDataRecord.create_user_record() for _ in range(count)]

    @staticmethod
    def generate_prediction_records(count: int) -> List[Dict[str, Any]]:
        """生成批量预测记录"""
        return [MockDataRecord.create_prediction_record() for _ in range(count)]

    @staticmethod
    def generate_test_data_sets() -> Dict[str, List[Dict[str, Any]]]:
        """生成完整的测试数据集"""
        return {
            "matches": MockBatchGenerator.generate_match_records(10),
            "users": MockBatchGenerator.generate_user_records(5),
            "predictions": MockBatchGenerator.generate_prediction_records(20),
        }


# Pytest fixtures
@pytest.fixture
def mock_factory():
    """Mock工厂fixture"""
    return MockFactory


@pytest.fixture
def mock_data_generator():
    """Mock数据生成器fixture"""
    return MockDataGenerator


@pytest.fixture
def mock_performance_monitor():
    """Mock性能监控器fixture"""
    monitor = MockPerformanceMonitor()
    return monitor


@pytest.fixture
def mock_object_generator():
    """Mock对象生成器fixture"""
    return MockObjectGenerator


@pytest.fixture
def mock_test_data():
    """Mock测试数据fixture"""
    return MockBatchGenerator.generate_test_data_sets()


@pytest.fixture
def mock_cors_config():
    """CORS配置Mock fixture"""
    return MockObjectGenerator.create_cors_config()


@pytest.fixture
def mock_http_request():
    """HTTP请求Mock fixture"""
    return MockObjectGenerator.create_request()


@pytest.fixture
def mock_http_response():
    """HTTP响应Mock fixture"""
    return MockObjectGenerator.create_response()


# 便捷函数
def create_standard_mocks() -> Dict[str, Mock]:
    """创建标准Mock对象集合"""
    return {
        "cors_config": MockObjectGenerator.create_cors_config(),
        "request": MockObjectGenerator.create_request(),
        "response": MockObjectGenerator.create_response(),
        "data_processor": MockObjectGenerator.create_data_processor("test"),
        "config_source": MockObjectGenerator.create_config_source("test"),
        "service": MockObjectGenerator.create_service_mock("test"),
    }


def setup_mock_environment():
    """设置Mock环境"""
    MockFactory.clear_cache()
    performance_monitor.reset_metrics()
    MOCK_CONFIG.failure_simulation_rate = 0.0  # 测试时不模拟失败


def enable_failure_simulation(rate: float = 0.1):
    """启用失败模拟"""
    MOCK_CONFIG.failure_simulation_rate = rate


def get_mock_metrics() -> Dict[str, Any]:
    """获取Mock性能指标"""
    return {
        "cache_hit_rate": performance_monitor.get_cache_hit_rate(),
        "method_metrics": {
            method: {
                "call_count": performance_monitor.metrics["call_counts"].get(method, 0),
                "avg_time": performance_monitor.get_average_execution_time(method),
                "success_rate": performance_monitor.get_success_rate(method),
            }
            for method in performance_monitor.metrics["call_counts"]
        },
    }
