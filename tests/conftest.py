"""
统一的测试配置和Fixtures
提供测试所需的所有Mock数据和配置

V119.0: 新增回归测试所需的数据库连接和Playwright浏览器fixtures
V144.2: 新增.env文件自动加载，确保测试能获取正确的数据库配置
"""

# 添加src路径
import sys
from pathlib import Path
from unittest.mock import Mock
from typing import AsyncGenerator, Generator, Any

import numpy as np
import pandas as pd
import pytest
import psycopg2
import psycopg2.extras

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# V144.2: 加载.env文件（必须在src导入之后，确保路径正确）
from dotenv import load_dotenv
import os

project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
load_dotenv(env_file, override=True)


# ============================================================================
# V119.0: 回归测试 Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def db_connection():
    """V119.0: 数据库连接 Fixture (Session级别)

    用于回归测试中查询历史比赛数据。

    Yields:
        psycopg2.connection: 数据库连接对象
    """
    from src.config_unified import get_settings

    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=psycopg2.extras.RealDictCursor
    )

    yield conn

    conn.close()


@pytest.fixture(scope="session")
def historical_match_sample(db_connection: psycopg2.extensions.connection) -> dict[str, Any]:
    """V119.0: 历史比赛样本 (Session级别)

    用于 Test A - 2021-2022 年历史比赛兼容性测试。

    Args:
        db_connection: 数据库连接

    Returns:
        dict: 包含 match_id 和 oddsportal_url 的历史比赛样本
    """
    cursor = db_connection.cursor()
    cursor.execute("""
        SELECT match_id, oddsportal_url, match_date
        FROM matches
        WHERE oddsportal_url IS NOT NULL
          AND oddsportal_url LIKE '%oddsportal.com%'
          AND match_date >= '2021-01-01'
          AND match_date <= '2022-12-31'
          AND is_finished = true
        ORDER BY RANDOM()
        LIMIT 1
    """)

    result = cursor.fetchone()
    cursor.close()

    if not result:
        pytest.skip("No historical matches found for testing")

    return {
        "match_id": result["match_id"],
        "oddsportal_url": result["oddsportal_url"],
        "match_date": result["match_date"]
    }


@pytest.fixture(scope="session")
def recent_match_sample(db_connection: psycopg2.extensions.connection) -> dict[str, Any]:
    """V119.0: 近期比赛样本 (Session级别)

    用于 Test B - 2024-2025 年高精度验证测试。

    Args:
        db_connection: 数据库连接

    Returns:
        dict: 包含 match_id 和 oddsportal_url 的近期比赛样本
    """
    cursor = db_connection.cursor()
    cursor.execute("""
        SELECT match_id, oddsportal_url, match_date
        FROM matches
        WHERE oddsportal_url IS NOT NULL
          AND oddsportal_url LIKE '%oddsportal.com%'
          AND match_date >= '2024-01-01'
          AND is_finished = true
        ORDER BY RANDOM()
        LIMIT 1
    """)

    result = cursor.fetchone()
    cursor.close()

    if not result:
        pytest.skip("No recent matches found for testing")

    return {
        "match_id": result["match_id"],
        "oddsportal_url": result["oddsportal_url"],
        "match_date": result["match_date"]
    }


@pytest.fixture
async def playwright_browser() -> AsyncGenerator:
    """V119.0: Playwright 浏览器 Fixture (Function级别)

    用于 E2E 回归测试。每次测试后自动关闭浏览器。

    Yields:
        Page: Playwright Page 对象
    """
    from playwright.async_api import async_playwright, Browser, Page

    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page: Page = await context.new_page()

        yield page

        await context.close()
        await browser.close()


# ============================================================================
# 原有 Fixtures
# ============================================================================


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
    config.addinivalue_line("markers", "e2e: 标记端到端测试 (V119.0)")


# 测试收集钩子
def pytest_collection_modifyitems(config, items):
    """修改测试收集，自动添加标记"""
    for item in items:
        # 根据路径自动添加标记
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
