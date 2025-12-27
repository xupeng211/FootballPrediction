"""
统一的测试配置和Fixtures
提供测试所需的所有Mock数据和配置
"""

# 添加src路径
import sys
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session")
def test_data_dir():
    """测试数据目录"""
    return Path(__file__).parent / "fixtures" / "data"


@pytest.fixture(scope="session")
def mock_responses_dir():
    """Mock响应数据目录"""
    return Path(__file__).parent / "fixtures" / "mock_responses"


@pytest.fixture
def sample_match_data():
    """标准比赛数据样本"""
    return {
        "id": "4147463",
        "homeTeam": {"id": 8455, "name": "Manchester City", "shortName": "Man City"},
        "awayTeam": {"id": 8466, "name": "Liverpool", "shortName": "Liverpool"},
        "status": {"finished": True, "started": True},
        "content": {
            "stats": {
                "Periods": {
                    "All": {
                        "stats": [
                            {"key": "expected_goals", "stats": [{"value": 2.1}, {"value": 1.8}]},
                            {"key": "BallPossesion", "stats": [{"value": 65}, {"value": 35}]},
                            {"key": "TotalShots", "stats": [{"value": 18}, {"value": 12}]},
                            {"key": "ShotsOnTarget", "stats": [{"value": 7}, {"value": 4}]},
                            {"key": "Corners", "stats": [{"value": 8}, {"value": 3}]},
                            {"key": "YellowCards", "stats": [{"value": 2}, {"value": 3}]},
                            {"key": "RedCards", "stats": [{"value": 0}, {"value": 0}]},
                        ]
                    }
                }
            }
        },
    }


@pytest.fixture
def sample_match_data_edge_cases():
    """边缘情况比赛数据"""
    return [
        # 空值情况
        {
            "id": "empty_1",
            "content": {"stats": {"Periods": {"All": {"stats": []}}}},
            "homeTeam": {"name": "Team A"},
            "awayTeam": {"name": "Team B"},
        },
        # 缺失字段
        {"id": "missing_fields", "homeTeam": {"name": "Team A"}, "awayTeam": {"name": "Team B"}, "content": {}},
        # 异常数据类型
        {
            "id": "invalid_types",
            "homeTeam": {"name": None},
            "awayTeam": {"name": ""},
            "content": {"stats": {"Periods": {"All": {"stats": [{"key": None}]}}}},
        },
        # 极端数值
        {
            "id": "extreme_values",
            "content": {
                "stats": {
                    "Periods": {
                        "All": {"stats": [{"key": "expected_goals", "stats": [{"value": 9999.9}, {"value": -1.0}]}]}
                    }
                }
            },
        },
    ]


@pytest.fixture
def sample_feature_df():
    """标准特征DataFrame样本"""
    data = {
        "home_xg": [2.1, 1.5, 0.8],
        "away_xg": [1.8, 2.2, 1.1],
        "home_possession": [65, 45, 55],
        "away_possession": [35, 55, 45],
        "home_shots": [18, 12, 8],
        "away_shots": [12, 15, 10],
        "home_corners": [8, 4, 6],
        "away_corners": [3, 7, 5],
        "home_yellow_cards": [2, 1, 3],
        "away_yellow_cards": [3, 2, 1],
        "home_red_cards": [0, 1, 0],
        "away_red_cards": [0, 0, 1],
        "result": [1, 0, 2],  # 1=主胜, 0=平局, 2=客胜
        "home_team": ["Man City", "Chelsea", "Arsenal"],
        "away_team": ["Liverpool", "Man United", "Tottenham"],
    }
    return pd.DataFrame(data)


@pytest.fixture
def mock_lightgbm_model():
    """Mock LightGBM模型"""
    model = Mock()
    model.predict = Mock(return_value=np.array([0.65, 0.25, 0.10]))
    model.num_feature = Mock(return_value=30)
    model.feature_name = Mock(return_value=[f"feature_{i}" for i in range(30)])
    return model


@pytest.fixture
def mock_api_client():
    """Mock API客户端"""
    client = Mock()
    client.get_request_stats = Mock(
        return_value={"session_id": "test_session_123", "total_requests": 10, "success_rate": 0.95}
    )
    client.fetch_match_data = Mock(return_value={"status": "success"})
    return client


@pytest.fixture
def mock_config():
    """Mock配置对象"""
    config = Mock()
    config.validate = Mock(return_value={"valid": True, "environment": "test", "issues": []})
    config.paths = Mock()
    config.paths.project_root = Path("/tmp/test_project")
    config.paths.data_dir = Path("/tmp/test_data")
    config.paths.current_model_path = Path("/tmp/test_model.model")
    config.paths.final_features_path = Path("/tmp/test_features.csv")
    config.paths.logs_dir = Path("/tmp/test_logs")
    return config


@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path):
    """自动设置测试环境"""
    # 创建临时目录结构
    test_dirs = [tmp_path / "data", tmp_path / "logs", tmp_path / "models"]
    for dir_path in test_dirs:
        dir_path.mkdir(parents=True, exist_ok=True)

    # 设置环境变量
    import os

    os.environ["ENVIRONMENT"] = "test"
    os.environ["LOG_LEVEL"] = "DEBUG"

    yield

    # 清理环境变量
    os.environ.pop("ENVIRONMENT", None)
    os.environ.pop("LOG_LEVEL", None)


# 测试标记
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line("markers", "unit: 标记单元测试")
    config.addinivalue_line("markers", "integration: 标记集成测试")
    config.addinivalue_line("markers", "slow: 标记慢速测试")
    config.addinivalue_line("markers", "network: 标记需要网络的测试")


# 测试收集钩子
def pytest_collection_modifyitems(config, items):
    """修改测试收集，自动添加标记"""
    for item in items:
        # 根据路径自动添加标记
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
