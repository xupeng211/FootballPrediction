#!/usr/bin/env python3
"""
数据收集服务 (Data Collection Service)

统一管理所有外部数据源的收集逻辑，为scripts目录提供的服务层抽象。
遵循单一职责原则，专门负责数据收集的协调和管理。

主要功能：
1. 外部API数据收集 (FotMob, OddsPortal等)
2. 多数据源聚合和标准化
3. 数据收集任务调度和监控
4. 错误处理和重试机制
5. 数据质量验证
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from pathlib import Path
import json
import time
from enum import Enum

from .__init__ import BaseService
from src.database.db_pool import get_db_pool
from src.database.config import get_database_config

logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """数据源类型枚举"""
    FOTMOB = "fotmob"
    ODPORTAL = "oddsportal"
    FOOTBALL_DATA = "football_data"
    CUSTOM = "custom"


class CollectionStatus(Enum):
    """收集状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class CollectionTask:
    """数据收集任务"""
    task_id: str
    source_type: DataSourceType
    source_config: Dict[str, Any]
    priority: int = 5
    max_retries: int = 3
    retry_count: int = 0
    status: CollectionStatus = CollectionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        """获取任务执行时长"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "task_id": self.task_id,
            "source_type": self.source_type.value,
            "source_config": self.source_config,
            "priority": self.priority,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "result": self.result,
            "error": self.error
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
    last_collection_time: Optional[datetime] = None

    def update(self, tasks: List[CollectionTask]) -> None:
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
            self.avg_duration = sum(t.duration_seconds for t in completed_tasks) / len(completed_tasks)

        # 记录最后一次收集时间
        successful_tasks = [t for t in tasks if t.status == CollectionStatus.SUCCESS]
        if successful_tasks:
            self.last_collection_time = max(t.completed_at for t in successful_tasks)


class CollectionService(BaseService):
    """
    数据收集服务

    职责：
    1. 管理多种数据源的收集任务
    2. 提供统一的数据收集接口
    3. 协调不同收集器的工作
    4. 监控和统计收集情况
    """

    def __init__(self):
        super().__init__("CollectionService")
        self.db_pool = None
        self.tasks: List[CollectionTask] = []
        self.collectors: Dict[DataSourceType, Callable] = {}
        self.is_running = False
        self.max_concurrent_tasks = 5
        self.stats = CollectionStats()

        # 注册收集器
        self._register_collectors()

    def _register_collectors(self) -> None:
        """注册数据收集器"""
        try:
            # 注册FotMob收集器
            from scripts.collectors.enhanced_fotmob_collector import EnhancedFotMobCollector
            self.collectors[DataSourceType.FOTMOB] = self._create_fotmob_collector(EnhancedFotMobCollector)
            self.logger.info("FotMob收集器已注册")

        except ImportError as e:
            self.logger.warning(f"FotMob收集器注册失败: {e}")

        try:
            # 注册OddsPortal收集器
            from scripts.collectors.odds_collector import OddsCollector
            self.collectors[DataSourceType.ODPORTAL] = self._create_odds_collector(OddsCollector)
            self.logger.info("OddsPortal收集器已注册")

        except ImportError as e:
            self.logger.warning(f"OddsPortal收集器注册失败: {e}")

        try:
            # 注册FootballData收集器
            from scripts.collectors.football_data_collector import FootballDataCollector
            self.collectors[DataSourceType.FOOTBALL_DATA] = self._create_football_data_collector(FootballDataCollector)
            self.logger.info("FootballData收集器已注册")

        except ImportError as e:
            self.logger.warning(f"FootballData收集器注册失败: {e}")

    def _create_fotmob_collector(self, collector_class) -> Callable:
        """创建FotMob收集器包装器"""
        def wrapper(config: Dict[str, Any]) -> Dict[str, Any]:
            try:
                collector = collector_class()
                # 根据配置调用相应的收集方法
                if config.get("match_id"):
                    return collector.collect_match_data(config["match_id"])
                elif config.get("league_id"):
                    return collector.collect_league_data(config["league_id"])
                else:
                    raise ValueError("FotMob收集器需要match_id或league_id参数")
            except Exception as e:
                self.logger.error(f"FotMob收集器执行失败: {e}")
                raise
        return wrapper

    def _create_odds_collector(self, collector_class) -> Callable:
        """创建Odds收集器包装器"""
        def wrapper(config: Dict[str, Any]) -> Dict[str, Any]:
            try:
                collector = collector_class()
                # 根据配置调用相应的收集方法
                if config.get("match_id"):
                    return collector.collect_match_odds(config["match_id"])
                elif config.get("league_id"):
                    return collector.collect_league_odds(config["league_id"])
                else:
                    raise ValueError("Odds收集器需要match_id或league_id参数")
            except Exception as e:
                self.logger.error(f"Odds收集器执行失败: {e}")
                raise
        return wrapper

    def _create_football_data_collector(self, collector_class) -> Callable:
        """创建FootballData收集器包装器"""
        def wrapper(config: Dict[str, Any]) -> Dict[str, Any]:
            try:
                collector = collector_class()
                # 根据配置调用相应的收集方法
                if config.get("league_code"):
                    return collector.collect_league_data(config["league_code"])
                elif config.get("match_id"):
                    return collector.collect_match_data(config["match_id"])
                else:
                    raise ValueError("FootballData收集器需要league_code或match_id参数")
            except Exception as e:
                self.logger.error(f"FootballData收集器执行失败: {e}")
                raise
        return wrapper

    async def initialize(self) -> bool:
        """初始化服务"""
        try:
            self.logger.info("正在初始化数据收集服务...")

            # 初始化数据库连接池
            self.db_pool = await get_db_pool()

            # 测试数据库连接
            await self.db_pool.fetchval("SELECT 1")

            self.is_running = True
            self.logger.info("数据收集服务初始化成功")
            return True

        except Exception as e:
            self.logger.error(f"数据收集服务初始化失败: {e}")
            return False

    async def shutdown(self) -> None:
        """关闭服务"""
        try:
            self.logger.info("正在关闭数据收集服务...")

            # 停止所有运行中的任务
            self.is_running = False

            # 关闭数据库连接
            if self.db_pool:
                await self.db_pool.close()

            self.logger.info("数据收集服务已关闭")

        except Exception as e:
            self.logger.error(f"数据收集服务关闭失败: {e}")

    def create_collection_task(
        self,
        source_type: Union[str, DataSourceType],
        source_config: Dict[str, Any],
        priority: int = 5,
        task_id: Optional[str] = None
    ) -> str:
        """
        创建数据收集任务

        Args:
            source_type: 数据源类型
            source_config: 数据源配置
            priority: 任务优先级 (1-10, 数字越小优先级越高)
            task_id: 任务ID，如果为None则自动生成

        Returns:
            str: 任务ID
        """
        if isinstance(source_type, str):
            source_type = DataSourceType(source_type)

        if task_id is None:
            task_id = f"{source_type.value}_{int(time.time())}_{len(self.tasks)}"

        task = CollectionTask(
            task_id=task_id,
            source_type=source_type,
            source_config=source_config,
            priority=priority
        )

        self.tasks.append(task)
        self.logger.info(f"已创建收集任务: {task_id} (来源: {source_type.value})")

        return task_id

    async def execute_task(self, task_id: str) -> Dict[str, Any]:
        """
        执行单个收集任务

        Args:
            task_id: 任务ID

        Returns:
            Dict[str, Any]: 执行结果
        """
        # 查找任务
        task = next((t for t in self.tasks if t.task_id == task_id), None)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")

        # 检查收集器是否可用
        if task.source_type not in self.collectors:
            error_msg = f"不支持的收集器类型: {task.source_type.value}"
            task.status = CollectionStatus.FAILED
            task.error = error_msg
            task.completed_at = datetime.now()
            raise ValueError(error_msg)

        # 更新任务状态
        task.status = CollectionStatus.RUNNING
        task.started_at = datetime.now()
        task.retry_count += 1

        try:
            self.logger.info(f"开始执行任务: {task_id}")

            # 执行收集
            collector_func = self.collectors[task.source_type]
            result = await self._execute_collector_async(collector_func, task.source_config)

            # 更新任务结果
            task.status = CollectionStatus.SUCCESS
            task.result = result
            task.completed_at = datetime.now()

            # 更新统计
            self.stats.total_data_points += self._count_data_points(result)
            self.stats.last_collection_time = datetime.now()

            self.logger.info(f"任务执行成功: {task_id}")
            return task.to_dict()

        except Exception as e:
            # 任务执行失败
            error_msg = str(e)
            task.status = CollectionStatus.FAILED
            task.error = error_msg
            task.completed_at = datetime.now()

            self.logger.error(f"任务执行失败: {task_id}, 错误: {error_msg}")

            # 如果还有重试机会，则重新调度
            if task.retry_count < task.max_retries:
                task.status = CollectionStatus.RETRY
                self.logger.info(f"任务将重试: {task_id} (第{task.retry_count + 1}次)")

            return task.to_dict()

        finally:
            # 更新统计信息
            self.stats.update(self.tasks)

    async def _execute_collector_async(self, collector_func: Callable, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        异步执行收集器函数

        Args:
            collector_func: 收集器函数
            config: 配置参数

        Returns:
            Dict[str, Any]: 收集结果
        """
        # 在线程池中执行同步的收集器函数
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, collector_func, config)

    def _count_data_points(self, result: Dict[str, Any]) -> int:
        """计算收集的数据点数量"""
        if isinstance(result, dict):
            return len(result)
        elif isinstance(result, list):
            return len(result)
        else:
            return 1

    async def execute_all_tasks(self, max_concurrent: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        执行所有待处理的任务

        Args:
            max_concurrent: 最大并发数

        Returns:
            List[Dict[str, Any]]: 所有任务的执行结果
        """
        if max_concurrent is None:
            max_concurrent = self.max_concurrent_tasks

        # 过滤出待处理的任务
        pending_tasks = [t for t in self.tasks if t.status in [
            CollectionStatus.PENDING, CollectionStatus.RETRY
        ]]

        if not pending_tasks:
            self.logger.info("没有待处理的任务")
            return []

        # 按优先级排序
        pending_tasks.sort(key=lambda t: t.priority)

        self.logger.info(f"开始执行 {len(pending_tasks)} 个任务，最大并发数: {max_concurrent}")

        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_with_semaphore(task: CollectionTask) -> Dict[str, Any]:
            async with semaphore:
                return await self.execute_task(task.task_id)

        # 并发执行任务
        results = await asyncio.gather(
            *[execute_with_semaphore(task) for task in pending_tasks],
            return_exceptions=True
        )

        # 处理异常结果
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"任务执行异常: {result}")
                final_results.append({
                    "task_id": pending_tasks[i].task_id,
                    "status": "failed",
                    "error": str(result)
                })
            else:
                final_results.append(result)

        return final_results

    def get_tasks(
        self,
        status: Optional[CollectionStatus] = None,
        source_type: Optional[DataSourceType] = None
    ) -> List[Dict[str, Any]]:
        """
        获取任务列表

        Args:
            status: 按状态过滤
            source_type: 按数据源类型过滤

        Returns:
            List[Dict[str, Any]]: 任务列表
        """
        filtered_tasks = self.tasks

        if status:
            filtered_tasks = [t for t in filtered_tasks if t.status == status]

        if source_type:
            filtered_tasks = [t for t in filtered_tasks if t.source_type == source_type]

        return [task.to_dict() for task in filtered_tasks]

    def get_stats(self) -> Dict[str, Any]:
        """
        获取收集统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        self.stats.update(self.tasks)

        return {
            "service_status": "running" if self.is_running else "stopped",
            "total_tasks": self.stats.total_tasks,
            "successful_tasks": self.stats.successful_tasks,
            "failed_tasks": self.stats.failed_tasks,
            "running_tasks": self.stats.running_tasks,
            "pending_tasks": self.stats.pending_tasks,
            "success_rate": self.stats.success_rate,
            "avg_duration_seconds": self.stats.avg_duration,
            "total_data_points": self.stats.total_data_points,
            "last_collection_time": self.stats.last_collection_time.isoformat() if self.stats.last_collection_time else None,
            "available_collectors": [source_type.value for source_type in self.collectors.keys()],
            "max_concurrent_tasks": self.max_concurrent_tasks
        }

    def clear_completed_tasks(self, older_than_hours: int = 24) -> int:
        """
        清理已完成的任务

        Args:
            older_than_hours: 清理多少小时前的任务

        Returns:
            int: 清理的任务数量
        """
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)

        original_count = len(self.tasks)
        self.tasks = [
            task for task in self.tasks
            if task.status not in [CollectionStatus.SUCCESS, CollectionStatus.FAILED]
            or (task.completed_at and task.completed_at > cutoff_time)
        ]

        cleaned_count = original_count - len(self.tasks)
        self.logger.info(f"已清理 {cleaned_count} 个已完成任务")

        return cleaned_count

    async def collect_match_data(
        self,
        match_id: str,
        sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        收集指定比赛的数据

        Args:
            match_id: 比赛ID
            sources: 指定数据源，如果为None则使用所有可用源

        Returns:
            Dict[str, Any]: 收集结果
        """
        if sources is None:
            sources = [source_type.value for source_type in self.collectors.keys()]

        task_ids = []

        # 为每个数据源创建任务
        for source in sources:
            task_id = self.create_collection_task(
                source_type=source,
                source_config={"match_id": match_id},
                priority=1  # 高优先级
            )
            task_ids.append(task_id)

        # 等待所有任务完成
        await asyncio.sleep(1)  # 给任务调度一些时间
        results = await self.execute_all_tasks()

        return {
            "match_id": match_id,
            "task_ids": task_ids,
            "results": results,
            "total_sources": len(sources),
            "successful_collections": len([r for r in results if r.get("status") == "success"])
        }

    # 便捷方法：直接与特定收集器交互
    async def collect_fotmob_data(self, match_id: str) -> Dict[str, Any]:
        """收集FotMob数据"""
        return await self.collect_match_data(match_id, sources=["fotmob"])

    async def collect_odds_data(self, match_id: str) -> Dict[str, Any]:
        """收集赔率数据"""
        return await self.collect_match_data(match_id, sources=["oddsportal"])

    async def collect_league_data(self, league_code: str, league_id: Optional[str] = None) -> Dict[str, Any]:
        """收集联赛数据"""
        task_ids = []

        if DataSourceType.FOOTBALL_DATA in self.collectors:
            task_id = self.create_collection_task(
                source_type="football_data",
                source_config={"league_code": league_code},
                priority=3
            )
            task_ids.append(task_id)

        if league_id and DataSourceType.FOTMOB in self.collectors:
            task_id = self.create_collection_task(
                source_type="fotmob",
                source_config={"league_id": league_id},
                priority=3
            )
            task_ids.append(task_id)

        if task_ids:
            await asyncio.sleep(1)
            results = await self.execute_all_tasks()

            return {
                "league_code": league_code,
                "league_id": league_id,
                "task_ids": task_ids,
                "results": results
            }
        else:
            return {"error": "没有可用的数据源"}


# 创建全局服务实例
collection_service = CollectionService()

__all__ = [
    "CollectionService",
    "CollectionTask",
    "CollectionStats",
    "DataSourceType",
    "CollectionStatus",
    "collection_service"
]