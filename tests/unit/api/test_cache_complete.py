"""
Cache API完整测试
测试覆盖所有缓存功能，提升覆盖率
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import asyncio
from fastapi import HTTPException, BackgroundTasks

# 直接导入模块
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))

# 动态导入模块以避免依赖问题
def import_cache_module():
    import importlib.util
    cache_path = os.path.join(os.path.dirname(__file__), '../../../src/api/cache.py')
    spec = importlib.util.spec_from_file_location("cache", cache_path)
    cache_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cache_module)
    return cache_module

cache_module = None


@pytest.mark.asyncio
class TestCacheStats:
    """测试缓存统计功能"""

    @patch('src.api.cache.get_cache_manager')
    async def test_get_cache_stats_success(self, mock_get_manager):
        """测试获取缓存统计成功"""
        # 模拟缓存管理器
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        # 模拟统计数据
        mock_manager.get_stats.return_value = {
            "l1_cache": {
                "hit_rate": 0.85,
                "miss_rate": 0.15,
                "size": 1000,
                "max_size": 2000
            },
            "l2_cache": {
                "hit_rate": 0.65,
                "miss_rate": 0.35,
                "size": 5000,
                "max_size": 10000
            },
            "overall": {
                "total_hit_rate": 0.75,
                "total_requests": 10000,
                "total_hits": 7500
            },
            "config": {
                "ttl": 3600,
                "max_memory": "1GB"
            }
        }

        result = await get_cache_stats()

        assert isinstance(result, CacheStatsResponse)
        assert result.l1_cache["hit_rate"] == 0.85
        assert result.l2_cache["hit_rate"] == 0.65
        assert result.overall["total_hit_rate"] == 0.75
        assert result.config["ttl"] == 3600

    @patch('src.api.cache.get_cache_manager')
    async def test_get_cache_stats_manager_not_initialized(self, mock_get_manager):
        """测试缓存管理器未初始化"""
        mock_get_manager.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_cache_stats()

        assert exc_info.value.status_code == 503
        assert "缓存管理器未初始化" in str(exc_info.value.detail)

    @patch('src.api.cache.get_cache_manager')
    async def test_get_cache_stats_error(self, mock_get_manager):
        """测试获取缓存统计时发生错误"""
        mock_get_manager.side_effect = Exception("Database connection failed")

        with pytest.raises(HTTPException) as exc_info:
            await get_cache_stats()

        assert exc_info.value.status_code == 500
        assert "获取缓存统计失败" in str(exc_info.value.detail)


@pytest.mark.asyncio
class TestCacheClear:
    """测试缓存清理功能"""

    @patch('src.api.cache.get_cache_manager')
    @patch('src.api.cache.clear_cache_by_pattern')
    async def test_clear_cache_with_keys(self, mock_clear_pattern, mock_get_manager):
        """测试清理指定键的缓存"""
        # 模拟缓存管理器
        mock_manager = MagicMock()
        mock_manager.delete = AsyncMock(return_value=True)
        mock_get_manager.return_value = mock_manager

        # 创建请求
        request = CacheKeyRequest(keys=["key1", "key2", "key3"])
        background_tasks = BackgroundTasks()

        result = await clear_cache(request, background_tasks)

        assert isinstance(result, CacheOperationResponse)
        assert result.success is True
        assert "成功清理" in result.message
        assert len(result.data["cleared_keys"]) == 3
        assert mock_manager.delete.call_count == 3

    @patch('src.api.cache.get_cache_manager')
    @patch('src.api.cache.clear_cache_by_pattern')
    async def test_clear_cache_with_pattern(self, mock_clear_pattern, mock_get_manager):
        """测试使用模式清理缓存"""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        request = CacheKeyRequest(keys=[], pattern="test:*")
        background_tasks = BackgroundTasks()

        result = await clear_cache(request, background_tasks)

        assert isinstance(result, CacheOperationResponse)
        assert result.success is True
        # 验证后台任务被添加
        background_tasks.add_task.assert_called_once_with(
            mock_clear_pattern,
            "test:*"
        )

    @patch('src.api.cache.get_cache_manager')
    async def test_clear_cache_partial_failure(self, mock_get_manager):
        """测试部分缓存清理失败"""
        # 第三个键删除失败
        manager = MagicMock()
        manager.delete = AsyncMock(side_effect=[True, True, False])
        mock_get_manager.return_value = manager

        request = CacheKeyRequest(keys=["key1", "key2", "key3"])
        background_tasks = BackgroundTasks()

        result = await clear_cache(request, background_tasks)

        assert result.success is True
        assert len(result.data["cleared_keys"]) == 2
        assert "key3" not in result.data["cleared_keys"]

    @patch('src.api.cache.get_cache_manager')
    async def test_clear_cache_empty_request(self, mock_get_manager):
        """测试空请求清理缓存"""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        request = CacheKeyRequest(keys=[], pattern=None)
        background_tasks = BackgroundTasks()

        result = await clear_cache(request, background_tasks)

        assert result.success is True
        assert len(result.data["cleared_keys"]) == 0


@pytest.mark.asyncio
class TestCachePrewarm:
    """测试缓存预热功能"""

    @patch('src.api.cache.get_cache_initializer')
    @patch('src.api.cache.execute_prewarm_tasks')
    async def test_prewarm_cache_success(self, mock_execute_tasks, mock_get_initializer):
        """测试成功执行缓存预热"""
        mock_initializer = MagicMock()
        mock_get_initializer.return_value = mock_initializer

        request = CachePrewarmRequest(
            task_types=["predictions", "teams"],
            force=False
        )
        background_tasks = BackgroundTasks()

        result = await prewarm_cache(request, background_tasks)

        assert isinstance(result, CacheOperationResponse)
        assert result.success is True
        assert "已启动 2 个预热任务" in result.message
        assert result.data["task_types"] == ["predictions", "teams"]
        # 验证后台任务被添加
        background_tasks.add_task.assert_called_once_with(
            mock_execute_tasks,
            ["predictions", "teams"],
            False
        )

    @patch('src.api.cache.get_cache_initializer')
    async def test_prewarm_cache_invalid_task_types(self, mock_get_initializer):
        """测试缓存预热时任务类型无效"""
        mock_initializer = MagicMock()
        mock_get_initializer.return_value = mock_initializer

        request = CachePrewarmRequest(
            task_types=["predictions", "invalid_task"],
            force=False
        )
        background_tasks = BackgroundTasks()

        with pytest.raises(HTTPException) as exc_info:
            await prewarm_cache(request, background_tasks)

        assert exc_info.value.status_code == 400
        assert "无效的任务类型: invalid_task" in str(exc_info.value.detail)

    @patch('src.api.cache.get_cache_initializer')
    async def test_prewarm_cache_initializer_not_initialized(self, mock_get_initializer):
        """测试缓存初始化器未初始化时执行预热"""
        mock_get_initializer.return_value = None

        request = CachePrewarmRequest(task_types=["predictions"])
        background_tasks = BackgroundTasks()

        with pytest.raises(HTTPException) as exc_info:
            await prewarm_cache(request, background_tasks)

        assert exc_info.value.status_code == 503
        assert "缓存初始化器未初始化" in str(exc_info.value.detail)


@pytest.mark.asyncio
class TestCacheOptimize:
    """测试缓存优化功能"""

    @patch('src.api.cache.get_cache_initializer')
    @patch('src.api.cache.execute_optimization_tasks')
    async def test_optimize_cache_success(self, mock_execute_tasks, mock_get_initializer):
        """测试成功执行缓存优化"""
        mock_initializer = MagicMock()
        mock_get_initializer.return_value = mock_initializer

        background_tasks = BackgroundTasks()
        result = await optimize_cache(background_tasks)

        assert isinstance(result, CacheOperationResponse)
        assert result.success is True
        assert "已启动缓存优化任务" in result.message
        # 验证后台任务被添加
        background_tasks.add_task.assert_called_once_with(mock_execute_tasks)

    @patch('src.api.cache.get_cache_initializer')
    async def test_optimize_cache_initializer_not_initialized(self, mock_get_initializer):
        """测试缓存初始化器未初始化时执行优化"""
        mock_get_initializer.return_value = None

        background_tasks = BackgroundTasks()

        with pytest.raises(HTTPException) as exc_info:
            await optimize_cache(background_tasks)

        assert exc_info.value.status_code == 503
        assert "缓存初始化器未初始化" in str(exc_info.value.detail)

    @patch('src.api.cache.get_cache_initializer')
    async def test_optimize_cache_error(self, mock_get_initializer):
        """测试缓存优化时发生错误"""
        mock_get_initializer.side_effect = Exception("Redis connection failed")

        background_tasks = BackgroundTasks()

        with pytest.raises(HTTPException) as exc_info:
            await optimize_cache(background_tasks)

        assert exc_info.value.status_code == 500
        assert "缓存优化失败" in str(exc_info.value.detail)


class TestCacheModels:
    """测试缓存相关模型"""

    def test_cache_stats_response_creation(self):
        """测试CacheStatsResponse创建"""
        stats = CacheStatsResponse(
            l1_cache={"hit_rate": 0.8},
            l2_cache={"hit_rate": 0.6},
            overall={"total_hit_rate": 0.7},
            config={"ttl": 3600}
        )

        assert stats.l1_cache["hit_rate"] == 0.8
        assert stats.l2_cache["hit_rate"] == 0.6
        assert stats.overall["total_hit_rate"] == 0.7
        assert stats.config["ttl"] == 3600

    def test_cache_operation_response_creation(self):
        """测试CacheOperationResponse创建"""
        # 成功响应
        response = CacheOperationResponse(
            success=True,
            message="操作成功",
            data={"cleared_keys": ["key1"]}
        )
        assert response.success is True
        assert response.data["cleared_keys"] == ["key1"]

        # 失败响应
        response2 = CacheOperationResponse(
            success=False,
            message="操作失败"
        )
        assert response2.success is False
        assert response2.data is None

    def test_cache_key_request_creation(self):
        """测试CacheKeyRequest创建"""
        # 只有键
        request = CacheKeyRequest(keys=["key1", "key2"])
        assert request.keys == ["key1", "key2"]
        assert request.pattern is None

        # 带模式
        request2 = CacheKeyRequest(keys=["key1"], pattern="test:*")
        assert request2.pattern == "test:*"

    def test_cache_prewarm_request_creation(self):
        """测试CachePrewarmRequest创建"""
        # 基本请求
        request = CachePrewarmRequest(task_types=["predictions"])
        assert request.task_types == ["predictions"]
        assert request.force is False

        # 强制预热
        request2 = CachePrewarmRequest(
            task_types=["teams"],
            force=True
        )
        assert request2.force is True


class TestCacheRouter:
    """测试缓存路由配置"""

    def test_router_exists(self):
        """测试路由器存在"""
        assert router is not None
        assert hasattr(router, 'routes')

    def test_router_prefix(self):
        """测试路由前缀"""
        assert router.prefix == "/cache"

    def test_router_tags(self):
        """测试路由标签"""
        assert "缓存" in router.tags

    def test_router_has_endpoints(self):
        """测试路由器有端点"""
        route_count = len(list(router.routes))
        assert route_count > 0

        # 检查关键路径存在
        route_paths = [route.path for route in router.routes]
        expected_paths = [
            "/stats",
            "/clear",
            "/prewarm",
            "/optimize"
        ]

        for path in expected_paths:
            assert any(path in route_path for route_path in route_paths), f"路径 {path} 不存在"


@pytest.mark.asyncio
class TestCacheEdgeCases:
    """测试缓存边界情况"""

    @patch('src.api.cache.get_cache_manager')
    async def test_clear_cache_manager_not_initialized(self, mock_get_manager):
        """测试缓存管理器未初始化时清理缓存"""
        mock_get_manager.return_value = None

        request = CacheKeyRequest(keys=["key1"])
        background_tasks = BackgroundTasks()

        with pytest.raises(HTTPException) as exc_info:
            await clear_cache(request, background_tasks)

        assert exc_info.value.status_code == 503
        assert "缓存管理器未初始化" in str(exc_info.value.detail)

    @patch('src.api.cache.get_cache_manager')
    async def test_clear_cache_all_keys(self, mock_get_manager):
        """测试清理所有缓存键"""
        manager = MagicMock()
        manager.delete = AsyncMock(return_value=True)
        mock_get_manager.return_value = manager

        request = CacheKeyRequest(keys=["*"])
        background_tasks = BackgroundTasks()

        result = await clear_cache(request, background_tasks)

        assert result.success is True

    @patch('src.api.cache.get_cache_initializer')
    @patch('src.api.cache.execute_prewarm_tasks')
    async def test_prewarm_cache_all_tasks(self, mock_execute_tasks, mock_get_initializer):
        """测试预热所有任务类型"""
        mock_initializer = MagicMock()
        mock_get_initializer.return_value = mock_initializer

        all_tasks = ["predictions", "teams", "matches", "leagues", "players"]
        request = CachePrewarmRequest(task_types=all_tasks, force=True)
        background_tasks = BackgroundTasks()

        result = await prewarm_cache(request, background_tasks)

        assert result.success is True
        assert len(result.data["task_types"]) == len(all_tasks)
        assert result.data["force"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])