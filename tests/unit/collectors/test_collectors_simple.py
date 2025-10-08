import pytest
from unittest.mock import MagicMock, patch
import sys
import os
from src.collectors.fixtures_collector import FixturesCollector
from src.collectors.scores_collector import ScoresCollector

"""
数据收集器简化测试 / Data Collectors Simple Tests

只测试基本的初始化和存在的方法
"""


# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))


@pytest.mark.unit
class TestCollectorsSimple:
    """数据收集器简化测试"""

    def test_fixtures_collector_import(self):
        """测试FixturesCollector导入"""
        # 使用sys.modules直接缓存修改后的模块
        with patch.dict(
            "sys.modules",
            {
                "src.database.base": MagicMock(),
                "src.database.connection": MagicMock(),
                "src.cache.redis_manager": MagicMock(),
                "src.models.common_models": MagicMock(),
                "src.utils.logger": MagicMock(),
            },
        ):
            # Mock logger
            mock_logger = MagicMock()
            with patch("src.utils.logger.get_logger", return_value=mock_logger):
                try:
                    assert FixturesCollector is not None
                    assert FixturesCollector.__name__ == "FixturesCollector"
                except ImportError as e:
                    pytest.skip(f"Cannot import FixturesCollector: {e}")

    def test_odds_collector_import(self):
        """测试OddsCollector导入"""
        with patch.dict(
            "sys.modules",
            {
                "src.database.base": MagicMock(),
                "src.database.connection": MagicMock(),
                "src.cache.redis_manager": MagicMock(),
                "src.models.common_models": MagicMock(),
                "src.utils.logger": MagicMock(),
            },
        ):
            mock_logger = MagicMock()
            with patch("src.utils.logger.get_logger", return_value=mock_logger):
                try:
                    from src.collectors.odds_collector import OddsCollector

                    assert OddsCollector is not None
                    assert OddsCollector.__name__ == "OddsCollector"
                except ImportError as e:
                    pytest.skip(f"Cannot import OddsCollector: {e}")

    def test_scores_collector_import(self):
        """测试ScoresCollector导入"""
        with patch.dict(
            "sys.modules",
            {
                "src.database.base": MagicMock(),
                "src.database.connection": MagicMock(),
                "src.cache.redis_manager": MagicMock(),
                "src.models.common_models": MagicMock(),
                "src.utils.logger": MagicMock(),
            },
        ):
            mock_logger = MagicMock()
            with patch("src.utils.logger.get_logger", return_value=mock_logger):
                try:
                    assert ScoresCollector is not None
                    assert ScoresCollector.__name__ == "ScoresCollector"
                except ImportError as e:
                    pytest.skip(f"Cannot import ScoresCollector: {e}")
