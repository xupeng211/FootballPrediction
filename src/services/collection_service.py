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
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import aiohttp
import asyncpg
from tenacity import retry, stop_after_attempt, wait_exponential

from .__init__ import BaseService
from src.config import get_settings
from src.database.db_pool import get_db_pool

logger = logging.getLogger(__name__)


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
    match_id: Optional[str] = None
    league_id: Optional[str] = None
    collection_type: str = "match"  # match, league, fixtures
    priority: int = 5
    max_retries: int = 3
    retry_count: int = 0
    status: CollectionStatus = CollectionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    data_points_collected: int = 0

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
            "match_id": self.match_id,
            "league_id": self.league_id,
            "collection_type": self.collection_type,
            "priority": self.priority,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "result": self.result,
            "error": self.error,
            "data_points_collected": self.data_points_collected
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
    circuit_breaker_trips: int = 0
    last_error: Optional[str] = None

    def update(self, tasks: List[FotMobCollectionTask]) -> None:
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

        # 统计数据点
        self.total_data_points = sum(t.data_points_collected for t in tasks)

        # 记录最后一次成功收集时间
        successful_tasks = [t for t in tasks if t.status == CollectionStatus.SUCCESS]
        if successful_tasks:
            self.last_collection_time = max(t.completed_at for t in successful_tasks)


