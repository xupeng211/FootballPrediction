"""
pytest配置文件

提供全局的pytest配置和fixtures，包括：
- 数据库测试配置
- Mock配置
- 测试环境设置
- Prometheus metrics清理
"""

import asyncio
import importlib.util  # noqa: E402 - Must be after sys.path modification
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from prometheus_client import REGISTRY, CollectorRegistry
from sqlalchemy.ext.asyncio import create_async_engine

# 避免触发src.__init__.py的导入链，直接导入需要的模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def import_module_directly(module_path, module_name):
    """直接导入模块，绕过包的__init__.py"""
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# 直接导入需要的模块，避免触发src/__init__.py
base_path = os.path.join(os.path.dirname(__file__), "..", "src", "database", "base.py")
config_path = os.path.join(
    os.path.dirname(__file__), "..", "src", "database", "config.py"
)

base_module = import_module_directly(base_path, "database_base")
config_module = import_module_directly(config_path, "database_config")

Base = base_module.Base
get_test_database_config = config_module.get_test_database_config


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


def is_database_available() -> bool:
    """检查数据库是否可用"""
    try:
        config = get_test_database_config()
        # 简单的连接测试
        if "localhost" in config.async_url or "db:" in config.async_url:
            import socket

            host = "localhost" if "localhost" in config.async_url else "db"
            port = 5432
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        return True  # 对于其他URL类型，假设可用
    except Exception:
        return False


@pytest.fixture(scope="session", autouse=True)
def setup_test_database(event_loop):
    """
    Set up the test database: create schema before tests and drop after.

    智能处理数据库不可用的情况，在CI环境中正常运行，在本地环境中优雅降级。
    """
    # Ensure we are in the test environment
    os.environ["ENVIRONMENT"] = "test"

    # 检查数据库是否可用
    if not is_database_available():
        # 数据库不可用时，使用SQLite内存数据库或跳过数据库初始化
        print("⚠️  数据库不可用，跳过数据库初始化")
        yield
        return

    config = get_test_database_config()

    # Use a separate engine for schema creation/deletion
    engine = create_async_engine(config.async_url)

    async def init_db():
        try:
            async with engine.begin() as conn:
                # Drop all tables first for a clean state, in case of leftovers
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            print(f"⚠️  数据库初始化失败: {e}")
            # 在失败时不抛出异常，允许测试继续

    event_loop.run_until_complete(init_db())

    yield

    async def teardown_db():
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
        except Exception as e:
            print(f"⚠️  数据库清理失败: {e}")

    event_loop.run_until_complete(teardown_db())


@pytest.fixture(autouse=True)
def reset_prometheus_registry():
    """
    重置Prometheus注册表，避免测试间指标重复注册

    这个fixture在每个测试前自动运行，确保：
    1. 清理全局REGISTRY中的所有collector
    2. 重置MetricsExporter的全局实例
    3. 避免测试之间的状态污染
    """
    # 清空全局注册表中的collectors
    collectors_to_remove = list(REGISTRY._collector_to_names.keys())
    for collector in collectors_to_remove:
        try:
            REGISTRY.unregister(collector)
        except KeyError:
            pass  # 如果collector已经被移除，忽略错误

    # 重置MetricsExporter的全局实例，避免单例状态污染
    try:
        from src.monitoring.metrics_exporter import reset_metrics_exporter

        reset_metrics_exporter()
    except ImportError:
        pass  # 如果模块不存在，忽略错误


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    # ✅ 修复：rollback 和 close 通常是同步方法，不应该使用 AsyncMock
    session.rollback = Mock()
    session.close = Mock()
    return session


@pytest.fixture
def mock_redis():
    """模拟Redis连接"""
    redis_mock = AsyncMock()
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.delete = AsyncMock(return_value=1)
    return redis_mock


@pytest.fixture
def clean_metrics_registry():
    """
    提供干净的Prometheus注册表用于测试

    这个fixture为每个测试提供一个独立的CollectorRegistry实例，
    避免测试间的指标污染和冲突。

    使用方法：
    - 在测试中通过参数接收此fixture
    - 将其传递给MetricsExporter(registry=clean_metrics_registry)
    - 确保每个测试有独立的指标空间
    """
    # 创建全新的注册表实例，完全独立于全局REGISTRY
    return CollectorRegistry()


