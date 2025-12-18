#!/usr/bin/env python3
"""
pytest conftest.py - 测试环境配置
为测试套件提供自动化的环境变量配置和Mock支持
"""

import os
import sys
import pytest
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path

# 确保src目录在Python路径中
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """自动化测试环境配置"""
    # 设置必要的测试环境变量
    test_env_vars = {
        # 数据库配置
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "football_prediction_test",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_password",
        # Redis配置
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "REDIS_DB": "1",
        "REDIS_PASSWORD": "",
        # API配置
        "FOTMOB_X_MAS_HEADER": "test_mas_header",
        "FOTMOB_X_FOO_HEADER": "test_foo_header",
        # 安全配置
        "SECRET_KEY": "test_secret_key_for_testing_only",
        "JWT_SECRET_KEY": "test_jwt_secret_key_for_testing_only",
        # 应用配置
        "ENVIRONMENT": "testing",
        "DEBUG": "true",
        "API_HOST": "0.0.0.0",
        "API_PORT": "8000",
        # 模型配置
        "MODEL_PATH": str(project_root / "models" / "test_model.pkl"),
        "DEFAULT_MODEL_NAME": "test_model",
        # 服务配置
        "INFERENCE_SERVICE_V2_ENABLED": "true",
        "COLLECTION_SERVICE_ENABLED": "true",
        "EXPLAINABILITY_SERVICE_ENABLED": "true",
        # 缓存配置
        "CACHE_TTL_SECONDS": "60",
        "MAX_CACHE_SIZE": "100",
        # 测试标志
        "PYTEST_CURRENT_TEST": "1",
    }

    # 保存原始环境变量
    original_env = {}
    for key, value in test_env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # 恢复原始环境变量
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture(scope="function")
def temp_model_file():
    """创建临时模型文件"""
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as tmp:
        # 写入一些虚拟数据作为"模型"
        tmp.write(b"dummy_model_data")
        tmp_path = tmp.name

    yield tmp_path

    # 清理
    try:
        os.unlink(tmp_path)
    except OSError:
        pass


@pytest.fixture(scope="function")
def mock_database():
    """Mock数据库连接"""
    mock_conn = MagicMock()
    mock_conn.fetchrow.return_value = {"test": "data"}
    mock_conn.fetch.return_value = [{"test": "data"}]

    with patch("src.database.connection.asyncpg.connect", return_value=mock_conn):
        with patch("src.database.db_pool.asyncpg.create_pool", return_value=mock_conn):
            yield mock_conn


@pytest.fixture(scope="function")
def mock_redis():
    """Mock Redis连接"""
    mock_redis_client = MagicMock()
    mock_redis_client.get.return_value = None
    mock_redis_client.set.return_value = True
    mock_redis_client.exists.return_value = False
    mock_redis_client.ping.return_value = True

    with patch("redis.Redis", return_value=mock_redis_client):
        yield mock_redis_client


@pytest.fixture(scope="function")
def mock_model_loader(temp_model_file):
    """Mock模型加载器"""
    mock_model = MagicMock()
    mock_model.predict.return_value = [1]  # HOME_WIN
    mock_model.predict_proba.return_value = [0.6, 0.3, 0.1]  # HOME, DRAW, AWAY
    mock_model.is_trained = True
    mock_model.get_model_info.return_value = {"name": "test_model", "version": "1.0"}

    with patch("src.ml.inference.model_loader.ModelLoader") as mock_loader_class:
        mock_loader_instance = MagicMock()
        mock_loader_instance.load_model.return_value = mock_model
        mock_loader_instance.model = mock_model
        mock_loader_class.return_value = mock_loader_instance

        # Mock Path.exists() for model file
        with patch("pathlib.Path.exists", return_value=True):
            yield mock_loader_instance


@pytest.fixture(scope="function")
def mock_config():
    """Mock配置对象"""
    from src.config_secure import Settings

    # 创建测试配置
    test_config = Settings()
    test_config.database.host = "localhost"
    test_config.database.port = 5432
    test_config.database.name = "football_prediction_test"
    test_config.database.user = "test_user"
    test_config.database.password = "test_password"

    test_config.redis.host = "localhost"
    test_config.redis.port = 6379
    test_config.redis.db = 1
    test_config.redis.password = ""

    test_config.api.secret_key = "test_secret_key_for_testing_only"
    test_config.api.jwt_secret_key = "test_jwt_secret_key_for_testing_only"

    with patch("src.config.get_settings", return_value=test_config):
        with patch("src.config.settings", test_config):
            yield test_config