class CircuitBreaker:
    """熔断器实现"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 300,
                 half_open_max_calls: int = 3):
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
        elif self.state == "OPEN":
            if now - self.last_failure_time >= self.recovery_timeout:
                self.state = "HALF_OPEN"
                self.half_open_calls = 0
                logger.info("熔断器状态从OPEN转为HALF_OPEN")
                return True
            return False
        elif self.state == "HALF_OPEN":
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

        if self.failure_count >= self.failure_threshold:
            if self.state != "OPEN":
                self.state = "OPEN"
                logger.warning(f"熔断器触发! 失败次数: {self.failure_count}")

    def get_state(self) -> Dict[str, Any]:
        """获取熔断器状态"""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "recovery_timeout": self.recovery_timeout
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
        self.tasks: List[FotMobCollectionTask] = []
        self.is_running = False
        self.max_concurrent_tasks = self.settings.fotmob.max_concurrent_requests
        self.stats = CollectionStats()

        # 初始化熔断器
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=self.settings.fotmob.circuit_breaker_failure_threshold,
            recovery_timeout=self.settings.fotmob.circuit_breaker_recovery_timeout,
            half_open_max_calls=self.settings.fotmob.circuit_breaker_half_open_max_calls
        )

        # HTTP会话
        self.http_session: Optional[aiohttp.ClientSession] = None

        logger.info("🚀 FotMob数据收集服务初始化完成")

    async def initialize(self) -> bool:
        """初始化服务"""
        try:
            self.logger.info("正在初始化FotMob数据收集服务...")

            # 初始化数据库连接池
            self.db_pool = await get_db_pool()

            # 测试数据库连接
            await self.db_pool.fetchval("SELECT 1")

            # 初始化HTTP会话
            headers = self.settings.fotmob.get_headers()
            timeout = aiohttp.ClientTimeout(total=self.settings.fotmob.timeout)
            self.http_session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout
            )

            self.is_running = True
            self.logger.info("✅ FotMob数据收集服务初始化成功")
            return True

        except Exception as e:
            self.logger.error(f"❌ FotMob数据收集服务初始化失败: {e}")
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
            self.logger.error(f"❌ FotMob数据收集服务关闭失败: {e}")

    def create_match_collection_task(
        self,
        match_id: str,
        priority: int = 5,
        task_id: Optional[str] = None
    ) -> str:
        """创建比赛数据收集任务"""
        if task_id is None:
            task_id = f"match_{match_id}_{int(time.time())}"

        task = FotMobCollectionTask(
            task_id=task_id,
            match_id=match_id,
            collection_type="match",
            priority=priority
        )

        self.tasks.append(task)
        self.logger.info(f"已创建比赛收集任务: {task_id} (match_id: {match_id})")
        return task_id

    def create_league_collection_task(
        self,
        league_id: str,
        priority: int = 3,
        task_id: Optional[str] = None
    ) -> str:
        """创建联赛数据收集任务"""
        if task_id is None:
            task_id = f"league_{league_id}_{int(time.time())}"

        task = FotMobCollectionTask(
            task_id=task_id,
            league_id=league_id,
            collection_type="league",
            priority=priority
        )

        self.tasks.append(task)
        self.logger.info(f"已创建联赛收集任务: {task_id} (league_id: {league_id})")
        return task_id

    async def execute_task(self, task_id: str) -> Dict[str, Any]:
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

            self.logger.error(f"❌ 任务执行失败: {task_id}, 错误: {error_msg}")
            return task.to_dict()

        finally:
            # 更新统计信息
            self.stats.update(self.tasks)

    async def _transform_data(self, raw_data: Dict[str, Any], task: FotMobCollectionTask) -> Dict[str, Any]:
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
                "task_id": task.task_id
            }

            # 根据收集类型进行不同的转换
            if task.collection_type == "match":
                transformed.update({
                    "match_id": task.match_id,
                    "raw_data": raw_data,  # 暂时保存原始数据
                    "processed_data": self._process_match_data(raw_data)
                })
            elif task.collection_type == "league":
                transformed.update({
                    "league_id": task.league_id,
                    "raw_data": raw_data,
                    "processed_data": self._process_league_data(raw_data)
                })

            return transformed

        except Exception as e:
            self.logger.error(f"数据转换失败: {e}")
            raise

    def _process_match_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理比赛数据"""
        processed = {}

        try:
            # 提取基本信息
            if "general" in raw_data:
                general = raw_data["general"]
                processed.update({
                    "home_team": general.get("homeTeam", {}).get("name"),
                    "away_team": general.get("awayTeam", {}).get("name"),
                    "home_score": general.get("homeGoals"),
                    "away_score": general.get("awayGoals"),
                    "status": general.get("statusText"),
                    "match_time": general.get("startDateStr"),
                    "venue": general.get("venue", {}).get("name")
                })

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

            self.logger.debug(f"比赛数据处理完成: {len(processed)} 个字段")
            return processed

        except Exception as e:
            self.logger.error(f"比赛数据处理失败: {e}")
            return {"error": str(e)}

    def _process_league_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理联赛数据"""
        processed = {}

        try:
            # 这里可以添加联赛数据的具体处理逻辑
            processed["league_data"] = raw_data
            processed["processed_at"] = datetime.utcnow().isoformat()

            self.logger.debug(f"联赛数据处理完成")
            return processed

        except Exception as e:
            self.logger.error(f"联赛数据处理失败: {e}")
            return {"error": str(e)}

    async def _load_data(self, data: Dict[str, Any], task: FotMobCollectionTask) -> None:
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

            self.logger.debug(f"数据入库完成: {task.collection_type}")

        except Exception as e:
            self.logger.error(f"数据入库失败: {e}")
            raise

    async def _save_match_data(self, data: Dict[str, Any], task: FotMobCollectionTask) -> None:
        """保存比赛数据到数据库"""
        try:
            # 这里应该实现具体的数据库保存逻辑
            # 由于没有具体的Match模型定义，暂时使用通用SQL

            sql = """
            INSERT INTO matches (
                fotmob_id, home_team, away_team, home_score, away_score,
                status, match_time, venue, lineups, stats, metadata,
                data_source, collection_time
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
            )
            ON CONFLICT (fotmob_id) DO UPDATE SET
                home_team = EXCLUDED.home_team,
                away_team = EXCLUDED.away_team,
                home_score = EXCLUDED.home_score,
                away_score = EXCLUDED.away_score,
                status = EXCLUDED.status,
                match_time = EXCLUDED.match_time,
                venue = EXCLUDED.venue,
                lineups = EXCLUDED.lineups,
                stats = EXCLUDED.stats,
                metadata = EXCLUDED.metadata,
                collection_time = EXCLUDED.collection_time
            """

            await self.db_pool.execute(
                sql,
                task.match_id,
                data.get("home_team"),
                data.get("away_team"),
                data.get("home_score"),
                data.get("away_score"),
                data.get("status"),
                data.get("match_time"),
                data.get("venue"),
                data.get("lineups"),
                data.get("stats"),
                data.get("xg"),
                "fotmob",
                datetime.utcnow()
            )

            self.logger.debug(f"比赛数据已保存: {task.match_id}")

        except Exception as e:
            self.logger.error(f"比赛数据保存失败: {e}")
            raise

    async def _save_league_data(self, data: Dict[str, Any], task: FotMobCollectionTask) -> None:
        """保存联赛数据到数据库"""
        try:
            # 暂时使用通用SQL，实际应该有具体的League模型
            self.logger.info(f"联赛数据保存: {task.league_id} (暂未实现)")

        except Exception as e:
            self.logger.error(f"联赛数据保存失败: {e}")
            raise

    def _count_data_points(self, data: Dict[str, Any]) -> int:
        """计算收集的数据点数量"""
        if isinstance(data, dict):
            return len(data)
        elif isinstance(data, list):
            return len(data)
        else:
            return 1

    async def execute_all_tasks(self, max_concurrent: Optional[int] = None) -> List[Dict[str, Any]]:
        """执行所有待处理的任务"""
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

        self.logger.info(f"🚀 开始执行 {len(pending_tasks)} 个任务，最大并发数: {max_concurrent}")

        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_with_semaphore(task: FotMobCollectionTask) -> Dict[str, Any]:
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

    def get_service_status(self) -> Dict[str, Any]:
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
            "last_collection_time": self.stats.last_collection_time.isoformat() if self.stats.last_collection_time else None,
            "circuit_breaker": self.circuit_breaker.get_state(),
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "last_error": self.stats.last_error
        }