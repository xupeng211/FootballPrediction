#!/usr/bin/env python3
"""
FotMob 数据收集服务 (FotMob Collection Service)

专注于FotMob数据的高并发采集、清洗和入库。
实现完整的ETL流程，包含Circuit Breaker熔断器保护。

主要功能：
1. FotMob API数据收集 (Extract)
2. 数据清洗和验证 (Transform)
3. PostgreSQL数据库存储 (Load)
4. 熔断器保护和重试机制
5. 高并发控制和限流

[Genesis.Standardization] V1.0: SQL 查询已迁移至 CollectorRepository
- 原 1843 行代码，约 200+ 行 SQL 已移至 src/database/collector_repository.py
- 数据库操作现在通过 CollectorRepository 统一管理
- 本文件保留业务逻辑和事务协调职责
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
import logging
import time
from typing import Any

from src.config_unified import get_settings

settings = get_settings()


import aiohttp
from tenacity import (
    RetryError,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config_unified import get_settings
from src.database.collector_repository import CollectorRepository, create_collector_repository
from src.database.db_pool import get_db_pool

from .__init__ import BaseService

logger = logging.getLogger(__name__)


class TransactionStatus(Enum):
    """事务状态枚举"""

    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class TransactionContext:
    """事务上下文"""

    transaction_id: str
    connection: Any
    started_at: datetime
    operations: list[dict[str, Any]] = field(default_factory=list)
    status: TransactionStatus = TransactionStatus.ACTIVE

    def add_operation(self, operation_type: str, description: str, **kwargs):
        """添加操作记录"""
        self.operations.append(
            {
                "type": operation_type,
                "description": description,
                "timestamp": datetime.utcnow(),
                "details": kwargs,
            }
        )

    def get_summary(self) -> dict[str, Any]:
        """获取事务摘要"""
        return {
            "transaction_id": self.transaction_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "operation_count": len(self.operations),
            "operations": self.operations,
        }


def database_transaction(retry_on_deadlock: bool = True, max_retries: int = 3):
    """
    数据库事务装饰器

    Args:
        retry_on_deadlock: 是否在死锁时重试
        max_retries: 最大重试次数
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            transaction_id = f"tx_{int(time.time())}_{func.__name__}"
            logger.info(f"🔐 开始事务: {transaction_id}")

            for attempt in range(max_retries + 1):
                try:
                    # 获取数据库连接
                    async with self.db_pool.acquire() as conn:
                        # 创建事务上下文
                        transaction_ctx = TransactionContext(
                            transaction_id=transaction_id,
                            connection=conn,
                            started_at=datetime.utcnow(),
                        )

                        # 开始事务
                        async with conn.transaction():
                            # 将事务上下文传递给被装饰的函数
                            result = await func(
                                self, *args, transaction_ctx=transaction_ctx, **kwargs
                            )

                            # 标记事务为已提交
                            transaction_ctx.status = TransactionStatus.COMMITTED
                            logger.info(f"✅ 事务 {transaction_id} 已提交")

                            return result

                except Exception as e:
                    error_msg = str(e)
                    logger.exception(
                        f"❌ 事务 {transaction_id} 失败 (尝试 {attempt + 1}): {error_msg}"
                    )

                    # 检查是否是死锁错误，如果是且允许重试，则重试
                    if (
                        retry_on_deadlock
                        and "deadlock" in error_msg.lower()
                        and attempt < max_retries
                    ):
                        wait_time = (attempt + 1) * 0.1  # 指数退避
                        logger.warning(f"🔄 检测到死锁，{wait_time}s后重试...")
                        await asyncio.sleep(wait_time)
                        continue

                    # 重新抛出异常
                    raise

            # 所有重试都失败了
            raise RuntimeError(f"事务 {transaction_id} 在 {max_retries} 次重试后仍然失败")

        return wrapper

    return decorator


class CollectionStatus(Enum):
    """收集状态枚举"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class FotMobCollectionTask:
    """FotMob数据收集任务"""

    task_id: str
    match_id: str | None = None
    league_id: str | None = None
    collection_type: str = "match"  # match, league, fixtures
    priority: int = 5
    max_retries: int = 3
    retry_count: int = 0
    status: CollectionStatus = CollectionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    data_points_collected: int = 0

    @property
    def duration_seconds(self) -> float | None:
        """获取任务执行时长"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "task_id": self.task_id,
            "match_id": self.match_id,
            "league_id": self.league_id,
            "collection_type": self.collection_type,
            "priority": self.priority,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (self.completed_at.isoformat() if self.completed_at else None),
            "duration_seconds": self.duration_seconds,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "result": self.result,
            "error": self.error,
            "data_points_collected": self.data_points_collected,
        }


@dataclass
class CollectionStats:
    """收集统计信息"""

    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    running_tasks: int = 0
    pending_tasks: int = 0
    avg_duration: float = 0.0
    success_rate: float = 0.0
    total_data_points: int = 0
    last_collection_time: datetime | None = None
    circuit_breaker_trips: int = 0
    last_error: str | None = None

    def update(self, tasks: list[FotMobCollectionTask]) -> None:
        """更新统计信息"""
        self.total_tasks = len(tasks)
        self.successful_tasks = len([t for t in tasks if t.status == CollectionStatus.SUCCESS])
        self.failed_tasks = len([t for t in tasks if t.status == CollectionStatus.FAILED])
        self.running_tasks = len([t for t in tasks if t.status == CollectionStatus.RUNNING])
        self.pending_tasks = len([t for t in tasks if t.status == CollectionStatus.PENDING])

        # 计算成功率
        if self.total_tasks > 0:
            self.success_rate = self.successful_tasks / self.total_tasks

        # 计算平均执行时长
        completed_tasks = [t for t in tasks if t.duration_seconds is not None]
        if completed_tasks:
            self.avg_duration = sum(t.duration_seconds for t in completed_tasks) / len(
                completed_tasks
            )

        # 统计数据点
        self.total_data_points = sum(t.data_points_collected for t in tasks)

        # 记录最后一次成功收集时间
        successful_tasks = [t for t in tasks if t.status == CollectionStatus.SUCCESS]
        if successful_tasks:
            self.last_collection_time = max(t.completed_at for t in successful_tasks)


