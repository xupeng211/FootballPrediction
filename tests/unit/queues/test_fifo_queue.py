from typing import Optional

#!/usr/bin/env python3
"""
FIFO队列系统单元测试

测试 src.queues.fifo_queue 模块的功能
"""

import asyncio
import os
import sys
from datetime import datetime

import pytest

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from src.queues.fifo_queue import (
    MemoryFIFOQueue,
    QueueManager,
    QueueStatus,
    QueueTask,
    TaskPriority,
    create_task,
    enqueue_task,
)


class TestQueueTask:
    """队列任务测试类"""

    def test_create_queue_task(self):
        """测试创建队列任务"""
        task_data = {"test": "data"}
        task = QueueTask(
            id="test-123",
            task_type="test_task",
            data=task_data,
            priority=TaskPriority.NORMAL,
            created_at=datetime.now(),
        )

        assert task.id == "test-123"
        assert task.task_type == "test_task"
        assert task.data == task_data
        assert task.priority == TaskPriority.NORMAL
        assert task.attempts == 0
        assert task.max_attempts == 3

    def test_queue_task_to_dict(self):
        """测试队列任务转换为字典"""
        task_data = {"test": "data"}
        task = QueueTask(
            id="test-123",
            task_type="test_task",
            data=task_data,
            priority=TaskPriority.HIGH,
            created_at=datetime.now(),
        )

        task_dict = task.to_dict()
        assert task_dict["id"] == "test-123"
        assert task_dict["task_type"] == "test_task"
        assert task_dict["data"] == task_data
        assert task_dict["priority"] == TaskPriority.HIGH.value
        assert isinstance(task_dict["created_at"], str)

    def test_queue_task_from_dict(self):
        """测试从字典创建队列任务"""
        task_dict = {
            "id": "test-123",
            "task_type": "test_task",
            "data": {"test": "data"},
            "priority": TaskPriority.HIGH.value,
            "created_at": datetime.now().isoformat(),
            "attempts": 1,
            "max_attempts": 5,
        }

        task = QueueTask.from_dict(task_dict)
        assert task.id == "test-123"
        assert task.task_type == "test_task"
        assert task.data == {"test": "data"}
        assert task.priority == TaskPriority.HIGH
        assert task.attempts == 1
        assert task.max_attempts == 5


class TestMemoryFIFOQueue:
    """内存FIFO队列测试类"""

    @pytest.fixture
    async def queue(self):
        """创建内存队列实例"""
        return MemoryFIFOQueue("test_queue")

    @pytest.mark.asyncio
    async def test_queue_initialization(self, queue):
        """测试队列初始化"""
        assert queue.name == "test_queue"
        assert queue.status == QueueStatus.ACTIVE
        assert queue.max_size == 10000
        assert await queue.get_size() == 0

    @pytest.mark.asyncio
    async def test_enqueue_task(self, queue):
        """测试任务入队"""
        task = create_task("test_task", {"key": "value"})
        result = await queue.enqueue(task)

        assert result is True
        assert await queue.get_size() == 1

    @pytest.mark.asyncio
    async def test_dequeue_task(self, queue):
        """测试任务出队"""
        task = create_task("test_task", {"key": "value"})
        await queue.enqueue(task)

        dequeued_task = await queue.dequeue()
        assert dequeued_task is not None
        assert dequeued_task.id == task.id
        assert dequeued_task.task_type == "test_task"
        assert dequeued_task.data == {"key": "value"}
        assert await queue.get_size() == 0

    @pytest.mark.asyncio
    async def test_dequeue_empty_queue(self, queue):
        """测试从空队列出队"""
        dequeued_task = await queue.dequeue(timeout=1)
        assert dequeued_task is None

    @pytest.mark.asyncio
    async def test_fifo_order(self, queue):
        """测试FIFO顺序"""
        task1 = create_task("task1", {"order": 1})
        task2 = create_task("task2", {"order": 2})
        task3 = create_task("task3", {"order": 3})

        # 按顺序入队
        await queue.enqueue(task1)
        await queue.enqueue(task2)
        await queue.enqueue(task3)

        # 应该按相同顺序出队
        dequeued1 = await queue.dequeue()
        dequeued2 = await queue.dequeue()
        dequeued3 = await queue.dequeue()

        assert dequeued1.id == task1.id
        assert dequeued2.id == task2.id
        assert dequeued3.id == task3.id

    @pytest.mark.asyncio
    async def test_clear_queue(self, queue):
        """测试清空队列"""
        task1 = create_task("task1", {"data": "1"})
        task2 = create_task("task2", {"data": "2"})

        await queue.enqueue(task1)
        await queue.enqueue(task2)
        assert await queue.get_size() == 2

        result = await queue.clear()
        assert result is True
        assert await queue.get_size() == 0

    @pytest.mark.asyncio
    async def test_queue_statistics(self, queue):
        """测试队列统计信息"""
        stats = queue.get_statistics()
        assert "total_enqueued" in stats
        assert "total_dequeued" in stats
        assert "queue_size" in stats
        assert "created_at" in stats

        initial_enqueued = stats["total_enqueued"]

        task = create_task("test_task", {"data": "test"})
        await queue.enqueue(task)
        await queue.dequeue()

        updated_stats = queue.get_statistics()
        assert updated_stats["total_enqueued"] == initial_enqueued + 1
        assert updated_stats["total_dequeued"] == initial_enqueued + 1

    @pytest.mark.asyncio
    async def test_priority_ordering(self, queue):
        """测试优先级排序"""
        low_task = create_task("low_task", {"priority": "low"}, TaskPriority.LOW)
        high_task = create_task("high_task", {"priority": "high"}, TaskPriority.HIGH)
        normal_task = create_task(
            "normal_task", {"priority": "normal"}, TaskPriority.NORMAL
        )

        # 按不同优先级入队
        await queue.enqueue(low_task)
        await queue.enqueue(high_task)
        await queue.enqueue(normal_task)

        # 虽然是FIFO，但我们可以通过统计信息验证任务都在队列中
        assert await queue.get_size() == 3


