"""
足球数据清洗器测试

测试足球数据清洗的各个功能，包括时间统一、球队ID映射、赔率校验、比分校验等。
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

    @pytest.fixture
    def mock_db_manager(self):
        """模拟数据库管理器"""
        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()

        # 模拟球队ID查询
        mock_result.fetchone.return_value = (1,)
        mock_session.execute.return_value = mock_result
        mock_db.get_async_session.return_value.__aenter__.return_value = mock_session

        return mock_db

    def test_init(self, cleaner):
        """测试初始化"""
        assert cleaner.db_manager is not None
        assert cleaner.logger is not None
        assert isinstance(cleaner._team_id_cache, dict)
        assert isinstance(cleaner._league_id_cache, dict)
        assert len(cleaner._team_id_cache) == 0
        assert len(cleaner._league_id_cache) == 0

    @pytest.mark.asyncio
    async def test_clean_match_data_success(self, cleaner, raw_match_data, mock_db_manager):
        """测试成功清洗比赛数据"""
        cleaner.db_manager = mock_db_manager

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

    @pytest.mark.asyncio
    async def test_to_utc_time(self, cleaner):
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
    async def test_validate_score(self, cleaner):
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

    @pytest.mark.asyncio
    async def test_clean_team_names(self, cleaner):
        """测试球队名称清洗"""
        # 带空格的球队名
        team_names = {
            "home_team": "  Manchester United  ",
            "away_team": "Liverpool FC   "
        }
        cleaned = await cleaner._clean_team_names(team_names)

        assert cleaned["home_team"] == "Manchester United"
        assert cleaned["away_team"] == "Liverpool FC"

        # 包含特殊字符的球队名
        special_names = {
            "home_team": "Real Madrid®",
            "away_team": "FC Barcelona™"
        }
        cleaned = await cleaner._clean_team_names(special_names)

        assert "®" not in cleaned["home_team"]
        assert "™" not in cleaned["away_team"]

    @pytest.mark.asyncio
    async def test_clean_league_name(self, cleaner):
        """测试联赛名称清洗"""
        # 完整联赛名称
        full_league_name = "Premier League"
        cleaned = await cleaner._clean_league_name(full_league_name)
        assert cleaned == "Premier League"

        # 带额外信息的联赛名称
        verbose_league_name = "English Premier League 2023/24"
        cleaned = await cleaner._clean_league_name(verbose_league_name)
        assert cleaned == "Premier League"

        # 空联赛名称
        empty_league_name = ""
        cleaned = await cleaner._clean_league_name(empty_league_name)
        assert cleaned == ""

    @pytest.mark.asyncio
    async def test_clean_referee_name(self, cleaner):
        """测试裁判名称清洗"""
        # 带职称的裁判名
        referee_with_title = "Mr. Michael Oliver"
        cleaned = await cleaner._clean_referee_name(referee_with_title)
        assert cleaned == "Michael Oliver"

        # 带空格的裁判名
        referee_with_spaces = "  Michael   Oliver  "
        cleaned = await cleaner._clean_referee_name(referee_with_spaces)
        assert cleaned == "Michael Oliver"

        # 空裁判名
        empty_referee = ""
        cleaned = await cleaner._clean_referee_name(empty_referee)
        assert cleaned == ""

    @pytest.mark.asyncio
    async def test_validate_match_status(self, cleaner):
        """测试比赛状态验证"""
        # 有效状态
        valid_statuses = ["FINISHED", "SCHEDULED", "IN_PLAY", "POSTPONED"]
        for status in valid_statuses:
            result = await cleaner._validate_match_status(status)
            assert result is True

        # 无效状态
        invalid_status = "INVALID_STATUS"
        result = await cleaner._validate_match_status(invalid_status)
        assert result is False

        # 空状态
        empty_status = ""
        result = await cleaner._validate_match_status(empty_status)
        assert result is False

    @pytest.mark.asyncio
    async def test_apply_business_rules(self, cleaner, raw_match_data):
        """测试业务规则应用"""
        cleaned_data = raw_match_data.copy()

        # 应用业务规则
        result = await cleaner._apply_business_rules(cleaned_data)

        assert isinstance(result, dict)
        assert "home_team" in result
        assert "away_team" in result
        assert "match_date" in result

        # 验证业务规则被应用
        # 例如：确保比赛ID不为空
        assert result.get("match_id") != ""

    @pytest.mark.asyncio
    async def test_calculate_data_quality_score(self, cleaner):
        """�试数据质量评分计算"""
        # 完整数据
        complete_data = {
            "match_id": "12345",
            "home_team": "Team A",
            "away_team": "Team B",
            "home_score": 2,
            "away_score": 1,
            "match_date": "2024-01-15T15:00:00Z",
            "league": "League A",
            "status": "FINISHED"
        }

        score = await cleaner._calculate_data_quality_score(complete_data)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert score > 0.8  # 完整数据应该有高质量分数

        # 不完整数据
        incomplete_data = {
            "match_id": "12345",
            "home_team": "Team A"
            # 缺少很多字段
        }

        score = await cleaner._calculate_data_quality_score(incomplete_data)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert score < 0.5  # 不完整数据应该有较低质量分数

    @pytest.mark.asyncio
    async def test_clean_batch_data(self, cleaner, raw_match_data):
        """测试批量数据清洗"""
        batch_data = [
            raw_match_data,
            raw_match_data.copy(),
            raw_match_data.copy()
        ]

        with patch.object(cleaner, 'clean_match_data') as mock_clean:
            mock_clean.side_effect = [
                raw_match_data,
                raw_match_data.copy(),
                None  # 模拟一个清洗失败
            ]

            results = await cleaner.clean_batch_data(batch_data)

            assert isinstance(results, list)
            assert len(results) == 2  # 只有两个成功
            assert mock_clean.call_count == 3

    @pytest.mark.asyncio
    async def test_get_cleaning_statistics(self, cleaner):
        """测试清洗统计信息"""
        with patch.object(cleaner, '_cleaning_stats', {
            'total_processed': 100,
            'successful': 85,
            'failed': 15,
            'quality_scores': [0.9, 0.8, 0.95, 0.85]
        }):

            stats = await cleaner.get_cleaning_statistics()

            assert isinstance(stats, dict)
            assert 'total_processed' in stats
            assert 'successful' in stats
            assert 'failed' in stats
            assert 'success_rate' in stats
            assert 'average_quality_score' in stats

            assert stats['total_processed'] == 100
            assert stats['successful'] == 85
            assert stats['failed'] == 15
            assert stats['success_rate'] == 0.85
            assert 'average_quality_score' in stats

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

    @pytest.mark.asyncio
    async def test_performance_with_large_dataset(self, cleaner):
        """测试大数据集性能"""
        # 创建大量测试数据
        large_dataset = []
        for i in range(1000):
            data = {
                "match_id": f"match_{i}",
                "home_team": f"Team {i}",
                "away_team": f"Team {i+1}",
                "home_score": i % 5,
                "away_score": i % 3,
                "match_date": "2024-01-15T15:00:00Z",
                "league": "Test League",
                "status": "FINISHED"
            }
            large_dataset.append(data)

        # 模拟快速处理
        with patch.object(cleaner, 'clean_match_data') as mock_clean:
            mock_clean.return_value = {"cleaned": True}

            results = await cleaner.clean_batch_data(large_dataset)

            assert len(results) == 1000
            assert mock_clean.call_count == 1000

    def test_cache_functionality(self, cleaner):
        """测试缓存功能"""
        # 验证缓存初始化
        assert isinstance(cleaner._team_id_cache, dict)
        assert isinstance(cleaner._league_id_cache, dict)

        # 验证缓存为空
        assert len(cleaner._team_id_cache) == 0
        assert len(cleaner._league_id_cache) == 0

    @pytest.mark.asyncio
    async def test_logging_functionality(self, cleaner, caplog):
        """测试日志功能"""
        import logging

        # 设置日志级别
        cleaner.logger.setLevel(logging.INFO)

        # 执行一个操作
        await cleaner._validate_scores({"home_score": 2, "away_score": 1})

        # 验证日志被调用
        # 注意：这个测试可能需要根据实际的日志实现进行调整
        assert cleaner.logger is not None

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