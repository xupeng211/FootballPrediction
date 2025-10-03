import os
"""
缓存API端点测试 / Tests for Cache API Endpoints

测试覆盖src/api/cache.py中的API端点：
- GET /cache/stats - 获取缓存统计
- POST /cache/clear - 清理缓存
- POST /cache/prewarm - 缓存预热
- POST /cache/optimize - 优化缓存
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import BackgroundTasks
from datetime import datetime

from src.api.cache import router, CacheStatsResponse, CacheOperationResponse


class TestCacheAPIEndpoints:
    """缓存API端点测试类"""

    @pytest.fixture
    def mock_cache_manager(self):
        """模拟缓存管理器"""
        manager = MagicMock()
        manager.get_stats.return_value = {
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
        manager.delete = AsyncMock(return_value=True)
        return manager

    @pytest.fixture
    def mock_cache_initializer(self):
        """模拟缓存初始化器"""
        initializer = MagicMock()
        return initializer

    @pytest.fixture
    def mock_background_tasks(self):
        """模拟后台任务"""
        tasks = MagicMock()
        tasks.add_task = MagicMock()
        return tasks

    @pytest.mark.asyncio
    @patch('src.api.cache.get_cache_manager')
    async def test_get_cache_stats_success(self, mock_get_manager, mock_cache_manager):
        """测试成功获取缓存统计"""
        # 设置模拟
        mock_get_manager.return_value = mock_cache_manager

        # 执行测试
        from src.api.cache import get_cache_stats
        response = await get_cache_stats()

        # 验证结果
        assert isinstance(response, CacheStatsResponse)
        assert response.l1_cache["hit_rate"] == 0.85
        assert response.l2_cache["hit_rate"] == 0.65
        assert response.overall["total_hit_rate"] == 0.75
        assert "ttl" in response.config

    @pytest.mark.asyncio
    @patch('src.api.cache.get_cache_manager')
    async def test_get_cache_stats_manager_not_initialized(self, mock_get_manager):
        """测试缓存管理器未初始化"""
        from src.api.cache import get_cache_stats
        from fastapi import HTTPException

        # 设置模拟
        mock_get_manager.return_value = None

        # 执行测试并验证异常
        with pytest.raises(HTTPException) as exc_info:
            await get_cache_stats()

        assert exc_info.value.status_code == 503
        assert "缓存管理器未初始化" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch('src.api.cache.get_cache_manager')
    async def test_get_cache_stats_error(self, mock_get_manager):
        """测试获取缓存统计时发生错误"""
        from src.api.cache import get_cache_stats
        from fastapi import HTTPException

        # 设置模拟
        mock_get_manager.side_effect = Exception("Database connection failed")

        # 执行测试并验证异常
        with pytest.raises(HTTPException) as exc_info:
            await get_cache_stats()

        assert exc_info.value.status_code == 500
        assert "获取缓存统计失败" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch('src.api.cache.get_cache_manager')
    @patch('src.api.cache.clear_cache_by_pattern')
    async def test_clear_cache_with_keys(
        self, mock_clear_pattern, mock_get_manager,
        mock_cache_manager, mock_background_tasks
    ):
        """测试清理指定键的缓存"""
        # 设置模拟
        mock_get_manager.return_value = mock_cache_manager

        # 创建请求
        from src.api.cache import CacheKeyRequest
        request = CacheKeyRequest(keys=["key1", "key2", "key3"])

        # 执行测试
        from src.api.cache import clear_cache
        response = await clear_cache(request, mock_background_tasks)

        # 验证结果
        assert isinstance(response, CacheOperationResponse)
        assert response.success is True
        assert "成功清理" in response.message
        assert len(response.data["cleared_keys"]) == 3
        assert mock_cache_manager.delete.call_count == 3

    @pytest.mark.asyncio
    @patch('src.api.cache.get_cache_manager')
    @patch('src.api.cache.clear_cache_by_pattern')
    async def test_clear_cache_with_pattern(
        self, mock_clear_pattern, mock_get_manager,
        mock_cache_manager, mock_background_tasks
    ):
        """测试使用模式清理缓存"""
        # 设置模拟
        mock_get_manager.return_value = mock_cache_manager

        # 创建请求
        from src.api.cache import CacheKeyRequest
        request = CacheKeyRequest(keys=[], pattern = os.getenv("TEST_CACHE_API_ENDPOINTS_PATTERN_156"))

        # 执行测试
        from src.api.cache import clear_cache
        response = await clear_cache(request, mock_background_tasks)

        # 验证结果
        assert isinstance(response, CacheOperationResponse)
        assert response.success is True
        # 验证后台任务被添加
        mock_background_tasks.add_task.assert_called_once_with(
            mock_clear_pattern,
            "test:*"
        )

    @pytest.mark.asyncio
    @patch('src.api.cache.get_cache_manager')
    async def test_clear_cache_manager_not_initialized(
        self, mock_get_manager, mock_background_tasks
    ):
        """测试缓存管理器未初始化时清理缓存"""
        from src.api.cache import clear_cache
        from fastapi import HTTPException

        # 设置模拟
        mock_get_manager.return_value = None

        # 创建请求
        from src.api.cache import CacheKeyRequest
        request = CacheKeyRequest(keys=["key1"])

        # 执行测试并验证异常
        with pytest.raises(HTTPException) as exc_info:
            await clear_cache(request, mock_background_tasks)

        assert exc_info.value.status_code == 503
        assert "缓存管理器未初始化" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch('src.api.cache.get_cache_initializer')
    @patch('src.api.cache.execute_prewarm_tasks')
    async def test_prewarm_cache_success(
        self, mock_execute_tasks, mock_get_initializer,
        mock_cache_initializer, mock_background_tasks
    ):
        """测试成功执行缓存预热"""
        # 设置模拟
        mock_get_initializer.return_value = mock_cache_initializer

        # 创建请求
        from src.api.cache import CachePrewarmRequest
        request = CachePrewarmRequest(
            task_types=["predictions", "teams"],
            force=False
        )

        # 执行测试
        from src.api.cache import prewarm_cache
        response = await prewarm_cache(request, mock_background_tasks)

        # 验证结果
        assert isinstance(response, CacheOperationResponse)
        assert response.success is True
        assert "已启动 2 个预热任务" in response.message
        assert response.data["task_types"] == ["predictions", "teams"]
        # 验证后台任务被添加
        mock_background_tasks.add_task.assert_called_once_with(
            mock_execute_tasks,
            ["predictions", "teams"],
            False
        )

    @pytest.mark.asyncio
    @patch('src.api.cache.get_cache_initializer')
    async def test_prewarm_cache_invalid_task_types(
        self, mock_get_initializer, mock_background_tasks
    ):
        """测试缓存预热时任务类型无效"""
        from src.api.cache import prewarm_cache
        from fastapi import HTTPException

        # 设置模拟
        mock_get_initializer.return_value = MagicMock()

        # 创建请求（包含无效任务类型）
        from src.api.cache import CachePrewarmRequest
        request = CachePrewarmRequest(
            task_types=["predictions", "invalid_task"],
            force=False
        )

        # 执行测试并验证异常
        with pytest.raises(HTTPException) as exc_info:
            await prewarm_cache(request, mock_background_tasks)

        assert exc_info.value.status_code == 400
        assert "无效的任务类型: invalid_task" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch('src.api.cache.get_cache_initializer')
    async def test_prewarm_cache_initializer_not_initialized(
        self, mock_get_initializer, mock_background_tasks
    ):
        """测试缓存初始化器未初始化时执行预热"""
        from src.api.cache import prewarm_cache
        from fastapi import HTTPException

        # 设置模拟
        mock_get_initializer.return_value = None

        # 创建请求
        from src.api.cache import CachePrewarmRequest
        request = CachePrewarmRequest(task_types=["predictions"])

        # 执行测试并验证异常
        with pytest.raises(HTTPException) as exc_info:
            await prewarm_cache(request, mock_background_tasks)

        assert exc_info.value.status_code == 503
        assert "缓存初始化器未初始化" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch('src.api.cache.get_cache_initializer')
    @patch('src.api.cache.execute_optimization_tasks')
    async def test_optimize_cache_success(
        self, mock_execute_tasks, mock_get_initializer,
        mock_cache_initializer, mock_background_tasks
    ):
        """测试成功执行缓存优化"""
        # 设置模拟
        mock_get_initializer.return_value = mock_cache_initializer

        # 执行测试
        from src.api.cache import optimize_cache
        response = await optimize_cache(mock_background_tasks)

        # 验证结果
        assert isinstance(response, CacheOperationResponse)
        assert response.success is True
        assert "已启动缓存优化任务" in response.message
        # 验证后台任务被添加
        mock_background_tasks.add_task.assert_called_once_with(
            mock_execute_tasks
        )

    @pytest.mark.asyncio
    @patch('src.api.cache.get_cache_initializer')
    async def test_optimize_cache_initializer_not_initialized(
        self, mock_get_initializer, mock_background_tasks
    ):
        """测试缓存初始化器未初始化时执行优化"""
        from src.api.cache import optimize_cache
        from fastapi import HTTPException

        # 设置模拟
        mock_get_initializer.return_value = None

        # 执行测试并验证异常
        with pytest.raises(HTTPException) as exc_info:
            await optimize_cache(mock_background_tasks)

        assert exc_info.value.status_code == 503
        assert "缓存初始化器未初始化" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch('src.api.cache.get_cache_initializer')
    async def test_optimize_cache_error(
        self, mock_get_initializer, mock_background_tasks
    ):
        """测试缓存优化时发生错误"""
        from src.api.cache import optimize_cache
        from fastapi import HTTPException

        # 设置模拟
        mock_get_initializer.side_effect = Exception("Redis connection failed")

        # 执行测试并验证异常
        with pytest.raises(HTTPException) as exc_info:
            await optimize_cache(mock_background_tasks)

        assert exc_info.value.status_code == 500
        assert "缓存优化失败" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch('src.api.cache.get_cache_manager')
    async def test_clear_cache_partial_failure(
        self, mock_get_manager, mock_background_tasks
    ):
        """测试部分缓存清理失败"""
        # 设置模拟 - 第三个键删除失败
        manager = MagicMock()
        manager.delete = AsyncMock(side_effect=[True, True, False])
        mock_get_manager.return_value = manager

        # 创建请求
        from src.api.cache import CacheKeyRequest
        request = CacheKeyRequest(keys=["key1", "key2", "key3"])

        # 执行测试
        from src.api.cache import clear_cache
        response = await clear_cache(request, mock_background_tasks)

        # 验证结果 - 应该只返回成功清理的键
        assert response.success is True
        assert len(response.data["cleared_keys"]) == 2
        assert "key3" not in response.data["cleared_keys"]

    @pytest.mark.asyncio
    @patch('src.api.cache.get_cache_manager')
    async def test_clear_cache_with_empty_request(
        self, mock_get_manager, mock_cache_manager, mock_background_tasks
    ):
        """测试空请求清理缓存"""
        # 设置模拟
        mock_get_manager.return_value = mock_cache_manager

        # 创建空请求
        from src.api.cache import CacheKeyRequest
        request = CacheKeyRequest(keys=[], pattern=None)

        # 执行测试
        from src.api.cache import clear_cache
        response = await clear_cache(request, mock_background_tasks)

        # 验证结果
        assert response.success is True
        assert len(response.data["cleared_keys"]) == 0

    def test_cache_key_request_model(self):
        """测试缓存键请求模型"""
        from src.api.cache import CacheKeyRequest

        # 测试只有键
        request = CacheKeyRequest(keys=["key1", "key2"])
        assert request.keys == ["key1", "key2"]
        assert request.pattern is None

        # 测试有键和模式
        request = CacheKeyRequest(keys=["key1"], pattern = os.getenv("TEST_CACHE_API_ENDPOINTS_PATTERN_156"))
        assert request.pattern == "test:*"

    def test_cache_prewarm_request_model(self):
        """测试缓存预热请求模型"""
        from src.api.cache import CachePrewarmRequest

        # 测试基本请求
        request = CachePrewarmRequest(task_types=["predictions"])
        assert request.task_types == ["predictions"]
        assert request.force is False

        # 测试强制预热
        request = CachePrewarmRequest(
            task_types=["teams", "hot_matches"],
            force=True
        )
        assert request.force is True

    def test_cache_stats_response_model(self):
        """测试缓存统计响应模型"""
        from src.api.cache import CacheStatsResponse

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

    def test_cache_operation_response_model(self):
        """测试缓存操作响应模型"""
        from src.api.cache import CacheOperationResponse

        # 成功响应
        response = CacheOperationResponse(
            success=True,
            message="操作成功",
            data={"cleared_keys": ["key1"]}
        )
        assert response.success is True
        assert response.data["cleared_keys"] == ["key1"]

        # 失败响应
        response = CacheOperationResponse(
            success=False,
            message="操作失败"
        )
        assert response.success is False
        assert response.data is None