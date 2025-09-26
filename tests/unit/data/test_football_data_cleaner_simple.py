"""
足球数据清洗器测试 - 简化版本

测试足球数据清洗的核心功能，专注于实际存在的方法。
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List
import pandas as pd

from src.data.processing.football_data_cleaner import FootballDataCleaner


class TestFootballDataCleaner:
    """足球数据清洗器测试类"""

    @pytest.fixture
    def cleaner(self):
        """创建FootballDataCleaner实例"""
        with patch("src.data.processing.football_data_cleaner.DatabaseManager"):
            return FootballDataCleaner()

    @pytest.fixture
    def raw_match_data(self):
        """原始比赛数据"""
        return {
            "id": "12345",
            "homeTeam": {"name": "Manchester United"},
            "awayTeam": {"name": "Liverpool FC"},
            "score": {
                "fullTime": {"home": 2, "away": 1},
                "halfTime": {"home": 1, "away": 0}
            },
            "utcDate": "2024-01-15T15:00:00Z",
            "competition": {"id": "PL"},
            "status": "FINISHED",
            "season": {"startDate": "2024-01-01", "endDate": "2024-12-31"},
            "matchday": 21,
            "venue": "Old Trafford",
            "referees": [{"name": "Michael Oliver"}]
        }

    @pytest.fixture
    def invalid_match_data(self):
        """包含无效数据的比赛数据"""
        return {
            # 缺少必需的 id 字段
            "homeTeam": {"name": ""},
            "awayTeam": {"name": "Liverpool FC"},
            "score": {
                "fullTime": {"home": -1, "away": 150},
                "halfTime": {"home": 0, "away": 0}
            },
            "utcDate": "invalid-date",
            "competition": {"id": ""},
            "status": "FINISHED"
        }

    def test_init(self, cleaner):
        """测试初始化"""
    assert cleaner.db_manager is not None
    assert cleaner.logger is not None
    assert isinstance(cleaner._team_id_cache, dict)
    assert isinstance(cleaner._league_id_cache, dict)
    assert len(cleaner._team_id_cache) == 0
    assert len(cleaner._league_id_cache) == 0

    def test_validate_score(self, cleaner):
        """测试比分验证"""
        # 正常比分
        result = cleaner._validate_score(2)
    assert result == 2

        # 负数比分
        result = cleaner._validate_score(-1)
    assert result is None

        # 过大比分
        result = cleaner._validate_score(150)
    assert result is None

        # 非整数比分 - 应该转换为整数
        result = cleaner._validate_score(2.5)
    assert result == 2  # 转换为整数

        # 字符串数字
        result = cleaner._validate_score("3")
    assert result == 3

        # 无效字符串
        result = cleaner._validate_score("invalid")
    assert result is None

    def test_validate_odds_value(self, cleaner):
        """测试赔率验证"""
        # 正常赔率
        result = cleaner._validate_odds_value(2.10)
    assert result is True

        # 过小赔率
        result = cleaner._validate_odds_value(0.50)
    assert result is False

        # 边界值
        result = cleaner._validate_odds_value(1.01)
    assert result is True

        result = cleaner._validate_odds_value(1.00)
    assert result is False

        # 很大但有效的赔率
        result = cleaner._validate_odds_value(10000.0)
    assert result is True  # 只要有下限，没有上限

        # 无效赔率格式
        result = cleaner._validate_odds_value("invalid")
    assert result is False

        # 字符串数字
        result = cleaner._validate_odds_value("2.50")
    assert result is True

    def test_clean_venue_name(self, cleaner):
        """测试场馆名称清洗"""
        # 带空格的场馆名
        venue = "  Old Trafford  "
        cleaned = cleaner._clean_venue_name(venue)
    assert cleaned == "Old Trafford"

        # 空场馆名
        empty_venue = ""
        cleaned = cleaner._clean_venue_name(empty_venue)
    assert cleaned is None  # 空字符串返回None

        # None值
        none_venue = None
        cleaned = cleaner._clean_venue_name(none_venue)
    assert cleaned is None

    def test_clean_referee_name(self, cleaner):
        """测试裁判名称清洗"""
        # 正常裁判列表
        referees = [
            {"name": "Michael Oliver", "role": "REFEREE"},
            {"name": "Assistant Referee 1", "role": "ASSISTANT_REFEE"}
        ]
        cleaned = cleaner._clean_referee_name(referees)
    assert cleaned == "Michael Oliver"

        # 没有主裁判
        no_main_referee = [
            {"name": "Assistant Referee 1", "role": "ASSISTANT_REFeree"}
        ]
        cleaned = cleaner._clean_referee_name(no_main_referee)
    assert cleaned is None

        # 空列表
        empty_referees = []
        cleaned = cleaner._clean_referee_name(empty_referees)
    assert cleaned is None

        # None值
        none_referees = None
        cleaned = cleaner._clean_referee_name(none_referees)
    assert cleaned is None

        # 非列表输入
        string_input = "not a list"
        cleaned = cleaner._clean_referee_name(string_input)
    assert cleaned is None

    @pytest.mark.asyncio
    async def test_clean_match_data_success(self, cleaner, raw_match_data):
        """测试成功清洗比赛数据"""
        # Mock database operations
        cleaner.db_manager = MagicMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)
        mock_session.execute.return_value = mock_result
        cleaner.db_manager.get_async_session.return_value.__aenter__.return_value = mock_session

        result = await cleaner.clean_match_data(raw_match_data)

    assert result is not None
    assert isinstance(result, dict)
    assert result["external_match_id"] == "12345"
    assert result["home_score"] == 2
    assert result["away_score"] == 1
    assert result["home_ht_score"] == 1
    assert result["away_ht_score"] == 0
    assert result["match_status"] == "finished"
    assert result["league_id"] is not None
    assert result["matchday"] == 21

    @pytest.mark.asyncio
    async def test_clean_match_data_invalid_data(self, cleaner, invalid_match_data):
        """测试清洗无效数据"""
        result = await cleaner.clean_match_data(invalid_match_data)

        # 无效数据应该返回None
    assert result is None

    @pytest.mark.asyncio
    async def test_clean_match_data_missing_required_fields(self, cleaner):
        """测试缺失必需字段的数据"""
        incomplete_data = {
            "match_id": "12345",
            "home_team": "Team A",
            # 缺少away_team等必需字段
        }

        result = await cleaner.clean_match_data(incomplete_data)

        # 缺失必需字段应该返回None
    assert result is None

    def test_to_utc_time(self, cleaner):
        """测试时间标准化"""
        # 测试UTC时间
        utc_time = "2024-01-15T15:00:00Z"
        normalized = cleaner._to_utc_time(utc_time)
    assert normalized == "2024-01-15T15:00:00+00:00"

        # 测试带时区的时间
        local_time = "2024-01-15T15:00:00+08:00"
        normalized = cleaner._to_utc_time(local_time)
        # 应该转换为UTC
    assert normalized is not None

        # 测试无效时间格式
        invalid_time = "2024-01-15 15:00:00"
        normalized = cleaner._to_utc_time(invalid_time)
        # 应该尝试解析或返回默认值
    assert normalized is not None

    @pytest.mark.asyncio
    async def test_error_handling(self, cleaner):
        """测试错误处理"""
        # 模拟数据库异常
        cleaner.db_manager = MagicMock()
        cleaner.db_manager.get_async_session.side_effect = Exception("Database error")

        invalid_data = {"invalid": "data"}
        result = await cleaner.clean_match_data(invalid_data)

        # 异常情况下应该返回None或抛出适当的异常
    assert result is None

    def test_cache_functionality(self, cleaner):
        """测试缓存功能"""
        # 验证缓存初始化
    assert isinstance(cleaner._team_id_cache, dict)
    assert isinstance(cleaner._league_id_cache, dict)

        # 验证缓存为空
    assert len(cleaner._team_id_cache) == 0
    assert len(cleaner._league_id_cache) == 0

    @pytest.mark.asyncio
    async def test_edge_cases(self, cleaner):
        """测试边界情况"""
        # 测试None输入
        result = await cleaner.clean_match_data(None)
    assert result is None

        # 测试空字典输入
        result = await cleaner.clean_match_data({})
    assert result is None

        # 测试只有部分字段的输入
        partial_data = {"match_id": "123"}
        result = await cleaner.clean_match_data(partial_data)
    assert result is None


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])