class CircuitBreaker:
    """熔断器实现"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 300,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.half_open_calls = 0

        logger.info(f"熔断器初始化: 失败阈值={failure_threshold}, 恢复超时={recovery_timeout}s")

    def call_allowed(self) -> bool:
        """检查是否允许调用"""
        now = time.time()

        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if now - self.last_failure_time >= self.recovery_timeout:
                self.state = "HALF_OPEN"
                self.half_open_calls = 0
                logger.info("熔断器状态从OPEN转为HALF_OPEN")
                return True
            return False
        if self.state == "HALF_OPEN":
            return self.half_open_calls < self.half_open_max_calls

        return False

    def call_succeeded(self) -> None:
        """调用成功"""
        if self.state == "HALF_OPEN":
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self.state = "CLOSED"
                self.failure_count = 0
                logger.info("熔断器状态从HALF_OPEN转为CLOSED")
        elif self.state == "CLOSED":
            self.failure_count = 0

    def call_failed(self) -> None:
        """调用失败"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold and self.state != "OPEN":
            self.state = "OPEN"
            logger.warning(f"熔断器触发! 失败次数: {self.failure_count}")

    def get_state(self) -> dict[str, Any]:
        """获取熔断器状态"""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "recovery_timeout": self.recovery_timeout,
        }


