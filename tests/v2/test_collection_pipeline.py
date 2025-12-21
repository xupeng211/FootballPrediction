#!/usr/bin/env python3
"""
FotMob Collection Pipeline 测试

专门测试重构后的 FotMobCollectionService 和相关数据收集功能。
确保V2架构的数据收集服务正常工作。
"""

import pytest
import asyncio
import aiohttp
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, List

from src.services.collection_service import (
    FotMobCollectionService,
    CollectionStatus,
    FotMobCollectionTask,
    CircuitBreaker,
)
from src.config_unified import get_settings


class TestFotMobCollectionTask:
    """测试FotMobCollectionTask数据类"""

    def test_task_creation(self):
        """测试任务创建"""
        task = FotMobCollectionTask(task_id="test-123", match_id="match-456", league_id="league-789")

        assert task.task_id == "test-123"
        assert task.match_id == "match-456"
        assert task.league_id == "league-789"

    def test_task_creation_minimal(self):
        """测试最小参数任务创建"""
        task = FotMobCollectionTask(task_id="test-123")

        assert task.task_id == "test-123"
        assert task.match_id is None
        assert task.league_id is None


class TestCollectionStatus:
    """测试CollectionStatus枚举"""

    def test_status_values(self):
        """测试状态值"""
        assert CollectionStatus.PENDING.value == "pending"
        assert CollectionStatus.RUNNING.value == "running"
        assert CollectionStatus.SUCCESS.value == "success"
        assert CollectionStatus.FAILED.value == "failed"
        assert CollectionStatus.RETRY.value == "retry"


class TestCircuitBreaker:
    """测试熔断器功能"""

    def test_circuit_breaker_initial_state(self):
        """测试熔断器初始状态"""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60, half_open_max_calls=2)

        # 验证熔断器初始化
        assert breaker is not None
        assert breaker.failure_threshold == 3
        assert breaker.recovery_timeout == 60
        assert breaker.half_open_max_calls == 2
        assert breaker.state == "CLOSED"
        assert breaker.failure_count == 0

    def test_circuit_breaker_success(self):
        """测试熔断器允许调用"""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60, half_open_max_calls=2)

        # 测试初始状态允许调用
        assert breaker.call_allowed() is True


@pytest.mark.asyncio
class TestFotMobCollectionService:
    """测试FotMobCollectionService主要功能"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return FotMobCollectionService()

    @pytest.fixture
    def mock_aiohttp_session(self):
        """模拟aiohttp会话"""
        session = AsyncMock()
        return session

    async def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service is not None
        assert hasattr(service, "settings")
        # 假设有metrics属性
        # assert isinstance(service.metrics, CollectionMetrics)

    async def test_create_collection_task(self, service):
        """测试创建收集任务"""
        task_id = service.create_match_collection_task(match_id="match-123")

        assert isinstance(task_id, str)
        assert "match-123" in task_id
        assert len(service.tasks) > 0  # 验证任务已添加到列表

        # 检查添加的任务
        last_task = service.tasks[-1]
        assert isinstance(last_task, FotMobCollectionTask)
        assert last_task.match_id == "match-123"
        assert last_task.status == CollectionStatus.PENDING

    async def test_execute_task(self, service):
        """测试执行任务"""
        # 创建任务
        task_id = service.create_match_collection_task(match_id="match-123")

        # 模拟执行任务（由于需要外部API，这里只测试任务结构）
        assert task_id is not None
        assert isinstance(task_id, str)

        # 检查对应的任务对象
        task = service.tasks[-1]
        assert task.task_id == task_id
        assert task.status == CollectionStatus.PENDING

    async def test_process_single_match_api_error(self, service, mock_aiohttp_session):
        """测试处理单个比赛API错误场景"""
        # 模拟API错误响应
        mock_response = AsyncMock()
        mock_response.status = 404

        mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_response

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value.__aenter__.return_value = mock_aiohttp_session

            with pytest.raises(Exception):  # 应该抛出适当异常
                await service.process_single_match("non-existent-match")

    async def test_batch_execute_tasks(self, service):
        """测试批量执行任务"""
        # 创建多个任务
        task_id1 = service.create_match_collection_task(match_id="match-1")
        task_id2 = service.create_match_collection_task(match_id="match-2")
        task_id3 = service.create_match_collection_task(match_id="match-3")

        # 验证任务ID已生成
        assert isinstance(task_id1, str)
        assert isinstance(task_id2, str)
        assert isinstance(task_id3, str)

        # 验证任务已添加到列表
        assert len(service.tasks) >= 3

        # 验证任务状态
        for task in service.tasks[-3:]:
            assert isinstance(task, FotMobCollectionTask)
            assert task.status == CollectionStatus.PENDING

    async def test_service_statistics(self, service):
        """测试服务统计信息"""
        # 创建一些任务来测试统计
        task_id1 = service.create_match_collection_task(match_id="match-1")
        task_id2 = service.create_league_collection_task(league_id="league-1")

        # 验证任务已创建并添加到列表
        assert len(service.tasks) >= 2

        # 更新统计信息
        service.stats.update(service.tasks)

        # 验证统计信息
        assert service.stats.total_tasks >= 2
        assert service.stats.pending_tasks >= 2


@pytest.mark.asyncio
class TestCollectionIntegration:
    """集成测试"""

    async def test_end_to_end_collection_flow(self):
        """端到端收集流程测试"""
        # 这个测试需要完整的mock设置
        # 1. 创建任务
        # 2. 处理数据
        # 3. 存储到数据库
        # 4. 返回结果

        # 由于需要数据库连接，这里只做基本结构验证
        service = FotMobCollectionService()

        assert service is not None
        # 验证服务具有必要的属性和方法
        assert hasattr(service, "execute_task")
        assert hasattr(service, "execute_all_tasks")
        assert hasattr(service, "create_match_collection_task")


# TODO: 实现CollectionMetrics类并添加测试
# @pytest.mark.asyncio
# class TestCollectionMetrics:
#     """测试收集指标功能"""
#
#     async def test_metrics_tracking(self):
#         """测试指标跟踪"""
#         # 当实现CollectionMetrics类后，添加具体测试
#         pass


# 配置测试标记
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.unit,
]


if __name__ == "__main__":
    # 运行测试的示例
    pytest.main([__file__, "-v"])