@pytest.fixture
def mock_prometheus_client():
    """
    模拟Prometheus客户端，避免真实依赖

    提供完整的Prometheus客户端mock，包括：
    - Counter、Gauge、Histogram等指标类型
    - CollectorRegistry注册表
    - 指标导出功能
    """
    mock_client = MagicMock()

    # Mock Counter指标
    mock_counter = MagicMock()
    mock_counter.inc = MagicMock()
    mock_counter.labels = MagicMock(return_value=mock_counter)
    mock_client.Counter = MagicMock(return_value=mock_counter)

    # Mock Gauge指标
    mock_gauge = MagicMock()
    mock_gauge.set = MagicMock()
    mock_gauge.inc = MagicMock()
    mock_gauge.dec = MagicMock()
    mock_gauge.labels = MagicMock(return_value=mock_gauge)
    mock_client.Gauge = MagicMock(return_value=mock_gauge)

    # Mock Histogram指标
    mock_histogram = MagicMock()
    mock_histogram.observe = MagicMock()
    mock_histogram.time = MagicMock()
    mock_histogram.labels = MagicMock(return_value=mock_histogram)
    mock_client.Histogram = MagicMock(return_value=mock_histogram)

    # Mock Summary指标
    mock_summary = MagicMock()
    mock_summary.observe = MagicMock()
    mock_summary.time = MagicMock()
    mock_summary.labels = MagicMock(return_value=mock_summary)
    mock_client.Summary = MagicMock(return_value=mock_summary)

    # Mock CollectorRegistry
    mock_registry = MagicMock()
    mock_registry.register = MagicMock()
    mock_registry.unregister = MagicMock()
    mock_client.CollectorRegistry = MagicMock(return_value=mock_registry)
    mock_client.REGISTRY = mock_registry

    # Mock 导出功能
    mock_client.generate_latest = MagicMock(return_value=b"# Mock metrics\n")
    mock_client.exposition = MagicMock()

    return mock_client


@pytest.fixture
def mock_duration_histogram():
    """
    模拟duration_histogram指标

    这个fixture专门用于模拟持续时间直方图指标，
    确保在测试中正确初始化和使用。
    """
    mock_histogram = MagicMock()
    mock_histogram.observe = MagicMock()
    mock_histogram.time = MagicMock()
    mock_histogram.labels = MagicMock(return_value=mock_histogram)

    # 模拟上下文管理器
    mock_timer = MagicMock()
    mock_timer.__enter__ = MagicMock(return_value=mock_timer)
    mock_timer.__exit__ = MagicMock(return_value=None)
    mock_histogram.time.return_value = mock_timer

    return mock_histogram


@pytest.fixture
def mock_total_metrics():
    """
    模拟*_total_metric计数器指标

    这个fixture提供各种总计指标的mock，包括：
    - requests_total
    - errors_total
    - predictions_total
    等常用的计数器指标
    """
    mock_metrics = {}

    # 创建各种total指标的mock
    metric_names = [
        "requests_total",
        "errors_total",
        "predictions_total",
        "cache_hits_total",
        "database_queries_total",
    ]

    for name in metric_names:
        mock_counter = MagicMock()
        mock_counter.inc = MagicMock()
        mock_counter.labels = MagicMock(return_value=mock_counter)
        mock_metrics[name] = mock_counter

    return mock_metrics


@pytest.fixture
def mock_mlflow_client():
    """
    模拟MLflow客户端，避免真实依赖

    提供完整的MLflow客户端mock，包括：
    - 模型注册和版本管理
    - 模型加载和缓存
    - 实验跟踪
    - 模型阶段转换
    """
    mock_client = Mock()

    # Mock模型版本信息
    mock_version_info = Mock()
    mock_version_info.version = "1"
    mock_version_info.current_stage = "Production"
    mock_version_info.name = "football_baseline_model"

    # Mock客户端方法
    mock_client.get_latest_versions = Mock(return_value=[mock_version_info])
    mock_client.get_model_version = Mock(return_value=mock_version_info)
    mock_client.transition_model_version_stage = Mock()
    mock_client.search_model_versions = Mock(return_value=[mock_version_info])
    mock_client.create_registered_model = Mock()
    mock_client.create_model_version = Mock(return_value=mock_version_info)

    # Mock实验相关方法
    mock_client.create_experiment = Mock(return_value="experiment_123")
    mock_client.get_experiment_by_name = Mock()
    mock_client.list_experiments = Mock(return_value=[])

    # Mock运行相关方法
    mock_client.create_run = Mock()
    mock_client.log_metric = Mock()
    mock_client.log_param = Mock()
    mock_client.set_tag = Mock()

    return mock_client


