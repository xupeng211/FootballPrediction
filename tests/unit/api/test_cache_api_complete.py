"""
缓存API完整测试
测试src/api/cache.py模块的所有功能
"""

import pytest
import sys
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))

from src.api.cache import (
    router,
    CacheStatsResponse,
    CacheOperationResponse,
    CacheKeyRequest,
    CachePrewarmRequest,
    get_cache_stats,
    clear_cache,
    prewarm_cache,
    optimize_cache,
    cache_health_check,
    get_cache_config,
    clear_cache_by_pattern,
    execute_prewarm_tasks,
    execute_cache_optimization
)


class TestCacheModels:
    """测试缓存数据模型"""

    def test_cache_stats_response(self):
        """测试缓存统计响应模型"""
        data = {
            "l1_cache": {"hit_rate": 0.85, "size": 1000},
            "l2_cache": {"hit_rate": 0.92, "size": 5000},
            "overall": {"total_hits": 10000, "total_misses": 1500},
            "config": {"ttl": 3600, "max_size": 10000}
        }

        response = CacheStatsResponse(**data)
        assert response.l1_cache["hit_rate"] == 0.85
        assert response.l2_cache["hit_rate"] == 0.92
        assert response.overall["total_hits"] == 10000
        assert response.config["ttl"] == 3600

    def test_cache_operation_response(self):
        """测试缓存操作响应模型"""
        response = CacheOperationResponse(
            success=True,
            message="操作成功",
            data={"cleared_keys": ["key1", "key2"]}
        )
        assert response.success is True
        assert response.message == "操作成功"
        assert response.data["cleared_keys"] == ["key1", "key2"]

    def test_cache_operation_response_no_data(self):
        """测试无数据的缓存操作响应"""
        response = CacheOperationResponse(
            success=False,
            message="操作失败"
        )
        assert response.success is False
        assert response.data is None

    def test_cache_key_request(self):
        """测试缓存键请求模型"""
        request = CacheKeyRequest(
            keys=["key1", "key2", "key3"],
            pattern="test:*"
        )
        assert request.keys == ["key1", "key2", "key3"]
        assert request.pattern == "test:*"

    def test_cache_key_request_no_pattern(self):
        """测试无模式的缓存键请求"""
        request = CacheKeyRequest(
            keys=["key1", "key2"],
            pattern=None
        )
        assert request.pattern is None

    def test_cache_prewarm_request(self):
        """测试缓存预热请求模型"""
        request = CachePrewarmRequest(
            task_types=["predictions", "teams"],
            force=True
        )
        assert request.task_types == ["predictions", "teams"]
        assert request.force is True

    def test_cache_prewarm_request_default_force(self):
        """测试默认force值的缓存预热请求"""
        request = CachePrewarmRequest(
            task_types=["hot_matches"]
        )
        assert request.force is False


