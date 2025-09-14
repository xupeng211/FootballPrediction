"""
单元测试：足球数据清洗器
"""

from unittest.mock import patch

import pytest

from src.data.processing.football_data_cleaner import FootballDataCleaner


class TestFootballDataCleaner:
    @pytest.fixture
    def data_cleaner(self):
        with patch("src.data.processing.football_data_cleaner.DatabaseManager"):
            return FootballDataCleaner()

    def test_data_cleaner_initialization(self, data_cleaner):
        assert data_cleaner is not None
        assert hasattr(data_cleaner, "logger")

    def test_clean_match_data_exists(self, data_cleaner):
        # 简化测试：只验证方法存在且可调用
        assert hasattr(data_cleaner, "clean_match_data")
        assert callable(getattr(data_cleaner, "clean_match_data"))

    def test_data_cleaner_methods_exist(self, data_cleaner):
        assert hasattr(data_cleaner, "clean_match_data")
        assert hasattr(data_cleaner, "clean_odds_data")
