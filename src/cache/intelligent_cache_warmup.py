"""
智能缓存预热系统
Intelligent Cache Warmup System

提供基于机器学习、访问模式分析和业务规则的智能缓存预热解决方案。
"""

import asyncio
import logging
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class WarmupStrategy(Enum):
    """预热策略"""

    ACCESS_PATTERN = "access_pattern"  # 基于访问模式
    BUSINESS_RULES = "business_rules"  # 基于业务规则
    PREDICTIVE = "predictive"  # 预测性预热
    HYBRID = "hybrid"  # 混合策略
    SCHEDULED = "scheduled"  # 定时预热


class PriorityLevel(Enum):
    """优先级级别"""

    CRITICAL = "critical"  # 关键数据
    HIGH = "high"  # 高优先级
    MEDIUM = "medium"  # 中等优先级
    LOW = "low"  # 低优先级
    BACKGROUND = "background"  # 后台预热


@dataclass
class AccessPattern:
    """访问模式"""

    key: str
    access_frequency: float = 0.0  # 访问频率
    access_times: list[datetime] = field(default_factory=list)
    hourly_distribution: dict[int, int] = field(
        default_factory=lambda: defaultdict(int)
    )
    daily_distribution: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    last_access: datetime | None = None
    access_duration: float = 0.0  # 平均访问持续时间
    correlation_score: float = 0.0  # 与其他键的关联度

    def add_access(self, timestamp: datetime, duration: float = 0.0):
        """添加访问记录"""
        self.access_times.append(timestamp)
        self.last_access = timestamp
        self.access_duration = (
            self.access_duration * (len(self.access_times) - 1) + duration
        ) / len(self.access_times)

        # 更新时间分布
        hour = timestamp.hour
        day = timestamp.weekday()
        self.hourly_distribution[hour] += 1
        self.daily_distribution[day] += 1

    def calculate_frequency(self, time_window: timedelta = timedelta(days=7)) -> float:
        """计算访问频率"""
        if not self.access_times:
            return 0.0

        cutoff_time = datetime.utcnow() - time_window
        recent_accesses = [t for t in self.access_times if t > cutoff_time]

        if not recent_accesses:
            return 0.0

        time_span = (max(recent_accesses) - min(recent_accesses)).total_seconds()
        if time_span == 0:
            return len(recent_accesses)

        return len(recent_accesses) / (time_span / 3600)  # 每小时访问次数

    def predict_next_access(self) -> datetime | None:
        """预测下次访问时间"""
        if len(self.access_times) < 3:
            return None

        # 简单的时间序列预测
        recent_times = sorted(self.access_times[-10:])
        intervals = []

        for i in range(1, len(recent_times)):
            interval = (recent_times[i] - recent_times[i - 1]).total_seconds()
            intervals.append(interval)

        if not intervals:
            return None

        avg_interval = sum(intervals) / len(intervals)
        next_access = self.last_access + timedelta(seconds=avg_interval)
        return next_access


@dataclass
class WarmupTask:
    """预热任务"""

    task_id: str
    key: str
    priority: PriorityLevel
    data_loader: Callable
    estimated_size: int = 0
    ttl: int | None = None
    dependencies: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: str = "pending"  # pending, running, completed, failed, cancelled
    retry_count: int = 0
    max_retries: int = 3
    error_message: str | None = None
    execution_time: float = 0.0
    result: Any | None = None


@dataclass
class WarmupPlan:
    """预热计划"""

    plan_id: str
    strategy: WarmupStrategy
    tasks: list[WarmupTask] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_at: datetime | None = None
    status: str = "draft"  # draft, scheduled, running, completed, failed
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0


