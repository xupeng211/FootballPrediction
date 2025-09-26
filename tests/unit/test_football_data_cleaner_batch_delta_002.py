"""
Football Data Cleaner Batch-Δ-002 测试套件

专门为 data/processing/football_data_cleaner.py 设计的测试，目标是将其覆盖率从 10% 提升至 ≥20%
覆盖初始化、比赛数据清洗、赔率数据清洗、数据验证、时间转换等功能
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.data.processing.football_data_cleaner import FootballDataCleaner


class TestFootballDataCleanerBatchDelta002:
    """FootballDataCleaner Batch-Δ-002 测试类"""

    @pytest.fixture
    def cleaner(self):
        """创建足球数据清洗器实例"""
        # Mock DatabaseManager 以避免数据库连接
        with patch('src.data.processing.football_data_cleaner.DatabaseManager') as mock_db:
            mock_db.return_value = Mock()
            cleaner = FootballDataCleaner()
            # Mock logger
            cleaner.logger = Mock()
            return cleaner

    @pytest.fixture
    def sample_match_data(self):
        """创建示例比赛数据"""
        return {
            "id": "12345",
            "competition": {
                "id": "PL",
                "name": "Premier League"
            },
            "utcDate": "2025-01-15T15:00:00Z",
            "homeTeam": {
                "id": 64,
                "name": "Liverpool FC"
            },
            "awayTeam": {
                "id": 61,
                "name": "Arsenal FC"
            },
            "status": "FINISHED",
            "score": {
                "fullTime": {
                    "home": 2,
                    "away": 1
                },
                "halfTime": {
                    "home": 1,
                    "away": 0
                }
            },
            "season": {
                "id": 2024,
                "startDate": "2024-08-01",
                "endDate": "2025-05-31"
            },
            "matchday": 22,
            "venue": "Anfield",
            "referees": [
                {
                    "id": 12345,
                    "name": "Michael Oliver",
                    "role": "REFEREE"
                }
            ]
        }

    @pytest.fixture
    def sample_odds_data(self):
        """创建示例赔率数据"""
        return [
            {
                "match_id": "12345",
                "bookmaker": {
                    "id": 8,
                    "name": "Bet365"
                },
                "market_type": "h2h",
                "outcomes": [
                    {
                        "name": "Home",
                        "price": 2.10
                    },
                    {
                        "name": "Draw",
                        "price": 3.40
                    },
                    {
                        "name": "Away",
                        "price": 3.60
                    }
                ]
            },
            {
                "match_id": "12345",
                "bookmaker": {
                    "id": 9,
                    "name": "William Hill"
                },
                "market_type": "h2h",
                "outcomes": [
                    {
                        "name": "1",
                        "price": 2.15
                    },
                    {
                        "name": "X",
                        "price": 3.30
                    },
                    {
                        "name": "2",
                        "price": 3.50
                    }
                ]
            }
        ]

    def test_cleaner_initialization(self):
        """测试清洗器初始化"""
        with patch('src.data.processing.football_data_cleaner.DatabaseManager') as mock_db:
            mock_db.return_value = Mock()
            cleaner = FootballDataCleaner()

            # 验证初始化属性
            assert cleaner.db_manager is not None
            assert cleaner.logger is not None
            assert cleaner._team_id_cache == {}
            assert cleaner._league_id_cache == {}

    def test_cleaner_initialization_with_logger(self):
        """测试清洗器日志器初始化"""
        with patch('src.data.processing.football_data_cleaner.DatabaseManager') as mock_db, \
             patch('src.data.processing.football_data_cleaner.logging.getLogger') as mock_logger:

            mock_db.return_value = Mock()
            mock_logger.return_value = Mock()

            cleaner = FootballDataCleaner()

            # 验证日志器被正确调用
            mock_logger.assert_called_once()
            assert "cleaner.FootballDataCleaner" in mock_logger.call_args[0][0]

    @pytest.mark.asyncio
    async def test_clean_match_data_success(self, cleaner, sample_match_data):
        """测试成功清洗比赛数据"""
        # Mock team and league mapping methods
        cleaner._map_team_id = AsyncMock(side_effect=lambda team_data: team_data.get("id"))
        cleaner._map_league_id = AsyncMock(return_value=39)

        result = await cleaner.clean_match_data(sample_match_data)

        # 验证返回结构
        assert result is not None
        assert result["external_match_id"] == "12345"
        assert result["external_league_id"] == "PL"
        assert result["home_team_id"] == 64
        assert result["away_team_id"] == 61
        assert result["league_id"] == 39
        assert result["home_score"] == 2
        assert result["away_score"] == 1
        assert result["match_status"] == "finished"
        assert result["matchday"] == 22
        assert result["data_source"] == "cleaned"

    @pytest.mark.asyncio
    async def test_clean_match_data_invalid_input(self, cleaner):
        """测试清洗无效比赛数据"""
        # 测试空数据
        result = await cleaner.clean_match_data({})
        assert result is None

        # 测试None输入
        result = await cleaner.clean_match_data(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_clean_match_data_validation_failure(self, cleaner, sample_match_data):
        """测试比赛数据验证失败的情况"""
        # Mock validation method to return False
        cleaner._validate_match_data = Mock(return_value=False)

        result = await cleaner.clean_match_data(sample_match_data)
        assert result is None

    @pytest.mark.asyncio
    async def test_clean_match_data_exception_handling(self, cleaner, sample_match_data):
        """测试清洗比赛数据时的异常处理"""
        # Mock validation method to raise exception
        cleaner._validate_match_data = Mock(side_effect=Exception("Validation failed"))

        result = await cleaner.clean_match_data(sample_match_data)
        assert result is None

        # 验证错误被记录
        cleaner.logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_clean_odds_data_success(self, cleaner, sample_odds_data):
        """测试成功清洗赔率数据"""
        result = await cleaner.clean_odds_data(sample_odds_data)

        # 验证返回结构
        assert isinstance(result, list)
        assert len(result) >= 1  # 至少有一个bookmaker的数据

        # 验证基本结构存在
        first_odds = result[0]
        assert "bookmaker" in first_odds
        assert "market_type" in first_odds
        assert "outcomes" in first_odds
        assert len(first_odds["outcomes"]) >= 1

    @pytest.mark.asyncio
    async def test_clean_odds_data_empty_input(self, cleaner):
        """测试清洗空赔率数据"""
        result = await cleaner.clean_odds_data([])
        assert result == []

    @pytest.mark.asyncio
    async def test_clean_odds_data_invalid_items_filtered(self, cleaner):
        """测试无效赔率数据项被过滤"""
        invalid_odds = [
            {
                "bookmaker": {"id": 8, "name": "Bet365"},
                "market_type": "h2h",
                "outcomes": []  # 空结果
            },
            {
                "bookmaker": {"id": 9, "name": "William Hill"},
                "market_type": "h2h",
                "outcomes": [
                    {"name": "Home", "price": "invalid"}  # 无效价格
                ]
            }
        ]

        result = await cleaner.clean_odds_data(invalid_odds)
        assert result == []

    def test_validate_match_data_valid(self, cleaner, sample_match_data):
        """测试验证有效比赛数据"""
        result = cleaner._validate_match_data(sample_match_data)
        assert result is True

    def test_validate_match_data_missing_id(self, cleaner):
        """测试缺少ID的比赛数据验证"""
        invalid_data = {"competition": {"id": "PL"}}
        result = cleaner._validate_match_data(invalid_data)
        assert result is False

    def test_validate_match_data_missing_competition(self, cleaner):
        """测试缺少比赛信息的比赛数据验证"""
        invalid_data = {"id": "12345"}
        result = cleaner._validate_match_data(invalid_data)
        assert result is False

    def test_validate_match_data_missing_teams(self, cleaner):
        """测试缺少队伍信息的比赛数据验证"""
        invalid_data = {"id": "12345", "competition": {"id": "PL"}}
        result = cleaner._validate_match_data(invalid_data)
        assert result is False

    def test_validate_odds_data_valid(self, cleaner, sample_odds_data):
        """测试验证有效赔率数据"""
        valid_odds = sample_odds_data[0]
        result = cleaner._validate_odds_data(valid_odds)
        assert result is True

    def test_validate_odds_data_missing_bookmaker(self, cleaner):
        """测试缺少bookmaker信息的赔率数据验证"""
        invalid_odds = {"market_type": "h2h", "outcomes": []}
        result = cleaner._validate_odds_data(invalid_odds)
        assert result is False

    def test_validate_odds_data_missing_outcomes(self, cleaner):
        """测试缺少outcomes信息的赔率数据验证"""
        invalid_odds = {"bookmaker": {"id": 8, "name": "Bet365"}, "market": "h2h"}
        result = cleaner._validate_odds_data(invalid_odds)
        assert result is False

    def test_to_utc_time_valid_string(self, cleaner):
        """测试有效时间字符串转换"""
        time_str = "2025-01-15T15:00:00Z"
        result = cleaner._to_utc_time(time_str)
        # 验证返回有效的时间字符串（格式可能被标准化）
        assert result is not None
        assert "2025-01-15T15:00:00" in result

    def test_to_utc_time_none_input(self, cleaner):
        """测试None输入的时间转换"""
        result = cleaner._to_utc_time(None)
        assert result is None

    def test_to_utc_time_empty_string(self, cleaner):
        """测试空字符串的时间转换"""
        result = cleaner._to_utc_time("")
        assert result is None

    def test_to_utc_time_invalid_format(self, cleaner):
        """测试无效格式的时间转换"""
        invalid_time = "invalid-time-format"
        result = cleaner._to_utc_time(invalid_time)
        assert result is None

    @pytest.mark.asyncio
    async def test_map_team_id_success(self, cleaner):
        """测试成功映射队伍ID"""
        team_data = {"id": 64, "name": "Liverpool FC"}

        # Mock database query
        cleaner.db_manager.execute_query = AsyncMock(return_value=[{"team_id": 64}])

        result = await cleaner._map_team_id(team_data)
        # 验证返回的是整数类型的ID
        assert isinstance(result, int)
        assert result > 0

    @pytest.mark.asyncio
    async def test_map_team_id_cache_hit(self, cleaner):
        """测试队伍ID映射缓存命中"""
        team_data = {"id": 64, "name": "Liverpool FC"}

        # 预填充缓存
        cleaner._team_id_cache = {"Liverpool FC": 64}

        result = await cleaner._map_team_id(team_data)
        # 验证返回整数类型的ID
        assert isinstance(result, int)
        assert result > 0
        # 验证数据库查询未被调用
        cleaner.db_manager.execute_query.assert_not_called()

    @pytest.mark.asyncio
    async def test_map_team_id_not_found(self, cleaner):
        """测试队伍ID未找到的情况"""
        team_data = {"id": 999, "name": "Unknown Team"}

        # Mock database query returning empty result
        cleaner.db_manager.execute_query = AsyncMock(return_value=[])

        result = await cleaner._map_team_id(team_data)
        # 根据实际实现，队伍ID映射会返回哈希值而不是None
        assert isinstance(result, int)
        assert result > 0

    @pytest.mark.asyncio
    async def test_map_league_id_success(self, cleaner):
        """测试成功映射联赛ID"""
        league_data = {"id": "PL", "name": "Premier League"}

        # Mock database query
        cleaner.db_manager.execute_query = AsyncMock(return_value=[{"league_id": 39}])

        result = await cleaner._map_league_id(league_data)
        # 根据实际实现，联赛ID映射会返回哈希值而不是数据库查询结果
        assert isinstance(result, int)
        assert result > 0

    def test_standardize_match_status_finished(self, cleaner):
        """测试标准化比赛状态 - FINISHED"""
        result = cleaner._standardize_match_status("FINISHED")
        assert result == "finished"

    def test_standardize_match_status_scheduled(self, cleaner):
        """测试标准化比赛状态 - SCHEDULED"""
        result = cleaner._standardize_match_status("SCHEDULED")
        assert result == "scheduled"

    def test_standardize_match_status_in_play(self, cleaner):
        """测试标准化比赛状态 - IN_PLAY"""
        result = cleaner._standardize_match_status("IN_PLAY")
        assert result == "live"

    def test_standardize_match_status_unknown(self, cleaner):
        """测试标准化比赛状态 - 未知状态"""
        result = cleaner._standardize_match_status("UNKNOWN_STATUS")
        assert result == "unknown"

    def test_standardize_match_status_none(self, cleaner):
        """测试标准化比赛状态 - None输入"""
        result = cleaner._standardize_match_status(None)
        assert result == "unknown"

    def test_validate_score_valid_integer(self, cleaner):
        """测试验证有效比分"""
        result = cleaner._validate_score(2)
        assert result == 2

    def test_validate_score_valid_string(self, cleaner):
        """测试验证字符串格式的有效比分"""
        result = cleaner._validate_score("3")
        assert result == 3

    def test_validate_score_none(self, cleaner):
        """测试验证None比分"""
        result = cleaner._validate_score(None)
        assert result is None

    def test_validate_score_negative(self, cleaner):
        """测试验证负数比分"""
        result = cleaner._validate_score(-1)
        assert result is None

    def test_validate_score_too_large(self, cleaner):
        """测试验证过大比分"""
        result = cleaner._validate_score(100)
        assert result is None

    def test_validate_score_invalid_string(self, cleaner):
        """测试验证无效字符串比分"""
        result = cleaner._validate_score("invalid")
        assert result is None

    def test_extract_season_success(self, cleaner):
        """测试成功提取赛季信息"""
        season_data = {"id": 2024, "startDate": "2024-08-01", "endDate": "2025-05-31"}
        result = cleaner._extract_season(season_data)
        assert result == "2024"

    def test_extract_season_missing_id(self, cleaner):
        """测试缺少ID的赛季信息提取"""
        season_data = {"startDate": "2024-08-01"}
        result = cleaner._extract_season(season_data)
        assert result is None

    def test_clean_venue_name_valid(self, cleaner):
        """测试清洗有效场馆名称"""
        result = cleaner._clean_venue_name("Anfield")
        assert result == "Anfield"

    def test_clean_venue_name_none(self, cleaner):
        """测试清洗None场馆名称"""
        result = cleaner._clean_venue_name(None)
        assert result is None

    def test_clean_venue_name_empty(self, cleaner):
        """测试清洗空字符串场馆名称"""
        result = cleaner._clean_venue_name("")
        assert result is None

    def test_clean_referee_name_valid(self, cleaner):
        """测试清洗有效裁判名称"""
        referees = [{"id": 12345, "name": "Michael Oliver", "role": "REFEREE"}]
        result = cleaner._clean_referee_name(referees)
        assert result == "Michael Oliver"

    def test_clean_referee_name_empty_list(self, cleaner):
        """测试清洗空裁判列表"""
        result = cleaner._clean_referee_name([])
        assert result is None

    def test_clean_referee_name_no_referee(self, cleaner):
        """测试清洗没有裁判的列表"""
        referees = [{"id": 12345, "name": "Assistant", "role": "ASSISTANT_REF"}]
        result = cleaner._clean_referee_name(referees)
        assert result is None

    def test_validate_odds_value_valid(self, cleaner):
        """测试验证有效赔率值"""
        assert cleaner._validate_odds_value(2.5) is True
        assert cleaner._validate_odds_value("3.2") is True
        assert cleaner._validate_odds_value(1.01) is True

    def test_validate_odds_value_invalid(self, cleaner):
        """测试验证无效赔率值"""
        assert cleaner._validate_odds_value(0.5) is False
        assert cleaner._validate_odds_value(1.0) is False  # 等于最小值但不是大于
        assert cleaner._validate_odds_value("invalid") is False
        assert cleaner._validate_odds_value(None) is False
        assert cleaner._validate_odds_value(-1) is False

    def test_standardize_outcome_name_home(self, cleaner):
        """测试标准化结果名称 - Home"""
        result = cleaner._standardize_outcome_name("Home")
        assert result == "home"

    def test_standardize_outcome_name_draw(self, cleaner):
        """测试标准化结果名称 - Draw"""
        result = cleaner._standardize_outcome_name("Draw")
        assert result == "draw"

    def test_standardize_outcome_name_away(self, cleaner):
        """测试标准化结果名称 - Away"""
        result = cleaner._standardize_outcome_name("Away")
        assert result == "away"

    def test_standardize_outcome_name_numeric(self, cleaner):
        """测试标准化数字结果名称"""
        assert cleaner._standardize_outcome_name("1") == "home"
        assert cleaner._standardize_outcome_name("X") == "draw"
        assert cleaner._standardize_outcome_name("2") == "away"

    def test_standardize_outcome_name_unknown(self, cleaner):
        """测试标准化未知结果名称"""
        result = cleaner._standardize_outcome_name("Unknown")
        assert result == "unknown"

    def test_standardize_bookmaker_name_valid(self, cleaner):
        """测试标准化庄家名称"""
        result = cleaner._standardize_bookmaker_name("Bet365")
        assert result == "bet365"

    def test_standardize_bookmaker_name_none(self, cleaner):
        """测试标准化None庄家名称"""
        result = cleaner._standardize_bookmaker_name(None)
        assert result == "unknown"

    def test_standardize_market_type_h2h(self, cleaner):
        """测试标准化市场类型 - h2h"""
        result = cleaner._standardize_market_type("h2h")
        assert result == "1x2"

    def test_standardize_market_type_none(self, cleaner):
        """测试标准化None市场类型"""
        result = cleaner._standardize_market_type(None)
        assert result == "unknown"

    def test_validate_odds_consistency_valid(self, cleaner):
        """测试验证赔率一致性 - 有效"""
        outcomes = [
            {"name": "Home", "price": 2.0},
            {"name": "Draw", "price": 3.0},
            {"name": "Away", "price": 4.0}
        ]
        result = cleaner._validate_odds_consistency(outcomes)
        assert result is True

    def test_validate_odds_consistency_insufficient_outcomes(self, cleaner):
        """测试验证赔率一致性 - 结果不足"""
        outcomes = [{"name": "Home", "price": 2.0}]
        result = cleaner._validate_odds_consistency(outcomes)
        assert result is False

    def test_validate_odds_consistency_invalid_probabilities(self, cleaner):
        """测试验证赔率一致性 - 概率无效"""
        outcomes = [
            {"name": "Home", "price": 1.1},  # 概率太高
            {"name": "Draw", "price": 1.1},
            {"name": "Away", "price": 1.1}
        ]
        result = cleaner._validate_odds_consistency(outcomes)
        assert result is False

    def test_calculate_implied_probabilities(self, cleaner):
        """测试计算隐含概率"""
        outcomes = [
            {"name": "Home", "price": 2.0},
            {"name": "Draw", "price": 4.0},
            {"name": "Away", "price": 4.0}
        ]

        probabilities = cleaner._calculate_implied_probabilities(outcomes)

        # 验证概率和约等于100%
        total_prob = sum(probabilities.values())
        assert 0.95 <= total_prob <= 1.05  # 允许小的误差
        assert probabilities["Home"] == 0.5
        assert probabilities["Draw"] == 0.25
        assert probabilities["Away"] == 0.25