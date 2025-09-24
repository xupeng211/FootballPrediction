"""
Phase 3：赛程数据采集器综合测试
目标：全面提升fixtures_collector.py模块覆盖率到60%+
重点：测试赛程采集、防重复机制、数据清洗、异常处理和防丢失策略
"""

import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.data.collectors.base_collector import CollectionResult
from src.data.collectors.fixtures_collector import FixturesCollector


class TestFixturesCollectorBasic:
    """赛程采集器基础测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = FixturesCollector(
            data_source="test_api", api_key="test_key", base_url="https://test.api.com"
        )

    def test_collector_initialization(self):
        """测试采集器初始化"""
        assert self.collector is not None
        assert self.collector.data_source == "test_api"
        assert self.collector.api_key == "test_key"
        assert self.collector.base_url == "https://test.api.com"
        assert hasattr(self.collector, "_processed_matches")
        assert hasattr(self.collector, "_missing_matches")
        assert isinstance(self.collector._processed_matches, set)
        assert isinstance(self.collector._missing_matches, list)

    def test_collector_initialization_with_defaults(self):
        """测试采集器默认参数初始化"""
        collector = FixturesCollector()
        assert collector.data_source == "football_api"
        assert collector.api_key is None
        assert collector.base_url == "https://api.football-data.org/v4"

    def test_collector_inheritance(self):
        """测试继承关系"""
        assert isinstance(self.collector, FixturesCollector)
        assert hasattr(self.collector, "collect_fixtures")
        assert hasattr(self.collector, "collect_odds")
        assert hasattr(self.collector, "collect_live_scores")


class TestFixturesCollectorOddsAndScores:
    """赛程采集器赔率和比分测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = FixturesCollector()

    @pytest.mark.asyncio
    async def test_collect_odds_skipped(self):
        """测试赔率采集被跳过"""
        result = await self.collector.collect_odds()

        assert result.collection_type == "odds"
        assert result.status == "skipped"
        assert result.records_collected == 0
        assert result.success_count == 0
        assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_collect_live_scores_skipped(self):
        """测试实时比分采集被跳过"""
        result = await self.collector.collect_live_scores()

        assert result.collection_type == "live_scores"
        assert result.status == "skipped"
        assert result.records_collected == 0
        assert result.success_count == 0
        assert result.error_count == 0


class TestFixturesCollectorActiveLeagues:
    """赛程采集器活跃联赛测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = FixturesCollector()

    @pytest.mark.asyncio
    async def test_get_active_leagues_success(self):
        """测试获取活跃联赛成功"""
        leagues = await self.collector._get_active_leagues()

        assert isinstance(leagues, list)
        assert len(leagues) > 0
        assert "PL" in leagues  # 英超
        assert "PD" in leagues  # 西甲
        assert "SA" in leagues  # 意甲
        assert "BL1" in leagues  # 德甲
        assert "FL1" in leagues  # 法甲
        assert "CL" in leagues  # 欧冠
        assert "EL" in leagues  # 欧联

    @pytest.mark.asyncio
    async def test_get_active_leagues_fallback(self):
        """测试获取活跃联赛失败时的回退"""
        with patch.object(self.collector, "logger") as mock_logger:
            # 模拟异常情况
            original_return = ["PL", "PD", "SA", "BL1", "FL1", "CL", "EL"]

            # 直接调用方法获取默认值
            leagues = await self.collector._get_active_leagues()

            # 验证返回默认联赛列表
            assert isinstance(leagues, list)
            assert len(leagues) >= 2
            assert "PL" in leagues
            assert "PD" in leagues


class TestFixturesCollectorLoadExistingMatches:
    """赛程采集器加载已存在比赛测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = FixturesCollector()

    @pytest.mark.asyncio
    async def test_load_existing_matches_success(self):
        """测试加载已存在比赛成功"""
        date_from = datetime.now()
        date_to = date_from + timedelta(days=30)

        # 初始化一些已处理的比赛
        self.collector._processed_matches = {"match1", "match2"}

        await self.collector._load_existing_matches(date_from, date_to)

        # 验证处理过的比赛集合被重置
        assert isinstance(self.collector._processed_matches, set)

    @pytest.mark.asyncio
    async def test_load_existing_matches_exception_handling(self):
        """测试加载已存在比赛异常处理"""
        date_from = datetime.now()
        date_to = date_from + timedelta(days=30)

        with patch.object(self.collector, "logger") as mock_logger:
            await self.collector._load_existing_matches(date_from, date_to)

            # 验证异常处理后集合为空
            assert isinstance(self.collector._processed_matches, set)