class AccessPatternAnalyzer:
    """访问模式分析器"""

    def __init__(self):
        self.patterns: dict[str, AccessPattern] = {}
        self.correlation_matrix: dict[str, dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        self.session_history: list[list[str]] = []  # 会话历史
        self.lock = threading.Lock()

    def record_access(
        self, key: str, session_id: str | None = None, duration: float = 0.0
    ):
        """记录访问"""
        with self.lock:
            if key not in self.patterns:
                self.patterns[key] = AccessPattern(key=key)

            self.patterns[key].add_access(datetime.utcnow(), duration)

            # 记录会话历史
            if session_id:
                # 这里可以实现更复杂的会话跟踪
                pass

    def analyze_patterns(
        self, time_window: timedelta = timedelta(days=7)
    ) -> dict[str, Any]:
        """分析访问模式"""
        analysis = {
            "total_keys": len(self.patterns),
            "high_frequency_keys": [],
            "time_based_patterns": {},
            "correlation_clusters": [],
            "predictions": {},
        }

        for key, pattern in self.patterns.items():
            frequency = pattern.calculate_frequency(time_window)
            pattern.access_frequency = frequency

            if frequency > 10:  # 高频访问
                analysis["high_frequency_keys"].append(
                    {
                        "key": key,
                        "frequency": frequency,
                        "last_access": (
                            pattern.last_access.isoformat()
                            if pattern.last_access
                            else None
                        ),
                    }
                )

            # 时间模式分析
            if pattern.hourly_distribution:
                peak_hour = max(pattern.hourly_distribution.items(), key=lambda x: x[1])
                analysis["time_based_patterns"][key] = {
                    "peak_hour": peak_hour[0],
                    "peak_count": peak_hour[1],
                    "distribution": dict(pattern.hourly_distribution),
                }

            # 预测下次访问
            next_access = pattern.predict_next_access()
            if next_access:
                analysis["predictions"][key] = next_access.isoformat()

        return analysis

    def find_correlated_keys(self, key: str, threshold: float = 0.3) -> list[str]:
        """查找关联键"""
        if key not in self.correlation_matrix:
            return []

        correlations = self.correlation_matrix[key]
        return [k for k, v in correlations.items() if v >= threshold]

    def update_correlation_matrix(self, access_sequence: list[str]):
        """更新关联矩阵"""
        for i in range(len(access_sequence)):
            for j in range(i + 1, len(access_sequence)):
                key1, key2 = access_sequence[i], access_sequence[j]
                self.correlation_matrix[key1][key2] += 1
                self.correlation_matrix[key2][key1] += 1

    def get_warmup_candidates(self, limit: int = 100) -> list[tuple[str, float]]:
        """获取预热候选键"""
        candidates = []

        for key, pattern in self.patterns.items():
            # 综合评分：频率 + 时效性 + 关联度
            frequency_score = min(pattern.access_frequency / 100, 1.0)

            # 时效性评分（最近访问时间越近，分数越高）
            if pattern.last_access:
                time_diff = (datetime.utcnow() - pattern.last_access).total_seconds()
                recency_score = max(0, 1 - time_diff / (7 * 24 * 3600))  # 7天内衰减
            else:
                recency_score = 0.0

            # 关联度评分
            correlation_score = pattern.correlation_score

            total_score = (
                frequency_score * 0.5 + recency_score * 0.3 + correlation_score * 0.2
            )

            candidates.append((key, total_score))

        # 按分数排序
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:limit]


class PredictiveModel(ABC):
    """预测模型抽象类"""

    @abstractmethod
    def train(self, training_data: list[dict[str, Any]]) -> bool:
        """训练模型"""
        pass

    @abstractmethod
    def predict(self, input_data: dict[str, Any]) -> float:
        """预测"""
        pass

    @abstractmethod
    def get_feature_importance(self) -> dict[str, float]:
        """获取特征重要性"""
        pass


class SimpleFrequencyPredictor(PredictiveModel):
    """简单频率预测器"""

    def __init__(self):
        self.frequencies: dict[str, float] = {}
        self.time_weights: dict[int, float] = {}

    def train(self, training_data: list[dict[str, Any]]) -> bool:
        """训练频率模型"""
        try:
            for record in training_data:
                key = record["key"]
                frequency = record.get("frequency", 0.0)
                hour = record.get("hour", datetime.utcnow().hour)

                self.frequencies[key] = frequency
                self.time_weights[hour] = self.time_weights.get(hour, 0) + frequency

            # 归一化时间权重
            total_weight = sum(self.time_weights.values())
            if total_weight > 0:
                for hour in self.time_weights:
                    self.time_weights[hour] /= total_weight

            return True

        except Exception as e:
            logger.error(f"Error training frequency predictor: {e}")
            return False

    def predict(self, input_data: dict[str, Any]) -> float:
        """预测访问概率"""
        key = input_data.get("key", "")
        hour = input_data.get("hour", datetime.utcnow().hour)

        base_frequency = self.frequencies.get(key, 0.0)
        time_weight = self.time_weights.get(hour, 0.1)

        return base_frequency * time_weight

    def get_feature_importance(self) -> dict[str, float]:
        """获取特征重要性"""
        return {"frequency": 0.7, "time_weight": 0.3}