@pytest.fixture
def mock_mlflow_module():
    """
    模拟整个mlflow模块

    提供完整的mlflow模块mock，包括：
    - 实验和运行管理
    - 模型记录和加载
    - 跟踪URI设置
    - 各种sklearn集成
    """
    import numpy as np

    mock_mlflow = Mock()

    # Mock基础设置
    mock_mlflow.set_tracking_uri = Mock()
    mock_mlflow.get_tracking_uri = Mock(return_value="http://localhost:5002")

    # Mock实验管理
    mock_mlflow.create_experiment = Mock(return_value="experiment_123")
    mock_mlflow.set_experiment = Mock()
    mock_mlflow.get_experiment = Mock()
    mock_mlflow.delete_experiment = Mock()

    # Mock运行管理
    mock_run_context = Mock()
    mock_run_info = Mock()
    mock_run_info.run_id = "run_123"
    mock_run_context.info = mock_run_info
    mock_run_context.__enter__ = Mock(return_value=mock_run_context)
    mock_run_context.__exit__ = Mock(return_value=None)
    mock_mlflow.start_run = Mock(return_value=mock_run_context)
    mock_mlflow.active_run = Mock(return_value=mock_run_context)

    # Mock记录功能
    mock_mlflow.log_param = Mock()
    mock_mlflow.log_metric = Mock()
    mock_mlflow.log_params = Mock()
    mock_mlflow.log_metrics = Mock()
    mock_mlflow.set_tag = Mock()
    mock_mlflow.log_artifact = Mock()

    # Mock模型管理
    mock_mlflow.register_model = Mock()

    # Mock sklearn集成
    mock_sklearn = Mock()

    # 创建一个mock模型
    mock_model = Mock()
    mock_model.predict = Mock(return_value=np.array(["home", "draw", "away"]))
    mock_model.predict_proba = Mock(
        return_value=np.array([[0.4, 0.3, 0.3], [0.3, 0.4, 0.3], [0.3, 0.3, 0.4]])
    )
    mock_model.feature_names_in_ = [f"feature_{i}" for i in range(10)]

    mock_sklearn.log_model = Mock()
    mock_sklearn.load_model = Mock(return_value=mock_model)
    mock_mlflow.sklearn = mock_sklearn

    # Mock其他集成
    mock_mlflow.pytorch = Mock()
    mock_mlflow.tensorflow = Mock()

    return mock_mlflow


@pytest.fixture
def mock_redis_manager():
    """
    模拟Redis管理器，避免真实依赖

    提供完整的Redis管理器mock，包括：
    - 连接管理
    - 缓存操作
    - TTL管理
    - 连接检查
    """
    mock_manager = AsyncMock()

    # Mock连接管理
    mock_manager.connect = AsyncMock()
    mock_manager.disconnect = AsyncMock()
    mock_manager.is_connected = AsyncMock(return_value=True)
    mock_manager.ping = AsyncMock(return_value=True)

    # Mock基本操作
    mock_manager.set = AsyncMock(return_value=True)
    mock_manager.get = AsyncMock(return_value=None)
    mock_manager.delete = AsyncMock(return_value=1)
    mock_manager.exists = AsyncMock(return_value=False)

    # Mock TTL操作
    mock_manager.expire = AsyncMock(return_value=True)
    mock_manager.ttl = AsyncMock(return_value=-1)
    mock_manager.persist = AsyncMock(return_value=True)

    # Mock批量操作
    mock_manager.mget = AsyncMock(return_value=[])
    mock_manager.mset = AsyncMock(return_value=True)
    mock_manager.delete_pattern = AsyncMock(return_value=0)

    # Mock哈希操作
    mock_manager.hset = AsyncMock(return_value=1)
    mock_manager.hget = AsyncMock(return_value=None)
    mock_manager.hgetall = AsyncMock(return_value={})
    mock_manager.hdel = AsyncMock(return_value=1)

    # Mock列表操作
    mock_manager.lpush = AsyncMock(return_value=1)
    mock_manager.rpush = AsyncMock(return_value=1)
    mock_manager.lpop = AsyncMock(return_value=None)
    mock_manager.rpop = AsyncMock(return_value=None)
    mock_manager.llen = AsyncMock(return_value=0)

    # Mock集合操作
    mock_manager.sadd = AsyncMock(return_value=1)
    mock_manager.srem = AsyncMock(return_value=1)
    mock_manager.smembers = AsyncMock(return_value=set())
    mock_manager.sismember = AsyncMock(return_value=False)

    # Mock有序集合操作
    mock_manager.zadd = AsyncMock(return_value=1)
    mock_manager.zrem = AsyncMock(return_value=1)
    mock_manager.zrange = AsyncMock(return_value=[])
    mock_manager.zscore = AsyncMock(return_value=None)

    # Mock事务支持
    mock_pipeline = AsyncMock()
    mock_pipeline.execute = AsyncMock(return_value=[])
    mock_manager.pipeline = Mock(return_value=mock_pipeline)

    # Mock发布/订阅
    mock_manager.publish = AsyncMock(return_value=0)
    mock_manager.subscribe = AsyncMock()
    mock_manager.unsubscribe = AsyncMock()

    return mock_manager