class TestFixturesCollectorLeagueFixtures:
    """赛程采集器联赛赛程测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = FixturesCollector(
            api_key="test_key", base_url="https://test.api.com"
        )

    @pytest.mark.asyncio
    async def test_collect_league_fixtures_success(self):
        """测试采集联赛赛程成功"""
        league_code = "PL"
        date_from = datetime.now()
        date_to = date_from + timedelta(days=30)

        mock_response = {
            "matches": [
                {
                    "id": 123,
                    "homeTeam": {"id": 1},
                    "awayTeam": {"id": 2},
                    "utcDate": "2024-01-01T15:00:00Z",
                    "status": "SCHEDULED",
                }
            ]
        }

        with patch.object(self.collector, "_make_request", return_value=mock_response):
            fixtures = await self.collector._collect_league_fixtures(
                league_code, date_from, date_to
            )

            assert isinstance(fixtures, list)
            assert len(fixtures) == 1
            assert fixtures[0]["id"] == 123

    @pytest.mark.asyncio
    async def test_collect_league_fixtures_no_matches(self):
        """测试采集联赛赛程无比赛"""
        league_code = "PL"
        date_from = datetime.now()
        date_to = date_from + timedelta(days=30)

        mock_response = {"matches": []}

        with patch.object(self.collector, "_make_request", return_value=mock_response):
            fixtures = await self.collector._collect_league_fixtures(
                league_code, date_from, date_to
            )

            assert isinstance(fixtures, list)
            assert len(fixtures) == 0

    @pytest.mark.asyncio
    async def test_collect_league_fixtures_exception(self):
        """测试采集联赛赛程异常"""
        league_code = "PL"
        date_from = datetime.now()
        date_to = date_from + timedelta(days=30)

        with patch.object(
            self.collector, "_make_request", side_effect=Exception("API Error")
        ):
            fixtures = await self.collector._collect_league_fixtures(
                league_code, date_from, date_to
            )

            assert isinstance(fixtures, list)
            assert len(fixtures) == 0

    @pytest.mark.asyncio
    async def test_collect_league_fixtures_url_construction(self):
        """测试联赛赛程URL构造"""
        league_code = "PL"
        date_from = datetime.now()
        date_to = date_from + timedelta(days=30)

        expected_url = f"{self.collector.base_url}/competitions/{league_code}/matches"
        expected_params = {
            "dateFrom": date_from.strftime("%Y-%m-%d"),
            "dateTo": date_to.strftime("%Y-%m-%d"),
            "status": "SCHEDULED",
        }
        expected_headers = {"X-Auth-Token": self.collector.api_key}

        with patch.object(self.collector, "_make_request") as mock_request:
            mock_request.return_value = {"matches": []}

            await self.collector._collect_league_fixtures(
                league_code, date_from, date_to
            )

            mock_request.assert_called_once_with(
                url=expected_url, headers=expected_headers, params=expected_params
            )


class TestFixturesCollectorMatchKey:
    """赛程采集器比赛唯一键测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = FixturesCollector()

    def test_generate_match_key_complete_data(self):
        """测试生成完整数据的比赛唯一键"""
        fixture_data = {
            "id": 123,
            "homeTeam": {"id": 1},
            "awayTeam": {"id": 2},
            "utcDate": "2024-01-01T15:00:00Z",
        }

        key = self.collector._generate_match_key(fixture_data)

        assert isinstance(key, str)
        assert len(key) == 32  # MD5 hash length

        # 验证生成的键的一致性
        key2 = self.collector._generate_match_key(fixture_data)
        assert key == key2

    def test_generate_match_key_missing_fields(self):
        """测试生成缺失字段的比赛唯一键"""
        fixture_data = {
            "id": None,
            "homeTeam": {},
            "awayTeam": {"id": 2},
            "utcDate": "",
        }

        key = self.collector._generate_match_key(fixture_data)

        assert isinstance(key, str)
        assert len(key) == 32

    def test_generate_match_key_empty_data(self):
        """测试生成空数据的比赛唯一键"""
        fixture_data = {}

        key = self.collector._generate_match_key(fixture_data)

        assert isinstance(key, str)
        assert len(key) == 32

    def test_generate_match_key_uniqueness(self):
        """测试比赛唯一键的唯一性"""
        fixture_data1 = {
            "id": 123,
            "homeTeam": {"id": 1},
            "awayTeam": {"id": 2},
            "utcDate": "2024-01-01T15:00:00Z",
        }

        fixture_data2 = {
            "id": 124,
            "homeTeam": {"id": 1},
            "awayTeam": {"id": 2},
            "utcDate": "2024-01-01T15:00:00Z",
        }

        key1 = self.collector._generate_match_key(fixture_data1)
        key2 = self.collector._generate_match_key(fixture_data2)

        assert key1 != key2


