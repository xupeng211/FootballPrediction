"""
ML Data Tests Configuration
ML数据模块测试配置文件

提供测试所需的fixtures和配置
"""

import pytest
import pandas as pd
from datetime import datetime, timezone
from typing import List, Dict, Any
import asyncio
from unittest.mock import AsyncMock, Mock


@pytest.fixture
def sample_match_data() -> List[Dict[str, Any]]:
    """示例比赛数据fixture"""
    return [
        {
            'id': 1,
            'home_team_id': 'team_123',
            'away_team_id': 'team_456',
            'home_score': 2,
            'away_score': 1,
            'home_team_name': 'Manchester United',
            'away_team_name': 'Liverpool',
            'match_date': datetime(2024, 1, 15, 15, 0, 0, tzinfo=timezone.utc),
            'status': 'FT',
            'home_expected_goals': 1.5,
            'away_expected_goals': 0.8,
            'home_big_chances_created': 12,
            'away_big_chances_created': 8,
            'home_possession': 55.2,
            'away_possession': 44.8,
            'home_shots': 15,
            'away_shots': 12,
            'home_corners': 6,
            'away_corners': 4,
        },
        {
            'id': 2,
            'home_team_id': 'team_789',
            'away_team_id': 'team_012',
            'home_score': 1,
            'away_score': 1,
            'home_team_name': 'Arsenal',
            'away_team_name': 'Chelsea',
            'match_date': datetime(2024, 1, 16, 17, 30, 0, tzinfo=timezone.utc),
            'status': 'FT',
            'home_expected_goals': 1.2,
            'away_expected_goals': 1.1,
            'home_big_chances_created': 6,
            'away_big_chances_created': 7,
            'home_possession': 48.5,
            'away_possession': 51.5,
            'home_shots': 14,
            'away_shots': 16,
            'home_corners': 5,
            'away_corners': 7,
        },
    ]


@pytest.fixture
def sample_dataframe(sample_match_data) -> pd.DataFrame:
    """示例DataFrame fixture"""
    return pd.DataFrame(sample_match_data)


@pytest.fixture
def mock_database_session():
    """模拟数据库会话fixture"""
    session = Mock()
    session.execute = AsyncMock()
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    return session


@pytest.fixture
def mock_sql_result():
    """模拟SQL查询结果"""
    result = Mock()
    result.fetchall = Mock(return_value=[])
    result.first = Mock(return_value=None)
    result.scalar = Mock(return_value=None)
    return result


@pytest.fixture(scope="session")
def event_loop():
    """为异步测试提供事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ML相关测试标记
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line(
        "markers", "ml: Mark test as ML specific test"
    )
    config.addinivalue_line(
        "markers", "data: Mark test as data processing test"
    )
    config.addinivalue_line(
        "markers", "integration: Mark test as integration test"
    )