class TestGetCacheStats:
    """测试获取缓存统计"""

    @pytest.mark.asyncio
    async def test_get_cache_stats_success(self):
        """测试成功获取缓存统计"""
        mock_stats = {
            "l1_cache": {
                "hit_rate": 0.85,
                "size": 1000,
                "max_size": 2000
            },
            "l2_cache": {
                "hit_rate": 0.92,
                "size": 5000,
                "max_size": 10000
            },
            "overall": {
                "total_hits": 10000,
                "total_misses": 1500
            },
            "config": {
                "ttl": 3600,
                "max_size": 10000
            }
        }

        with patch('src.api.cache.get_cache_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_stats.return_value = mock_stats
            mock_get_manager.return_value = mock_manager

            result = await get_cache_stats()

            assert isinstance(result, CacheStatsResponse)
            assert result.l1_cache["hit_rate"] == 0.85
            assert result.l2_cache["hit_rate"] == 0.92
            assert result.overall["total_hits"] == 10000

    @pytest.mark.asyncio
    async def test_get_cache_stats_manager_not_initialized(self):
        """测试缓存管理器未初始化"""
        with patch('src.api.cache.get_cache_manager', return_value=None):
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await get_cache_stats()
            assert exc_info.value.status_code == 503
            assert "缓存管理器未初始化" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_cache_stats_exception(self):
        """测试获取缓存统计时发生异常"""
        with patch('src.api.cache.get_cache_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_stats.side_effect = Exception("Redis connection failed")
            mock_get_manager.return_value = mock_manager

            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await get_cache_stats()
            assert exc_info.value.status_code == 500
            assert "获取缓存统计失败" in str(exc_info.value.detail)


class TestClearCache:
    """测试清理缓存"""

    @pytest.mark.asyncio
    async def test_clear_cache_success(self):
        """测试成功清理缓存"""
        request = CacheKeyRequest(
            keys=["key1", "key2", "key3"],
            pattern="test:*"
        )

        mock_background_tasks = Mock()
        mock_background_tasks.add_task = Mock()

        with patch('src.api.cache.get_cache_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.delete.return_value = True
            mock_get_manager.return_value = mock_manager

            result = await clear_cache(request, mock_background_tasks)

            assert result.success is True
            assert "成功清理 3 个缓存项" in result.message
            assert result.data["cleared_keys"] == ["key1", "key2", "key3"]
            mock_background_tasks.add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_cache_partial_success(self):
        """测试部分清理成功"""
        request = CacheKeyRequest(keys=["key1", "key2"], pattern=None)

        mock_background_tasks = Mock()
        mock_background_tasks.add_task = Mock()

        with patch('src.api.cache.get_cache_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.delete.side_effect = [True, False]  # 第一个成功，第二个失败
            mock_get_manager.return_value = mock_manager

            result = await clear_cache(request, mock_background_tasks)

            assert result.success is True
            assert "成功清理 1 个缓存项" in result.message
            assert result.data["cleared_keys"] == ["key1"]

    @pytest.mark.asyncio
    async def test_clear_cache_no_keys(self):
        """测试清理空键列表"""
        request = CacheKeyRequest(keys=[], pattern=None)

        mock_background_tasks = Mock()
        mock_background_tasks.add_task = Mock()

        with patch('src.api.cache.get_cache_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_get_manager.return_value = mock_manager

            result = await clear_cache(request, mock_background_tasks)

            assert result.success is True
            assert "成功清理 0 个缓存项" in result.message
            assert result.data["cleared_keys"] == []

    @pytest.mark.asyncio
    async def test_clear_cache_with_pattern_only(self):
        """测试仅使用模式清理"""
        request = CacheKeyRequest(keys=[], pattern="temp:*")

        mock_background_tasks = Mock()
        mock_background_tasks.add_task = Mock()

        with patch('src.api.cache.get_cache_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_get_manager.return_value = mock_manager

            result = await clear_cache(request, mock_background_tasks)

            assert result.success is True
            assert "成功清理 0 个缓存项" in result.message
            mock_background_tasks.add_task.assert_called_once_with(
                clear_cache_by_pattern,
                "temp:*"
            )

    @pytest.mark.asyncio
    async def test_clear_cache_manager_not_initialized(self):
        """测试缓存管理器未初始化"""
        request = CacheKeyRequest(keys=["key1"], pattern=None)

        with patch('src.api.cache.get_cache_manager', return_value=None):
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await clear_cache(request, Mock())
            assert exc_info.value.status_code == 503
            assert "缓存管理器未初始化" in str(exc_info.value.detail)


class TestPrewarmCache:
    """测试缓存预热"""

    @pytest.mark.asyncio
    async def test_prewarm_cache_success(self):
        """测试成功启动缓存预热"""
        request = CachePrewarmRequest(
            task_types=["predictions", "teams"],
            force=True
        )

        mock_background_tasks = Mock()
        mock_background_tasks.add_task = Mock()

        with patch('src.api.cache.get_cache_initializer') as mock_get_initializer:
            mock_initializer = Mock()
            mock_get_initializer.return_value = mock_initializer

            result = await prewarm_cache(request, mock_background_tasks)

            assert result.success is True
            assert "已启动 2 个预热任务" in result.message
            assert result.data["task_types"] == ["predictions", "teams"]
            mock_background_tasks.add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_prewarm_cache_invalid_task_types(self):
        """测试无效的任务类型"""
        request = CachePrewarmRequest(
            task_types=["invalid_task", "another_invalid"]
        )

        with patch('src.api.cache.get_cache_initializer') as mock_get_initializer:
            mock_initializer = Mock()
            mock_get_initializer.return_value = mock_initializer

            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await prewarm_cache(request, Mock())
            assert exc_info.value.status_code == 400
            assert "无效的任务类型" in str(exc_info.value.detail)
            assert "invalid_task" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_prewarm_cache_mixed_valid_invalid(self):
        """测试混合有效和无效的任务类型"""
        request = CachePrewarmRequest(
            task_types=["predictions", "invalid_task"]
        )

        with patch('src.api.cache.get_cache_initializer') as mock_get_initializer:
            mock_initializer = Mock()
            mock_get_initializer.return_value = mock_initializer

            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await prewarm_cache(request, Mock())
            assert exc_info.value.status_code == 400
            assert "invalid_task" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_prewarm_cache_initializer_not_initialized(self):
        """测试缓存初始化器未初始化"""
        request = CachePrewarmRequest(
            task_types=["predictions"]
        )

        with patch('src.api.cache.get_cache_initializer', return_value=None):
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await prewarm_cache(request, Mock())
            assert exc_info.value.status_code == 503
            assert "缓存初始化器未初始化" in str(exc_info.value.detail)


class TestOptimizeCache:
    """测试缓存优化"""

    @pytest.mark.asyncio
    async def test_optimize_cache_success(self):
        """测试成功启动缓存优化"""
        mock_background_tasks = Mock()
        mock_background_tasks.add_task = Mock()

        with patch('src.api.cache.get_cache_initializer') as mock_get_initializer:
            mock_initializer = Mock()
            mock_get_initializer.return_value = mock_initializer

            result = await optimize_cache(mock_background_tasks)

            assert result.success is True
            assert "已启动缓存优化任务" in result.message
            mock_background_tasks.add_task.assert_called_once_with(
                execute_cache_optimization
            )

    @pytest.mark.asyncio
    async def test_optimize_cache_initializer_not_initialized(self):
        """测试缓存初始化器未初始化"""
        with patch('src.api.cache.get_cache_initializer', return_value=None):
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await optimize_cache(Mock())
            assert exc_info.value.status_code == 503
            assert "缓存初始化器未初始化" in str(exc_info.value.detail)


class TestCacheHealthCheck:
    """测试缓存健康检查"""

    @pytest.mark.asyncio
    async def test_cache_health_check_all_healthy(self):
        """测试所有缓存健康"""
        with patch('src.api.cache.get_cache_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_l1_cache = Mock()
            mock_l1_cache.get_stats.return_value = {
                "size": 1000,
                "max_size": 2000,
                "utilization": 0.5
            }
            mock_manager.l1_cache = mock_l1_cache

            mock_redis_manager = AsyncMock()
            mock_redis_manager.ping.return_value = True
            mock_manager.redis_manager = mock_redis_manager
            mock_get_manager.return_value = mock_manager

            result = await cache_health_check()

            assert result["status"] == "healthy"
            assert result["checks"]["l1_cache"]["status"] == "healthy"
            assert result["checks"]["l2_cache"]["status"] == "healthy"
            assert result["checks"]["l1_cache"]["size"] == 1000
            assert result["checks"]["l2_cache"]["type"] == "Redis"

    @pytest.mark.asyncio
    async def test_cache_health_check_l1_unavailable(self):
        """测试L1缓存不可用"""
        with patch('src.api.cache.get_cache_manager', return_value=None):
            result = await cache_health_check()

            assert result["status"] == "degraded"
            assert result["checks"]["l1_cache"]["status"] == "unavailable"
            assert "缓存管理器未初始化" in result["checks"]["l1_cache"]["message"]

    @pytest.mark.asyncio
    async def test_cache_health_check_l2_unhealthy(self):
        """测试L2缓存不健康"""
        with patch('src.api.cache.get_cache_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_l1_cache = Mock()
            mock_l1_cache.get_stats.return_value = {
                "size": 1000,
                "max_size": 2000,
                "utilization": 0.5
            }
            mock_manager.l1_cache = mock_l1_cache

            mock_redis_manager = AsyncMock()
            mock_redis_manager.ping.side_effect = Exception("Redis connection failed")
            mock_manager.redis_manager = mock_redis_manager
            mock_get_manager.return_value = mock_manager

            result = await cache_health_check()

            assert result["status"] == "degraded"
            assert result["checks"]["l1_cache"]["status"] == "healthy"
            assert result["checks"]["l2_cache"]["status"] == "unhealthy"
            assert "Redis connection failed" in result["checks"]["l2_cache"]["message"]

    @pytest.mark.asyncio
    async def test_cache_health_check_l2_disabled(self):
        """测试L2缓存禁用"""
        with patch('src.api.cache.get_cache_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_l1_cache = Mock()
            mock_l1_cache.get_stats.return_value = {
                "size": 1000,
                "max_size": 2000,
                "utilization": 0.5
            }
            mock_manager.l1_cache = mock_l1_cache
            mock_manager.redis_manager = None
            mock_get_manager.return_value = mock_manager

            result = await cache_health_check()

            assert result["status"] == "healthy"
            assert result["checks"]["l1_cache"]["status"] == "healthy"
            assert result["checks"]["l2_cache"]["status"] == "disabled"
            assert "Redis未配置" in result["checks"]["l2_cache"]["message"]


class TestGetCacheConfig:
    """测试获取缓存配置"""

    @pytest.mark.asyncio
    async def test_get_cache_config_success(self):
        """测试成功获取缓存配置"""
        mock_config_manager = Mock()
        mock_config_manager.settings.enabled = True
        mock_config_manager.settings.default_ttl = 3600
        mock_config_manager.settings.redis_host = "localhost"
        mock_config_manager.settings.redis_port = 6379
        mock_config_manager.settings.redis_db = 0
        mock_config_manager.settings.redis_max_connections = 100
        mock_config_manager.settings.memory_cache_size = 1000
        mock_config_manager.settings.memory_cache_ttl = 1800
        mock_config_manager.settings.preload_enabled = True
        mock_config_manager.settings.preload_batch_size = 50
        mock_config_manager.settings.path_configs = {"api/*": {"ttl": 300}}

        # 由于get_cache_config_manager是在函数内部导入的，
        # 我们需要patch它所在的模块路径
        with patch('src.config.cache.get_cache_config_manager', return_value=mock_config_manager):
            result = await get_cache_config()

            assert result["enabled"] is True
            assert result["default_ttl"] == 3600
            assert result["redis"]["host"] == "localhost"
            assert result["redis"]["port"] == 6379
            assert result["memory_cache"]["size"] == 1000
            assert result["preload"]["enabled"] is True
            assert result["preload"]["batch_size"] == 50
            assert "api/*" in result["path_configs"]

    @pytest.mark.asyncio
    async def test_get_cache_config_exception(self):
        """测试获取缓存配置失败"""
        # patch正确的模块路径
        with patch('src.config.cache.get_cache_config_manager', side_effect=Exception("Config not found")):
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await get_cache_config()
            assert exc_info.value.status_code == 500
            assert "获取缓存配置失败" in str(exc_info.value.detail)


class TestBackgroundTasks:
    """测试后台任务"""

    @pytest.mark.asyncio
    async def test_clear_cache_by_pattern_success(self):
        """测试根据模式清理缓存"""
        with patch('src.api.cache.get_cache_manager') as mock_get_manager:
            with patch('src.api.cache.logger') as mock_logger:
                mock_manager = Mock()
                mock_get_manager.return_value = mock_manager

                await clear_cache_by_pattern("test:*")

                mock_logger.info.assert_called_once()
                assert "执行缓存清理任务" in mock_logger.info.call_args[0][0]

    @pytest.mark.asyncio
    async def test_clear_cache_by_pattern_exception(self):
        """测试清理缓存任务失败"""
        with patch('src.api.cache.get_cache_manager', side_effect=Exception("Cache error")):
            with patch('src.api.cache.logger') as mock_logger:
                await clear_cache_by_pattern("test:*")

                mock_logger.error.assert_called_once()
                assert "缓存清理任务失败" in mock_logger.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_execute_prewarm_tasks_predictions(self):
        """测试执行预测数据预热"""
        with patch('src.api.cache.get_cache_initializer') as mock_get_initializer:
            with patch('src.api.cache.logger') as mock_logger:
                mock_cache_warmer = AsyncMock()
                mock_initializer = Mock()
                mock_initializer.cache_warmer = mock_cache_warmer
                mock_get_initializer.return_value = mock_initializer

                await execute_prewarm_tasks(["predictions"])

                mock_cache_warmer.warmup_predictions.assert_called_once()
                mock_logger.info.assert_called_once_with("完成预热任务: predictions")

    @pytest.mark.asyncio
    async def test_execute_prewarm_tasks_teams(self):
        """测试执行球队数据预热"""
        with patch('src.api.cache.get_cache_initializer') as mock_get_initializer:
            with patch('src.api.cache.logger') as mock_logger:
                mock_cache_warmer = AsyncMock()
                mock_initializer = Mock()
                mock_initializer.cache_warmer = mock_cache_warmer
                mock_get_initializer.return_value = mock_initializer

                await execute_prewarm_tasks(["teams"])

                mock_cache_warmer.warmup_teams.assert_called_once()
                mock_logger.info.assert_called_once_with("完成预热任务: teams")

    @pytest.mark.asyncio
    async def test_execute_prewarm_tasks_hot_matches(self):
        """测试执行热门比赛预热"""
        with patch('src.api.cache.get_cache_initializer') as mock_get_initializer:
            with patch('src.api.cache.logger') as mock_logger:
                mock_cache_warmer = AsyncMock()
                mock_initializer = Mock()
                mock_initializer.cache_warmer = mock_cache_warmer
                mock_get_initializer.return_value = mock_initializer

                await execute_prewarm_tasks(["hot_matches"])

                mock_cache_warmer._warmup_hot_matches.assert_called_once()
                mock_logger.info.assert_called_once_with("完成预热任务: hot_matches")

    @pytest.mark.asyncio
    async def test_execute_prewarm_tasks_multiple(self):
        """测试执行多个预热任务"""
        with patch('src.api.cache.get_cache_initializer') as mock_get_initializer:
            with patch('src.api.cache.logger') as mock_logger:
                mock_cache_warmer = AsyncMock()
                mock_initializer = Mock()
                mock_initializer.cache_warmer = mock_cache_warmer
                mock_get_initializer.return_value = mock_initializer

                await execute_prewarm_tasks(["predictions", "teams", "hot_matches"])

                mock_cache_warmer.warmup_predictions.assert_called_once()
                mock_cache_warmer.warmup_teams.assert_called_once()
                mock_cache_warmer._warmup_hot_matches.assert_called_once()
                assert mock_logger.info.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_prewarm_tasks_no_cache_warmer(self):
        """测试没有缓存预热器"""
        with patch('src.api.cache.get_cache_initializer') as mock_get_initializer:
            mock_initializer = Mock()
            mock_initializer.cache_warmer = None
            mock_get_initializer.return_value = mock_initializer

            # 应该不会抛出异常
            await execute_prewarm_tasks(["predictions"])

    @pytest.mark.asyncio
    async def test_execute_cache_optimization_success(self):
        """测试执行缓存优化成功"""
        with patch('src.api.cache.get_cache_initializer') as mock_get_initializer:
            with patch('src.api.cache.logger') as mock_logger:
                mock_optimizer = AsyncMock()
                mock_initializer = Mock()
                mock_initializer.cache_optimizer = mock_optimizer
                mock_get_initializer.return_value = mock_initializer

                await execute_cache_optimization()

                mock_optimizer.optimize.assert_called_once()
                mock_logger.info.assert_called_once_with("缓存优化任务完成")

    @pytest.mark.asyncio
    async def test_execute_cache_optimization_no_optimizer(self):
        """测试没有缓存优化器"""
        with patch('src.api.cache.get_cache_initializer') as mock_get_initializer:
            mock_initializer = Mock()
            mock_initializer.cache_optimizer = None
            mock_get_initializer.return_value = mock_initializer

            # 应该不会抛出异常
            await execute_cache_optimization()

    @pytest.mark.asyncio
    async def test_execute_cache_optimization_exception(self):
        """测试缓存优化任务失败"""
        with patch('src.api.cache.get_cache_initializer') as mock_get_initializer:
            with patch('src.api.cache.logger') as mock_logger:
                mock_optimizer = AsyncMock()
                mock_optimizer.optimize.side_effect = Exception("Optimization failed")
                mock_initializer = Mock()
                mock_initializer.cache_optimizer = mock_optimizer
                mock_get_initializer.return_value = mock_initializer

                await execute_cache_optimization()

                mock_logger.error.assert_called_once()
                assert "缓存优化任务失败" in mock_logger.error.call_args[0][0]


class TestCacheRouter:
    """测试缓存路由"""

    def test_router_setup(self):
        """测试路由设置"""
        assert router is not None
        assert len(router.routes) > 0
        assert router.prefix == "/cache"
        assert router.tags == ["缓存管理"]

    def test_route_endpoints(self):
        """测试路由端点"""
        route_paths = [route.path for route in router.routes]
        expected_paths = [
            "/stats",
            "/clear",
            "/prewarm",
            "/optimize",
            "/health",
            "/config"
        ]

        for path in expected_paths:
            assert f"/cache{path}" in route_paths


class TestCacheEdgeCases:
    """测试缓存边界情况"""

    @pytest.mark.asyncio
    async def test_clear_cache_with_special_characters(self):
        """测试清理包含特殊字符的键"""
        request = CacheKeyRequest(
            keys=["test:key:1", "user@domain.com", "path/to/resource"],
            pattern="*:special:*"
        )

        mock_background_tasks = Mock()
        mock_background_tasks.add_task = Mock()

        with patch('src.api.cache.get_cache_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.delete.return_value = True
            mock_get_manager.return_value = mock_manager

            result = await clear_cache(request, mock_background_tasks)

            assert result.success is True
            assert len(result.data["cleared_keys"]) == 3

    @pytest.mark.asyncio
    async def test_prewarm_cache_with_force(self):
        """测试强制预热缓存"""
        request = CachePrewarmRequest(
            task_types=["predictions"],
            force=True
        )

        mock_background_tasks = Mock()
        mock_background_tasks.add_task = Mock()

        with patch('src.api.cache.get_cache_initializer') as mock_get_initializer:
            mock_initializer = Mock()
            mock_get_initializer.return_value = mock_initializer

            result = await prewarm_cache(request, mock_background_tasks)

            assert result.success is True
            # 验证force参数被传递
            mock_background_tasks.add_task.assert_called_once()
            call_args = mock_background_tasks.add_task.call_args
            assert call_args[0][0] == execute_prewarm_tasks
            assert call_args[0][1] == ["predictions"]
            assert call_args[0][2] is True

    @pytest.mark.asyncio
    async def test_get_cache_stats_with_large_numbers(self):
        """测试大数值的缓存统计"""
        mock_stats = {
            "l1_cache": {
                "hit_rate": 0.999999,
                "size": 1000000,
                "max_size": 2000000
            },
            "l2_cache": {
                "hit_rate": 0.85,
                "size": 5000000,
                "max_size": 10000000
            },
            "overall": {
                "total_hits": 1000000000,
                "total_misses": 150000000
            },
            "config": {
                "ttl": 86400,
                "max_size": 50000000
            }
        }

        with patch('src.api.cache.get_cache_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_stats.return_value = mock_stats
            mock_get_manager.return_value = mock_manager

            result = await get_cache_stats()

            assert result.l1_cache["size"] == 1000000
            assert result.overall["total_hits"] == 1000000000
            assert result.config["max_size"] == 50000000


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "-s"])