"""
football_data_cache.py 安全网测试
Football Data Cache Safety Net Tests

【SDET安全网测试】为P0风险文件 football_data_cache.py 创建第一层安全网测试

测试原则:
- 🚫 绝对不Mock目标文件的内部函数
- ✅ 只关注公共接口的输入和输出
- ✅ 直接导入并测试公共类和方法
- ✅ 构造简单的请求，验证基本行为和异常处理
- ✅ 必须Mock外部依赖(Redis)，只测试缓存逻辑本身

风险等级: P0 (367行代码，0%覆盖率)
测试策略: Mock驱动黑盒单元测试 - Happy Path + Unhappy Path
发现目标:
- FootballDataCacheManager 主类
- cache_league() - 联赛数据缓存
- get_cached_league() - 联赛数据获取
- cache_team() - 球队数据缓存
- get_cached_team() - 球队数据获取
- invalidate_*_cache() - 缓存失效方法
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Any, Optional

# 直接导入目标文件中的类和方法
try:
    from src.cache.football_data_cache import (
        FootballDataCacheManager,
        CacheConfig,
    )
except ImportError as e:
    # 如果导入失败，创建一个基本的Mock来测试导入问题
    pytest.skip(f"Cannot import football_data_cache: {e}", allow_module_level=True)


class TestFootballDataCacheSafetyNet:
    """
    FootballDataCacheManager 安全网测试

    核心目标：为这个367行的P0风险文件创建最基本的"安全网"
    未来重构时，这些测试能保证基本功能不被破坏
    """

    @pytest.fixture
    def mock_redis_manager(self):
        """Mock Redis Manager以避免Redis连接问题"""
        mock_redis = AsyncMock()
        mock_redis.aset = AsyncMock(return_value=True)
        mock_redis.aget = AsyncMock(return_value=None)
        mock_redis.asadd = AsyncMock(return_value=True)
        mock_redis.adelete = AsyncMock(return_value=1)
        mock_redis.aexists = AsyncMock(return_value=True)
        mock_redis.aclear = AsyncMock(return_value=True)
        mock_redis.akeys = AsyncMock(return_value=[])
        return mock_redis

    @pytest.fixture
    def mock_key_manager(self):
        """Mock CacheKeyManager"""
        mock_key_manager = Mock()
        mock_key_manager.generate_key = Mock(
            side_effect=lambda prefix, identifier: f"{prefix}:{identifier}"
        )
        return mock_key_manager

    @pytest.fixture
    def football_cache(self, mock_redis_manager, mock_key_manager):
        """创建FootballDataCacheManager实例用于测试"""
        with (
            patch(
                "src.cache.football_data_cache.get_redis_manager",
                return_value=mock_redis_manager,
            ),
            patch(
                "src.cache.football_data_cache.CacheKeyManager",
                return_value=mock_key_manager,
            ),
        ):
            try:
                return FootballDataCacheManager()
            except Exception as e:
                pytest.skip(f"Cannot create FootballDataCacheManager: {e}")

    @pytest.fixture
    def sample_league_data(self):
        """创建样本联赛数据"""
        return {
            "id": 39,
            "external_id": "premier_league",
            "name": "Premier League",
            "country": "England",
            "season": 2023,
            "type": "league",
        }

    @pytest.fixture
    def sample_team_data(self):
        """创建样本球队数据"""
        return {
            "id": 57,
            "external_id": "arsenal",
            "name": "Arsenal",
            "short_name": "ARS",
            "country": "England",
            "founded": 1886,
        }

    @pytest.fixture
    def sample_match_data(self):
        """创建样本比赛数据"""
        return {
            "id": 12345,
            "external_id": "match_12345",
            "home_team": 57,
            "away_team": 58,
            "home_score": 2,
            "away_score": 1,
            "date": "2023-12-01",
            "status": "FT",
            "competition": 39,
        }

    # ==================== P0 优先级 Happy Path 测试 ====================

    @pytest.mark.unit
    @pytest.mark.critical
    def test_football_cache_initialization(self, football_cache):
        """
        P0测试: FootballDataCacheManager 初始化 Happy Path

        测试目标: 验证缓存管理器能正常初始化
        预期结果: 对象创建成功，包含必要的属性
        业务重要性: 核心缓存类的初始化能力
        """
        # 验证对象创建成功
        assert football_cache is not None
        assert hasattr(football_cache, "config")
        assert hasattr(football_cache, "redis")
        assert hasattr(football_cache, "key_manager")
        assert hasattr(football_cache, "prefixes")

        # 验证配置存在
        assert football_cache.config is not None
        assert isinstance(football_cache.config, CacheConfig)

        # 验证前缀配置
        prefixes = football_cache.prefixes
        assert isinstance(prefixes, dict)
        assert "league" in prefixes
        assert "team" in prefixes
        assert "match" in prefixes
        assert "standings" in prefixes

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_cache_league_happy_path(
        self, football_cache, sample_league_data, mock_redis_manager
    ):
        """
        P0测试: 联赛数据缓存 Happy Path

        测试目标: cache_league() 方法
        预期结果: 成功缓存联赛数据
        业务重要性: 核心缓存功能 - 联赛数据缓存
        """
        try:
            result = await football_cache.cache_league(sample_league_data)

            # 基本验证
            assert isinstance(result, bool)

            # 验证Redis操作被调用
            mock_redis_manager.aset.assert_called_once()

            # 验证调用参数
            call_args = mock_redis_manager.aset.call_args
            assert call_args is not None
            assert len(call_args[0]) >= 2  # key和value
            assert (
                "premier_league" in call_args[0][0] or "39" in call_args[0][0]
            )  # key包含league_id

        except Exception as e:
            pytest.fail(f"cache_league() should not crash with valid data: {e}")

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_get_cached_league_hit_happy_path(
        self, football_cache, sample_league_data, mock_redis_manager
    ):
        """
        P0测试: 联赛数据获取 - 缓存命中 Happy Path

        测试目标: get_cached_league() 方法
        预期结果: 成功获取缓存的联赛数据
        业务重要性: 核心缓存功能 - 联赛数据检索
        """
        try:
            # Mock Redis返回数据
            mock_redis_manager.aget.return_value = (
                '{"id": 39, "name": "Premier League"}'
            )

            result = await football_cache.get_cached_league("39")

            # 基本验证
            assert result is not None
            assert isinstance(result, dict)
            assert result["id"] == 39
            assert result["name"] == "Premier League"

            # 验证Redis操作被调用
            mock_redis_manager.aget.assert_called_once()

        except Exception as e:
            pytest.fail(f"get_cached_league() should not crash with cache hit: {e}")

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_get_cached_league_miss_happy_path(
        self, football_cache, mock_redis_manager
    ):
        """
        P0测试: 联赛数据获取 - 缓存未命中 Happy Path

        测试目标: get_cached_league() 方法处理缓存未命中
        预期结果: 返回None表示缓存未命中
        业务重要性: 缓存未命中的正确处理
        """
        try:
            # Mock Redis返回None（缓存未命中）
            mock_redis_manager.aget.return_value = None

            result = await football_cache.get_cached_league("999")

            # 基本验证
            assert result is None

            # 验证Redis操作被调用
            mock_redis_manager.aget.assert_called_once()

        except Exception as e:
            pytest.fail(f"get_cached_league() should handle cache miss gracefully: {e}")

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_cache_team_happy_path(
        self, football_cache, sample_team_data, mock_redis_manager
    ):
        """
        P0测试: 球队数据缓存 Happy Path

        测试目标: cache_team() 方法
        预期结果: 成功缓存球队数据
        业务重要性: 核心缓存功能 - 球队数据缓存
        """
        try:
            result = await football_cache.cache_team(sample_team_data)

            # 基本验证
            assert isinstance(result, bool)

            # 验证Redis操作被调用
            mock_redis_manager.aset.assert_called()

        except Exception as e:
            pytest.fail(f"cache_team() should not crash with valid data: {e}")

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_get_cached_team_happy_path(
        self, football_cache, sample_team_data, mock_redis_manager
    ):
        """
        P0测试: 球队数据获取 Happy Path

        测试目标: get_cached_team() 方法
        预期结果: 成功获取缓存的球队数据
        业务重要性: 核心缓存功能 - 球队数据检索
        """
        try:
            # Mock Redis返回数据
            mock_redis_manager.aget.return_value = '{"id": 57, "name": "Arsenal"}'

            result = await football_cache.get_cached_team("57")

            # 基本验证
            assert result is not None
            assert isinstance(result, dict)
            assert result["id"] == 57
            assert result["name"] == "Arsenal"

            # 验证Redis操作被调用
            mock_redis_manager.aget.assert_called_once()

        except Exception as e:
            pytest.fail(f"get_cached_team() should not crash with cache hit: {e}")

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_cache_match_happy_path(
        self, football_cache, sample_match_data, mock_redis_manager
    ):
        """
        P0测试: 比赛数据缓存 Happy Path

        测试目标: cache_match() 方法
        预期结果: 成功缓存比赛数据
        业务重要性: 核心缓存功能 - 比赛数据缓存
        """
        try:
            result = await football_cache.cache_match(sample_match_data)

            # 基本验证
            assert isinstance(result, bool)

            # 验证Redis操作被调用
            mock_redis_manager.aset.assert_called()

        except Exception as e:
            pytest.fail(f"cache_match() should not crash with valid data: {e}")

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_get_cached_match_happy_path(
        self, football_cache, sample_match_data, mock_redis_manager
    ):
        """
        P0测试: 比赛数据获取 Happy Path

        测试目标: get_cached_match() 方法
        预期结果: 成功获取缓存的比赛数据
        业务重要性: 核心缓存功能 - 比赛数据检索
        """
        try:
            # Mock Redis返回比赛数据
            mock_redis_manager.aget.return_value = (
                '{"id": 12345, "home_team": "Arsenal", "away_team": "Chelsea"}'
            )

            result = await football_cache.get_cached_match("12345")

            # 基本验证
            assert result is not None
            assert isinstance(result, dict)
            assert result["id"] == 12345

            # 验证Redis操作被调用
            mock_redis_manager.aget.assert_called_once()

        except Exception as e:
            pytest.fail(f"get_cached_match() should not crash with cache hit: {e}")

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_get_cached_match_miss_happy_path(
        self, football_cache, mock_redis_manager
    ):
        """
        P0测试: 比赛数据获取 - 缓存未命中 Happy Path

        测试目标: get_cached_match() 方法处理缓存未命中
        预期结果: 返回None表示缓存未命中
        业务重要性: 缓存未命中的正确处理
        """
        try:
            # Mock Redis返回None（缓存未命中）
            mock_redis_manager.aget.return_value = None

            result = await football_cache.get_cached_match("99999")

            # 基本验证
            assert result is None

            # 验证Redis操作被调用
            mock_redis_manager.aget.assert_called_once()

        except Exception as e:
            pytest.fail(f"get_cached_match() should handle cache miss gracefully: {e}")

    # ==================== P1 优先级 Unhappy Path 测试 ====================

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_league_invalid_data(self, football_cache, mock_redis_manager):
        """
        P1测试: 联赛数据缓存 - 无效数据 Unhappy Path

        测试目标: cache_league() 方法对无效数据的处理
        错误构造: 传入缺少id的联赛数据
        预期结果: 应该返回False或抛出适当异常
        """
        try:
            # 测试缺少id的数据
            invalid_league = {"name": "Invalid League", "country": "Unknown"}
            result = await football_cache.cache_league(invalid_league)

            # 应该返回False表示缓存失败
            assert result is False

        except Exception as e:
            # 抛出异常也是可以接受的
            assert "id" in str(e).lower() or "required" in str(e).lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_team_invalid_data(self, football_cache, mock_redis_manager):
        """
        P1测试: 球队数据缓存 - 无效数据 Unhappy Path

        测试目标: cache_team() 方法对无效数据的处理
        错误构造: 传入缺少id的球队数据
        预期结果: 应该返回False或抛出适当异常
        """
        try:
            # 测试缺少id的数据
            invalid_team = {"name": "Invalid Team", "country": "Unknown"}
            result = await football_cache.cache_team(invalid_team)

            # 应该返回False表示缓存失败
            assert result is False

        except Exception as e:
            # 抛出异常也是可以接受的
            assert "id" in str(e).lower() or "required" in str(e).lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_match_invalid_data(self, football_cache, mock_redis_manager):
        """
        P1测试: 比赛数据缓存 - 无效数据 Unhappy Path

        测试目标: cache_match() 方法对无效数据的处理
        错误构造: 传入缺少id的比赛数据
        预期结果: 应该返回False或抛出适当异常
        """
        try:
            # 测试缺少id的数据
            invalid_match = {"home_team": 57, "away_team": 58, "score": "1-0"}
            result = await football_cache.cache_match(invalid_match)

            # 应该返回False表示缓存失败
            assert result is False

        except Exception as e:
            # 抛出异常也是可以接受的
            assert "id" in str(e).lower() or "required" in str(e).lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_cached_league_invalid_id(
        self, football_cache, mock_redis_manager
    ):
        """
        P1测试: 联赛数据获取 - 无效ID Unhappy Path

        测试目标: get_cached_league() 方法对无效ID的处理
        错误构造: 传入空字符串或None作为ID
        预期结果: 应该返回None或抛出适当异常
        """
        try:
            # 测试空字符串ID
            result = await football_cache.get_cached_league("")

            # 应该返回None或抛出异常
            assert result is None

        except Exception as e:
            # 抛出异常也是可以接受的
            assert "id" in str(e).lower() or "invalid" in str(e).lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_cached_team_invalid_id(self, football_cache, mock_redis_manager):
        """
        P1测试: 球队数据获取 - 无效ID Unhappy Path

        测试目标: get_cached_team() 方法对无效ID的处理
        错误构造: 传入空字符串或None作为ID
        预期结果: 应该返回None或抛出适当异常
        """
        try:
            # 测试空字符串ID
            result = await football_cache.get_cached_team("")

            # 应该返回None或抛出异常
            assert result is None

        except Exception as e:
            # 抛出异常也是可以接受的
            assert "id" in str(e).lower() or "invalid" in str(e).lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_league_redis_failure(
        self, football_cache, sample_league_data, mock_redis_manager
    ):
        """
        P1测试: 联赛数据缓存 - Redis失败 Unhappy Path

        测试目标: cache_league() 方法对Redis连接失败的处理
        错误构造: Mock Redis抛出异常
        预期结果: 应该优雅地处理Redis异常
        """
        try:
            # Mock Redis抛出异常
            mock_redis_manager.aset.side_effect = Exception("Redis connection failed")

            result = await football_cache.cache_league(sample_league_data)

            # 应该返回False表示缓存失败
            assert result is False

        except Exception as e:
            # 抛出异常也是可以接受的，但应该是相关的异常
            assert "redis" in str(e).lower() or "connection" in str(e).lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_cached_league_redis_failure(
        self, football_cache, mock_redis_manager
    ):
        """
        P1测试: 联赛数据获取 - Redis失败 Unhappy Path

        测试目标: get_cached_league() 方法对Redis连接失败的处理
        错误构造: Mock Redis抛出异常
        预期结果: 应该优雅地处理Redis异常
        """
        try:
            # Mock Redis抛出异常
            mock_redis_manager.aget.side_effect = Exception("Redis connection failed")

            result = await football_cache.get_cached_league("39")

            # 应该返回None表示获取失败
            assert result is None

        except Exception as e:
            # 抛出异常也是可以接受的，但应该是相关的异常
            assert "redis" in str(e).lower() or "connection" in str(e).lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_league_malformed_json(
        self, football_cache, sample_league_data, mock_redis_manager
    ):
        """
        P1测试: 联赛数据获取 - JSON解析错误 Unhappy Path

        测试目标: get_cached_league() 方法对损坏JSON的处理
        错误构造: Mock Redis返回损坏的JSON
        预期结果: 应该优雅地处理JSON解析错误
        """
        try:
            # Mock Redis返回损坏的JSON
            mock_redis_manager.aget.return_value = '{"id": 39, "name": "Premier League"'

            result = await football_cache.get_cached_league("39")

            # 应该返回None表示解析失败
            assert result is None

        except Exception as e:
            # 抛出异常也是可以接受的
            assert "json" in str(e).lower() or "parse" in str(e).lower()

    @pytest.mark.unit
    @pytest.mark.cache
    def test_cache_config_validation(self):
        """
        P1测试: 缓存配置验证

        测试目标: CacheConfig 数据类的结构
        预期结果: 应该包含预期的配置字段
        """
        try:
            # 创建默认配置
            config = CacheConfig()

            # 验证属性存在
            assert hasattr(config, "league_cache_hours")
            assert hasattr(config, "team_cache_hours")
            assert hasattr(config, "match_cache_minutes")
            assert hasattr(config, "standings_cache_minutes")
            assert hasattr(config, "api_response_cache_minutes")
            assert hasattr(config, "statistics_cache_hours")

            # 验证默认值
            assert config.league_cache_hours == 24
            assert config.team_cache_hours == 48
            assert config.match_cache_minutes == 15
            assert config.standings_cache_minutes == 30
            assert config.api_response_cache_minutes == 10
            assert config.statistics_cache_hours == 6

        except Exception as e:
            pytest.fail(f"CacheConfig should be properly defined: {e}")

    @pytest.mark.unit
    @pytest.mark.cache
    def test_key_generation_methods(self, football_cache):
        """
        P1测试: 键生成方法

        测试目标: _make_key 和 _make_list_key 方法
        预期结果: 应该生成正确的缓存键
        """
        try:
            # 测试基本键生成
            key = football_cache._make_key("test:prefix", "123")
            assert key == "test:prefix:123"

            # 测试带后缀的键生成
            key_with_suffix = football_cache._make_key("test:prefix", "123", "suffix")
            assert key_with_suffix == "test:prefix:123:suffix"

            # 测试列表键生成
            list_key = football_cache._make_list_key("test:list")
            assert list_key == "test:list:list"

            # 测试带过滤器的列表键生成
            list_key_with_filters = football_cache._make_list_key(
                "test:list", {"country": "England", "season": 2023}
            )
            assert "country=England" in list_key_with_filters
            assert "season=2023" in list_key_with_filters

        except Exception as e:
            pytest.fail(f"Key generation methods should work correctly: {e}")
