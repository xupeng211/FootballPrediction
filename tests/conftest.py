"""
pytest配置文件 - Issue #88 阶段2 简化版本
Simplified pytest configuration for Stage 2
"""

import os
import sys
import warnings
from typing import Any, Generator
from unittest.mock import MagicMock

import pytest

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 忽略一些警告
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# =============================================================================
# 简化的依赖
# =============================================================================


# 只导入最基本的依赖，避免复杂的依赖链
@pytest.fixture(scope="session")
def test_database_url():
    """测试数据库URL"""
    return "sqlite:///:memory:"


@pytest.fixture(scope="session")
def mock_async_db():
    """模拟异步数据库会话"""
    return MagicMock()


@pytest.fixture(scope="session")
def mock_db():
    """模拟数据库会话"""
    return MagicMock()


# =============================================================================
# 测试数据工厂
# =============================================================================


@pytest.fixture
def sample_match_data():
    """示例比赛数据"""
    return {
        "id": 1,
        "home_team": "Team A",
        "away_team": "Team B",
        "date": "2025-01-01",
        "status": "scheduled",
    }


@pytest.fixture
def sample_prediction_data():
    """示例预测数据"""
    return {
        "match_id": 1,
        "predicted_winner": "Team A",
        "confidence": 0.75,
        "prediction_type": "winner",
    }


@pytest.fixture
def sample_team_data():
    """示例队伍数据"""
    return {"id": 1, "name": "Team A", "league": "Premier League", "founded": 1890}


# =============================================================================
# 基础测试工具
# =============================================================================


@pytest.fixture
def mock_logger():
    """模拟日志记录器"""
    import logging

    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.fixture
def temp_directory():
    """临时目录fixture"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# =============================================================================
# 测试配置
# =============================================================================


@pytest.fixture(scope="session")
def test_config():
    """测试配置"""
    return {
        "timeout": 30,
        "retry_attempts": 3,
        "debug": False,
        "mock_external_services": True,
    }


# =============================================================================
# 标记和配置
# =============================================================================


def pytest_configure(config):
    """pytest配置"""
    # 添加自定义标记
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "api: API测试")
    config.addinivalue_line("markers", "database: 数据库测试")
    config.addinivalue_line("markers", "slow: 慢速测试")
    config.addinivalue_line("markers", "external: 外部服务测试")


def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    # 为没有标记的测试添加默认标记
    for item in items:
        if not any(item.iter_markers()):
            item.add_marker(pytest.mark.unit)


# =============================================================================
# 测试报告
# =============================================================================


@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    """会话结束时的清理"""
    print("\n" + "=" * 50)
    print("🧪 测试会话结束")
    print(f"📊 总测试数: {len(session.items)}")
    # print(f"⏱️  总用时: {session.duration}秒")
    if exitstatus == 0:
        print("✅ 所有测试通过")
    else:
        print(f"❌ 有 {session.testsfailed} 个测试失败")
    print("=" * 50)


# =============================================================================
# 清理和重置
# =============================================================================


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """每个测试后的清理"""
    # 可以在这里添加测试后的清理逻辑
    pass


@pytest.fixture(scope="session", autouse=True)
def global_cleanup():
    """全局清理"""
    # 可以在这里添加全局清理逻辑
    pass