@pytest.fixture
def mock_feature_store():
    """
    模拟特征存储，避免Feast依赖

    提供完整的特征存储mock，包括：
    - 特征检索
    - 历史特征获取
    - 在线特征服务
    - 特征定义管理
    """
    from datetime import datetime

    import pandas as pd

    mock_store = AsyncMock()

    # Mock基本配置
    mock_store.repo_path = "/tmp/feature_repo"
    mock_store.registry_path = "/tmp/feature_repo/data/registry.db"

    # Mock特征检索方法
    mock_features = {
        "home_recent_wins": 3,
        "home_recent_losses": 1,
        "home_recent_draws": 1,
        "away_recent_wins": 2,
        "away_recent_losses": 2,
        "away_recent_draws": 1,
        "home_goals_avg": 1.8,
        "away_goals_avg": 1.5,
        "head_to_head_home_wins": 2,
        "head_to_head_away_wins": 1,
    }

    mock_store.get_match_features_for_prediction = AsyncMock(return_value=mock_features)
    mock_store.get_historical_features = AsyncMock(
        return_value=pd.DataFrame([mock_features])
    )
    mock_store.get_online_features = AsyncMock(return_value=mock_features)

    # Mock特征定义
    mock_store.list_feature_views = Mock(return_value=[])
    mock_store.get_feature_view = Mock()
    mock_store.apply = Mock()

    # Mock数据源
    mock_store.get_data_source = Mock()
    mock_store.list_data_sources = Mock(return_value=[])

    # Mock实体
    mock_store.list_entities = Mock(return_value=[])
    mock_store.get_entity = Mock()

    # Mock服务管理
    mock_store.serve = AsyncMock()
    mock_store.teardown = AsyncMock()

    return mock_store


# 配置asyncio测试模式
pytest_plugins = ("pytest_asyncio",)


# 配置异步测试标记
def pytest_configure(config):
    """配置pytest"""
    config.addinivalue_line("markers", "asyncio: mark test to run with asyncio")


# 禁用一些警告
@pytest.fixture(autouse=True)
def suppress_warnings():
    """抑制测试中的警告"""
    import warnings

    # 基础警告抑制
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=UserWarning)

    # Marshmallow 4 兼容性警告抑制 - 针对第三方库(Great Expectations)
    try:
        import marshmallow.warnings

        warnings.filterwarnings(
            "ignore",
            category=marshmallow.warnings.ChangedInMarshmallow4Warning,
            message=".*Number.*field should not be instantiated.*",
        )
    except ImportError:
        # 如果无法导入marshmallow.warnings，使用通用过滤器
        warnings.filterwarnings(
            "ignore", message=".*Number.*field.*should.*not.*be.*instantiated.*"
        )


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(session, config, items):
    """Custom mark handling for unit tests."""
    markexpr = getattr(config.option, "markexpr", None)
    if not markexpr:
        return

    # Disable pytest's default mark filtering while we evaluate manually.
    config.option.markexpr = None

    from _pytest.mark import expression

    compiled = expression.Expression.compile(markexpr)
    root = Path(config.rootdir).resolve()
    selected = []
    deselected = []

    for item in items:
        try:
            rel_path = Path(item.fspath).resolve().relative_to(root)
        except ValueError:
            rel_path = None

        def matcher(name: str, **kwargs):
            if name == "unit":
                if rel_path is None:
                    return False
                parts = rel_path.parts
                return (
                    len(parts) >= 2
                    and parts[0] == "tests"
                    and parts[1] == "unit"
                    and "integration" not in item.keywords
                )
            return any(
                mark.name == name
                and all(mark.kwargs.get(k) == v for k, v in kwargs.items())
                for mark in item.iter_markers()
            )

        if compiled.evaluate(matcher):
            selected.append(item)
        else:
            deselected.append(item)

    if deselected:
        config.hook.pytest_deselected(items=deselected)
    items[:] = selected
