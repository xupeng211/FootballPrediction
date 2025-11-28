"""
FotMob详情采集器单元测试
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.data.collectors.fotmob_details_collector import (
    FotmobDetailsCollector,
    MatchDetails,
    MatchStats,
    TeamLineup,
    Player,
    collect_match_details,
    collect_multiple_matches,
)


@pytest.fixture
def mock_raw_match_data():
    """模拟的原始比赛数据"""
    return {
        "id": 4721983,
        "home": {"id": 6262, "name": "Morocco", "shortName": "Morocco", "score": 0},
        "away": {"id": 230692, "name": "Comoros", "shortName": "Comoros", "score": 0},
        "matchDate": "21.12.2025 20:00",
        "homeScore": 0,
        "awayScore": 0,
        "status": {
            "utcTime": "2025-12-21T19:00:00.000Z",
            "halfs": {
                "firstHalfStarted": "",
                "secondHalfStarted": "",
                "firstExtraHalfStarted": "",
                "secondExtraHalfStarted": "",
            },
            "periodLength": 45,
            "started": False,
            "cancelled": False,
            "finished": False,
        },
        "pageUrl": "/matches/morocco-vs-comoros/cwadbx1#4721983",
        "odds": None,
        "liveTime": {"short": "1'", "shortKey": "", "long": "00:01", "longKey": ""},
        "startDay": None,
        "stats": None,
    }


@pytest.fixture
def mock_raw_match_data_with_stats(mock_raw_match_data):
    """模拟包含统计数据的原始比赛数据"""
    base_data = mock_raw_match_data
    base_data["stats"] = {
        "stats": [
            {"type": "xg", "home": 1.5, "away": 0.8},
            {"type": "possession", "home": 65.5, "away": 34.5},
            {"type": "shots", "home": 12, "away": 8},
        ]
    }
    return base_data


class TestFotmobDetailsCollector:
    """FotMob详情采集器测试"""

    @pytest.fixture
    def collector(self):
        """创建采集器实例"""
        return FotmobDetailsCollector()

    @pytest.mark.asyncio
    async def test_init_session(self, collector):
        """测试HTTP会话初始化"""
        with patch(
            "src.data.collectors.fotmob_details_collector.AsyncSession"
        ) as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            mock_session.get.return_value.status_code = 200

            await collector._init_session()

            assert collector.session is not None
            mock_session_class.assert_called_once()
            mock_session.get.assert_called_once_with(
                "https://www.fotmob.com/", timeout=5
            )

    @pytest.mark.asyncio
    async def test_collect_match_details_success(self, collector, mock_raw_match_data):
        """测试成功采集比赛详情"""
        # Mock HTTP会话和响应
        with patch(
            "src.data.collectors.fotmob_details_collector.AsyncSession"
        ) as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            mock_session.get.return_value.status_code = 200
            mock_session.get.return_value.json.return_value = mock_raw_match_data

            # 执行采集
            result = await collector.collect_match_details("4721983")

            # 验证结果
            assert result is not None
            assert isinstance(result, MatchDetails)
            assert result.match_id == 4721983
            assert result.home_team == "Morocco"
            assert result.away_team == "Comoros"
            assert result.home_score == 0
            assert result.away_score == 0
            assert result.match_date == "21.12.2025 20:00"
            assert result.status["started"] is False
            assert result.raw_data == mock_raw_match_data

    @pytest.mark.asyncio
    async def test_collect_match_details_not_found(self, collector):
        """测试比赛不存在的情况"""
        with patch(
            "src.data.collectors.fotmob_details_collector.AsyncSession"
        ) as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            mock_session.get.return_value.status_code = 404

            result = await collector.collect_match_details("9999999")

            assert result is None

    @pytest.mark.asyncio
    async def test_collect_match_details_server_error(self, collector):
        """测试服务器错误的情况"""
        with patch(
            "src.data.collectors.fotmob_details_collector.AsyncSession"
        ) as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            mock_session.get.return_value.status_code = 500

            result = await collector.collect_match_details("4721983")

            assert result is None

    def test_parse_basic_info_success(self, collector, mock_raw_match_data):
        """测试成功解析基础信息"""
        result = collector._parse_basic_info(mock_raw_match_data, "4721983")

        assert result is not None
        assert result.match_id == 4721983
        assert result.home_team == "Morocco"
        assert result.away_team == "Comoros"
        assert result.home_score == 0
        assert result.away_score == 0

    def test_parse_basic_info_missing_data(self, collector):
        """测试缺少数据的情况"""
        incomplete_data = {"home": {"name": "Team A"}}
        result = collector._parse_basic_info(incomplete_data, "4721983")

        assert result is None

    def test_parse_stats_with_data(self, collector, mock_raw_match_data_with_stats):
        """测试解析统计数据"""
        # 更新mock数据以包含实际的统计数据结构
        stats_data = mock_raw_match_data_with_stats
        stats_data["stats"] = {
            "xg": {"home": 1.5, "away": 0.8},
            "possession": {"home": 65.5, "away": 34.5},
            "shots": {"home": 12, "away": 8},
        }

        result = collector._parse_stats(stats_data)

        # 当前实现返回基础统计结构，因为我们需要根据实际数据结构调整
        assert result is not None
        assert isinstance(result, MatchStats)
        assert result.home_team == "Morocco"
        assert result.away_team == "Comoros"

    def test_parse_stats_no_data(self, collector, mock_raw_match_data):
        """测试没有统计数据的情况"""
        result = collector._parse_stats(mock_raw_match_data)

        # 即使没有统计数据，也应该返回基础结构
        assert result is not None
        assert isinstance(result, MatchStats)
        assert result.home_team == "Morocco"
        assert result.away_team == "Comoros"

    def test_parse_lineups(self, collector, mock_raw_match_data):
        """测试解析阵容数据"""
        home_lineup, away_lineup = collector._parse_lineups(mock_raw_match_data)

        assert home_lineup is not None
        assert away_lineup is not None
        assert isinstance(home_lineup, TeamLineup)
        assert isinstance(away_lineup, TeamLineup)
        assert home_lineup.team_name == "Morocco"
        assert away_lineup.team_name == "Comoros"
        assert home_lineup.players == []
        assert away_lineup.players == []

    @pytest.mark.asyncio
    async def test_batch_collect(self, collector, mock_raw_match_data):
        """测试批量采集"""
        match_ids = ["4721983", "4721984", "4721985"]

        with patch(
            "src.data.collectors.fotmob_details_collector.AsyncSession"
        ) as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            # Mock成功的响应
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = AsyncMock(return_value=mock_raw_match_data)
            mock_session.get.return_value = mock_response

            results = await collector.batch_collect(match_ids)

            assert len(results) == 3
            for result in results:
                assert isinstance(result, MatchDetails)
                assert result.home_team == "Morocco"
                assert result.away_team == "Comoros"

    @pytest.mark.asyncio
    async def test_batch_collect_with_errors(self, collector, mock_raw_match_data):
        """测试批量采集中包含错误的情况"""
        match_ids = ["4721983", "9999999", "4721984"]

        with patch(
            "src.data.collectors.fotmob_details_collector.AsyncSession"
        ) as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            def mock_get(*args, **kwargs):
                mock_response = MagicMock()
                if "9999999" in args[0]:
                    mock_response.status_code = 404
                else:
                    mock_response.status_code = 200
                    mock_response.json = AsyncMock(return_value=mock_raw_match_data)
                return mock_response

            mock_session.get.side_effect = mock_get

            results = await collector.batch_collect(match_ids)

            # 应该只返回成功的比赛数据
            assert len(results) == 2
            for result in results:
                assert isinstance(result, MatchDetails)


class TestConvenienceFunctions:
    """便捷函数测试"""

    @pytest.mark.asyncio
    async def test_collect_match_details_function(self, mock_raw_match_data):
        """测试单一比赛采集便捷函数"""
        with patch(
            "src.data.collectors.fotmob_details_collector.AsyncSession"
        ) as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            mock_session.get.return_value.status_code = 200
            mock_session.get.return_value.json.return_value = mock_raw_match_data

            result = await collect_match_details("4721983")

            assert result is not None
            assert isinstance(result, MatchDetails)
            assert result.match_id == 4721983

    @pytest.mark.asyncio
    async def test_collect_multiple_matches_function(self, mock_raw_match_data):
        """测试批量比赛采集便捷函数"""
        match_ids = ["4721983", "4721984"]

        with patch(
            "src.data.collectors.fotmob_details_collector.AsyncSession"
        ) as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = AsyncMock(return_value=mock_raw_match_data)
            mock_session.get.return_value = mock_response

            results = await collect_multiple_matches(match_ids)

            assert len(results) == 2
            for result in results:
                assert isinstance(result, MatchDetails)


# 集成测试 - 实际调用API（仅在需要时运行）
@pytest.mark.integration
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.skip(
    reason="Remote CI Flakiness/Environment Specific Issue - Requires actual network connection to FotMob API"
)
class TestRealApiIntegration:
    """真实API集成测试"""

    @pytest.mark.asyncio
    async def test_real_match_collection(self):
        """测试真实的比赛数据采集"""
        # 使用已知的比赛ID
        match_id = "4721983"

        collector = FotmobDetailsCollector()
        try:
            result = await collector.collect_match_details(match_id)

            # 验证基本结构
            assert result is not None
            assert isinstance(result, MatchDetails)
            assert result.match_id == int(match_id)
            assert result.home_team != ""
            assert result.away_team != ""

            # 打印实际数据以便分析
            print("\n📊 实际采集数据:")
            print(f"   比赛: {result.home_team} vs {result.away_team}")
            print(f"   比分: {result.home_score} - {result.away_score}")
            print(f"   日期: {result.match_date}")
            print(f"   状态: {result.status}")

            if result.stats:
                print("   统计数据: ✅")
                print(f"   主队xG: {result.stats.home_xg}")
                print(f"   客队xG: {result.stats.away_xg}")
            else:
                print("   统计数据: ❌")

            if result.home_lineup and result.home_lineup.players:
                print(f"   主队阵容: {len(result.home_lineup.players)} 名球员")
                # 查找前锋
                forwards = [
                    p
                    for p in result.home_lineup.players
                    if "forward" in p.position.lower()
                ]
                if forwards:
                    print(
                        f"   主队前锋: {forwards[0].name} (位置: {forwards[0].position})"
                    )
            else:
                print("   主队阵容: ❌")

        finally:
            await collector.close()