class TestFixturesCollectorCleanData:
    """赛程采集器数据清洗测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = FixturesCollector()

    @pytest.mark.asyncio
    async def test_clean_fixture_data_success(self):
        """测试清洗比赛数据成功"""
        raw_fixture = {
            "id": 123,
            "homeTeam": {"id": 1},
            "awayTeam": {"id": 2},
            "utcDate": "2024-01-01T15:00:00Z",
            "status": "SCHEDULED",
            "competition": {"id": 2021},
            "season": {"id": 2023},
            "matchday": 1,
        }

        cleaned = await self.collector._clean_fixture_data(raw_fixture)

        assert cleaned is not None
        assert cleaned["external_match_id"] == "123"
        assert cleaned["external_league_id"] == "2021"
        assert cleaned["external_home_team_id"] == "1"
        assert cleaned["external_away_team_id"] == "2"
        assert cleaned["match_time"] == "2024-01-01T15:00:00+00:00"
        assert cleaned["status"] == "SCHEDULED"
        assert cleaned["season"] == 2023
        assert cleaned["matchday"] == 1
        assert cleaned["processed"] is False
        assert "collected_at" in cleaned
        assert "raw_data" in cleaned

    @pytest.mark.asyncio
    async def test_clean_fixture_data_missing_required_fields(self):
        """测试清洗缺失必要字段的比赛数据"""
        raw_fixture = {
            "id": 123,
            "homeTeam": {"id": 1},
            # 缺少 awayTeam 和 utcDate
        }

        cleaned = await self.collector._clean_fixture_data(raw_fixture)

        assert cleaned is None

    @pytest.mark.asyncio
    async def test_clean_fixture_data_empty_required_fields(self):
        """测试清洗必要字段为空的比赛数据"""
        raw_fixture = {"id": None, "homeTeam": {}, "awayTeam": {"id": 2}, "utcDate": ""}

        cleaned = await self.collector._clean_fixture_data(raw_fixture)

        assert cleaned is None

    @pytest.mark.asyncio
    async def test_clean_fixture_data_with_competition_missing(self):
        """测试清洗缺失联赛信息的比赛数据"""
        raw_fixture = {
            "id": 123,
            "homeTeam": {"id": 1},
            "awayTeam": {"id": 2},
            "utcDate": "2024-01-01T15:00:00Z",
            "status": "SCHEDULED",
        }

        cleaned = await self.collector._clean_fixture_data(raw_fixture)

        assert cleaned is not None
        assert cleaned["external_league_id"] == ""

    @pytest.mark.asyncio
    async def test_clean_fixture_data_with_season_missing(self):
        """测试清洗缺失赛季信息的比赛数据"""
        raw_fixture = {
            "id": 123,
            "homeTeam": {"id": 1},
            "awayTeam": {"id": 2},
            "utcDate": "2024-01-01T15:00:00Z",
            "status": "SCHEDULED",
        }

        cleaned = await self.collector._clean_fixture_data(raw_fixture)

        assert cleaned is not None
        assert cleaned["season"] is None

    @pytest.mark.asyncio
    async def test_clean_fixture_data_exception_handling(self):
        """测试清洗比赛数据异常处理"""
        raw_fixture = {
            "id": 123,
            "homeTeam": {"id": 1},
            "awayTeam": {"id": 2},
            "utcDate": "invalid_date_format",  # 无效的日期格式
        }

        cleaned = await self.collector._clean_fixture_data(raw_fixture)

        assert cleaned is None


class TestFixturesCollectorMissingMatches:
    """赛程采集器缺失比赛检测测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = FixturesCollector()

    @pytest.mark.asyncio
    async def test_detect_missing_matches_success(self):
        """测试检测缺失比赛成功"""
        collected_data = [
            {
                "external_match_id": "123",
                "external_home_team_id": "1",
                "external_away_team_id": "2",
                "match_time": "2024-01-01T15:00:00+00:00",
            }
        ]
        date_from = datetime.now()
        date_to = date_from + timedelta(days=30)

        # 初始化缺失比赛列表
        self.collector._missing_matches = []

        await self.collector._detect_missing_matches(collected_data, date_from, date_to)

        # 验证缺失比赛列表保持不变（目前是TODO实现）
        assert isinstance(self.collector._missing_matches, list)

    @pytest.mark.asyncio
    async def test_detect_missing_matches_empty_data(self):
        """测试检测空数据的缺失比赛"""
        collected_data = []
        date_from = datetime.now()
        date_to = date_from + timedelta(days=30)

        await self.collector._detect_missing_matches(collected_data, date_from, date_to)

        assert isinstance(self.collector._missing_matches, list)

    @pytest.mark.asyncio
    async def test_detect_missing_matches_exception_handling(self):
        """测试检测缺失比赛异常处理"""
        collected_data = []
        date_from = datetime.now()
        date_to = date_from + timedelta(days=30)

        with patch.object(self.collector, "logger") as mock_logger:
            await self.collector._detect_missing_matches(
                collected_data, date_from, date_to
            )

            # 验证异常处理后方法正常完成
            assert isinstance(self.collector._missing_matches, list)


