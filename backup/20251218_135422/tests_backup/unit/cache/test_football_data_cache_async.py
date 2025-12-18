"""足球数据缓存异步测试
Football Data Cache Async Tests.

测试足球数据缓存管理器的异步功能。
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.cache.football_data_cache import CacheConfig, FootballDataCacheManager


class TestFootballDataCacheAsync:
    """足球数据缓存异步测试类."""

    def setup_method(self):
        """每个测试方法前的设置."""
        self.test_league_data = {
            "id": 39,
            "name": "Premier League",
            "country": "England",
            "season": 2023,
        }

        self.test_team_data = {
            "id": 57,
            "name": "Arsenal",
            "short_name": "ARS",
            "country": "England",
        }

        self.test_match_data = {
            "id": 12345,
            "home_team": 57,
            "away_team": 58,
            "home_score": 2,
            "away_score": 1,
            "date": "2023-12-01",
            "status": "FT",
        }

    @pytest.mark.asyncio
    async def test_cache_config_initialization(self):
        """测试缓存配置初始化."""
        # 测试默认配置
        config = CacheConfig()
        assert config.league_cache_hours == 24
        assert config.team_cache_hours == 48
        assert config.match_cache_minutes == 15
        assert config.standings_cache_minutes == 30
        assert config.api_response_cache_minutes == 10
        assert config.statistics_cache_hours == 6

        # 测试自定义配置
        custom_config = CacheConfig(
            league_cache_hours=48, team_cache_hours=72, match_cache_minutes=30
        )
        assert custom_config.league_cache_hours == 48
        assert custom_config.team_cache_hours == 72
        assert custom_config.match_cache_minutes == 30

    @pytest.mark.asyncio
    @patch("src.cache.football_data_cache.get_redis_manager")
    @patch("src.cache.football_data_cache.CacheKeyManager")
    async def test_football_data_cache_manager_initialization(
        self, mock_key_manager, mock_redis_manager
    ):
        """测试足球数据缓存管理器初始化."""
        # 模拟依赖
        mock_redis_instance = AsyncMock()
        mock_key_manager_instance = Mock()
        mock_redis_manager.return_value = mock_redis_instance
        mock_key_manager.return_value = mock_key_manager_instance

        # 测试默认配置初始化
        manager = FootballDataCacheManager()

        assert manager.config == CacheConfig()
        assert manager.redis == mock_redis_instance
        assert manager.key_manager == mock_key_manager_instance

        # 验证前缀设置
        expected_prefixes = {
            "league": "football:league",
            "team": "football:team",
            "match": "football:match",
            "standings": "football:standings",
            "api_response": "football:api",
            "statistics": "football:stats",
            "sync_status": "football:sync",
        }
        assert manager.prefixes == expected_prefixes

    @pytest.mark.asyncio
    @patch("src.cache.football_data_cache.get_redis_manager")
    @patch("src.cache.football_data_cache.CacheKeyManager")
    async def test_league_data_caching(self, mock_key_manager, mock_redis_manager):
        """测试联赛数据缓存."""
        # 设置模拟
        mock_redis_instance = AsyncMock()
        mock_redis_instance.aset.return_value = True
        mock_redis_instance.asadd.return_value = 1
        mock_redis_manager.return_value = mock_redis_instance
        mock_key_manager.return_value = Mock()

        manager = FootballDataCacheManager()

        # 测试成功缓存联赛数据
        result = await manager.cache_league(self.test_league_data)

        assert result is True
        mock_redis_instance.aset.assert_called_once()

        # 验证调用参数
        call_args = mock_redis_instance.aset.call_args
        key, value = call_args[0]
        kwargs = call_args[1]
        assert key == "football:league:39"  # 预期的键格式
        assert json.loads(value) == self.test_league_data
        assert kwargs["ex"] == 24 * 3600  # 24小时的秒数

    @pytest.mark.asyncio
    @patch("src.cache.football_data_cache.get_redis_manager")
    @patch("src.cache.football_data_cache.CacheKeyManager")
    async def test_league_data_caching_missing_id(
        self, mock_key_manager, mock_redis_manager
    ):
        """测试缺少ID的联赛数据缓存."""
        mock_redis_instance = AsyncMock()
        mock_redis_manager.return_value = mock_redis_instance
        mock_key_manager.return_value = Mock()

        manager = FootballDataCacheManager()

        # 测试缺少external_id的数据
        invalid_data = {"name": "Invalid League", "country": "England"}
        result = await manager.cache_league(invalid_data)

        assert result is False
        mock_redis_instance.aset.assert_not_called()

        # 测试空数据
        empty_data = {}
        result = await manager.cache_league(empty_data)
        assert result is False

    @pytest.mark.asyncio
    @patch("src.cache.football_data_cache.get_redis_manager")
    @patch("src.cache.football_data_cache.CacheKeyManager")
    async def test_get_cached_league(self, mock_key_manager, mock_redis_manager):
        """测试获取缓存的联赛数据."""
        mock_redis_instance = AsyncMock()
        mock_redis_instance.aget.return_value = json.dumps(self.test_league_data)
        mock_redis_manager.return_value = mock_redis_instance
        mock_key_manager.return_value = Mock()

        manager = FootballDataCacheManager()

        # 测试成功获取缓存数据
        result = await manager.get_cached_league("39")

        assert result == self.test_league_data
        mock_redis_instance.aget.assert_called_once_with("football:league:39")

    @pytest.mark.asyncio
    @patch("src.cache.football_data_cache.get_redis_manager")
    @patch("src.cache.football_data_cache.CacheKeyManager")
    async def test_get_cached_league_not_found(
        self, mock_key_manager, mock_redis_manager
    ):
        """测试获取不存在的缓存联赛数据."""
        mock_redis_instance = AsyncMock()
        mock_redis_instance.aget.return_value = None
        mock_redis_manager.return_value = mock_redis_instance
        mock_key_manager.return_value = Mock()

        manager = FootballDataCacheManager()

        # 测试获取不存在的数据
        result = await manager.get_cached_league("999")

        assert result is None
        mock_redis_instance.aget.assert_called_once_with("football:league:999")

    @pytest.mark.asyncio
    @patch("src.cache.football_data_cache.get_redis_manager")
    @patch("src.cache.football_data_cache.CacheKeyManager")
    async def test_team_data_caching(self, mock_key_manager, mock_redis_manager):
        """测试球队数据缓存."""
        mock_redis_instance = AsyncMock()
        mock_redis_instance.aset.return_value = True
        mock_redis_manager.return_value = mock_redis_instance
        mock_key_manager.return_value = Mock()

        manager = FootballDataCacheManager()

        # 测试成功缓存球队数据
        result = await manager.cache_team(self.test_team_data)

        assert result is True
        mock_redis_instance.aset.assert_called_once()

        # 验证TTL
        call_args = mock_redis_instance.aset.call_args
        kwargs = call_args[1]
        assert kwargs["ex"] == 48 * 3600  # 48小时的秒数

    @pytest.mark.asyncio
    @patch("src.cache.football_data_cache.get_redis_manager")
    @patch("src.cache.football_data_cache.CacheKeyManager")
    async def test_match_data_caching(self, mock_key_manager, mock_redis_manager):
        """测试比赛数据缓存."""
        mock_redis_instance = AsyncMock()
        mock_redis_instance.aset.return_value = True
        mock_redis_manager.return_value = mock_redis_instance
        mock_key_manager.return_value = Mock()

        manager = FootballDataCacheManager()

        # 测试成功缓存比赛数据
        result = await manager.cache_match(self.test_match_data)

        assert result is True
        mock_redis_instance.aset.assert_called_once()

        # 验证TTL（比赛数据使用分钟）
        call_args = mock_redis_instance.aset.call_args
        kwargs = call_args[1]
        assert kwargs["ex"] == 15 * 60  # 15分钟的秒数

    @pytest.mark.asyncio
    @patch("src.cache.football_data_cache.get_redis_manager")
    @patch("src.cache.football_data_cache.CacheKeyManager")
    async def test_api_response_caching(self, mock_key_manager, mock_redis_manager):
        """测试API响应缓存."""
        mock_redis_instance = AsyncMock()
        mock_redis_instance.aset.return_value = True
        mock_redis_manager.return_value = mock_redis_instance
        mock_key_manager.return_value = Mock()

        manager = FootballDataCacheManager()

        params = {"page": 1}
        response_data = {"count": 100}

        # 测试成功缓存API响应
        result = await manager.cache_api_response(
            "test_endpoint", params, response_data
        )

        assert result is True
        mock_redis_instance.aset.assert_called_once()

        # 验证TTL（API响应使用默认配置，10分钟 = 600秒）
        call_args = mock_redis_instance.aset.call_args
        kwargs = call_args[1]
        assert kwargs["ex"] == 600  # 默认TTL

    @pytest.mark.asyncio
    @patch("src.cache.football_data_cache.get_redis_manager")
    @patch("src.cache.football_data_cache.CacheKeyManager")
    async def test_get_cached_api_response(self, mock_key_manager, mock_redis_manager):
        """测试获取缓存的API响应."""
        api_response_data = {"count": 100}
        full_api_response = {"status": "success", "data": api_response_data}

        mock_redis_instance = AsyncMock()
        mock_redis_instance.aget.return_value = json.dumps(full_api_response)
        mock_redis_manager.return_value = mock_redis_instance
        mock_key_manager.return_value = Mock()

        manager = FootballDataCacheManager()

        # 测试成功获取API响应
        result = await manager.get_cached_api_response("test_endpoint")

        assert result == api_response_data  # 应该只返回data部分
        mock_redis_instance.aget.assert_called_once()

    def test_cache_key_generation(self):
        """测试缓存键生成."""
        # 直接测试键生成方法
        manager = FootballDataCacheManager()

        # 测试基本键生成
        key1 = manager._make_key("test:prefix", "123")
        assert key1 == "test:prefix:123"

        # 测试带后缀的键生成
        key2 = manager._make_key("test:prefix", "123", "suffix")
        assert key2 == "test:prefix:123:suffix"

        # 测试列表键生成
        key3 = manager._make_list_key("test:list")
        assert key3 == "test:list:list"

        # 测试带过滤器的列表键生成
        filters = {"country": "England", "season": 2023}
        key4 = manager._make_list_key("test:list", filters)
        # 过滤器应该按字母顺序排序
        assert "country=England" in key4
        assert "season=2023" in key4

    @pytest.mark.asyncio
    @patch("src.cache.football_data_cache.get_redis_manager")
    @patch("src.cache.football_data_cache.CacheKeyManager")
    async def test_error_handling_redis_failure(
        self, mock_key_manager, mock_redis_manager
    ):
        """测试Redis连接失败的错误处理."""
        mock_redis_instance = AsyncMock()
        mock_redis_instance.aset.side_effect = Exception("Redis connection failed")
        mock_redis_manager.return_value = mock_redis_instance
        mock_key_manager.return_value = Mock()

        manager = FootballDataCacheManager()

        # 测试Redis操作失败时的错误处理
        result = await manager.cache_league(self.test_league_data)

        assert result is False  # 应该优雅地处理错误

    @pytest.mark.asyncio
    @patch("src.cache.football_data_cache.get_redis_manager")
    @patch("src.cache.football_data_cache.CacheKeyManager")
    @patch("src.cache.football_data_cache.logger")
    async def test_error_handling_logging(
        self, mock_logger, mock_key_manager, mock_redis_manager
    ):
        """测试错误处理和日志记录."""
        mock_redis_instance = AsyncMock()
        mock_redis_instance.aset.side_effect = Exception("Test error")
        mock_redis_manager.return_value = mock_redis_instance
        mock_key_manager.return_value = Mock()

        manager = FootballDataCacheManager()

        # 执行会触发错误的操作
        await manager.cache_league(self.test_league_data)

        # 验证错误被记录
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    @patch("src.cache.football_data_cache.get_redis_manager")
    @patch("src.cache.football_data_cache.CacheKeyManager")
    async def test_complex_data_serialization(
        self, mock_key_manager, mock_redis_manager
    ):
        """测试复杂数据序列化."""
        complex_league_data = {
            "id": 39,
            "name": "Premier League",
            "country": "England",
            "season": 2023,
            "teams": [{"id": 57, "name": "Arsenal"}, {"id": 58, "name": "Chelsea"}],
            "metadata": {
                "created_at": "2023-01-01",
                "updated_at": "2023-12-01",
                "version": 1.0,
            },
        }

        mock_redis_instance = AsyncMock()
        mock_redis_instance.aset.return_value = True
        mock_redis_manager.return_value = mock_redis_instance
        mock_key_manager.return_value = Mock()

        manager = FootballDataCacheManager()

        # 测试复杂数据的缓存
        result = await manager.cache_league(complex_league_data)

        assert result is True

        # 验证序列化的数据
        call_args = mock_redis_instance.aset.call_args
        serialized_data = call_args[0][1]
        parsed_data = json.loads(serialized_data)
        assert parsed_data == complex_league_data

    def test_config_ttl_conversion(self):
        """测试TTL时间转换."""
        config = CacheConfig()

        # 验证TTL转换
        assert config.league_cache_hours * 3600 == 86400  # 24小时
        assert config.team_cache_hours * 3600 == 172800  # 48小时
        assert config.match_cache_minutes * 60 == 900  # 15分钟
        assert config.api_response_cache_minutes * 60 == 600  # 10分钟
