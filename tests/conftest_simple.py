"""
简化的pytest配置文件 - Issue #88 阶段1
Minimal pytest configuration for Stage 1 testing
"""

import os
import sys
import warnings
from typing import Any, Generator

import pytest

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 忽略一些警告
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)


@pytest.fixture(scope="session")
def test_config():
    """测试配置fixture"""
    return {
        "database_url": "sqlite:///:memory:",
        "test_timeout": 30,
        "mock_external_services": True,
    }


@pytest.fixture
def sample_data():
    """示例数据fixture"""
    return {
        "test_match": {
            "id": 1,
            "home_team": "Team A",
            "away_team": "Team B",
            "date": "2025-01-01",
        },
        "test_prediction": {
            "match_id": 1,
            "predicted_winner": "Team A",
            "confidence": 0.75,
        },
    }


@pytest.fixture
def mock_logger():
    """模拟loggerfixture"""
    import logging

    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)
    return logger


def pytest_configure(config):
    """pytest配置"""
    # 添加自定义标记
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "api: API测试")
    config.addinivalue_line("markers", "database: 数据库测试")
    config.addinivalue_line("markers", "slow: 慢速测试")


def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    # 为没有标记的测试添加默认标记
    for item in items:
        if not any(item.iter_markers()):
            item.add_marker(pytest.mark.unit)