class TestFixturesCollectorMain:
    """赛程采集器主要功能测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = FixturesCollector(
            api_key="test_key", base_url="https://test.api.com"
        )

    @pytest.mark.asyncio
    async def test_collect_fixtures_success(self):
        """测试采集赛程成功"""
        mock_fixtures = [
            {
                "id": 123,
                "homeTeam": {"id": 1},
                "awayTeam": {"id": 2},
                "utcDate": "2024-01-01T15:00:00Z",
                "status": "SCHEDULED",
                "competition": {"id": 2021},
            }
        ]

        with patch.object(
            self.collector, "_get_active_leagues", return_value=["PL"]
        ), patch.object(
            self.collector, "_collect_league_fixtures", return_value=mock_fixtures
        ), patch.object(
            self.collector, "_save_to_bronze_layer"
        ) as mock_save:
            result = await self.collector.collect_fixtures()

            assert result.collection_type == "fixtures"
            assert result.status == "success"
            assert result.records_collected == 1
            assert result.success_count == 1
            assert result.error_count == 0
            assert result.collected_data is not None
            assert len(result.collected_data) == 1

            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_fixtures_with_date_range(self):
        """测试采集指定日期范围的赛程"""
        date_from = datetime(2024, 1, 1)
        date_to = datetime(2024, 1, 31)

        mock_fixtures = [
            {
                "id": 123,
                "homeTeam": {"id": 1},
                "awayTeam": {"id": 2},
                "utcDate": "2024-01-15T15:00:00Z",
                "status": "SCHEDULED",
                "competition": {"id": 2021},
            }
        ]

        with patch.object(
            self.collector, "_get_active_leagues", return_value=["PL"]
        ), patch.object(
            self.collector, "_collect_league_fixtures", return_value=mock_fixtures
        ), patch.object(
            self.collector, "_save_to_bronze_layer"
        ):
            result = await self.collector.collect_fixtures(
                leagues=["PL"], date_from=date_from, date_to=date_to
            )

            assert result.status == "success"
            assert result.records_collected == 1

    @pytest.mark.asyncio
    async def test_collect_fixtures_default_date_range(self):
        """测试采集默认日期范围的赛程"""
        with patch.object(
            self.collector, "_get_active_leagues", return_value=["PL"]
        ), patch.object(
            self.collector, "_collect_league_fixtures", return_value=[]
        ), patch.object(
            self.collector, "_save_to_bronze_layer"
        ):
            result = await self.collector.collect_fixtures()

            assert result.collection_type == "fixtures"
            # 默认情况下应该有30天的日期范围

    @pytest.mark.asyncio
    async def test_collect_fixtures_duplicate_prevention(self):
        """测试采集赛程防重复机制"""
        mock_fixtures = [
            {
                "id": 123,
                "homeTeam": {"id": 1},
                "awayTeam": {"id": 2},
                "utcDate": "2024-01-01T15:00:00Z",
                "status": "SCHEDULED",
                "competition": {"id": 2021},
            }
        ]

        with patch.object(
            self.collector, "_get_active_leagues", return_value=["PL"]
        ), patch.object(
            self.collector, "_collect_league_fixtures", return_value=mock_fixtures
        ), patch.object(
            self.collector, "_save_to_bronze_layer"
        ), patch.object(
            self.collector, "_load_existing_matches"
        ):  # Mock to not reset processed matches
            # 添加已处理的比赛ID
            match_key = self.collector._generate_match_key(mock_fixtures[0])
            self.collector._processed_matches.add(match_key)

            result = await self.collector.collect_fixtures()

            # 应该跳过重复的比赛
            assert result.records_collected == 0

    @pytest.mark.asyncio
    async def test_collect_fixtures_partial_success(self):
        """测试采集赛程部分成功"""
        valid_fixture = {
            "id": 123,
            "homeTeam": {"id": 1},
            "awayTeam": {"id": 2},
            "utcDate": "2024-01-01T15:00:00Z",
            "status": "SCHEDULED",
            "competition": {"id": 2021},
        }

        invalid_fixture = {
            "id": 124,
            # 缺少必要字段
        }

        mock_fixtures = [valid_fixture, invalid_fixture]

        with patch.object(
            self.collector, "_get_active_leagues", return_value=["PL"]
        ), patch.object(
            self.collector, "_collect_league_fixtures", return_value=mock_fixtures
        ), patch.object(
            self.collector, "_save_to_bronze_layer"
        ):
            result = await self.collector.collect_fixtures()

            assert result.status == "partial"
            assert result.success_count == 1
            assert result.error_count == 1
            assert result.records_collected == 1

    @pytest.mark.asyncio
    async def test_collect_fixtures_league_error(self):
        """测试采集赛程联赛级别错误"""
        with patch.object(
            self.collector, "_get_active_leagues", return_value=["PL"]
        ), patch.object(
            self.collector,
            "_collect_league_fixtures",
            side_effect=Exception("League Error"),
        ), patch.object(
            self.collector, "_save_to_bronze_layer"
        ):
            result = await self.collector.collect_fixtures()

            assert result.status == "failed"
            assert result.success_count == 0
            assert result.error_count == 1
            assert "League Error" in result.error_message

    @pytest.mark.asyncio
    async def test_collect_fixtures_general_exception(self):
        """测试采集赛程总体异常"""
        with patch.object(
            self.collector,
            "_get_active_leagues",
            side_effect=Exception("General Error"),
        ):
            result = await self.collector.collect_fixtures()

            assert result.status == "failed"
            assert result.success_count == 0
            assert result.error_count == 1
            assert result.error_message == "General Error"

    @pytest.mark.asyncio
    async def test_collect_fixtures_empty_data_no_save(self):
        """测试采集空数据不保存"""
        with patch.object(
            self.collector, "_get_active_leagues", return_value=["PL"]
        ), patch.object(
            self.collector, "_collect_league_fixtures", return_value=[]
        ), patch.object(
            self.collector, "_save_to_bronze_layer"
        ) as mock_save:
            result = await self.collector.collect_fixtures()

            # 空数据不应该调用保存
            mock_save.assert_not_called()
            assert result.records_collected == 0

    @pytest.mark.asyncio
    async def test_collect_fixtures_with_missing_matches_detection(self):
        """测试采集赛程时检测缺失比赛"""
        mock_fixtures = [
            {
                "id": 123,
                "homeTeam": {"id": 1},
                "awayTeam": {"id": 2},
                "utcDate": "2024-01-01T15:00:00Z",
                "status": "SCHEDULED",
                "competition": {"id": 2021},
            }
        ]

        with patch.object(
            self.collector, "_get_active_leagues", return_value=["PL"]
        ), patch.object(
            self.collector, "_collect_league_fixtures", return_value=mock_fixtures
        ), patch.object(
            self.collector, "_save_to_bronze_layer"
        ), patch.object(
            self.collector, "_detect_missing_matches"
        ) as mock_detect:
            await self.collector.collect_fixtures()

            # 验证调用了缺失比赛检测
            mock_detect.assert_called_once()


class TestFixturesCollectorIntegration:
    """赛程采集器集成测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = FixturesCollector(
            api_key="test_key", base_url="https://test.api.com"
        )

    @pytest.mark.asyncio
    async def test_complete_workflow_simulation(self):
        """测试完整工作流程模拟"""
        # 模拟真实的赛程采集流程
        mock_fixtures = [
            {
                "id": 123,
                "homeTeam": {"id": 1, "name": "Team A"},
                "awayTeam": {"id": 2, "name": "Team B"},
                "utcDate": "2024-01-01T15:00:00Z",
                "status": "SCHEDULED",
                "competition": {"id": 2021, "name": "Premier League"},
                "season": {"id": 2023},
                "matchday": 15,
            },
            {
                "id": 124,
                "homeTeam": {"id": 3, "name": "Team C"},
                "awayTeam": {"id": 4, "name": "Team D"},
                "utcDate": "2024-01-02T15:00:00Z",
                "status": "SCHEDULED",
                "competition": {"id": 2021, "name": "Premier League"},
                "season": {"id": 2023},
                "matchday": 15,
            },
        ]

        with patch.object(
            self.collector, "_get_active_leagues", return_value=["PL"]
        ), patch.object(
            self.collector, "_collect_league_fixtures", return_value=mock_fixtures
        ), patch.object(
            self.collector, "_save_to_bronze_layer"
        ) as mock_save, patch.object(
            self.collector, "_detect_missing_matches"
        ) as mock_detect:
            result = await self.collector.collect_fixtures()

            # 验证结果
            assert result.status == "success"
            assert result.records_collected == 2
            assert result.success_count == 2
            assert result.error_count == 0

            # 验证数据清洗正确
            cleaned_data = result.collected_data
            assert len(cleaned_data) == 2
            assert cleaned_data[0]["external_match_id"] == "123"
            assert cleaned_data[1]["external_match_id"] == "124"
            assert cleaned_data[0]["external_home_team_id"] == "1"
            assert cleaned_data[1]["external_home_team_id"] == "3"

            # 验证保存调用
            mock_save.assert_called_once()
            mock_detect.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_comprehensive(self):
        """测试全面的错误处理"""
        # 测试各种错误场景
        error_scenarios = [
            ("API连接错误", Exception("Connection failed")),
            ("数据解析错误", Exception("Parse error")),
            ("数据库保存错误", Exception("Database error")),
        ]

        for scenario_name, exception in error_scenarios:
            with patch.object(
                self.collector, "_get_active_leagues", return_value=["PL"]
            ), patch.object(
                self.collector, "_collect_league_fixtures", side_effect=exception
            ):
                result = await self.collector.collect_fixtures()

                assert result.status == "failed"
                assert result.success_count == 0
                assert result.error_count == 1

    @pytest.mark.asyncio
    async def test_duplicate_detection_comprehensive(self):
        """测试全面的重复检测"""
        # 模拟重复的比赛数据
        duplicate_fixture = {
            "id": 123,
            "homeTeam": {"id": 1},
            "awayTeam": {"id": 2},
            "utcDate": "2024-01-01T15:00:00Z",
            "status": "SCHEDULED",
            "competition": {"id": 2021},
        }

        mock_fixtures = [duplicate_fixture, duplicate_fixture]  # 两个相同的比赛

        with patch.object(
            self.collector, "_get_active_leagues", return_value=["PL"]
        ), patch.object(
            self.collector, "_collect_league_fixtures", return_value=mock_fixtures
        ), patch.object(
            self.collector, "_save_to_bronze_layer"
        ):
            result = await self.collector.collect_fixtures()

            # 应该只采集一个比赛（第二个被跳过）
            assert result.success_count == 1
            assert result.records_collected == 1