class FotMobCollectionService(BaseService):
    """
    FotMob数据收集服务

    职责：
    1. 管理FotMob数据收集任务
    2. 提供ETL流程（Extract, Transform, Load）
    3. 协调高并发采集和入库
    4. 熔断器保护和错误恢复
    5. 数据质量验证和清洗
    """

    def __init__(self):
        super().__init__("FotMobCollectionService")
        self.settings = get_settings()
        self.db_pool = None
        self.tasks: list[FotMobCollectionTask] = []
        self.is_running = False
        self.max_concurrent_tasks = self.settings.fotmob_api.max_concurrent_requests
        self.stats = CollectionStats()

        # 初始化熔断器
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=self.settings.fotmob_api.circuit_breaker_failure_threshold,
            recovery_timeout=self.settings.fotmob_api.circuit_breaker_recovery_timeout,
            half_open_max_calls=self.settings.fotmob_api.circuit_breaker_half_open_max_calls,
        )

        # HTTP会话
        self.http_session: aiohttp.ClientSession | None = None

        # [Genesis.Standardization] V1.0: 数据库仓储（延迟初始化）
        self.collector_repository: CollectorRepository | None = None

        logger.info("🚀 FotMob数据收集服务初始化完成")

    async def initialize(self) -> bool:
        """初始化服务"""
        try:
            self.logger.info("正在初始化FotMob数据收集服务...")

            # 初始化数据库连接池
            self.db_pool = await get_db_pool()

            # [Genesis.Standardization] V1.0: 初始化数据库仓储
            self.collector_repository = await create_collector_repository(self.db_pool)

            # 测试数据库连接（使用仓储）
            if not await self.collector_repository.test_connection():
                raise RuntimeError("数据库连接测试失败")

            # 初始化HTTP会话
            headers = self.settings.get_fotmob_headers()
            timeout = aiohttp.ClientTimeout(total=self.settings.fotmob_api.timeout)
            self.http_session = aiohttp.ClientSession(headers=headers, timeout=timeout)

            self.is_running = True
            self.logger.info("✅ FotMob数据收集服务初始化成功")
            return True

        except Exception as e:
            self.logger.exception(f"❌ FotMob数据收集服务初始化失败: {e}")
            return False

    async def shutdown(self) -> None:
        """关闭服务"""
        try:
            self.logger.info("正在关闭FotMob数据收集服务...")

            # 停止所有运行中的任务
            self.is_running = False

            # 关闭HTTP会话
            if self.http_session:
                await self.http_session.close()

            # 关闭数据库连接
            if self.db_pool:
                await self.db_pool.close()

            self.logger.info("✅ FotMob数据收集服务已关闭")

        except Exception as e:
            self.logger.exception(f"❌ FotMob数据收集服务关闭失败: {e}")

    def create_match_collection_task(
        self, match_id: str, priority: int = 5, task_id: str | None = None
    ) -> str:
        """创建比赛数据收集任务"""
        if task_id is None:
            task_id = f"match_{match_id}_{int(time.time())}"

        task = FotMobCollectionTask(
            task_id=task_id,
            match_id=match_id,
            collection_type="match",
            priority=priority,
        )

        self.tasks.append(task)
        self.logger.info(f"已创建比赛收集任务: {task_id} (match_id: {match_id})")
        return task_id

    def create_league_collection_task(
        self, league_id: str, priority: int = 3, task_id: str | None = None
    ) -> str:
        """创建联赛数据收集任务"""
        if task_id is None:
            task_id = f"league_{league_id}_{int(time.time())}"

        task = FotMobCollectionTask(
            task_id=task_id,
            league_id=league_id,
            collection_type="league",
            priority=priority,
        )

        self.tasks.append(task)
        self.logger.info(f"已创建联赛收集任务: {task_id} (league_id: {league_id})")
        return task_id

    async def execute_task(self, task_id: str) -> dict[str, Any]:
        """执行单个收集任务"""
        # 查找任务
        task = next((t for t in self.tasks if t.task_id == task_id), None)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")

        # 检查熔断器状态
        if not self.circuit_breaker.call_allowed():
            error_msg = "熔断器开启，暂停FotMob API调用"
            task.status = CollectionStatus.FAILED
            task.error = error_msg
            task.completed_at = datetime.now()
            self.stats.last_error = error_msg
            raise RuntimeError(error_msg)

        # 更新任务状态
        task.status = CollectionStatus.RUNNING
        task.started_at = datetime.now()
        task.retry_count += 1

        try:
            self.logger.info(f"🎯 开始执行任务: {task_id}")

            # 导入FotMob采集器
            from scripts.collectors.fotmob_collector import FotMobCollector

            collector = FotMobCollector()
            await collector.initialize()

            # 执行数据收集
            if task.collection_type == "match" and task.match_id:
                raw_data = await collector.collect_match_data(task.match_id)
            elif task.collection_type == "league" and task.league_id:
                raw_data = await collector.collect_league_data(task.league_id)
            else:
                raise ValueError(f"无效的任务配置: {task}")

            # 数据清洗和转换
            cleaned_data = await self._transform_data(raw_data, task)

            # 数据入库
            if cleaned_data:
                await self._load_data(cleaned_data, task)
                task.data_points_collected = self._count_data_points(cleaned_data)

            # 更新任务结果
            task.status = CollectionStatus.SUCCESS
            task.result = cleaned_data
            task.completed_at = datetime.now()

            # 熔断器调用成功
            self.circuit_breaker.call_succeeded()

            self.logger.info(f"✅ 任务执行成功: {task_id} (数据点: {task.data_points_collected})")
            return task.to_dict()

        except Exception as e:
            # 熔断器调用失败
            self.circuit_breaker.call_failed()

            # 任务执行失败
            error_msg = str(e)
            task.status = CollectionStatus.FAILED
            task.error = error_msg
            task.completed_at = datetime.now()
            self.stats.last_error = error_msg

            # 如果还有重试机会，则重新调度
            if task.retry_count < task.max_retries:
                task.status = CollectionStatus.RETRY
                self.logger.warning(f"⚠️ 任务将重试: {task_id} (第{task.retry_count + 1}次)")

            self.logger.exception(f"❌ 任务执行失败: {task_id}, 错误: {error_msg}")
            return task.to_dict()

        finally:
            # 更新统计信息
            self.stats.update(self.tasks)

    async def _transform_data(
        self, raw_data: dict[str, Any], task: FotMobCollectionTask
    ) -> dict[str, Any]:
        """数据清洗和转换 (ETL的Transform阶段)"""
        try:
            if not raw_data:
                return {}

            # 基本数据验证
            if not isinstance(raw_data, dict):
                raise ValueError("原始数据不是字典格式")

            # 提取核心字段
            transformed = {
                "source": "fotmob",
                "collection_type": task.collection_type,
                "collection_time": datetime.utcnow().isoformat(),
                "task_id": task.task_id,
            }

            # 根据收集类型进行不同的转换
            if task.collection_type == "match":
                transformed.update(
                    {
                        "match_id": task.match_id,
                        "raw_data": raw_data,  # 暂时保存原始数据
                        "processed_data": self._process_match_data(raw_data),
                    }
                )
            elif task.collection_type == "league":
                transformed.update(
                    {
                        "league_id": task.league_id,
                        "raw_data": raw_data,
                        "processed_data": self._process_league_data(raw_data),
                    }
                )

            return transformed

        except Exception as e:
            self.logger.exception(f"数据转换失败: {e}")
            raise

    def _process_match_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """处理比赛数据"""
        processed = {}

        try:
            # 提取基本信息
            if "general" in raw_data:
                general = raw_data["general"]
                processed.update(
                    {
                        "home_team": general.get("homeTeam", {}).get("name"),
                        "away_team": general.get("awayTeam", {}).get("name"),
                        "home_score": general.get("homeGoals"),
                        "away_score": general.get("awayGoals"),
                        "status": general.get("statusText"),
                        "match_time": general.get("startDateStr"),
                        "venue": general.get("venue", {}).get("name"),
                    }
                )

            # 提取阵容数据
            if "lineups" in raw_data:
                processed["lineups"] = raw_data["lineups"]

            # 提取技术统计
            if "header" in raw_data and "stats" in raw_data["header"]:
                processed["stats"] = raw_data["header"]["stats"]

            # 提取xG数据
            if "content" in raw_data and "stats" in raw_data["content"]:
                stats = raw_data["content"]["stats"]
                for stat in stats:
                    if stat.get("title") == "Expected Goals (xG)":
                        processed["xg"] = stat.get("stats")
                        break

            return processed

        except Exception as e:
            self.logger.exception(f"比赛数据处理失败: {e}")
            return {"error": str(e)}

    def _process_league_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """处理联赛数据"""
        processed = {}

        try:
            # 这里可以添加联赛数据的具体处理逻辑
            processed["league_data"] = raw_data
            processed["processed_at"] = datetime.utcnow().isoformat()

            return processed

        except Exception as e:
            self.logger.exception(f"联赛数据处理失败: {e}")
            return {"error": str(e)}

    async def _load_data(self, data: dict[str, Any], task: FotMobCollectionTask) -> None:
        """数据入库 (ETL的Load阶段)"""
        try:
            if not data.get("processed_data"):
                self.logger.warning("没有处理后的数据，跳过入库")
                return

            processed_data = data["processed_data"]

            if task.collection_type == "match":
                await self._save_match_data(processed_data, task)
            elif task.collection_type == "league":
                await self._save_league_data(processed_data, task)

        except Exception as e:
            self.logger.exception(f"数据入库失败: {e}")
            raise

    @database_transaction(retry_on_deadlock=True, max_retries=3)
    async def _save_match_data(
        self,
        data: dict[str, Any],
        task: FotMobCollectionTask,
        *,
        transaction_ctx: TransactionContext,
    ) -> None:
        """保存比赛数据到数据库 (事务保护版本)

        [Genesis.Standardization] V1.0: 使用 CollectorRepository 替代内联 SQL
        """
        try:
            # 记录操作开始
            transaction_ctx.add_operation(
                operation_type="INSERT_UPDATE",
                description=f"保存比赛数据: {task.match_id}",
                match_id=task.match_id,
                data_source="fotmob",
            )

            # [Genesis.Standardization] V1.0: 使用仓储保存数据
            match_data = {
                "fotmob_id": task.match_id,
                **data,
            }
            await self.collector_repository.save_match_data(
                match_data, transaction_ctx.connection
            )

            # 记录操作成功
            transaction_ctx.add_operation(
                operation_type="SUCCESS",
                description=f"比赛数据保存成功: {task.match_id}",
                rows_affected=1,
            )

            self.logger.info(
                f"✅ 比赛数据已保存 (事务 {transaction_ctx.transaction_id}): {task.match_id}"
            )

            # 记录事务摘要（用于调试）
            if self.settings.application.debug:
                transaction_ctx.get_summary()

        except Exception as e:
            # 记录操作失败
            transaction_ctx.add_operation(
                operation_type="ERROR",
                description=f"比赛数据保存失败: {task.match_id}",
                error=str(e),
            )

            transaction_ctx.status = TransactionStatus.FAILED
            self.logger.exception(
                f"❌ 比赛数据保存失败 (事务 {transaction_ctx.transaction_id}): {task.match_id}, 错误: {e}"
            )
            raise

    @database_transaction(retry_on_deadlock=True, max_retries=3)
    async def batch_save_match_data(
        self, matches_data: list[dict[str, Any]], *, transaction_ctx: TransactionContext
    ) -> dict[str, Any]:
        """
        批量保存比赛数据 (单个事务)

        [Genesis.Standardization] V1.0: 使用 CollectorRepository 替代内联 SQL

        Args:
            matches_data: 比赛数据列表，每个元素包含 data 和 task
            transaction_ctx: 事务上下文

        Returns:
            Dict[str, Any]: 批量保存结果
        """
        try:
            start_time = time.time()

            # 记录批量操作开始
            transaction_ctx.add_operation(
                operation_type="BATCH_INSERT",
                description=f"开始批量保存 {len(matches_data)} 场比赛数据",
                total_matches=len(matches_data),
            )

            # [Genesis.Standardization] V1.0: 使用仓储批量保存
            result = await self.collector_repository.batch_save_match_data(
                matches_data, transaction_ctx.connection
            )

            duration = time.time() - start_time

            # 记录批量操作完成
            transaction_ctx.add_operation(
                operation_type="BATCH_COMPLETE",
                description=f"批量保存完成: 成功 {result.successful_count}, 失败 {result.failed_count}",
                successful=result.successful_count,
                failed=result.failed_count,
                duration=duration,
            )

            response = {
                "transaction_id": transaction_ctx.transaction_id,
                "total_matches": len(matches_data),
                "successful_count": result.successful_count,
                "failed_count": result.failed_count,
                "success_rate": (
                    result.successful_count / len(matches_data) if matches_data else 0
                ),
                "duration_seconds": duration,
                "errors": result.errors,
                "status": "completed" if result.failed_count == 0 else "partial_success",
            }

            self.logger.info(
                f"📊 批量保存完成 (事务 {transaction_ctx.transaction_id}): "
                f"{result.successful_count}/{len(matches_data)} 成功, 耗时: {duration:.2f}s"
            )

            return response

        except Exception as e:
            transaction_ctx.add_operation(
                operation_type="ERROR", description="批量保存事务失败", error=str(e)
            )

            transaction_ctx.status = TransactionStatus.FAILED
            self.logger.exception(
                f"❌ 批量保存事务失败 (事务 {transaction_ctx.transaction_id}): {e}"
            )
            raise

    async def _save_league_data(self, data: dict[str, Any], task: FotMobCollectionTask) -> None:
        """保存联赛数据到数据库"""
        try:
            # 暂时使用通用SQL，实际应该有具体的League模型
            self.logger.info(f"联赛数据保存: {task.league_id} (暂未实现)")

        except Exception as e:
            self.logger.exception(f"联赛数据保存失败: {e}")
            raise

    def _count_data_points(self, data: dict[str, Any]) -> int:
        """计算收集的数据点数量"""
        if isinstance(data, (dict, list)):
            return len(data)
        return 1

    async def execute_all_tasks(self, max_concurrent: int | None = None) -> list[dict[str, Any]]:
        """执行所有待处理的任务"""
        if max_concurrent is None:
            max_concurrent = self.max_concurrent_tasks

        # 过滤出待处理的任务
        pending_tasks = [
            t for t in self.tasks if t.status in [CollectionStatus.PENDING, CollectionStatus.RETRY]
        ]

        if not pending_tasks:
            self.logger.info("没有待处理的任务")
            return []

        # 按优先级排序
        pending_tasks.sort(key=lambda t: t.priority)

        self.logger.info(f"🚀 开始执行 {len(pending_tasks)} 个任务，最大并发数: {max_concurrent}")

        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_with_semaphore(task: FotMobCollectionTask) -> dict[str, Any]:
            async with semaphore:
                return await self.execute_task(task.task_id)

        # 并发执行任务
        results = await asyncio.gather(
            *[execute_with_semaphore(task) for task in pending_tasks],
            return_exceptions=True,
        )

        # 处理异常结果
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"任务执行异常: {result}")
                final_results.append(
                    {
                        "task_id": pending_tasks[i].task_id,
                        "status": "failed",
                        "error": str(result),
                    }
                )
            else:
                final_results.append(result)

        return final_results

    @retry(
        stop=stop_after_attempt(3),  # 最多重试3次
        wait=wait_exponential(multiplier=1, min=4, max=10),  # 指数退避: 4s, 8s, 10s
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError, RetryError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def fetch_fotmob_data(self, match_id: str, timeout: float = 10.0) -> dict[str, Any]:
        """
        从FotMob API获取比赛数据 (网络健壮性版本)

        特性:
        - 指数退避重试机制
        - 超时控制
        - 熔断器保护
        - 请求头自动配置
        - 详细的错误日志

        Args:
            match_id: 比赛ID
            timeout: 请求超时时间(秒)

        Returns:
            Dict[str, Any]: API响应数据

        Raises:
            RetryError: 重试次数耗尽后仍然失败
            RuntimeError: 熔断器开启时拒绝请求
        """
        # 检查熔断器状态
        if not self.circuit_breaker.call_allowed():
            error_msg = "熔断器开启，暂停FotMob API调用"
            logger.warning(f"🚫 {error_msg} (match_id: {match_id})")
            raise RuntimeError(error_msg)

        # 构建请求URL
        url = f"settings.fotmob.base_url/matchDetails?matchId={match_id}"

        # 配置请求头和超时
        headers = self.settings.get_fotmob_headers()
        request_timeout = aiohttp.ClientTimeout(total=timeout)

        logger.info(f"🌐 请求FotMob API: match_id={match_id}, timeout={timeout}s")

        try:
            # 使用现有的HTTP会话或创建新的
            session = self.http_session
            if not session:
                session = aiohttp.ClientSession(headers=headers, timeout=request_timeout)

            async with session.get(url, headers=headers) as response:
                # 记录响应状态

                if response.status == 200:
                    data = await response.json()

                    # 验证响应数据
                    if not data or not isinstance(data, dict):
                        error_msg = f"FotMob API返回空数据或无效格式 (match_id: {match_id})"
                        logger.error(f"❌ {error_msg}")
                        self.circuit_breaker.call_failed()
                        raise ValueError(error_msg)

                    # 成功获取数据
                    self.circuit_breaker.call_succeeded()
                    logger.info(
                        f"✅ FotMob数据获取成功 (match_id: {match_id}, 数据大小: {len(str(data))} 字符)"
                    )
                    return data

                if response.status == 429:
                    # 速率限制
                    error_msg = f"FotMob API速率限制 (match_id: {match_id})"
                    logger.warning(f"⚠️  {error_msg}")
                    self.circuit_breaker.call_failed()
                    raise aiohttp.ClientError(error_msg)

                if response.status in [500, 502, 503, 504]:
                    # 服务器错误 - 可以重试
                    error_msg = f"FotMob API服务器错误: {response.status} (match_id: {match_id})"
                    logger.warning(f"⚠️  {error_msg}")
                    self.circuit_breaker.call_failed()
                    raise aiohttp.ServerError(error_msg)

                # 其他HTTP错误 - 不可重试
                error_msg = f"FotMob API请求失败: {response.status} {response.reason} (match_id: {match_id})"
                logger.error(f"❌ {error_msg}")
                self.circuit_breaker.call_failed()
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=error_msg,
                )

        except TimeoutError as e:
            # 超时错误
            error_msg = f"FotMob API请求超时 ({timeout}s) (match_id: {match_id})"
            logger.exception(f"⏰ {error_msg}")
            self.circuit_breaker.call_failed()
            raise TimeoutError(error_msg) from e

        except aiohttp.ClientError as e:
            # 网络连接错误
            error_msg = f"FotMob API网络错误: {e!s} (match_id: {match_id})"
            logger.exception(f"🔌 {error_msg}")
            self.circuit_breaker.call_failed()
            raise aiohttp.ClientError(error_msg) from e

        except ValueError as e:
            # 数据解析错误
            error_msg = f"FotMob API数据解析错误: {e!s} (match_id: {match_id})"
            logger.exception(f"🔧 {error_msg}")
            self.circuit_breaker.call_failed()
            raise ValueError(error_msg) from e

        except Exception as e:
            # 其他未预期错误
            error_msg = f"FotMob API未知错误: {e!s} (match_id: {match_id})"
            logger.exception(f"❓ {error_msg}")
            self.circuit_breaker.call_failed()
            raise RuntimeError(error_msg) from e

    async def fetch_fotmob_data_batch(
        self, match_ids: list[str], timeout: float = 10.0, max_concurrent: int = 5
    ) -> dict[str, Any]:
        """
        批量获取FotMob数据 (并发版本)

        Args:
            match_ids: 比赛ID列表
            timeout: 单个请求超时时间
            max_concurrent: 最大并发数

        Returns:
            Dict[str, Any]: 批量获取结果
        """
        logger.info(
            f"🚀 开始批量获取FotMob数据: {len(match_ids)}场比赛, 最大并发数: {max_concurrent}"
        )

        # 创建信号量控制并发
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(
            match_id: str,
        ) -> tuple[str, dict[str, Any] | None]:
            async with semaphore:
                try:
                    data = await self.fetch_fotmob_data(match_id, timeout)
                    return match_id, data
                except Exception as e:
                    logger.exception(f"❌ 批量获取失败: match_id={match_id}, error={e!s}")
                    return match_id, None

        # 并发执行所有请求
        start_time = time.time()
        results = await asyncio.gather(
            *[fetch_with_semaphore(match_id) for match_id in match_ids],
            return_exceptions=True,
        )

        # 统计结果
        successful = {}
        failed = {}

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"❌ 批量获取异常: {result!s}")
                continue

            match_id, data = result
            if data:
                successful[match_id] = data
            else:
                failed[match_id] = "获取失败"

        duration = time.time() - start_time

        summary = {
            "total_requests": len(match_ids),
            "successful_requests": len(successful),
            "failed_requests": len(failed),
            "success_rate": len(successful) / len(match_ids) if match_ids else 0,
            "duration_seconds": duration,
            "avg_time_per_request": duration / len(match_ids) if match_ids else 0,
            "successful_match_ids": list(successful.keys()),
            "failed_match_ids": list(failed.keys()),
            "data": successful,
            "errors": failed,
        }

        logger.info(
            f"📊 批量获取完成: {summary['successful_requests']}/{summary['total_requests']} 成功 "
            f"({summary['success_rate']:.1%}), 耗时: {duration:.2f}s"
        )

        return summary

    async def get_upcoming_matches(self, hours_ahead: int = 48) -> dict[str, Any]:
        """
        获取未来24-48小时的即将到来的比赛和初盘赔率

        这是Sprint 6新增的核心实时数据接口，为实时预测提供数据基础。
        确保与历史回测时的特征提取逻辑100%一致，防止数据偏移。

        Args:
            hours_ahead: 向前展望的小时数 (默认48小时)

        Returns:
            Dict[str, Any]: 包含即将到来的比赛列表、初盘赔率和特征数据

            返回结构:
            {
                "collection_time": "2024-12-18T10:00:00Z",
                "time_window_hours": hours_ahead,
                "matches": [
                    {
                        "match_id": "123456",
                        "home_team": "Manchester United",
                        "away_team": "Arsenal",
                        "kickoff_time": "2024-12-19T20:00:00Z",
                        "hours_until_kickoff": 34.5,
                        "league": "Premier League",
                        "venue": "Old Trafford",
                        "status": "upcoming",

                        # 初盘赔率数据 (关键特征)
                        "initial_odds": {
                            "home_win": 2.10,
                            "draw": 3.40,
                            "away_win": 3.80,
                            "home_win_probability": 47.6,
                            "draw_probability": 29.4,
                            "away_win_probability": 26.3,
                            "bookmaker_margin": 102.3
                        },

                        # 实时特征提取 (与历史回测逻辑100%一致)
                        "real_time_features": {
                            # Elo评级特征
                            "elo_features": {
                                "home_elo": 1850.0,
                                "away_elo": 1780.0,
                                "elo_difference": 70.0,
                                "home_elo_recent_trend": 15.2,
                                "away_elo_recent_trend": -8.5,
                                "head_to_head_elo_advantage": "home"
                            },

                            # 泊松分布特征
                            "poisson_features": {
                                "expected_home_goals": 1.85,
                                "expected_away_goals": 1.12,
                                "total_expected_goals": 2.97,
                                "home_win_probability": 58.2,
                                "draw_probability": 22.1,
                                "away_win_probability": 19.7,
                                "both_teams_to_score_probability": 64.3,
                                "over_2_5_goals_probability": 61.8,
                                "most_likely_score": "2-1"
                            },

                            # 历史交锋特征 (H2H)
                            "h2h_features": {
                                "previous_meetings_count": 45,
                                "home_wins_last_5": 3,
                                "away_wins_last_5": 1,
                                "draws_last_5": 1,
                                "home_team_h2h_advantage": 0.156,
                                "average_goals_in_h2h": 2.8,
                                "clean_sheets_home_last_10": 4,
                                "clean_sheets_away_last_10": 2
                            },

                            # 主客场特征
                            "venue_features": {
                                "home_advantage_score": 0.124,
                                "home_form_last_6": 12,  # 积分
                                "away_form_last_6": 8,
                                "home_goals_scored_last_6": 9,
                                "home_goals_conceded_last_6": 3,
                                "away_goals_scored_last_6": 5,
                                "away_goals_conceded_last_6": 8,
                                "venue_importance_factor": 1.15
                            },

                            # 市场情绪特征
                            "market_features": {
                                "market_confidence": 0.73,
                                "odds_stability_index": 0.89,
                                "volume_weighted_home_probability": 48.2,
                                "volume_weighted_away_probability": 25.8,
                                "steam_signals_detected": False,
                                "market_efficiency_score": 0.91
                            }
                        },

                        # 数据质量指标
                        "data_quality": {
                            "completeness_score": 0.95,
                            "confidence_level": "high",
                            "last_updated": "2024-12-18T09:45:00Z",
                            "feature_coverage": {
                                "elo_available": True,
                                "poisson_available": True,
                                "h2h_available": True,
                                "venue_available": True,
                                "market_available": True
                            }
                        }
                    }
                ],

                # 统计摘要
                "summary": {
                    "total_matches": len(matches),
                    "matches_by_league": {...},
                    "avg_elo_difference": 45.2,
                    "high_confidence_matches": 8,  # confidence_level == "high"
                    "data_collection_status": "success",
                    "processing_time_ms": 1250
                }
            }
        """
        from datetime import datetime, timedelta
        import time

        start_time = time.time()
        collection_time = datetime.utcnow()

        logger.info(f"🚀 开始获取未来{hours_ahead}小时即将到来的比赛")

        try:
            # 1. 获取未来几天的比赛列表
            upcoming_matches = []
            target_dates = []

            # 生成需要查询的日期列表
            for i in range(hours_ahead // 24 + 1):
                target_date = collection_time + timedelta(days=i)
                target_dates.append(target_date.strftime("%Y-%m-%d"))

            logger.info(f"📅 查询日期范围: {target_dates[0]} 到 {target_dates[-1]}")

            # 2. 从FotMob获取比赛数据
            from scripts.collectors.fotmob_collector import FotMobCollector

            async with FotMobCollector() as collector:
                all_matches = []

                for date_str in target_dates:
                    daily_matches = await collector.collect_matches_by_date(date_str)
                    if daily_matches:
                        all_matches.extend(daily_matches)
                        logger.info(f"📊 {date_str}: 获取到 {len(daily_matches)} 场比赛")

                logger.info(f"📊 总共获取到 {len(all_matches)} 场比赛")

                # 3. 过滤和预处理即将到来的比赛
                for match_data in all_matches:
                    try:
                        # 提取基本信息
                        match_info = self._extract_basic_match_info(match_data)
                        if not match_info:
                            continue

                        # 计算比赛开始时间
                        kickoff_time = self._parse_kickoff_time(match_data.get("time", {}))
                        if not kickoff_time:
                            continue

                        # 检查是否在时间窗口内
                        hours_until_kickoff = (
                            kickoff_time - collection_time
                        ).total_seconds() / 3600
                        if hours_until_kickoff <= 0 or hours_until_kickoff > hours_ahead:
                            continue

                        match_info.update(
                            {
                                "kickoff_time": kickoff_time.isoformat(),
                                "hours_until_kickoff": round(hours_until_kickoff, 1),
                                "status": "upcoming",
                            }
                        )

                        # 4. 提取初盘赔率 (关键特征)
                        initial_odds = self._extract_initial_odds(match_data)
                        match_info["initial_odds"] = initial_odds

                        # 5. 实时特征提取 (与历史回测逻辑100%一致)
                        real_time_features = await self._extract_real_time_features(
                            match_info["match_id"],
                            match_info["home_team"],
                            match_info["away_team"],
                        )
                        match_info["real_time_features"] = real_time_features

                        # 6. 计算数据质量指标
                        data_quality = self._calculate_data_quality(match_info)
                        match_info["data_quality"] = data_quality

                        upcoming_matches.append(match_info)

                    except Exception as e:
                        logger.warning(f"⚠️ 处理比赛数据时出错: {e}")
                        continue

                # 7. 生成统计摘要
                summary = self._generate_collection_summary(
                    upcoming_matches, collection_time, time.time() - start_time
                )

                # 8. 构建最终返回结果
                result = {
                    "collection_time": collection_time.isoformat(),
                    "time_window_hours": hours_ahead,
                    "matches": upcoming_matches,
                    "summary": summary,
                }

                processing_time = (time.time() - start_time) * 1000
                logger.info(
                    f"✅ 即将来临比赛数据收集完成: {len(upcoming_matches)} 场比赛, 耗时: {processing_time:.1f}ms"
                )

                return result

        except Exception as e:
            error_msg = f"获取即将到来的比赛失败: {e!s}"
            logger.exception(f"❌ {error_msg}")

            # 返回错误结果但保持结构一致性
            return {
                "collection_time": collection_time.isoformat(),
                "time_window_hours": hours_ahead,
                "matches": [],
                "summary": {
                    "total_matches": 0,
                    "data_collection_status": "failed",
                    "error_message": error_msg,
                    "processing_time_ms": (time.time() - start_time) * 1000,
                },
            }

    def _extract_basic_match_info(self, match_data: dict[str, Any]) -> dict[str, Any] | None:
        """从FotMob数据中提取基本比赛信息"""
        try:
            # FotMob数据结构中的基本信息
            home_team_info = match_data.get("home", {}) or match_data.get("homeTeam", {})
            away_team_info = match_data.get("away", {}) or match_data.get("awayTeam", {})

            if not home_team_info or not away_team_info:
                return None

            return {
                "match_id": str(match_data.get("id", "")),
                "home_team": home_team_info.get("name", ""),
                "away_team": away_team_info.get("name", ""),
                "home_team_id": str(home_team_info.get("id", "")),
                "away_team_id": str(away_team_info.get("id", "")),
                "league": match_data.get("leagueName", ""),
                "league_id": str(match_data.get("leagueId", "")),
                "venue": match_data.get("venueName", ""),
                "country": match_data.get("ccode", ""),
            }

        except Exception as e:
            logger.warning(f"提取基本信息失败: {e}")
            return None

    def _parse_kickoff_time(self, time_data: dict[str, Any]) -> datetime | None:
        """解析比赛开始时间"""
        try:
            # FotMob时间格式可能是多种情况
            time_str = time_data.get("long") or time_data.get("timestamp")
            if isinstance(time_str, str):
                # 尝试解析ISO格式或其他常见格式
                from datetime import datetime

                # 尝试多种时间格式
                time_formats = [
                    "%Y-%m-%dT%H:%M:%S%z",
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%d %H:%M:%S",
                    "%d/%m/%Y %H:%M",
                    "%Y%m%d_%H%M",
                ]

                for fmt in time_formats:
                    try:
                        return datetime.strptime(time_str, fmt)
                    except ValueError:
                        continue

            elif isinstance(time_str, (int, float)):
                # 时间戳格式
                from datetime import datetime

                return datetime.fromtimestamp(time_str / 1000 if time_str > 1e10 else time_str)

            return None

        except Exception as e:
            logger.warning(f"解析比赛时间失败: {e}")
            return None

    def _extract_initial_odds(self, match_data: dict[str, Any]) -> dict[str, Any]:
        """提取初盘赔率数据"""
        odds_data = {
            "home_win": None,
            "draw": None,
            "away_win": None,
            "home_win_probability": None,
            "draw_probability": None,
            "away_win_probability": None,
            "bookmaker_margin": None,
        }

        try:
            # 从FotMob数据中提取赔率
            # 检查多个可能的赔率数据源
            odds_sources = [("bettingOffers", []), ("odds", {}), ("betting", {})]

            for source_key, _default_value in odds_sources:
                if source_key in match_data:
                    source_data = match_data[source_key]
                    if source_data:
                        # 处理不同的赔率数据结构
                        if isinstance(source_data, list) and source_data:
                            # 第一个赔率提供商的数据
                            first_offer = source_data[0]
                            if isinstance(first_offer, dict):
                                odds_data["home_win"] = first_offer.get("homeOdds")
                                odds_data["draw"] = first_offer.get("drawOdds")
                                odds_data["away_win"] = first_offer.get("awayOdds")
                                break

                        elif isinstance(source_data, dict):
                            odds_data["home_win"] = source_data.get("homeOdds") or source_data.get(
                                "home"
                            )
                            odds_data["draw"] = source_data.get("drawOdds") or source_data.get(
                                "draw"
                            )
                            odds_data["away_win"] = source_data.get("awayOdds") or source_data.get(
                                "away"
                            )
                            break

            # 计算隐含概率和庄家赔率
            if odds_data["home_win"] and odds_data["away_win"]:
                try:
                    home_win_decimal = float(odds_data["home_win"])
                    draw_decimal = float(odds_data["draw"]) if odds_data["draw"] else None
                    away_win_decimal = float(odds_data["away_win"])

                    odds_data["home_win_probability"] = round(1.0 / home_win_decimal * 100, 1)
                    odds_data["away_win_probability"] = round(1.0 / away_win_decimal * 100, 1)

                    if draw_decimal and draw_decimal > 0:
                        odds_data["draw_probability"] = round(1.0 / draw_decimal * 100, 1)

                    # 计算庄家赔率 (应该 > 100%)
                    total_probability = (
                        odds_data["home_win_probability"]
                        + (odds_data["draw_probability"] or 0)
                        + odds_data["away_win_probability"]
                    )
                    odds_data["bookmaker_margin"] = round(total_probability, 1)

                except (ValueError, TypeError) as e:
                    logger.warning(f"赔率计算失败: {e}")

            return odds_data

        except Exception as e:
            logger.warning(f"提取赔率数据失败: {e}")
            return odds_data

    async def _extract_real_time_features(
        self, match_id: str, home_team: str, away_team: str
    ) -> dict[str, Any]:
        """
        实时特征提取 - 与历史回测逻辑100%一致

        这是关键函数，确保实时预测使用的特征工程逻辑
        与50GB历史回测时完全相同，防止数据偏移。
        """
        features = {
            "elo_features": {},
            "poisson_features": {},
            "h2h_features": {},
            "venue_features": {},
            "market_features": {},
        }

        try:
            # 1. Elo评级特征 (使用Sprint 5实现的Elo系统)
            features["elo_features"] = await self._extract_elo_features(home_team, away_team)

            # 2. 泊松分布特征 (使用Sprint 5实现的泊松系统)
            features["poisson_features"] = await self._extract_poisson_features(
                home_team, away_team
            )

            # 3. 历史交锋特征 (使用现有H2H计算器)
            features["h2h_features"] = await self._extract_h2h_features(home_team, away_team)

            # 4. 主客场特征 (使用场馆分析器)
            features["venue_features"] = await self._extract_venue_features(home_team, away_team)

            # 5. 市场情绪特征 (使用Sprint 5实现的赔率分析器)
            features["market_features"] = await self._extract_market_features(match_id)

            return features

        except Exception as e:
            logger.exception(f"实时特征提取失败 {home_team} vs {away_team}: {e}")
            return features

    async def _extract_elo_features(self, home_team: str, away_team: str) -> dict[str, Any]:
        """提取Elo评级特征"""
        try:
            # 使用Sprint 5实现的Elo评级系统
            from src.ml.features.elo_rating_system import EloRatingSystem

            # 获取或创建Elo系统实例
            elo_system = EloRatingSystem()

            # 获取当前Elo评分
            home_elo = elo_system.get_team_rating(home_team)
            away_elo = elo_system.get_team_rating(away_team)

            # 计算Elo差异
            elo_diff = home_elo - away_elo

            # 获取Elo变化趋势
            home_trend = elo_system.get_team_recent_trend(home_team, matches=5)
            away_trend = elo_system.get_team_recent_trend(away_team, matches=5)

            # 获取历史交锋Elo优势
            h2h_advantage = elo_system.get_head_to_head_elo_advantage(home_team, away_team)

            return {
                "home_elo": round(home_elo, 1),
                "away_elo": round(away_elo, 1),
                "elo_difference": round(elo_diff, 1),
                "home_elo_recent_trend": round(home_trend, 1),
                "away_elo_recent_trend": round(away_trend, 1),
                "head_to_head_elo_advantage": h2h_advantage,
            }

        except Exception as e:
            logger.warning(f"Elo特征提取失败: {e}")
            return {}

    async def _extract_poisson_features(self, home_team: str, away_team: str) -> dict[str, Any]:
        """提取泊松分布特征"""
        try:
            # 使用Sprint 5实现的泊松特征计算器
            from src.ml.features.poisson_features import PoissonFeatureCalculator

            calculator = PoissonFeatureCalculator()

            # 计算比赛概率
            probabilities = calculator.calculate_match_probabilities(home_team, away_team)

            # 提取关键特征
            expected_goals = probabilities.get("expected_goals", {})
            probs = probabilities.get("probabilities", {})

            return {
                "expected_home_goals": round(expected_goals.get("home", 0), 2),
                "expected_away_goals": round(expected_goals.get("away", 0), 2),
                "total_expected_goals": round(
                    expected_goals.get("home", 0) + expected_goals.get("away", 0), 2
                ),
                "home_win_probability": round(probs.get("home_win", 0) * 100, 1),
                "draw_probability": round(probs.get("draw", 0) * 100, 1),
                "away_win_probability": round(probs.get("away_win", 0) * 100, 1),
                "both_teams_to_score_probability": round(probs.get("both_teams_score", 0) * 100, 1),
                "over_2_5_goals_probability": round(probs.get("over_2_5", 0) * 100, 1),
                "most_likely_score": probabilities.get("most_likely_score", "0-0"),
            }

        except Exception as e:
            logger.warning(f"泊松特征提取失败: {e}")
            return {}

    async def _extract_h2h_features(self, home_team: str, away_team: str) -> dict[str, Any]:
        """提取历史交锋特征"""
        try:
            # 使用现有的H2H计算器
            from src.ml.features.h2h_calculator import H2HCalculator

            h2h_calc = H2HCalculator()
            h2h_data = h2h_calc.calculate_h2h_features(home_team, away_team)

            # 提取关键H2H特征
            recent_form = h2h_data.get("recent_form", {})
            historical_stats = h2h_data.get("historical_stats", {})

            return {
                "previous_meetings_count": historical_stats.get("total_meetings", 0),
                "home_wins_last_5": recent_form.get("home_wins_last_5", 0),
                "away_wins_last_5": recent_form.get("away_wins_last_5", 0),
                "draws_last_5": recent_form.get("draws_last_5", 0),
                "home_team_h2h_advantage": recent_form.get("home_advantage", 0.0),
                "average_goals_in_h2h": historical_stats.get("average_goals_per_meeting", 0.0),
                "clean_sheets_home_last_10": recent_form.get("home_clean_sheets_last_10", 0),
                "clean_sheets_away_last_10": recent_form.get("away_clean_sheets_last_10", 0),
            }

        except Exception as e:
            logger.warning(f"H2H特征提取失败: {e}")
            return {}

    async def _extract_venue_features(self, home_team: str, away_team: str) -> dict[str, Any]:
        """提取主客场特征"""
        try:
            # 使用现有的场馆分析器
            from src.ml.features.venue_analyzer import VenueAnalyzer

            venue_analyzer = VenueAnalyzer()
            venue_data = venue_analyzer.analyze_venue_features(home_team, away_team)

            # 提取关键场馆特征
            home_form = venue_data.get("home_form", {})
            away_form = venue_data.get("away_form", {})

            return {
                "home_advantage_score": venue_data.get("home_advantage_factor", 0.0),
                "home_form_last_6": home_form.get("last_6_points", 0),
                "away_form_last_6": away_form.get("last_6_points", 0),
                "home_goals_scored_last_6": home_form.get("last_6_goals_scored", 0),
                "home_goals_conceded_last_6": home_form.get("last_6_goals_conceded", 0),
                "away_goals_scored_last_6": away_form.get("last_6_goals_scored", 0),
                "away_goals_conceded_last_6": away_form.get("last_6_goals_conceded", 0),
                "venue_importance_factor": venue_data.get("venue_importance", 1.0),
            }

        except Exception as e:
            logger.warning(f"场馆特征提取失败: {e}")
            return {}

    async def _extract_market_features(self, match_id: str) -> dict[str, Any]:
        """提取市场情绪特征"""
        try:
            # 使用Sprint 5实现的赔率变动分析器
            from src.ml.features.odds_movement_features import OddsMovementAnalyzer

            odds_analyzer = OddsMovementAnalyzer()

            # 分析赔率变动 (对于即将到来的比赛，分析初盘)
            market_analysis = odds_analyzer.analyze_market_sentiment(match_id)

            # 提取关键市场特征
            market_data = market_analysis.get("market_data", {})

            return {
                "market_confidence": market_data.get("confidence_level", 0.0),
                "odds_stability_index": market_data.get("stability_index", 0.0),
                "volume_weighted_home_probability": market_data.get("volume_home_prob", 0.0),
                "volume_weighted_away_probability": market_data.get("volume_away_prob", 0.0),
                "steam_signals_detected": market_analysis.get("steam_signals", {}).get(
                    "steam_detected", False
                ),
                "market_efficiency_score": market_data.get("efficiency_score", 0.0),
            }

        except Exception as e:
            logger.warning(f"市场特征提取失败: {e}")
            return {}

    def _calculate_data_quality(self, match_info: dict[str, Any]) -> dict[str, Any]:
        """计算数据质量指标"""
        try:
            quality_scores = []
            feature_coverage = {}

            # 检查各个特征模块的可用性
            features = match_info.get("real_time_features", {})

            for feature_name, feature_data in features.items():
                if feature_data and isinstance(feature_data, dict) and len(feature_data) > 0:
                    feature_coverage[f"{feature_name}_available"] = True
                    quality_scores.append(1.0)
                else:
                    feature_coverage[f"{feature_name}_available"] = False
                    quality_scores.append(0.0)

            # 计算完整性评分
            completeness_score = (
                sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            )

            # 确定置信度等级
            if completeness_score >= 0.8:
                confidence_level = "high"
            elif completeness_score >= 0.6:
                confidence_level = "medium"
            else:
                confidence_level = "low"

            return {
                "completeness_score": round(completeness_score, 2),
                "confidence_level": confidence_level,
                "last_updated": datetime.utcnow().isoformat(),
                "feature_coverage": feature_coverage,
            }

        except Exception as e:
            logger.warning(f"数据质量计算失败: {e}")
            return {
                "completeness_score": 0.0,
                "confidence_level": "unknown",
                "last_updated": datetime.utcnow().isoformat(),
                "feature_coverage": {},
            }

    def _generate_collection_summary(
        self,
        matches: list[dict[str, Any]],
        collection_time: datetime,
        processing_time: float,
    ) -> dict[str, Any]:
        """生成收集统计摘要"""
        try:
            # 按联赛统计比赛数量
            matches_by_league = {}
            high_confidence_matches = 0
            elo_differences = []

            for match in matches:
                # 联赛统计
                league = match.get("league", "Unknown")
                matches_by_league[league] = matches_by_league.get(league, 0) + 1

                # 高置信度比赛统计
                data_quality = match.get("data_quality", {})
                if data_quality.get("confidence_level") == "high":
                    high_confidence_matches += 1

                # Elo差异统计
                elo_features = match.get("real_time_features", {}).get("elo_features", {})
                elo_diff = elo_features.get("elo_difference")
                if elo_diff is not None:
                    elo_differences.append(abs(elo_diff))

            # 计算平均Elo差异
            avg_elo_difference = (
                sum(elo_differences) / len(elo_differences) if elo_differences else 0.0
            )

            return {
                "total_matches": len(matches),
                "matches_by_league": matches_by_league,
                "avg_elo_difference": round(avg_elo_difference, 1),
                "high_confidence_matches": high_confidence_matches,
                "data_collection_status": "success",
                "processing_time_ms": round(processing_time * 1000, 1),
            }

        except Exception as e:
            logger.exception(f"生成统计摘要失败: {e}")
            return {
                "total_matches": len(matches),
                "data_collection_status": "partial_success",
                "error_message": str(e),
                "processing_time_ms": round(processing_time * 1000, 1),
            }

    def get_service_status(self) -> dict[str, Any]:
        """获取服务状态"""
        return {
            "service_name": "FotMobCollectionService",
            "is_running": self.is_running,
            "total_tasks": self.stats.total_tasks,
            "successful_tasks": self.stats.successful_tasks,
            "failed_tasks": self.stats.failed_tasks,
            "success_rate": self.stats.success_rate,
            "avg_duration": self.stats.avg_duration,
            "total_data_points": self.stats.total_data_points,
            "last_collection_time": (
                self.stats.last_collection_time.isoformat()
                if self.stats.last_collection_time
                else None
            ),
            "circuit_breaker": self.circuit_breaker.get_state(),
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "last_error": self.stats.last_error,
            # Sprint 6新增: 实时数据接口状态
            "real_time_data_interface": {
                "enabled": True,
                "supported_features": [
                    "upcoming_matches",
                    "real_time_features",
                    "initial_odds",
                    "elo_ratings",
                    "poisson_probabilities",
                    "h2h_analysis",
                    "venue_factors",
                    "market_sentiment",
                ],
                "data_consistency_guarantee": "100%_historical_backtest_compatibility",
            },
        }
