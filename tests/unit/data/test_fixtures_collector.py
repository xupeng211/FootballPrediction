"""
赛程数据采集器测试 - FixturesCollector

测试赛程数据采集的各个功能。
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import responses

from src.data.collectors.fixtures_collector import FixturesCollector, CollectionResult


class TestFixturesCollector:
    """测试赛程数据采集器"""

    @pytest.fixture
    def collector(self):
        """创建FixturesCollector实例"""
        with patch("src.data.collectors.base_collector.DatabaseManager"):
            return FixturesCollector(
                api_key="test_api_key",
                base_url="https://api.football-data.org/v4"
            )

    def test_init(self, collector):
        """测试初始化"""
        assert collector.data_source == "football_api"
        assert collector.api_key == "test_api_key"
        assert collector.base_url == "https://api.football-data.org/v4"
        assert hasattr(collector, '_processed_matches')
        assert isinstance(collector._processed_matches, set)
        assert hasattr(collector, '_missing_matches')
        assert isinstance(collector._missing_matches, list)

    @pytest.mark.asyncio
    async def test_collect_odds_skipped(self, collector):
        """测试FixturesCollector不处理赔率数据"""
        result = await collector.collect_odds()

        assert result.status == "skipped"
        assert result.records_collected == 0
        assert result.success_count == 0
        assert result.error_count == 0
        assert "FixturesCollector不支持采集赔率数据" in result.error_message

    @pytest.mark.asyncio
    async def test_collect_live_scores_skipped(self, collector):
        """测试FixturesCollector不处理实时比分数据"""
        result = await collector.collect_live_scores()

        assert result.status == "skipped"
        assert result.records_collected == 0
        assert result.success_count == 0
        assert result.error_count == 0
        assert "FixturesCollector不支持采集实时比分数据" in result.error_message

    @pytest.mark.asyncio
    async def test_get_active_leagues_success(self, collector):
        """测试成功获取活跃联赛列表"""
        with patch.object(collector, '_make_request_with_retry') as mock_request:
            mock_response = ["PL", "BL", "La Liga", "Serie A"]
            mock_request.return_value = mock_response

            leagues = await collector._get_active_leagues()

            assert leagues == ["PL", "BL", "La Liga", "Serie A"]
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_leagues_empty(self, collector):
        """测试没有活跃联赛的情况"""
        with patch.object(collector, '_make_request_with_retry') as mock_request:
            mock_request.return_value = []

            leagues = await collector._get_active_leagues()

            assert leagues == []
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_leagues_error(self, collector):
        """测试获取活跃联赛失败"""
        with patch.object(collector, '_make_request_with_retry') as mock_request:
            mock_request.side_effect = Exception("API Error")

            leagues = await collector._get_active_leagues()

            assert leagues == []
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_existing_matches_success(self, collector):
        """测试成功加载已存在的比赛数据"""
        mock_matches = [
            {"match_id": "match_1", "league_id": "PL", "status": "scheduled"},
            {"match_id": "match_2", "league_id": "BL", "status": "scheduled"}
        ]

        with patch.object(collector, '_query_database', return_value=mock_matches):
            existing_matches = await collector._load_existing_matches()

            assert existing_matches == set(["match_1", "match_2"])
            assert "match_1" in collector._processed_matches
            assert "match_2" in collector._processed_matches

    @pytest.mark.asyncio
    async def test_load_existing_matches_empty(self, collector):
        """测试没有已存在的比赛数据"""
        with patch.object(collector, '_query_database', return_value=[]):
            existing_matches = await collector._load_existing_matches()

            assert existing_matches == set()
            assert len(collector._processed_matches) == 0

    @pytest.mark.asyncio
    async def test_collect_fixtures_no_leagues(self, collector):
        """测试没有活跃联赛的情况"""
        with patch.object(collector, '_get_active_leagues', return_value=[]):
            result = await collector.collect_fixtures()

            assert result.status == "success"
            assert result.records_collected == 0
            assert result.success_count == 0
            assert result.error_count == 0
            assert "没有找到活跃联赛" in result.error_message

    @pytest.mark.asyncio
    async def test_collect_fixtures_single_league_success(self, collector):
        """测试单个联赛赛程采集成功"""
        mock_fixtures_data = [
            {
                "match_id": "match_1",
                "league_id": "PL",
                "home_team": "Team A",
                "away_team": "Team B",
                "date": "2024-01-15T15:00:00Z"
            }
        ]

        with patch.object(collector, '_get_active_leagues', return_value=["PL"]), \
             patch.object(collector, '_collect_league_fixtures', return_value=(True, mock_fixtures_data)), \
             patch.object(collector, '_save_to_database') as mock_save:

            result = await collector.collect_fixtures()

            assert result.status == "success"
            assert result.records_collected == 1
            assert result.success_count == 1
            assert result.error_count == 0
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_fixtures_multiple_leagues(self, collector):
        """测试多个联赛赛程采集"""
        mock_leagues = ["PL", "BL", "La Liga"]

        with patch.object(collector, '_get_active_leagues', return_value=mock_leagues), \
             patch.object(collector, '_collect_league_fixtures') as mock_collect, \
             patch.object(collector, '_save_to_database') as mock_save:

            # 模拟部分成功
            mock_collect.side_effect = [
                (True, [{"match_id": "match_1", "league": "PL"}]),
                (False, {"error": "API Error"}),
                (True, [{"match_id": "match_2", "league": "La Liga"}])
            ]

            result = await collector.collect_fixtures()

            assert result.status == "partial_success"
            assert result.records_collected == 2
            assert result.success_count == 2
            assert result.error_count == 1
            assert mock_save.call_count == 2

    @pytest.mark.asyncio
    async def test_collect_league_fixtures_success(self, collector):
        """测试单个联赛赛程采集成功"""
        mock_response = [
            {
                "id": "match_1",
                "homeTeam": {"name": "Team A"},
                "awayTeam": {"name": "Team B"},
                "utcDate": "2024-01-15T15:00:00Z",
                "competition": {"id": "PL"},
                "status": "SCHEDULED"
            }
        ]

        with patch.object(collector, '_make_request_with_retry', return_value=mock_response), \
             patch.object(collector, '_clean_fixture_data', return_value=mock_response):

            success, data = await collector._collect_league_fixtures("PL")

            assert success is True
            assert data == mock_response

    @pytest.mark.asyncio
    async def test_collect_league_fixtures_api_error(self, collector):
        """测试API错误处理"""
        with patch.object(collector, '_make_request_with_retry', side_effect=Exception("API Error")):
            success, data = await collector._collect_league_fixtures("PL")

            assert success is False
            assert data is None

    @pytest.mark.asyncio
    async def test_collect_league_fixtures_empty_response(self, collector):
        """测试空响应处理"""
        with patch.object(collector, '_make_request_with_retry', return_value=[]):
            success, data = await collector._collect_league_fixtures("PL")

            assert success is True
            assert data == []

    def test_generate_match_key(self, collector):
        """测试生成比赛键"""
        fixture_data = {
            "match_id": "match_1",
            "league_id": "PL",
            "home_team": "Team A",
            "away_team": "Team B",
            "date": "2024-01-15T15:00:00Z"
        }

        key = collector._generate_match_key(fixture_data)

        assert isinstance(key, str)
        assert len(key) > 0
        assert "match_1" in key
        assert "PL" in key

        # 相同的数据应该生成相同的键
        key2 = collector._generate_match_key(fixture_data)
        assert key == key2

    @pytest.mark.asyncio
    async def test_clean_fixture_data(self, collector):
        """测试数据清洗"""
        raw_fixture_data = [
            {
                "id": "match_1",
                "homeTeam": {"name": " Team A "},
                "awayTeam": {"name": "Team B  "},
                "utcDate": "2024-01-15T15:00:00Z",
                "competition": {"id": "PL"},
                "status": "SCHEDULED",
                "invalid_field": "should_be_removed"
            },
            {
                "id": "",  # 空ID，应该被过滤
                "homeTeam": {"name": "Team C"},
                "awayTeam": {"name": "Team D"},
                "utcDate": "2024-01-15T15:00:00Z",
                "competition": {"id": "BL"},
                "status": "SCHEDULED"
            }
        ]

        cleaned_data = await collector._clean_fixture_data(raw_fixture_data)

        assert len(cleaned_data) == 1  # 移除无效数据
        assert cleaned_data[0]["home_team"] == "Team A"  # 去除空格
        assert cleaned_data[0]["away_team"] == "Team B"
        assert cleaned_data[0]["match_id"] == "match_1"
        assert cleaned_data[0]["league_id"] == "PL"
        assert "invalid_field" not in cleaned_data[0]

    @pytest.mark.asyncio
    async def test_detect_missing_matches(self, collector):
        """测试检测缺失比赛"""
        # 添加一些已处理的比赛
        collector._processed_matches.update(["match_1", "match_2", "match_3"])

        current_fixtures = [
            {"match_id": "match_1", "status": "FINISHED"},
            {"match_id": "match_2", "status": "SCHEDULED"},
            {"match_id": "match_4", "status": "SCHEDULED"}  # 新比赛
        ]

        missing_matches = await collector._detect_missing_matches(current_fixtures)

        assert len(missing_matches) == 1
        assert "match_3" in missing_matches

    @pytest.mark.asyncio
    async def test_detect_missing_matches_no_missing(self, collector):
        """测试没有缺失比赛的情况"""
        collector._processed_matches.update(["match_1", "match_2"])

        current_fixtures = [
            {"match_id": "match_1", "status": "FINISHED"},
            {"match_id": "match_2", "status": "SCHEDULED"}
        ]

        missing_matches = await collector._detect_missing_matches(current_fixtures)

        assert len(missing_matches) == 0

    @pytest.mark.asyncio
    async def test_collect_fixtures_with_deduplication(self, collector):
        """测试去重功能"""
        # 预先添加已处理的比赛
        collector._processed_matches.add("match_1")

        mock_fixtures_data = [
            {"match_id": "match_1", "league_id": "PL", "home_team": "Team A", "away_team": "Team B"},
            {"match_id": "match_2", "league_id": "PL", "home_team": "Team C", "away_team": "Team D"}
        ]

        with patch.object(collector, '_get_active_leagues', return_value=["PL"]), \
             patch.object(collector, '_collect_league_fixtures', return_value=(True, mock_fixtures_data)), \
             patch.object(collector, '_save_to_database') as mock_save:

            result = await collector.collect_fixtures()

            # 只处理新比赛
            assert result.records_collected == 1
            assert result.success_count == 1
            mock_save.assert_called_once()

    @responses.activate
    @pytest.mark.asyncio
    async def test_api_rate_limiting(self, collector):
        """测试API限流处理"""
        responses.add(
            responses.GET,
            "https://api.football-data.org/v4/competitions",
            status=429,
            json={"error": "Rate limit exceeded"}
        )

        with patch.object(collector, '_make_request') as mock_make_request:
            mock_make_request.side_effect = Exception("Rate limit exceeded")

            try:
                await collector._get_active_leagues()
            except Exception as e:
                assert "Rate limit exceeded" in str(e)

    @pytest.mark.asyncio
    async def test_error_handling_and_logging(self, collector):
        """测试错误处理和日志记录"""
        with patch.object(collector, '_get_active_leagues', side_effect=Exception("Connection Error")):
            result = await collector.collect_fixtures()

            assert result.status == "error"
            assert result.error_count == 1
            assert "Connection Error" in result.error_message

    @pytest.mark.asyncio
    async def test_memory_cleanup_during_collection(self, collector):
        """测试采集过程中的内存清理"""
        # 添加大量缓存数据
        for i in range(1000):
            collector._processed_matches.add(f"match_{i}")
            collector._missing_matches[f"league_{i}"] = []

        # 执行采集
        with patch.object(collector, '_get_active_leagues', return_value=[]):
            await collector.collect_fixtures()

        # 验证状态保持
        assert len(collector._processed_matches) == 1000

    @pytest.mark.asyncio
    async def test_concurrent_collection_protection(self, collector):
        """测试并发采集保护"""
        # 模拟并发采集
        tasks = []
        for _ in range(3):
            task = asyncio.create_task(collector.collect_fixtures())
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证任务都执行了（并发保护不影响正常执行）
        success_count = sum(1 for r in results if isinstance(r, CollectionResult))
        assert success_count == 3

    @pytest.mark.asyncio
    async def test_collect_fixtures_with_cache_validation(self, collector):
        """测试缓存验证功能"""
        # 添加过期的缓存数据
        old_time = datetime.now() - timedelta(hours=2)
        collector._missing_matches["PL"] = {
            "timestamp": old_time,
            "fixtures": []
        }

        with patch.object(collector, '_get_active_leagues', return_value=["PL"]), \
             patch.object(collector, '_collect_league_fixtures', return_value=(True, [])), \
             patch.object(collector, '_save_to_database'):

            result = await collector.collect_fixtures()

            assert result.status == "success"
            # 验证缓存被更新
            assert "PL" in collector._missing_matches

    @pytest.mark.asyncio
    async def test_collect_fixtures_partial_data_recovery(self, collector):
        """测试部分数据恢复功能"""
        mock_leagues = ["PL", "BL"]

        with patch.object(collector, '_get_active_leagues', return_value=mock_leagues), \
             patch.object(collector, '_collect_league_fixtures') as mock_collect:

            # 模拟一个失败，一个成功
            mock_collect.side_effect = [
                (False, {"error": "API Error"}),
                (True, [{"match_id": "match_1", "league": "BL"}])
            ]

            result = await collector.collect_fixtures()

            assert result.status == "partial_success"
            assert result.records_collected == 1
            assert result.success_count == 1
            assert result.error_count == 1