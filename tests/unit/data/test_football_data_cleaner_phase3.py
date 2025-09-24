"""
Phase 3：足球数据清洗器测试
目标：全面提升football_data_cleaner.py模块覆盖率到60%+
重点：测试数据清洗、验证、标准化逻辑，包括正常场景、异常场景和边界情况
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.data.processing.football_data_cleaner import FootballDataCleaner


class TestFootballDataCleanerBasic:
    """足球数据清洗器基础测试"""

    def setup_method(self):
        """设置测试环境"""
        self.cleaner = FootballDataCleaner()

    def test_cleaner_initialization(self):
        """测试清洗器初始化"""
        assert self.cleaner is not None
        assert hasattr(self.cleaner, "db_manager")
        assert hasattr(self.cleaner, "logger")
        assert isinstance(self.cleaner._team_id_cache, dict)
        assert isinstance(self.cleaner._league_id_cache, dict)

    @pytest.mark.asyncio
    async def test_clean_match_data_success(self):
        """测试成功清洗比赛数据"""
        raw_data = {
            "id": "12345",
            "homeTeam": {"id": "100", "name": "Team A"},
            "awayTeam": {"id": "200", "name": "Team B"},
            "utcDate": "2024-01-15T15:00:00Z",
            "status": "SCHEDULED",
            "competition": {"id": "PL", "name": "Premier League"},
            "score": {
                "fullTime": {"home": 2, "away": 1},
                "halfTime": {"home": 1, "away": 0},
            },
            "season": {"id": "2023-2024"},
            "matchday": 20,
            "venue": "  Test Stadium  ",
            "referees": [{"role": "REFEREE", "name": "  John Doe  "}],
        }

        result = await self.cleaner.clean_match_data(raw_data)

        assert result is not None
        assert result["external_match_id"] == "12345"
        assert result["home_team_id"] is not None
        assert result["away_team_id"] is not None
        assert result["league_id"] is not None
        assert result["match_status"] == "scheduled"
        assert result["home_score"] == 2
        assert result["away_score"] == 1
        assert result["home_ht_score"] == 1
        assert result["away_ht_score"] == 0
        assert result["season"] == "2023-2024"
        assert result["matchday"] == 20
        assert result["venue"] == "Test Stadium"
        assert result["referee"] == "John Doe"
        assert result["data_source"] == "cleaned"

    @pytest.mark.asyncio
    async def test_clean_match_data_invalid_input(self):
        """测试无效输入数据处理"""
        result = await self.cleaner.clean_match_data({})
        assert result is None

    @pytest.mark.asyncio
    async def test_clean_match_data_missing_required_fields(self):
        """测试缺少必需字段"""
        # 缺少必需字段
        invalid_data = {"id": "123", "homeTeam": {"id": "100"}}
        result = await self.cleaner.clean_match_data(invalid_data)
        assert result is None

    @pytest.mark.asyncio
    async def test_clean_odds_data_success(self):
        """测试成功清洗赔率数据"""
        raw_odds = [
            {
                "match_id": "12345",
                "bookmaker": "Bet365",
                "market_type": "h2h",
                "outcomes": [
                    {"name": "1", "price": 2.50},
                    {"name": "X", "price": 3.20},
                    {"name": "2", "price": 2.80},
                ],
                "last_update": "2024-01-15T14:00:00Z",
            }
        ]

        result = await self.cleaner.clean_odds_data(raw_odds)

        assert len(result) == 1
        cleaned_odds = result[0]
        assert cleaned_odds["external_match_id"] == "12345"
        assert cleaned_odds["bookmaker"] == "bet365"
        assert cleaned_odds["market_type"] == "1x2"
        assert len(cleaned_odds["outcomes"]) == 3
        assert cleaned_odds["outcomes"][0]["name"] == "home"
        assert cleaned_odds["outcomes"][0]["price"] == 2.5
        assert "implied_probabilities" in cleaned_odds

    @pytest.mark.asyncio
    async def test_clean_odds_data_empty_list(self):
        """测试空赔率数据列表"""
        result = await self.cleaner.clean_odds_data([])
        assert result == []

    @pytest.mark.asyncio
    async def test_clean_odds_data_invalid_odds(self):
        """测试无效赔率数据"""
        raw_odds = [
            {
                "match_id": "12345",
                "bookmaker": "Bet365",
                "market_type": "h2h",
                "outcomes": [{"name": "1", "price": 0.5}],  # 无效赔率值
                "last_update": "2024-01-15T14:00:00Z",
            }
        ]

        result = await self.cleaner.clean_odds_data(raw_odds)
        assert result == []


class TestFootballDataCleanerTimeHandling:
    """时间处理测试"""

    def setup_method(self):
        """设置测试环境"""
        self.cleaner = FootballDataCleaner()

    def test_to_utc_time_iso_z(self):
        """测试ISO格式Z时间转换"""
        time_str = "2024-01-15T15:00:00Z"
        result = self.cleaner._to_utc_time(time_str)
        assert result is not None
        assert "+00:00" in result

    def test_to_utc_time_iso_with_offset(self):
        """测试带时区偏移的时间转换"""
        time_str = "2024-01-15T15:00:00+02:00"
        result = self.cleaner._to_utc_time(time_str)
        assert result is not None

    def test_to_utc_time_utc_suffix(self):
        """测试UTC后缀时间转换"""
        time_str = "2024-01-15T15:00:00UTC"
        result = self.cleaner._to_utc_time(time_str)
        assert result is not None

    def test_to_utc_time_invalid_format(self):
        """测试无效时间格式"""
        result = self.cleaner._to_utc_time("invalid-time")
        assert result is None

    def test_to_utc_time_none_input(self):
        """测试空输入"""
        result = self.cleaner._to_utc_time(None)
        assert result is None

    def test_to_utc_time_empty_string(self):
        """测试空字符串输入"""
        result = self.cleaner._to_utc_time("")
        assert result is None


class TestFootballDataCleanerScoreValidation:
    """比分验证测试"""

    def setup_method(self):
        """设置测试环境"""
        self.cleaner = FootballDataCleaner()

    def test_validate_score_valid(self):
        """测试有效比分"""
        assert self.cleaner._validate_score(2) == 2
        assert self.cleaner._validate_score(0) == 0
        assert self.cleaner._validate_score(99) == 99

    def test_validate_score_string(self):
        """测试字符串比分"""
        assert self.cleaner._validate_score("3") == 3
        assert self.cleaner._validate_score("0") == 0

    def test_validate_score_out_of_range(self):
        """测试超出范围的比分"""
        assert self.cleaner._validate_score(-1) is None
        assert self.cleaner._validate_score(100) is None

    def test_validate_score_none(self):
        """测试None比分"""
        assert self.cleaner._validate_score(None) is None

    def test_validate_score_invalid_string(self):
        """测试无效字符串比分"""
        assert self.cleaner._validate_score("invalid") is None


class TestFootballDataCleanerStatusMapping:
    """比赛状态映射测试"""

    def setup_method(self):
        """设置测试环境"""
        self.cleaner = FootballDataCleaner()

    def test_standardize_match_status_scheduled(self):
        """测试安排状态"""
        assert self.cleaner._standardize_match_status("SCHEDULED") == "scheduled"
        assert self.cleaner._standardize_match_status("TIMED") == "scheduled"

    def test_standardize_match_status_live(self):
        """测试进行中状态"""
        assert self.cleaner._standardize_match_status("IN_PLAY") == "live"
        assert self.cleaner._standardize_match_status("PAUSED") == "live"

    def test_standardize_match_status_finished(self):
        """测试完成状态"""
        assert self.cleaner._standardize_match_status("FINISHED") == "finished"
        assert self.cleaner._standardize_match_status("AWARDED") == "finished"

    def test_standardize_match_status_other(self):
        """测试其他状态"""
        assert self.cleaner._standardize_match_status("POSTPONED") == "postponed"
        assert self.cleaner._standardize_match_status("CANCELLED") == "cancelled"
        assert self.cleaner._standardize_match_status("SUSPENDED") == "suspended"

    def test_standardize_match_status_unknown(self):
        """测试未知状态"""
        assert self.cleaner._standardize_match_status("UNKNOWN") == "unknown"
        assert self.cleaner._standardize_match_status("") == "unknown"
        assert self.cleaner._standardize_match_status(None) == "unknown"


class TestFootballDataCleanerOddsHandling:
    """赔率处理测试"""

    def setup_method(self):
        """设置测试环境"""
        self.cleaner = FootballDataCleaner()

    def test_validate_odds_value_valid(self):
        """测试有效赔率值"""
        assert self.cleaner._validate_odds_value(1.5) is True
        assert self.cleaner._validate_odds_value(2.0) is True
        assert self.cleaner._validate_odds_value(1.01) is True

    def test_validate_odds_value_invalid(self):
        """测试无效赔率值"""
        assert self.cleaner._validate_odds_value(1.00) is False
        assert self.cleaner._validate_odds_value(0.5) is False
        assert self.cleaner._validate_odds_value("invalid") is False

    def test_standardize_outcome_name(self):
        """测试结果名称标准化"""
        assert self.cleaner._standardize_outcome_name("1") == "home"
        assert self.cleaner._standardize_outcome_name("X") == "draw"
        assert self.cleaner._standardize_outcome_name("2") == "away"
        assert self.cleaner._standardize_outcome_name("HOME") == "home"
        assert self.cleaner._standardize_outcome_name("Over") == "over"
        assert self.cleaner._standardize_outcome_name(None) == "unknown"

    def test_standardize_bookmaker_name(self):
        """测试博彩公司名称标准化"""
        assert self.cleaner._standardize_bookmaker_name("Bet 365") == "bet_365"
        assert (
            self.cleaner._standardize_bookmaker_name("William Hill") == "william_hill"
        )
        assert self.cleaner._standardize_bookmaker_name(None) == "unknown"

    def test_standardize_market_type(self):
        """测试市场类型标准化"""
        assert self.cleaner._standardize_market_type("h2h") == "1x2"
        assert self.cleaner._standardize_market_type("spreads") == "asian_handicap"
        assert self.cleaner._standardize_market_type("totals") == "over_under"
        assert self.cleaner._standardize_market_type("btts") == "both_teams_score"
        assert self.cleaner._standardize_market_type(None) == "unknown"

    def test_validate_odds_consistency_valid(self):
        """测试有效赔率一致性"""
        outcomes = [
            {"name": "home", "price": 2.0},
            {"name": "draw", "price": 3.0},
            {"name": "away", "price": 4.0},
        ]
        assert self.cleaner._validate_odds_consistency(outcomes) is True

    def test_validate_odds_consistency_invalid(self):
        """测试无效赔率一致性"""
        # 概率总和过小
        outcomes = [
            {"name": "home", "price": 1.1},
            {"name": "draw", "price": 1.1},
            {"name": "away", "price": 1.1},
        ]
        assert self.cleaner._validate_odds_consistency(outcomes) is False

    def test_validate_odds_consistency_empty(self):
        """测试空赔率列表"""
        assert self.cleaner._validate_odds_consistency([]) is False

    def test_calculate_implied_probabilities(self):
        """测试隐含概率计算"""
        outcomes = [
            {"name": "home", "price": 2.0},
            {"name": "draw", "price": 4.0},
            {"name": "away", "price": 4.0},
        ]

        result = self.cleaner._calculate_implied_probabilities(outcomes)

        assert "home" in result
        assert "draw" in result
        assert "away" in result
        # 概率总和应该接近1.0
        total_prob = sum(result.values())
        assert abs(total_prob - 1.0) < 0.01

    def test_calculate_implied_probabilities_empty(self):
        """测试空结果列表的概率计算"""
        result = self.cleaner._calculate_implied_probabilities([])
        assert result == {}


class TestFootballDataCleanerDataValidation:
    """数据验证测试"""

    def setup_method(self):
        """设置测试环境"""
        self.cleaner = FootballDataCleaner()

    def test_validate_match_data_valid(self):
        """测试有效比赛数据验证"""
        valid_data = {
            "id": "12345",
            "homeTeam": {"id": "100", "name": "Team A"},
            "awayTeam": {"id": "200", "name": "Team B"},
            "utcDate": "2024-01-15T15:00:00Z",
        }
        assert self.cleaner._validate_match_data(valid_data) is True

    def test_validate_match_data_missing_fields(self):
        """测试缺少字段的比赛数据"""
        invalid_data = {"id": "12345", "homeTeam": {"id": "100"}}
        assert self.cleaner._validate_match_data(invalid_data) is False

    def test_validate_odds_data_valid(self):
        """测试有效赔率数据验证"""
        valid_odds = {
            "match_id": "12345",
            "bookmaker": "Bet365",
            "market_type": "h2h",
            "outcomes": [{"name": "1", "price": 2.0}],
        }
        assert self.cleaner._validate_odds_data(valid_odds) is True

    def test_validate_odds_data_missing_fields(self):
        """测试缺少字段的赔率数据"""
        invalid_odds = {"match_id": "12345", "bookmaker": "Bet365"}
        assert self.cleaner._validate_odds_data(invalid_odds) is False


class TestFootballDataCleanerEdgeCases:
    """边界情况测试"""

    def setup_method(self):
        """设置测试环境"""
        self.cleaner = FootballDataCleaner()

    def test_clean_venue_name(self):
        """测试场地名称清洗"""
        assert self.cleaner._clean_venue_name("  Test  Stadium  ") == "Test Stadium"
        assert self.cleaner._clean_venue_name(None) is None
        assert self.cleaner._clean_venue_name("") is None

    def test_clean_referee_name(self):
        """测试裁判姓名清洗"""
        referees = [{"role": "REFEREE", "name": "  John  Doe  "}]
        assert self.cleaner._clean_referee_name(referees) == "John Doe"

    def test_clean_referee_name_no_referee(self):
        """测试没有裁判的情况"""
        referees = [{"role": "ASSISTANT", "name": "John Doe"}]
        assert self.cleaner._clean_referee_name(referees) is None

    def test_clean_referee_name_none_input(self):
        """测试None输入"""
        assert self.cleaner._clean_referee_name(None) is None

    def test_extract_season_from_id(self):
        """测试从ID提取赛季"""
        season_data = {"id": "2023-2024"}
        assert self.cleaner._extract_season(season_data) == "2023-2024"

    def test_extract_season_from_dates(self):
        """测试从日期提取赛季"""
        season_data = {
            "startDate": "2023-08-01T00:00:00Z",
            "endDate": "2024-05-31T23:59:59Z",
        }
        result = self.cleaner._extract_season(season_data)
        assert result == "2023-2024"

    def test_extract_season_none_input(self):
        """测试None输入"""
        assert self.cleaner._extract_season(None) is None


class TestFootballDataCleanerErrorHandling:
    """错误处理测试"""

    def setup_method(self):
        """设置测试环境"""
        self.cleaner = FootballDataCleaner()

    @pytest.mark.asyncio
    async def test_clean_match_data_invalid_date_handling(self):
        """测试无效日期处理"""
        # 构造包含无效日期的数据
        invalid_data = {
            "id": "12345",
            "homeTeam": {"id": "100", "name": "Team A"},
            "awayTeam": {"id": "200", "name": "Team B"},
            "utcDate": "invalid-date-format",
        }

        result = await self.cleaner.clean_match_data(invalid_data)
        # 应该返回数据但日期字段为None
        assert result is not None
        assert result["match_time"] is None
        assert result["external_match_id"] == "12345"

    @pytest.mark.asyncio
    async def test_clean_odds_data_exception_handling(self):
        """测试赔率数据清洗异常处理"""
        raw_odds = [
            {
                "match_id": "12345",
                "bookmaker": "Bet365",
                "market_type": "h2h",
                "outcomes": [{"name": "1", "price": "invalid-price"}],
                "last_update": "2024-01-15T14:00:00Z",
            }
        ]

        result = await self.cleaner.clean_odds_data(raw_odds)
        assert result == []

    @pytest.mark.asyncio
    async def test_team_id_mapping_none_data(self):
        """测试球队ID映射空数据处理"""
        # 构造空数据
        result = await self.cleaner._map_team_id(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_team_id_mapping_empty_data(self):
        """测试球队ID映射空字典处理"""
        # 构造空字典数据
        team_data = {"id": None, "name": None}
        result = await self.cleaner._map_team_id(team_data)
        # 应该返回哈希值而不是None
        assert result is not None
        assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_league_id_mapping_none_data(self):
        """测试联赛ID映射空数据处理"""
        # 构造空数据
        result = await self.cleaner._map_league_id(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_league_id_mapping_empty_data(self):
        """测试联赛ID映射空字典处理"""
        # 构造空字典数据
        league_data = {"id": None, "name": None}
        result = await self.cleaner._map_league_id(league_data)
        # 应该返回哈希值而不是None
        assert result is not None
        assert isinstance(result, int)

    def test_calculate_implied_probabilities_exception_handling(self):
        """测试概率计算异常处理"""
        # 构造会导致异常的数据
        outcomes = [{"name": "home", "price": 0}]  # 会导致除零错误
        result = self.cleaner._calculate_implied_probabilities(outcomes)
        assert result == {}


class TestFootballDataCleanerIntegration:
    """集成测试"""

    def setup_method(self):
        """设置测试环境"""
        self.cleaner = FootballDataCleaner()

    @pytest.mark.asyncio
    async def test_team_id_mapping_cache(self):
        """测试球队ID映射缓存"""
        team_data = {"id": "100", "name": "Team A"}

        # 第一次调用
        result1 = await self.cleaner._map_team_id(team_data)
        # 第二次调用应该从缓存获取
        result2 = await self.cleaner._map_team_id(team_data)

        assert result1 == result2
        assert f"100:Team A" in self.cleaner._team_id_cache

    @pytest.mark.asyncio
    async def test_league_id_mapping_cache(self):
        """测试联赛ID映射缓存"""
        league_data = {"id": "PL", "name": "Premier League"}

        # 第一次调用
        result1 = await self.cleaner._map_league_id(league_data)
        # 第二次调用应该从缓存获取
        result2 = await self.cleaner._map_league_id(league_data)

        assert result1 == result2
        assert f"PL:Premier League" in self.cleaner._league_id_cache

    @pytest.mark.asyncio
    async def test_complex_match_data_cleaning(self):
        """测试复杂比赛数据清洗"""
        complex_data = {
            "id": "67890",
            "homeTeam": {"id": "500", "name": "Manchester United"},
            "awayTeam": {"id": "600", "name": "Liverpool FC"},
            "utcDate": "2024-01-15T16:30:00+01:00",
            "status": "FINISHED",
            "competition": {"id": "PL", "name": "Premier League"},
            "score": {
                "fullTime": {"home": 2, "away": 2},
                "halfTime": {"home": 1, "away": 1},
            },
            "season": {
                "startDate": "2023-08-01T00:00:00Z",
                "endDate": "2024-05-31T23:59:59Z",
            },
            "matchday": 21,
            "venue": "  Old Trafford  ",
            "referees": [
                {"role": "ASSISTANT", "name": "Assistant 1"},
                {"role": "REFEREE", "name": "  Michael  Oliver  "},
            ],
        }

        result = await self.cleaner.clean_match_data(complex_data)

        assert result is not None
        assert result["external_match_id"] == "67890"
        assert result["match_status"] == "finished"
        assert result["home_score"] == 2
        assert result["away_score"] == 2
        assert result["home_ht_score"] == 1
        assert result["away_ht_score"] == 1
        assert result["season"] == "2023-2024"
        assert result["venue"] == "Old Trafford"
        assert result["referee"] == "Michael Oliver"

    @pytest.mark.asyncio
    async def test_complex_odds_data_cleaning(self):
        """测试复杂赔率数据清洗"""
        complex_odds = [
            {
                "match_id": "67890",
                "bookmaker": "William Hill",
                "market_type": "totals",
                "outcomes": [
                    {"name": "Over", "price": 1.85},
                    {"name": "Under", "price": 1.95},
                ],
                "last_update": "2024-01-15T15:30:00Z",
            },
            {
                "match_id": "67890",
                "bookmaker": "Bet365",
                "market_type": "h2h",
                "outcomes": [
                    {"name": "1", "price": 2.4},
                    {"name": "X", "price": 3.2},
                    {"name": "2", "price": 2.8},
                ],
                "last_update": "2024-01-15T15:35:00Z",
            },
        ]

        result = await self.cleaner.clean_odds_data(complex_odds)

        assert len(result) == 2

        # 检查第一个赔率
        odds1 = result[0]
        assert odds1["external_match_id"] == "67890"
        assert odds1["bookmaker"] == "william_hill"
        assert odds1["market_type"] == "over_under"
        assert len(odds1["outcomes"]) == 2
        assert odds1["outcomes"][0]["name"] == "over"
        assert odds1["outcomes"][0]["price"] == 1.85

        # 检查第二个赔率
        odds2 = result[1]
        assert odds2["bookmaker"] == "bet365"
        assert odds2["market_type"] == "1x2"
        assert len(odds2["outcomes"]) == 3
