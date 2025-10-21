from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from src.data.collectors.fixtures_collector import FixturesCollector

"""
数据收集器测试 - 比赛数据收集器
"""


@pytest.mark.unit
class TestFixturesCollector:
    """FixturesCollector测试"""

    @pytest.fixture
    def collector(self):
        """创建收集器实例"""
        collector = FixturesCollector()
        collector.logger = MagicMock()
        return collector

    @pytest.fixture
    def mock_http_client(self):
        """Mock HTTP客户端"""
        client = AsyncMock()
        client.get.return_value = MagicMock()
        client.get.return_value.status_code = 200
        client.get.return_value.json.return_value = {
            "matches": [
                {
                    "id": 12345,
                    "homeTeam": {"id": 10, "name": "Home Team"},
                    "awayTeam": {"id": 20, "name": "Away Team"},
                    "utcDate": "2025-10-05T15:00:00Z",
                    "status": "SCHEDULED",
                    "competition": {"id": 1, "name": "Premier League"},
                }
            ]
        }
        return client

    def test_collector_initialization(self, collector):
        """测试收集器初始化"""
        assert collector is not None
        assert collector.logger is not None

    @pytest.mark.asyncio
    async def test_collect_fixtures(self, collector, mock_http_client):
        """测试收集比赛数据"""
        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            _result = await collector.collect_fixtures(league_id=1)

            assert _result is not None
            assert len(result) == 1
            assert _result[0]["id"] == 12345
            assert _result[0]["homeTeam"]["name"] == "Home Team"

    @pytest.mark.asyncio
    async def test_collect_fixtures_with_date_range(self, collector, mock_http_client):
        """测试按日期范围收集比赛"""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=7)

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            _result = await collector.collect_fixtures(
                league_id=1, start_date=start_date, end_date=end_date
            )

            assert _result is not None
            mock_http_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_fixtures_error_handling(self, collector):
        """测试错误处理"""
        mock_http_client = AsyncMock()
        mock_http_client.get.side_effect = Exception("Network error")

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            _result = await collector.collect_fixtures(league_id=1)

            assert _result == []
            collector.logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_parse_fixture_data(self, collector):
        """测试解析比赛数据"""
        raw_data = {
            "id": 12345,
            "homeTeam": {"id": 10, "name": "Home Team"},
            "awayTeam": {"id": 20, "name": "Away Team"},
            "utcDate": "2025-10-05T15:00:00Z",
            "status": "SCHEDULED",
            "score": {"fullTime": {"homeTeam": None, "awayTeam": None}},
        }

        parsed = await collector._parse_fixture_data(raw_data)

        assert parsed["match_id"] == 12345
        assert parsed["home_team_id"] == 10
        assert parsed["away_team_id"] == 20
        assert parsed["match_time"] == "2025-10-05T15:00:00Z"
        assert parsed["status"] == "SCHEDULED"

    def test_build_api_url(self, collector):
        """测试构建API URL"""
        base_url = "https://api.football-data.org/v4"

        # 测试基础URL
        url = collector._build_api_url(base_url, "matches")
        assert url == f"{base_url}/matches"

        # 测试带参数的URL
        url = collector._build_api_url(
            base_url,
            "competitions/1/matches",
            dateFrom="2025-10-01",
            dateTo="2025-10-07",
        )
        assert "competitions/1/matches" in url
        assert "dateFrom=2025-10-01" in url
        assert "dateTo=2025-10-07" in url

    @pytest.mark.asyncio
    async def test_cache_fixture_data(self, collector):
        """测试缓存比赛数据"""
        fixture_data = {
            "match_id": 12345,
            "home_team": "Home Team",
            "away_team": "Away Team",
        }

        mock_cache = MagicMock()
        mock_cache.set.return_value = True

        with patch.object(collector, "get_cache_manager", return_value=mock_cache):
            _result = await collector._cache_fixture_data(fixture_data)

            assert _result is True
            mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_fixtures(self, collector):
        """测试获取缓存的比赛数据"""
        mock_cache = MagicMock()
        cached_data = [
            {"match_id": 12345, "home_team": "Home Team"},
            {"match_id": 12346, "home_team": "Another Team"},
        ]
        mock_cache.get.return_value = cached_data

        with patch.object(collector, "get_cache_manager", return_value=mock_cache):
            _result = await collector.get_cached_fixtures(league_id=1)

            assert _result == cached_data
            mock_cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limiting(self, collector, mock_http_client):
        """测试API限流"""
        # 模拟限流响应
        mock_http_client.get.return_value.status_code = 429
        mock_http_client.get.return_value.headers = {"X-Request-Reset": "60"}

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            with patch("asyncio.sleep") as mock_sleep:
                _result = await collector.collect_fixtures(league_id=1)

                mock_sleep.assert_called_once_with(60)
                assert _result == []

    def test_validate_fixture_data(self, collector):
        """测试验证比赛数据"""
        # 有效的数据
        valid_data = {
            "id": 12345,
            "homeTeam": {"id": 10},
            "awayTeam": {"id": 20},
            "utcDate": "2025-10-05T15:00:00Z",
        }
        assert collector._validate_fixture_data(valid_data) is True

        # 缺少ID
        invalid_data = {"homeTeam": {"id": 10}, "awayTeam": {"id": 20}}
        assert collector._validate_fixture_data(invalid_data) is False

    @pytest.mark.asyncio
    async def test_collect_league_fixtures(self, collector, mock_http_client):
        """测试收集联赛比赛"""
        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            _result = await collector.collect_league_fixtures(
                league_id=1, season="2024-25"
            )

            assert _result is not None
            # 验证调用参数
            call_args = mock_http_client.get.call_args[0][0]
            assert "competitions/1/matches" in call_args
            assert "season=2024-25" in call_args

    @pytest.mark.asyncio
    async def test_collect_team_fixtures(self, collector, mock_http_client):
        """测试收集球队比赛"""
        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            _result = await collector.collect_team_fixtures(team_id=10)

            assert _result is not None
            call_args = mock_http_client.get.call_args[0][0]
            assert "teams/10/matches" in call_args

    def test_extract_match_time(self, collector):
        """测试提取比赛时间"""
        date_string = "2025-10-05T15:00:00Z"
        _result = collector._extract_match_time(date_string)

        assert isinstance(result, datetime)
        assert _result.year == 2025
        assert _result.month == 10
        assert _result.day == 5

    def test_format_match_status(self, collector):
        """测试格式化比赛状态"""
        # 测试不同状态
        assert collector._format_match_status("SCHEDULED") == "scheduled"
        assert collector._format_match_status("LIVE") == "live"
        assert collector._format_match_status("FINISHED") == "finished"
        assert collector._format_match_status("POSTPONED") == "postponed"

    @pytest.mark.asyncio
    async def test_retry_mechanism(self, collector):
        """测试重试机制"""
        mock_http_client = AsyncMock()
        mock_http_client.get.side_effect = [
            Exception("First attempt failed"),
            Exception("Second attempt failed"),
            MagicMock(status_code=200, json=MagicMock(return_value={"matches": []})),
        ]

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            _result = await collector.collect_fixtures(league_id=1)

            assert _result == []
            assert mock_http_client.get.call_count == 3

    def test_build_cache_key(self, collector):
        """测试构建缓存键"""
        # 测试联赛比赛缓存键
        key = collector._build_cache_key("fixtures", league_id=1, season="2024-25")
        assert "fixtures:1:2024-25" in key

        # 测试球队比赛缓存键
        key = collector._build_cache_key("fixtures", team_id=10)
        assert "fixtures:10" in key

    @pytest.mark.asyncio
    async def test_filter_fixtures_by_status(self, collector):
        """测试按状态过滤比赛"""
        fixtures = [
            {"id": 1, "status": "SCHEDULED"},
            {"id": 2, "status": "FINISHED"},
            {"id": 3, "status": "LIVE"},
            {"id": 4, "status": "SCHEDULED"},
        ]

        # 只获取未开始的比赛
        _result = collector._filter_fixtures_by_status(
            fixtures, include_status=["SCHEDULED"]
        )
        assert len(result) == 2
        assert all(f["status"] == "SCHEDULED" for f in result)

    @pytest.mark.asyncio
    async def test_collect_fixtures_batch(self, collector, mock_http_client):
        """测试批量收集比赛"""
        league_ids = [1, 2, 3]

        with patch.object(collector, "_get_http_client", return_value=mock_http_client):
            results = await collector.collect_fixtures_batch(league_ids)

            assert len(results) == 3
            assert mock_http_client.get.call_count == 3

    def test_get_api_headers(self, collector):
        """测试获取API请求头"""
        headers = collector._get_api_headers()

        assert "X-Auth-Token" in headers
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_handle_api_response_errors(self, collector):
        """测试处理API响应错误"""
        # 401未授权
        response = MagicMock()
        response.status_code = 401
        error_msg = collector._handle_api_response_error(response)
        assert "unauthorized" in error_msg.lower()

        # 404未找到
        response.status_code = 404
        error_msg = collector._handle_api_response_error(response)
        assert "not found" in error_msg.lower()

        # 500服务器错误
        response.status_code = 500
        error_msg = collector._handle_api_response_error(response)
        assert "server error" in error_msg.lower()

    def test_parse_fixture_score(self, collector):
        """测试解析比赛比分"""
        raw_score = {
            "winner": "HOME_TEAM",
            "fullTime": {"homeTeam": 2, "awayTeam": 1},
            "halfTime": {"homeTeam": 1, "awayTeam": 1},
        }

        parsed = collector._parse_fixture_score(raw_score)

        assert parsed["winner"] == "home"
        assert parsed["home_score"] == 2
        assert parsed["away_score"] == 1
        assert parsed["home_ht_score"] == 1
        assert parsed["away_ht_score"] == 1