class IntelligentCacheWarmupManager:
    """智能缓存预热管理器"""

    def __init__(self, cache_manager, config: dict[str, Any] | None = None):
        self.cache_manager = cache_manager
        self.config = config or {}

        # 核心组件
        self.pattern_analyzer = AccessPatternAnalyzer()
        self.predictive_model = SimpleFrequencyPredictor()

        # 任务管理
        self.warmup_tasks: dict[str, WarmupTask] = {}
        self.warmup_plans: dict[str, WarmupPlan] = {}
        self.task_queue = asyncio.PriorityQueue()

        # 执行器
        self.max_concurrent_tasks = self.config.get("max_concurrent_tasks", 5)
        self.running_tasks: set[str] = set()
        self.executor_running = False

        # 策略配置
        self.strategies = {
            WarmupStrategy.ACCESS_PATTERN: self._access_pattern_strategy,
            WarmupStrategy.BUSINESS_RULES: self._business_rules_strategy,
            WarmupStrategy.PREDICTIVE: self._predictive_strategy,
            WarmupStrategy.HYBRID: self._hybrid_strategy,
            WarmupStrategy.SCHEDULED: self._scheduled_strategy,
        }

        # 数据加载器注册表
        self.data_loaders: dict[str, Callable] = {}

        # 统计信息
        self.stats = {
            "total_warmups": 0,
            "successful_warmups": 0,
            "failed_warmups": 0,
            "total_execution_time": 0.0,
            "cache_hits_prevented": 0,
            "memory_saved": 0,
        }

        # 事件处理器
        self.event_handlers: dict[str, list[Callable]] = defaultdict(list)

    def register_data_loader(self, key_pattern: str, loader: Callable):
        """注册数据加载器"""
        self.data_loaders[key_pattern] = loader

    async def record_access(
        self, key: str, session_id: str | None = None, duration: float = 0.0
    ):
        """记录访问（用于模式学习）"""
        self.pattern_analyzer.record_access(key, session_id, duration)

    async def create_warmup_plan(
        self,
        strategy: WarmupStrategy,
        keys: list[str] | None = None,
        priority_filter: list[PriorityLevel] | None = None,
        scheduled_at: datetime | None = None,
    ) -> str:
        """创建预热计划"""
        plan_id = f"plan_{int(time.time() * 1000)}"
        plan = WarmupPlan(plan_id=plan_id, strategy=strategy, scheduled_at=scheduled_at)

        # 根据策略生成任务
        tasks = await self.strategies[strategy](keys, priority_filter)
        plan.tasks = tasks
        plan.total_tasks = len(tasks)

        self.warmup_plans[plan_id] = plan

        logger.info(
            f"Created warmup plan {plan_id} with {len(tasks)} tasks using {strategy.value} strategy"
        )
        return plan_id

    async def execute_warmup_plan(self, plan_id: str) -> bool:
        """执行预热计划"""
        if plan_id not in self.warmup_plans:
            raise ValueError(f"Warmup plan {plan_id} not found")

        plan = self.warmup_plans[plan_id]
        plan.status = "running"

        try:
            # 启动任务执行器
            if not self.executor_running:
                await self.start_task_executor()

            # 将任务加入队列
            for task in plan.tasks:
                priority = self._get_priority_value(task.priority)
                await self.task_queue.put((priority, task.task_id, task))

            # 等待所有任务完成
            while plan.completed_tasks + plan.failed_tasks < plan.total_tasks:
                await asyncio.sleep(1)

            # 更新计划状态
            if plan.failed_tasks == 0:
                plan.status = "completed"
            else:
                plan.status = "failed"

            return plan.status == "completed"

        except Exception as e:
            logger.error(f"Error executing warmup plan {plan_id}: {e}")
            plan.status = "failed"
            return False

    async def _access_pattern_strategy(
        self,
        keys: list[str] | None = None,
        priority_filter: list[PriorityLevel] | None = None,
    ) -> list[WarmupTask]:
        """基于访问模式的预热策略"""
        candidates = self.pattern_analyzer.get_warmup_candidates(limit=200)

        if keys:
            # 过滤指定的键
            candidates = [(k, s) for k, s in candidates if k in keys]

        tasks = []
        for key, score in candidates:
            if not self._should_include_key(key, priority_filter):
                continue

            priority = self._determine_priority(score)
            data_loader = self._get_data_loader(key)

            if data_loader:
                task = WarmupTask(
                    task_id=f"task_{key}_{int(time.time() * 1000)}",
                    key=key,
                    priority=priority,
                    data_loader=data_loader,
                )
                tasks.append(task)

        return tasks

    async def _business_rules_strategy(
        self,
        keys: list[str] | None = None,
        priority_filter: list[PriorityLevel] | None = None,
    ) -> list[WarmupTask]:
        """基于业务规则的预热策略"""
        tasks = []
        business_rules = self.config.get("business_rules", {})

        for rule in business_rules.get("warmup_rules", []):
            if self._evaluate_business_rule(rule):
                rule_keys = rule.get("keys", [])
                if keys:
                    rule_keys = [k for k in rule_keys if k in keys]

                for key in rule_keys:
                    if not self._should_include_key(key, priority_filter):
                        continue

                    priority = PriorityLevel(rule.get("priority", "medium"))
                    data_loader = self._get_data_loader(key)
                    ttl = rule.get("ttl")

                    if data_loader:
                        task = WarmupTask(
                            task_id=f"task_{key}_{int(time.time() * 1000)}",
                            key=key,
                            priority=priority,
                            data_loader=data_loader,
                            ttl=ttl,
                        )
                        tasks.append(task)

        return tasks

    async def _predictive_strategy(
        self,
        keys: list[str] | None = None,
        priority_filter: list[PriorityLevel] | None = None,
    ) -> list[WarmupTask]:
        """预测性预热策略"""
        # 准备训练数据
        training_data = []
        patterns = self.pattern_analyzer.patterns

        for key, pattern in patterns.items():
            training_data.append(
                {
                    "key": key,
                    "frequency": pattern.access_frequency,
                    "hour": (
                        pattern.last_access.hour
                        if pattern.last_access
                        else datetime.utcnow().hour
                    ),
                }
            )

        # 训练预测模型
        if training_data:
            self.predictive_model.train(training_data)

        # 生成预测任务
        current_hour = datetime.utcnow().hour
        tasks = []

        for key in patterns.keys():
            if keys and key not in keys:
                continue

            if not self._should_include_key(key, priority_filter):
                continue

            # 预测访问概率
            prediction = self.predictive_model.predict(
                {"key": key, "hour": current_hour}
            )

            if prediction > 0.1:  # 预测概率阈值
                priority = self._determine_priority(prediction * 100)
                data_loader = self._get_data_loader(key)

                if data_loader:
                    task = WarmupTask(
                        task_id=f"task_{key}_{int(time.time() * 1000)}",
                        key=key,
                        priority=priority,
                        data_loader=data_loader,
                    )
                    tasks.append(task)

        return tasks

    async def _hybrid_strategy(
        self,
        keys: list[str] | None = None,
        priority_filter: list[PriorityLevel] | None = None,
    ) -> list[WarmupTask]:
        """混合策略"""
        # 结合多种策略的结果
        pattern_tasks = await self._access_pattern_strategy(keys, priority_filter)
        business_tasks = await self._business_rules_strategy(keys, priority_filter)
        predictive_tasks = await self._predictive_strategy(keys, priority_filter)

        # 合并并去重
        all_tasks = {}
        for task in pattern_tasks + business_tasks + predictive_tasks:
            if (
                task.key not in all_tasks
                or task.priority.value < all_tasks[task.key].priority.value
            ):
                all_tasks[task.key] = task

        return list(all_tasks.values())

    async def _scheduled_strategy(
        self,
        keys: list[str] | None = None,
        priority_filter: list[PriorityLevel] | None = None,
    ) -> list[WarmupTask]:
        """定时预热策略"""
        current_hour = datetime.utcnow().hour
        scheduled_warmups = self.config.get("scheduled_warmups", {})

        tasks = []
        for _schedule_key, schedule_config in scheduled_warmups.items():
            if schedule_config.get("hour") == current_hour:
                schedule_keys = schedule_config.get("keys", [])

                if keys:
                    schedule_keys = [k for k in schedule_keys if k in keys]

                for key in schedule_keys:
                    if not self._should_include_key(key, priority_filter):
                        continue

                    priority = PriorityLevel(schedule_config.get("priority", "medium"))
                    data_loader = self._get_data_loader(key)
                    ttl = schedule_config.get("ttl")

                    if data_loader:
                        task = WarmupTask(
                            task_id=f"task_{key}_{int(time.time() * 1000)}",
                            key=key,
                            priority=priority,
                            data_loader=data_loader,
                            ttl=ttl,
                            scheduled_at=datetime.utcnow(),
                        )
                        tasks.append(task)

        return tasks

    def _should_include_key(
        self, key: str, priority_filter: list[PriorityLevel] | None
    ) -> bool:
        """检查是否应该包含键"""
        if not priority_filter:
            return True

        # 这里可以根据键的属性确定优先级
        # 简化实现，默认为medium
        key_priority = PriorityLevel.MEDIUM
        return key_priority in priority_filter

    def _determine_priority(self, score: float) -> PriorityLevel:
        """根据分数确定优先级"""
        if score >= 80:
            return PriorityLevel.CRITICAL
        elif score >= 60:
            return PriorityLevel.HIGH
        elif score >= 40:
            return PriorityLevel.MEDIUM
        elif score >= 20:
            return PriorityLevel.LOW
        else:
            return PriorityLevel.BACKGROUND

    def _get_priority_value(self, priority: PriorityLevel) -> int:
        """获取优先级数值"""
        priority_values = {
            PriorityLevel.CRITICAL: 1,
            PriorityLevel.HIGH: 2,
            PriorityLevel.MEDIUM: 3,
            PriorityLevel.LOW: 4,
            PriorityLevel.BACKGROUND: 5,
        }
        return priority_values.get(priority, 3)

    def _get_data_loader(self, key: str) -> Callable | None:
        """获取数据加载器"""
        # 查找匹配的加载器
        for pattern, loader in self.data_loaders.items():
            if pattern in key or key in pattern:
                return loader

        # 默认加载器
        return self._default_data_loader

    async def _default_data_loader(self, key: str) -> Any:
        """默认数据加载器"""
        # 这里可以实现默认的数据加载逻辑
        logger.warning(f"Using default data loader for key: {key}")
        return None

    def _evaluate_business_rule(self, rule: dict[str, Any]) -> bool:
        """评估业务规则"""
        conditions = rule.get("conditions", [])

        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator")
            value = condition.get("value")

            # 这里可以实现具体的条件评估逻辑
            # 简化实现
            if field == "time" and operator == "between":
                current_hour = datetime.utcnow().hour
                start, end = value
                if not (start <= current_hour <= end):
                    return False

        return True

    async def start_task_executor(self):
        """启动任务执行器"""
        if self.executor_running:
            return

        self.executor_running = True
        asyncio.create_task(self._task_executor_loop())

    async def stop_task_executor(self):
        """停止任务执行器"""
        self.executor_running = False

    async def _task_executor_loop(self):
        """任务执行循环"""
        while self.executor_running:
            try:
                # 控制并发数
                while len(self.running_tasks) >= self.max_concurrent_tasks:
                    await asyncio.sleep(0.1)

                # 获取下一个任务
                try:
                    priority, task_id, task = await asyncio.wait_for(
                        self.task_queue.get(), timeout=1.0
                    )
                except TimeoutError:
                    continue

                # 检查任务是否已被取消
                if task.status in ["cancelled", "completed", "failed"]:
                    continue

                # 执行任务
                self.running_tasks.add(task_id)
                asyncio.create_task(self._execute_warmup_task(task))

            except Exception as e:
                logger.error(f"Error in task executor loop: {e}")
                await asyncio.sleep(1)

    async def _execute_warmup_task(self, task: WarmupTask):
        """执行预热任务"""
        task.status = "running"
        task.started_at = datetime.utcnow()

        try:
            start_time = time.time()

            # 执行数据加载
            result = await task.data_loader(task.key)
            task.result = result

            # 存储到缓存
            if result is not None:
                success = await self.cache_manager.set(task.key, result, task.ttl)

                if success:
                    task.status = "completed"
                    self.stats["successful_warmups"] += 1
                    self.stats["memory_saved"] += task.estimated_size
                else:
                    task.status = "failed"
                    task.error_message = "Failed to store in cache"
                    self.stats["failed_warmups"] += 1
            else:
                task.status = "failed"
                task.error_message = "Data loader returned None"
                self.stats["failed_warmups"] += 1

        except Exception as e:
            logger.error(f"Error executing warmup task {task.task_id}: {e}")
            task.status = "failed"
            task.error_message = str(e)
            task.retry_count += 1
            self.stats["failed_warmups"] += 1

            # 重试逻辑
            if task.retry_count < task.max_retries:
                task.status = "pending"
                delay = min(2**task.retry_count, 60)  # 指数退避
                await asyncio.sleep(delay)
                priority = self._get_priority_value(task.priority)
                await self.task_queue.put((priority, task.task_id, task))

        finally:
            task.completed_at = datetime.utcnow()
            task.execution_time = time.time() - start_time
            self.stats["total_execution_time"] += task.execution_time
            self.stats["total_warmups"] += 1

            # 更新计划统计
            for plan in self.warmup_plans.values():
                if task.task_id in [t.task_id for t in plan.tasks]:
                    if task.status == "completed":
                        plan.completed_tasks += 1
                    elif task.status == "failed":
                        plan.failed_tasks += 1
                    break

            # 从运行任务集合中移除
            self.running_tasks.discard(task.task_id)

            # 触发事件
            await self._trigger_event(
                "task_completed",
                {
                    "task_id": task.task_id,
                    "status": task.status,
                    "execution_time": task.execution_time,
                },
            )

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.warmup_tasks:
            task = self.warmup_tasks[task_id]
            if task.status in ["pending", "running"]:
                task.status = "cancelled"
                return True
        return False

    async def cancel_plan(self, plan_id: str) -> bool:
        """取消预热计划"""
        if plan_id in self.warmup_plans:
            plan = self.warmup_plans[plan_id]
            if plan.status in ["draft", "scheduled", "running"]:
                # 取消所有未完成的任务
                for task in plan.tasks:
                    if task.status in ["pending", "running"]:
                        await self.cancel_task(task.task_id)

                plan.status = "cancelled"
                return True
        return False

    async def get_warmup_statistics(self) -> dict[str, Any]:
        """获取预热统计信息"""
        analysis = self.pattern_analyzer.analyze_patterns()

        return {
            "statistics": self.stats.copy(),
            "running_tasks": len(self.running_tasks),
            "pending_tasks": self.task_queue.qsize(),
            "total_plans": len(self.warmup_plans),
            "pattern_analysis": analysis,
            "model_info": {
                "type": type(self.predictive_model).__name__,
                "feature_importance": self.predictive_model.get_feature_importance(),
            },
            "executor_status": {
                "running": self.executor_running,
                "max_concurrent": self.max_concurrent_tasks,
                "current_concurrent": len(self.running_tasks),
            },
        }

    async def _trigger_event(self, event_name: str, data: dict[str, Any]):
        """触发事件"""
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_name}: {e}")

    def add_event_handler(self, event_name: str, handler: Callable):
        """添加事件处理器"""
        self.event_handlers[event_name].append(handler)

    async def auto_warmup(
        self,
        strategy: WarmupStrategy = WarmupStrategy.HYBRID,
        schedule_interval: int = 3600,
    ) -> str:
        """自动预热（定时执行）"""
        plan_id = await self.create_warmup_plan(strategy)

        # 创建定时任务
        async def scheduled_warmup():
            while True:
                try:
                    await self.execute_warmup_plan(plan_id)
                    await asyncio.sleep(schedule_interval)
                except Exception as e:
                    logger.error(f"Auto warmup error: {e}")
                    await asyncio.sleep(60)  # 错误后等待1分钟

        asyncio.create_task(scheduled_warmup())
        logger.info(
            f"Auto warmup scheduled with {strategy.value} strategy every {schedule_interval} seconds"
        )

        return plan_id


# 全局智能缓存预热管理器实例
_warmup_manager: IntelligentCacheWarmupManager | None = None


def get_intelligent_warmup_manager() -> IntelligentCacheWarmupManager | None:
    """获取全局智能缓存预热管理器实例"""
    global _warmup_manager
    return _warmup_manager


async def initialize_intelligent_warmup(
    cache_manager, config: dict[str, Any] | None = None
) -> IntelligentCacheWarmupManager:
    """初始化智能缓存预热管理器"""
    global _warmup_manager

    _warmup_manager = IntelligentCacheWarmupManager(cache_manager, config)
    await _warmup_manager.start_task_executor()

    logger.info("Intelligent cache warmup manager initialized")
    return _warmup_manager