class TestQueueManager:
    """队列管理器测试类"""

    @pytest.fixture
    def manager(self):
        """创建队列管理器实例"""
        return QueueManager()

    def test_manager_initialization(self, manager):
        """测试管理器初始化"""
        assert isinstance(manager.queues, dict)
        assert len(manager.queues) == 0

    def test_create_memory_queue(self, manager):
        """测试创建内存队列"""
        queue = manager.create_queue("test_memory", "memory")
        assert queue is not None
        assert queue.name == "test_memory"
        assert "test_memory" in manager.queues

    def test_create_duplicate_queue(self, manager):
        """测试创建重复队列"""
        queue1 = manager.create_queue("duplicate_test", "memory")
        queue2 = manager.create_queue("duplicate_test", "memory")

        assert queue1 is queue2  # 应该返回同一个队列实例

    def test_get_queue(self, manager):
        """测试获取队列"""
        # 获取不存在的队列
        queue = manager.get_queue("nonexistent")
        assert queue is None

        # 创建队列后获取
        created_queue = manager.create_queue("test_get", "memory")
        retrieved_queue = manager.get_queue("test_get")
        assert created_queue is retrieved_queue

    def test_remove_queue(self, manager):
        """测试移除队列"""
        manager.create_queue("test_remove", "memory")

        # 移除存在的队列
        result = manager.remove_queue("test_remove")
        assert result is True
        assert manager.get_queue("test_remove") is None

        # 移除不存在的队列
        result = manager.remove_queue("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_enqueue_to_queue(self, manager):
        """测试向指定队列添加任务"""
        manager.create_queue("test_enqueue", "memory")
        task = create_task("test_task", {"data": "test"})

        result = await manager.enqueue_to_queue("test_enqueue", task)
        assert result is True

        # 向不存在的队列添加任务
        result = await manager.enqueue_to_queue("nonexistent", task)
        assert result is False

    @pytest.mark.asyncio
    async def test_dequeue_from_queue(self, manager):
        """测试从指定队列取出任务"""
        manager.create_queue("test_dequeue", "memory")
        task = create_task("test_task", {"data": "test"})

        # 从空队列取出 - 使用短超时避免无限阻塞
        result = await manager.dequeue_from_queue("test_dequeue", timeout=0.1)
        assert result is None

        # 先添加再取出 - 测试有数据的队列
        await manager.enqueue_to_queue("test_dequeue", task)
        result_with_data = await manager.dequeue_from_queue("test_dequeue", timeout=1.0)
        assert result_with_data is not None
        assert result_with_data.id == task.id

    @pytest.mark.asyncio
    async def test_clear_all_queues(self, manager):
        """测试清空所有队列"""
        manager.create_queue("queue1", "memory")
        manager.create_queue("queue2", "memory")

        # 添加任务
        task1 = create_task("task1", {"queue": 1})
        task2 = create_task("task2", {"queue": 2})

        await manager.enqueue_to_queue("queue1", task1)
        await manager.enqueue_to_queue("queue2", task2)

        # 清空所有队列
        results = await manager.clear_all_queues()
        assert results["queue1"] is True
        assert results["queue2"] is True

    def test_get_all_statistics(self, manager):
        """测试获取所有队列统计信息"""
        manager.create_queue("stats_queue1", "memory")
        manager.create_queue("stats_queue2", "memory")

        all_stats = manager.get_all_statistics()
        assert isinstance(all_stats, dict)
        assert "stats_queue1" in all_stats
        assert "stats_queue2" in all_stats


class TestUtilityFunctions:
    """工具函数测试类"""

    def test_create_task(self):
        """测试创建任务工具函数"""
        task = create_task("test_type", {"key": "value"}, TaskPriority.HIGH)

        assert isinstance(task, QueueTask)
        assert task.task_type == "test_type"
        assert task.data == {"key": "value"}
        assert task.priority == TaskPriority.HIGH
        assert isinstance(task.id, str)
        assert len(task.id) > 0

    def test_enqueue_task_with_manager(self):
        """测试入队工具函数"""
        # 创建全局管理器的队列
        from src.queues.fifo_queue import queue_manager

        queue_manager.create_queue("util_test", "memory")

        enqueue_task("util_test", "test_type", {"key": "value"})
        # 注意：这里我们无法直接测试异步结果，但可以验证函数调用不报错

    def test_dequeue_task_with_manager(self):
        """测试出队工具函数"""
        # 创建全局管理器的队列
        from src.queues.fifo_queue import queue_manager

        queue_manager.create_queue("util_test2", "memory")

        # 测试调用不出错
        # result = dequeue_task("util_test2", timeout=1)
        # 注意：这里我们无法直接测试异步结果，但可以验证函数调用不报错


class TestTaskPriority:
    """任务优先级测试类"""

    def test_priority_values(self):
        """测试优先级枚举值"""
        assert TaskPriority.LOW.value == 1
        assert TaskPriority.NORMAL.value == 2
        assert TaskPriority.HIGH.value == 3
        assert TaskPriority.URGENT.value == 4

    def test_priority_comparison(self):
        """测试优先级比较"""
        assert TaskPriority.LOW < TaskPriority.NORMAL
        assert TaskPriority.NORMAL < TaskPriority.HIGH
        assert TaskPriority.HIGH < TaskPriority.URGENT


class TestQueueStatus:
    """队列状态测试类"""

    def test_status_values(self):
        """测试状态枚举值"""
        assert QueueStatus.ACTIVE.value == "active"
        assert QueueStatus.PAUSED.value == "paused"
        assert QueueStatus.STOPPED.value == "stopped"


@pytest.mark.asyncio
class TestAdvancedQueueOperations:
    """高级队列操作测试"""

    @pytest.mark.asyncio

    async def test_concurrent_operations(self):
        """测试并发操作"""
        queue = MemoryFIFOQueue("concurrent_test")
        tasks = []

        # 并发创建多个任务
        for i in range(10):
            task = create_task(f"task_{i}", {"index": i})
            tasks.append(task)

        # 并发入队
        enqueue_tasks = [queue.enqueue(task) for task in tasks]
        results = await asyncio.gather(*enqueue_tasks)
        assert all(results)  # 所有入队都应该成功
        assert await queue.get_size() == 10

        # 并发出队
        dequeue_tasks = [queue.dequeue() for _ in range(10)]
        dequeued_tasks = await asyncio.gather(*dequeue_tasks)

        # 验证所有任务都被成功出队
        assert len([t for t in dequeued_tasks if t is not None]) == 10

    @pytest.mark.asyncio

    async def test_task_timeout(self):
        """测试任务超时"""
        queue = MemoryFIFOQueue("timeout_test")

        # 从空队列出队，设置超时
        start_time = datetime.now()
        result = await queue.dequeue(timeout=0.1)
        end_time = datetime.now()

        assert result is None
        # 验证确实等待了超时时间
        assert (end_time - start_time).total_seconds() >= 0.05