# 禁用某些测试中的警告
@pytest.fixture(scope="session", autouse=True)
def suppress_warnings():
    """抑制测试中的非关键警告"""
    import warnings

    # 忽略一些已知的弃用警告
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=UserWarning, module="pandas")

    # 忽略覆盖率警告
    warnings.filterwarnings("ignore", message=".*coverage.*")


# 异步测试支持
@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# 测试数据工厂
@pytest.fixture
def sample_match_data():
    """示例比赛数据"""
    return {
        "match_id": "test_match_001",
        "home_team": "Manchester United",
        "away_team": "Arsenal",
        "home_team_id": "team_001",
        "away_team_id": "team_002",
        "league": "Premier League",
        "season": "2023-2024",
        "date": "2024-01-15",
        "venue": "Old Trafford",
    }


@pytest.fixture
def sample_prediction_request():
    """示例预测请求"""
    return {
        "home_team": "Manchester United",
        "away_team": "Arsenal",
        "model_name": "test_model",
        "include_probabilities": True,
        "include_confidence": True,
    }


# 标记支持
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")
    config.addinivalue_line("markers", "performance: marks tests as performance tests")


# 真实数据支持
@pytest.fixture
def sample_fotmob_data():
    """提供示例FotMob数据（约10MB样本的简化版本）"""
    import json

    return {
        "matches": [
            {
                "id": "12345",
                "homeTeam": {
                    "id": 98,
                    "name": "Manchester United",
                    "shortName": "Man Utd",
                    "country": {"name": "England"},
                },
                "awayTeam": {
                    "id": 42,
                    "name": "Arsenal",
                    "shortName": "Arsenal",
                    "country": {"name": "England"},
                },
                "status": {"started": True, "finished": True, "scoreStr": "2-1"},
                "homeScore": {"normaltime": 2},
                "awayScore": {"normaltime": 1},
                "startTime": "2025-01-15T20:00:00.000Z",
                "competition": {"name": "Premier League", "type": "league"},
                "stats": {
                    "expectedGoals": {
                        "homeTeam": {"value": 1.8, "before": 1.7},
                        "awayTeam": {"value": 1.2, "before": 1.1},
                    },
                    "possession": {
                        "homeTeam": {"value": 58},
                        "awayTeam": {"value": 42},
                    },
                    "shots": {
                        "homeTeam": {"onTarget": 6, "total": 15},
                        "awayTeam": {"onTarget": 3, "total": 8},
                    },
                },
                "odds": {
                    "homeWin": "2.10",
                    "draw": "3.40",
                    "awayWin": "3.60",
                    "overUnder25": "1.85",
                },
            },
            {
                "id": "12346",
                "homeTeam": {
                    "id": 31,
                    "name": "Chelsea",
                    "shortName": "Chelsea",
                    "country": {"name": "England"},
                },
                "awayTeam": {
                    "id": 46,
                    "name": "Liverpool",
                    "shortName": "Liverpool",
                    "country": {"name": "England"},
                },
                "status": {"started": True, "finished": True, "scoreStr": "1-1"},
                "homeScore": {"normaltime": 1},
                "awayScore": {"normaltime": 1},
                "startTime": "2025-01-14T15:00:00.000Z",
                "competition": {"name": "Premier League", "type": "league"},
                "stats": {
                    "expectedGoals": {
                        "homeTeam": {"value": 1.4, "before": 1.3},
                        "awayTeam": {"value": 1.6, "before": 1.5},
                    },
                    "possession": {
                        "homeTeam": {"value": 45},
                        "awayTeam": {"value": 55},
                    },
                    "shots": {
                        "homeTeam": {"onTarget": 4, "total": 12},
                        "awayTeam": {"onTarget": 5, "total": 14},
                    },
                },
                "odds": {
                    "homeWin": "2.85",
                    "draw": "3.20",
                    "awayWin": "2.45",
                    "overUnder25": "1.95",
                },
            },
            {
                "id": "12347",
                "homeTeam": {
                    "id": 21,
                    "name": "Manchester City",
                    "shortName": "Man City",
                    "country": {"name": "England"},
                },
                "awayTeam": {
                    "id": 61,
                    "name": "Tottenham",
                    "shortName": "Tottenham",
                    "country": {"name": "England"},
                },
                "status": {"started": True, "finished": True, "scoreStr": "3-0"},
                "homeScore": {"normaltime": 3},
                "awayScore": {"normaltime": 0},
                "startTime": "2025-01-13T17:30:00.000Z",
                "competition": {"name": "Premier League", "type": "league"},
                "stats": {
                    "expectedGoals": {
                        "homeTeam": {"value": 2.6, "before": 2.4},
                        "awayTeam": {"value": 0.8, "before": 0.9},
                    },
                    "possession": {
                        "homeTeam": {"value": 68},
                        "awayTeam": {"value": 32},
                    },
                    "shots": {
                        "homeTeam": {"onTarget": 9, "total": 22},
                        "awayTeam": {"onTarget": 2, "total": 6},
                    },
                },
                "odds": {
                    "homeWin": "1.35",
                    "draw": "5.80",
                    "awayWin": "7.20",
                    "overUnder25": "1.65",
                },
            },
        ]
    }


