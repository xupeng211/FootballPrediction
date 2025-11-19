"""FIFO队列系统实现.

提供先进先出的任务队列管理功能，支持：
- Redis队列支持
- 内存队列支持
- 任务优先级管理
- 队列监控和统计
"""

import asyncio
import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class QueueStatus(Enum):
    """队列状态枚举."""

    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"


class TaskPriority(Enum):
    """任务优先级枚举."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class QueueTask:
    """队列任务数据类."""

    id: str
    task_type: str
    data: dict[str, Any]
    priority: TaskPriority
    created_at: datetime
    attempts: int = 0
    max_attempts: int = 3
    scheduled_at: datetime | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["scheduled_at"] = (
            self.scheduled_at.isoformat() if self.scheduled_at else None
        )
        data["priority"] = self.priority.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueueTask":
        """从字典创建任务."""
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data["scheduled_at"]:
            data["scheduled_at"] = datetime.fromisoformat(data["scheduled_at"])
        data["priority"] = TaskPriority(data["priority"])
        return cls(**data)


class FIFOQueue:
    """FIFO队列基类."""

    def __init__(self, name: str):
        self.name = name
        self.status = QueueStatus.ACTIVE
        self.statistics = {
            "total_enqueued": 0,
            "total_dequeued": 0,
            "total_failed": 0,
            "queue_size": 0,
            "created_at": datetime.now().isoformat(),
        }

    async def enqueue(self, task: QueueTask) -> bool:
        """将任务加入队列."""
        raise NotImplementedError

    async def dequeue(self, timeout: int | None = None) -> QueueTask | None:
        """从队列取出任务."""
        raise NotImplementedError

    async def get_size(self) -> int:
        """获取队列大小."""
        raise NotImplementedError

    async def clear(self) -> bool:
        """清空队列."""
        raise NotImplementedError

    def get_statistics(self) -> dict[str, Any]:
        """获取队列统计信息."""
        return self.statistics.copy()


class MemoryFIFOQueue(FIFOQueue):
    """内存FIFO队列实现."""

    def __init__(self, name: str, max_size: int = 10000):
        super().__init__(name)
        self.max_size = max_size
        self._queue = asyncio.Queue(maxsize=max_size)

    async def enqueue(self, task: QueueTask) -> bool:
        """将任务加入队列."""
        try:
            # 将任务序列化后放入队列
            task_data = task.to_dict()
            await self._queue.put(task_data)
            self.statistics["total_enqueued"] += 1
            self.statistics["queue_size"] = await self.get_size()
            logger.debug(f"任务 {task.id} 已加入队列 {self.name}")
            return True
        except asyncio.QueueFull:
            logger.warning(f"队列 {self.name} 已满，无法添加任务 {task.id}")
            return False
        except Exception as e:
            logger.error(f"队列 {self.name} 入队失败: {e}")
            return False

    async def dequeue(self, timeout: int | None = None) -> QueueTask | None:
        """从队列取出任务."""
        try:
            if timeout:
                task_data = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            else:
                task_data = await self._queue.get()

            task = QueueTask.from_dict(task_data)
            self.statistics["total_dequeued"] += 1
            self.statistics["queue_size"] = await self.get_size()
            logger.debug(f"任务 {task.id} 已从队列 {self.name} 取出")
            return task
        except TimeoutError:
            logger.debug(f"队列 {self.name} 在 {timeout} 秒内无任务")
            return None
        except Exception as e:
            logger.error(f"队列 {self.name} 出队失败: {e}")
            return None

    async def get_size(self) -> int:
        """获取队列大小."""
        return self._queue.qsize()

    async def clear(self) -> bool:
        """清空队列."""
        try:
            while not self._queue.empty():
                try:
                    # 尝试异步方式
                    await self._queue.get_nowait()
                except (TypeError, AttributeError):
                    # 如果不是异步队列，使用同步方式
                    self._queue.get_nowait()
            self.statistics["queue_size"] = 0
            logger.info(f"队列 {self.name} 已清空")
            return True
        except Exception as e:
            logger.error(f"清空队列 {self.name} 失败: {e}")
            return False


class RedisFIFOQueue(FIFOQueue):
    """Redis FIFO队列实现."""

    def __init__(self, name: str, redis_client=None, **redis_config):
        super().__init__(name)
        self.redis_client = redis_client
        self.redis_config = redis_config
        self.queue_key = f"fifo_queue:{name}"
        self.processing_key = f"processing:{name}"
        self.failed_key = f"failed:{name}"

    async def _get_redis_client(self):
        """获取Redis客户端."""
        if self.redis_client:
            return self.redis_client

        # 这里可以根据配置创建Redis客户端
        # 示例实现，实际使用时需要根据环境配置
        try:
            import redis.asyncio as redis

            self.redis_client = await redis.from_url(
                "redis://localhost:6379", encoding="utf-8", decode_responses=True
            )
            return self.redis_client
        except ImportError:
            logger.error("redis包未安装，无法使用Redis队列")
            return None
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            return None

    async def enqueue(self, task: QueueTask) -> bool:
        """将任务加入Redis队列."""
        try:
            redis = await self._get_redis_client()
            if not redis:
                logger.error("Redis客户端不可用")
                return False

            task_data = task.to_dict()
            await redis.lpush(self.queue_key, json.dumps(task_data))
            self.statistics["total_enqueued"] += 1
            self.statistics["queue_size"] = await self.get_size()
            logger.debug(f"任务 {task.id} 已加入Redis队列 {self.name}")
            return True
        except Exception as e:
            logger.error(f"Redis队列 {self.name} 入队失败: {e}")
            return False

    async def dequeue(self, timeout: int | None = None) -> QueueTask | None:
        """从Redis队列取出任务."""
        try:
            redis = await self._get_redis_client()
            if not redis:
                logger.error("Redis客户端不可用")
                return None

            # 原子操作：从队列取出并加入处理队列
            pipe = redis.pipeline()
            pipe.brpoplpush(self.queue_key, self.processing_key)
            pipe.llen(self.queue_key)

            if timeout:
                result = await asyncio.wait_for(pipe.execute(), timeout=timeout)
            else:
                result = await pipe.execute()

            if result and result[0]:
                task_data = json.loads(result[0])
                task = QueueTask.from_dict(task_data)
                self.statistics["total_dequeued"] += 1
                self.statistics["queue_size"] = result[1] if len(result) > 1 else 0
                logger.debug(f"任务 {task.id} 已从Redis队列 {self.name} 取出")
                return task
            else:
                logger.debug(f"Redis队列 {self.name} 在 {timeout} 秒内无任务")
                return None
        except TimeoutError:
            logger.debug(f"Redis队列 {self.name} 在 {timeout} 秒内无任务")
            return None
        except Exception as e:
            logger.error(f"Redis队列 {self.name} 出队失败: {e}")
            return None

    async def get_size(self) -> int:
        """获取Redis队列大小."""
        try:
            redis = await self._get_redis_client()
            if not redis:
                return 0
            size = await redis.llen(self.queue_key)
            return size
        except Exception as e:
            logger.error(f"获取Redis队列 {self.name} 大小失败: {e}")
            return 0

    async def clear(self) -> bool:
        """清空Redis队列."""
        try:
            redis = await self._get_redis_client()
            if not redis:
                return False

            pipe = redis.pipeline()
            pipe.delete(self.queue_key)
            pipe.delete(self.processing_key)
            pipe.delete(self.failed_key)
            await pipe.execute()

            self.statistics["queue_size"] = 0
            logger.info(f"Redis队列 {self.name} 已清空")
            return True
        except Exception as e:
            logger.error(f"清空Redis队列 {self.name} 失败: {e}")
            return False

    async def complete_task(self, task_id: str) -> bool:
        """标记任务完成，从处理队列移除."""
        try:
            redis = await self._get_redis_client()
            if not redis:
                return False

            # 从处理队列中移除
            keys = await redis.keys(f"{self.processing_key}:*")

            for key in keys:
                task_data = await redis.get(key)
                if task_data:
                    task = QueueTask.from_dict(json.loads(task_data))
                    if task.id == task_id:
                        await redis.delete(key)
                        logger.debug(f"任务 {task_id} 已标记完成")
                        return True

            return False
        except Exception as e:
            logger.error(f"标记任务 {task_id} 完成失败: {e}")
            return False

    async def fail_task(self, task_id: str, error_message: str = None) -> bool:
        """标记任务失败."""
        try:
            redis = await self._get_redis_client()
            if not redis:
                return False

            # 从处理队列中取出并加入失败队列
            keys = await redis.keys(f"{self.processing_key}:*")

            for key in keys:
                task_data = await redis.get(key)
                if task_data:
                    task = QueueTask.from_dict(json.loads(task_data))
                    if task.id == task_id:
                        task.attempts += 1

                        # 如果尝试次数未超限，重新加入队列
                        if task.attempts < task.max_attempts:
                            # 延迟重新入队
                            task.scheduled_at = datetime.now() + timedelta(minutes=5)
                            await redis.lpush(
                                self.queue_key, json.dumps(task.to_dict())
                            )
                            await redis.delete(key)
                            logger.info(
                                f"任务 {task_id} 重新入队，尝试次数: {task.attempts}"
                            )
                        else:
                            # 超过最大尝试次数，加入失败队列
                            task.metadata = task.metadata or {}
                            task.metadata["error"] = error_message or "超过最大尝试次数"
                            task.metadata["failed_at"] = datetime.now().isoformat()
                            await redis.lpush(
                                self.failed_key, json.dumps(task.to_dict())
                            )
                            await redis.delete(key)
                            self.statistics["total_failed"] += 1
                            logger.error(f"任务 {task_id} 超过最大尝试次数，标记失败")

                        return True

            return False
        except Exception as e:
            logger.error(f"标记任务 {task_id} 失败失败: {e}")
            return False

    async def get_failed_tasks(self, limit: int = 100) -> list[QueueTask]:
        """获取失败的任务列表."""
        try:
            redis = await self._get_redis_client()
            if not redis:
                return []

            failed_data = await redis.lrange(self.failed_key, 0, limit - 1)
            failed_tasks = []

            for data in failed_data:
                try:
                    task = QueueTask.from_dict(json.loads(data))
                    failed_tasks.append(task)
                except Exception as e:
                    logger.error(f"解析失败任务失败: {e}")

            return failed_tasks
        except Exception as e:
            logger.error(f"获取失败任务列表失败: {e}")
            return []


class QueueManager:
    """队列管理器."""

    def __init__(self):
        self.queues: dict[str, FIFOQueue] = {}

    def create_queue(
        self, name: str, queue_type: str = "memory", **kwargs
    ) -> FIFOQueue:
        """创建队列."""
        if name in self.queues:
            logger.warning(f"队列 {name} 已存在")
            return self.queues[name]

        if queue_type.lower() == "memory":
            queue = MemoryFIFOQueue(name, **kwargs)
        elif queue_type.lower() == "redis":
            queue = RedisFIFOQueue(name, **kwargs)
        else:
            raise ValueError(f"不支持的队列类型: {queue_type}")

        self.queues[name] = queue
        logger.info(f"创建 {queue_type} 队列: {name}")
        return queue

    def get_queue(self, name: str) -> FIFOQueue | None:
        """获取队列."""
        return self.queues.get(name)

    def remove_queue(self, name: str) -> bool:
        """移除队列."""
        if name in self.queues:
            del self.queues[name]
            logger.info(f"移除队列: {name}")
            return True
        return False

    async def enqueue_to_queue(self, queue_name: str, task: QueueTask) -> bool:
        """向指定队列添加任务."""
        queue = self.get_queue(queue_name)
        if not queue:
            logger.error(f"队列 {queue_name} 不存在")
            return False
        return await queue.enqueue(task)

    async def dequeue_from_queue(
        self, queue_name: str, timeout: int | None = None
    ) -> QueueTask | None:
        """从指定队列取出任务."""
        queue = self.get_queue(queue_name)
        if not queue:
            logger.error(f"队列 {queue_name} 不存在")
            return None
        return await queue.dequeue(timeout)

    def get_all_statistics(self) -> dict[str, Any]:
        """获取所有队列的统计信息."""
        return {
            queue_name: queue.get_statistics()
            for queue_name, queue in self.queues.items()
        }

    async def clear_all_queues(self) -> dict[str, bool]:
        """清空所有队列."""
        results = {}
        for queue_name, queue in self.queues.items():
            results[queue_name] = await queue.clear()
        return results


# 全局队列管理器实例
queue_manager = QueueManager()


# 便捷函数
def create_task(
    task_type: str,
    data: dict[str, Any],
    priority: TaskPriority = TaskPriority.NORMAL,
    **kwargs,
) -> QueueTask:
    """创建队列任务."""
    return QueueTask(
        id=str(uuid.uuid4()),
        task_type=task_type,
        data=data,
        priority=priority,
        created_at=datetime.now(),
        **kwargs,
    )


async def enqueue_task(
    queue_name: str,
    task_type: str,
    data: dict[str, Any],
    priority: TaskPriority = TaskPriority.NORMAL,
) -> bool:
    """便捷的入队函数."""
    task = create_task(task_type, data, priority)
    return await queue_manager.enqueue_to_queue(queue_name, task)


async def dequeue_task(queue_name: str, timeout: int | None = None) -> QueueTask | None:
    """便捷的出队函数."""
    return await queue_manager.dequeue_from_queue(queue_name, timeout)
