# TODO: Consider creating a fixture for 17 repeated Mock creations

# TODO: Consider creating a fixture for 17 repeated Mock creations

from unittest.mock import AsyncMock, Mock, patch

"""
测试Redis缓存预热管理器
"""

from datetime import datetime, timedelta

import pytest

from src.cache.redis.warmup.warmup_manager import CacheWarmupManager


@pytest.mark.unit
class TestCacheWarmupManager:
    """测试缓存预热管理器"""

    def setup_method(self):
        """设置测试环境"""
        self.mock_redis_manager = Mock()
        self.mock_redis_manager.aset = AsyncMock()
        self.warmup_manager = CacheWarmupManager(self.mock_redis_manager)

    @pytest.mark.asyncio
    async def test_warmup_match_cache_success(self):
        """测试成功预热比赛缓存"""
        # Mock数据库查询
        mock_match = Mock()
        mock_match.id = 123
        mock_match.home_team = "Team A"
        mock_match.away_team = "Team B"
        mock_match.match_time = datetime.now()
        mock_match.league_id = 1
        mock_match.match_status.value = "scheduled"
        mock_match.venue = "Stadium"

        with (
            patch("src.cache.redis.warmup.warmup_manager.select"),
            patch(
                "src.cache.redis.warmup.warmup_manager.get_async_session"
            ) as mock_session,
        ):
            # 设置mock返回值
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = mock_match
            mock_session.return_value.__aenter__.return_value.execute.return_value = (
                mock_result
            )

            _result = await self.warmup_manager.warmup_match_cache(123)

            assert _result is True
            # 验证缓存设置被调用了两次（比赛信息和特征）
            assert self.mock_redis_manager.aset.call_count == 2

    @pytest.mark.asyncio
    async def test_warmup_match_cache_not_found(self):
        """测试预热不存在的比赛缓存"""
        with (
            patch("src.cache.redis.warmup.warmup_manager.select"),
            patch(
                "src.cache.redis.warmup.warmup_manager.get_async_session"
            ) as mock_session,
        ):
            # 设置mock返回值
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.return_value.__aenter__.return_value.execute.return_value = (
                mock_result
            )

            _result = await self.warmup_manager.warmup_match_cache(999)

            assert _result is False
            # 验证没有调用缓存设置
            self.mock_redis_manager.aset.assert_not_called()

    @pytest.mark.asyncio
    async def test_warmup_team_cache_success(self):
        """测试成功预热球队缓存"""
        # Mock数据库查询
        mock_team = Mock()
        mock_team.id = 456
        mock_team.team_name = "Team X"
        mock_team.country = "Country"
        mock_team.founded_year = 1900
        mock_team.stadium = "Home Stadium"

        with (
            patch("src.cache.redis.warmup.warmup_manager.select"),
            patch(
                "src.cache.redis.warmup.warmup_manager.get_async_session"
            ) as mock_session,
        ):
            # 设置mock返回值
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = mock_team
            mock_session.return_value.__aenter__.return_value.execute.return_value = (
                mock_result
            )

            _result = await self.warmup_manager.warmup_team_cache(456)

            assert _result is True
            # 验证缓存设置被调用了两次（球队信息和特征）
            assert self.mock_redis_manager.aset.call_count == 2

    @pytest.mark.asyncio
    async def test_warmup_upcoming_matches(self):
        """测试预热即将开始的比赛"""
        # Mock比赛数据
        mock_match1 = Mock()
        mock_match1.id = 1
        mock_match1.home_team_id = 10
        mock_match1.away_team_id = 20
        mock_match2 = Mock()
        mock_match2.id = 2
        mock_match2.home_team_id = 30
        mock_match2.away_team_id = 40

        with (
            patch("src.cache.redis.warmup.warmup_manager.select"),
            patch(
                "src.cache.redis.warmup.warmup_manager.get_async_session"
            ) as mock_session,
        ):
            # 设置mock返回值
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = [
                mock_match1,
                mock_match2,
            ]
            mock_session.return_value.__aenter__.return_value.execute.return_value = (
                mock_result
            )

            # Mock warmup_match_cache 和 warmup_team_cache
            self.warmup_manager.warmup_match_cache = AsyncMock(return_value=True)
            self.warmup_manager.warmup_team_cache = AsyncMock(return_value=True)

            _result = await self.warmup_manager.warmup_upcoming_matches(24)

            assert _result == 2
            # 验证每个比赛和其主客队都被预热了
            assert self.warmup_manager.warmup_match_cache.call_count == 2
            assert self.warmup_manager.warmup_team_cache.call_count == 4

    @pytest.mark.asyncio
    async def test_warmup_historical_stats(self):
        """测试预热历史统计"""
        _result = await self.warmup_manager.warmup_historical_stats(7)

        assert _result is True
        # 验证缓存设置被调用
        self.mock_redis_manager.aset.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_warmup(self):
        """测试完整缓存预热"""
        # Mock各个预热方法
        self.warmup_manager.warmup_upcoming_matches = AsyncMock(return_value=5)
        self.warmup_manager.warmup_historical_stats = AsyncMock(return_value=True)

        _result = await self.warmup_manager.full_warmup()

        assert _result == {"upcoming_matches": 5, "historical_stats": 1, "total": 6}

    @pytest.mark.asyncio
    async def test_warmup_on_startup(self):
        """测试系统启动时的缓存预热"""
        from src.cache.redis.warmup.warmup_manager import warmup_cache_on_startup

        mock_manager = Mock()
        mock_warmup_manager = Mock()
        mock_warmup_manager.full_warmup = AsyncMock(return_value={"total": 10})

        with patch(
            "src.cache.redis.warmup.warmup_manager.CacheWarmupManager"
        ) as mock_warmup_class:
            mock_warmup_class.return_value = mock_warmup_manager

            _result = await warmup_cache_on_startup(mock_manager)

            assert _result == {"total": 10}
            mock_warmup_class.assert_called_once_with(mock_manager)