@pytest.fixture
def real_features_data():
    """提供真实特征数据的模拟"""
    try:
        import pandas as pd

        return pd.DataFrame(
            {
                "home_strength": [1.25, 0.95, 1.45],
                "away_strength": [0.85, 1.05, 0.75],
                "home_form": [0.75, 0.60, 0.85],
                "away_form": [0.65, 0.70, 0.55],
                "h2h_home_wins": [3, 2, 4],
                "h2h_away_wins": [2, 2, 1],
                "venue_factor": [1.1, 1.0, 1.2],
                "league_strength": [0.85, 0.85, 0.85],
                "recent_home_goals": [7, 5, 9],
                "recent_away_goals": [4, 5, 3],
                "expected_home_goals": [1.8, 1.4, 2.6],
                "expected_away_goals": [1.2, 1.6, 0.8],
            }
        )
    except ImportError:
        # 如果pandas不可用，返回字典格式
        return {
            "home_strength": [1.25, 0.95, 1.45],
            "away_strength": [0.85, 1.05, 0.75],
            "home_form": [0.75, 0.60, 0.85],
            "away_form": [0.65, 0.70, 0.55],
            "h2h_home_wins": [3, 2, 4],
            "h2h_away_wins": [2, 2, 1],
            "venue_factor": [1.1, 1.0, 1.2],
            "league_strength": [0.85, 0.85, 0.85],
            "recent_home_goals": [7, 5, 9],
            "recent_away_goals": [4, 5, 3],
            "expected_home_goals": [1.8, 1.4, 2.6],
            "expected_away_goals": [1.2, 1.6, 0.8],
        }


# 测试数据验证工具
class TestDataValidator:
    """测试数据验证工具类"""

    @staticmethod
    def validate_fotmob_match_data(match_data):
        """验证FotMob比赛数据的完整性"""
        required_fields = [
            "id",
            "homeTeam",
            "awayTeam",
            "status",
            "homeScore",
            "awayScore",
            "startTime",
        ]

        for field in required_fields:
            if field not in match_data:
                return False

        # 验证队伍数据
        for team in ["homeTeam", "awayTeam"]:
            if not all(key in match_data[team] for key in ["id", "name"]):
                return False

        # 验证比分
        if not all(key in match_data["status"] for key in ["started", "finished"]):
            return False

        return True

    @staticmethod
    def validate_prediction_result(result):
        """验证预测结果的完整性"""
        required_fields = ["probabilities", "predicted_class", "confidence"]

        for field in required_fields:
            if field not in result:
                return False

        # 验证概率格式
        probs = result["probabilities"]
        if not all(key in probs for key in ["home_win", "draw", "away_win"]):
            return False

        # 验证概率和
        prob_sum = probs["home_win"] + probs["draw"] + probs["away_win"]
        if abs(prob_sum - 1.0) > 0.01:
            return False

        return True


@pytest.fixture
def data_validator():
    """提供数据验证器实例"""
    return TestDataValidator()


# 收集测试时的钩子
def pytest_collection_modifyitems(config, items):
    """自动为测试添加标记"""
    for item in items:
        # 根据文件路径自动添加标记
        if "unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e/" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        elif "performance/" in str(item.fspath):
            item.add_marker(pytest.mark.performance)

        # 为异步测试添加marker
        if "async def" in item.nodeid:
            item.add_marker(pytest.mark.asyncio)

        # 为真实数据测试添加marker
        if "real_data" in item.nodeid:
            item.add_marker(pytest.mark.real_data)
