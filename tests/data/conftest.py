"""
pytest配置和fixture定义
全局测试配置和共享fixture
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, Any, Generator

from tests.data.generators.test_data_generator import (
    TestDataGenerator,
    create_test_data_generator,
)


# 全局测试数据生成器
@pytest.fixture(scope="session")
def test_data_generator() -> TestDataGenerator:
    """全局测试数据生成器"""
    return create_test_data_generator(42)


@pytest.fixture(scope="session")
def sample_match_data(test_data_generator: TestDataGenerator) -> Dict[str, Any]:
    """示例比赛数据"""
    return test_data_generator.generate_match_data()


@pytest.fixture(scope="session")
def sample_features(test_data_generator: TestDataGenerator) -> list:
    """示例特征数据"""
    return test_data_generator.generate_features()


@pytest.fixture(scope="session")
def sample_prediction_result(test_data_generator: TestDataGenerator) -> Dict[str, Any]:
    """示例预测结果"""
    return test_data_generator.generate_prediction_result()


@pytest.fixture(scope="session")
def sample_model_info(test_data_generator: TestDataGenerator) -> Dict[str, Any]:
    """示例模型信息"""
    return test_data_generator.generate_model_info()


@pytest.fixture(scope="session")
def sample_health_check(test_data_generator: TestDataGenerator) -> Dict[str, Any]:
    """示例健康检查数据"""
    return test_data_generator.generate_health_check_data()


@pytest.fixture(scope="session")
def sample_config_data(test_data_generator: TestDataGenerator) -> Dict[str, Any]:
    """示例配置数据"""
    return test_data_generator.generate_config_data()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """临时目录fixture"""
    temp_path = Path(tempfile.mkdtemp())
    try:
        yield temp_path
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_model():
    """Mock机器学习模型"""
    model = Mock()
    model.predict.return_value = [1]  # Draw
    model.predict_proba.return_value = [[0.2, 0.5, 0.3]]
    model.n_features_in_ = 12
    model.classes_ = [0, 1, 2]
    model.feature_importances_ = [
        0.1,
        0.2,
        0.15,
        0.05,
        0.1,
        0.15,
        0.05,
        0.05,
        0.05,
        0.05,
        0.02,
        0.03,
    ]
    return model


@pytest.fixture
def mock_model_loader(mock_model):
    """Mock模型加载器"""
    loader = Mock()
    loader.get_model.return_value = mock_model
    loader.get_model_metadata.return_value = Mock()
    loader.list_models.return_value = ["xgboost_v2.pkl", "neural_net_v1.pkl"]
    return loader


@pytest.fixture
def mock_cache():
    """Mock缓存管理器"""
    cache = Mock()
    cache.get.return_value = None  # 默认缓存未命中
    cache.set.return_value = True
    return cache


@pytest.fixture
def mock_database():
    """Mock数据库连接"""
    db = Mock()
    db.execute.return_value = True
    db.fetch.return_value = []
    db.connection = Mock()
    db.connection.is_connected.return_value = True
    return db


@pytest.fixture
def mock_redis():
    """Mock Redis连接"""
    redis = Mock()
    redis.ping.return_value = True
    redis.get.return_value = None
    redis.set.return_value = True
    redis.exists.return_value = False
    return redis


@pytest.fixture
def sample_api_request():
    """示例API请求数据"""
    return {
        "home_team": "Manchester United",
        "away_team": "Arsenal",
        "model_version": "xgboost_v2",
        "features": [1.0, 2.0, 3.0, 1.5, 2.2, 0.8, 0.9, 1.1, 0.7, 1.3, 0.6, 1.0],
    }


@pytest.fixture
def sample_batch_api_requests():
    """示例批量API请求数据"""
    return [
        {
            "home_team": "Manchester United",
            "away_team": "Arsenal",
            "model_version": "xgboost_v2",
        },
        {
            "home_team": "Liverpool",
            "away_team": "Chelsea",
            "model_version": "neural_net_v1",
        },
        {
            "home_team": "Barcelona",
            "away_team": "Real Madrid",
            "model_version": "xgboost_v2",
        },
    ]


@pytest.fixture
def mock_external_api_response():
    """Mock外部API响应"""
    return {
        "status": "success",
        "data": {
            "matches": [
                {
                    "id": "12345",
                    "home_team": "Manchester United",
                    "away_team": "Arsenal",
                    "league": "Premier League",
                    "date": "2024-01-15T20:00:00Z",
                }
            ]
        },
        "metadata": {"total": 1, "page": 1, "per_page": 20},
    }


# 环境变量Mock
@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock环境变量"""
    env_vars = {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "football_prediction_test",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_password",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "REDIS_DB": "0",
        "ENVIRONMENT": "testing",
        "DEBUG": "false",
        "API_HOST": "0.0.0.0",
        "API_PORT": "8000",
        "MODEL_PATH": "/tmp/test_models",
        "LOG_LEVEL": "INFO",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


# 测试数据文件路径
@pytest.fixture
def test_data_files():
    """测试数据文件路径"""
    data_dir = Path(__file__).parent / "fixtures"
    return {
        "matches": data_dir / "matches.json",
        "predictions": data_dir / "predictions.json",
        "models": data_dir / "models.json",
        "config": data_dir / "config.json",
        "health_checks": data_dir / "health_checks.json",
    }


# 性能测试fixture
@pytest.fixture
def performance_thresholds():
    """性能测试阈值"""
    return {
        "prediction_latency_ms": 100.0,
        "model_loading_time_ms": 1000.0,
        "cache_access_time_ms": 10.0,
        "api_response_time_ms": 200.0,
        "batch_prediction_throughput": 100.0,  # predictions per second
        "memory_usage_mb": 100.0,
    }


# 集成测试fixture
@pytest.fixture
def integration_test_config():
    """集成测试配置"""
    return {
        "database_url": "sqlite:///:memory:",
        "redis_url": "redis://localhost:6379/1",
        "model_path": "/tmp/test_models",
        "cache_ttl": 300,
        "max_workers": 2,
        "timeout": 30,
    }


# 错误场景测试fixture
@pytest.fixture
def error_scenarios():
    """错误场景测试数据"""
    return {
        "database_error": {
            "error": "Connection failed",
            "error_code": "DB_CONN_001",
            "details": {"host": "localhost", "port": 5432},
        },
        "model_error": {
            "error": "Model not found",
            "error_code": "MODEL_001",
            "details": {"model_name": "nonexistent_model.pkl"},
        },
        "validation_error": {
            "error": "Invalid input features",
            "error_code": "VALID_001",
            "details": {"field": "features", "expected": "list", "received": "string"},
        },
        "external_api_error": {
            "error": "Rate limit exceeded",
            "error_code": "API_429",
            "details": {"retry_after": 60, "limit": 100},
        },
    }


# 标记定义
def pytest_configure(config):
    """自定义pytest标记"""
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "performance: 性能测试")
    config.addinivalue_line("markers", "slow: 慢速测试（需要长时间运行）")
    config.addinivalue_line("markers", "external: 需要外部依赖的测试")
    config.addinivalue_line("markers", "database: 需要数据库的测试")
    config.addinivalue_line("markers", "redis: 需要Redis的测试")


# 测试收集钩子
def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    # 为没有标记的测试添加默认标记
    for item in items:
        if not any(item.iter_markers()):
            # 根据测试文件路径自动添加标记
            if "unit/" in str(item.fspath):
                item.add_marker(pytest.mark.unit)
            elif "integration/" in str(item.fspath):
                item.add_marker(pytest.mark.integration)
            elif "performance/" in str(item.fspath):
                item.add_marker(pytest.mark.performance)


# 测试报告钩子
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """生成测试报告"""
    outcome = yield
    rep = outcome.get_result()

    # 添加测试元数据到报告
    if rep.when == "call" and rep.passed:
        # 为通过的测试添加执行时间信息
        setattr(rep, "duration", call.duration)
        setattr(rep, "nodeid", item.nodeid)
