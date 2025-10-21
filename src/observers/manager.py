"""
观察者管理器
Observer Manager

统一管理观察者和被观察者。
Manages observers and subjects centrally.
"""

import asyncio
import logging
from typing import Any, Dict, Optional
from datetime import datetime

from .base import Observer, Subject, ObservableEventType
from .observers import (
    MetricsObserver,
    LoggingObserver,
    AlertingObserver,
    PerformanceObserver,
)
from .subjects import (
    SystemMetricsSubject,
    PredictionMetricsSubject,
    AlertSubject,
    CacheSubject,
)

logger = logging.getLogger(__name__)


class ObserverManager:
    """观察者管理器

    负责创建、管理和协调所有观察者和被观察者。
    Creates, manages, and coordinates all observers and subjects.
    """

    def __init__(self):
        """初始化观察者管理器"""
        self._observers: Dict[str, Observer] = {}
        self._subjects: Dict[str, Subject] = {}
        self._initialized = False
        self._running = False

    async def initialize(self) -> None:
        """初始化观察者系统"""
        if self._initialized:
            return

        logger.info("初始化观察者系统...")

        # 创建观察者
        await self._create_observers()

        # 创建被观察者
        await self._create_subjects()

        # 建立观察关系
        await self._setup_observation_relationships()

        # 配置告警规则
        await self._setup_alert_rules()

        self._initialized = True
        logger.info("观察者系统初始化完成")

    async def _create_observers(self) -> None:
        """创建所有观察者"""
        # 创建指标观察者
        self._observers["metrics"] = MetricsObserver(aggregation_window=60)

        # 创建日志观察者
        self._observers["logging"] = LoggingObserver(log_level=logging.INFO)

        # 创建告警观察者
        self._observers["alerting"] = AlertingObserver()

        # 创建性能观察者
        self._observers["performance"] = PerformanceObserver(window_size=100)

        logger.info(f"创建了 {len(self._observers)} 个观察者")

    async def _create_subjects(self) -> None:
        """创建所有被观察者"""
        # 创建系统指标被观察者
        self._subjects["system_metrics"] = SystemMetricsSubject()

        # 创建预测指标被观察者
        self._subjects["prediction_metrics"] = PredictionMetricsSubject()

        # 创建告警被观察者
        self._subjects["alert"] = AlertSubject()

        # 创建缓存被观察者
        self._subjects["cache"] = CacheSubject()

        logger.info(f"创建了 {len(self._subjects)} 个被观察者")

    async def _setup_observation_relationships(self) -> None:
        """建立观察关系"""
        # 系统指标 -> 指标观察者、日志观察者、告警观察者、性能观察者
        system_subject = self._subjects["system_metrics"]
        await system_subject.attach(self._observers["metrics"])
        await system_subject.attach(self._observers["logging"])
        await system_subject.attach(self._observers["alerting"])
        await system_subject.attach(self._observers["performance"])

        # 预测指标 -> 所有观察者
        prediction_subject = self._subjects["prediction_metrics"]
        for observer in self._observers.values():
            await prediction_subject.attach(observer)

        # 告警 -> 日志观察者、告警观察者
        alert_subject = self._subjects["alert"]
        await alert_subject.attach(self._observers["logging"])
        await alert_subject.attach(self._observers["alerting"])

        # 缓存 -> 指标观察者、日志观察者
        cache_subject = self._subjects["cache"]
        await cache_subject.attach(self._observers["metrics"])
        await cache_subject.attach(self._observers["logging"])

        logger.info("观察关系建立完成")

    async def _setup_alert_rules(self) -> None:
        """配置告警规则"""
        alerting_observer = self._observers["alerting"]

        # CPU使用率告警
        alerting_observer.add_alert_rule(
            name="high_cpu_usage",
            condition=lambda e: (
                e.event_type == ObservableEventType.THRESHOLD_EXCEEDED
                and e.data.get("metric_name") == "cpu_usage"
                and e.data.get("metric_value", 0) > 80
            ),
            severity="warning",
            message_template="CPU使用率过高: {metric_value}%",
            cooldown_minutes=5,
        )

        # 内存使用率告警
        alerting_observer.add_alert_rule(
            name="high_memory_usage",
            condition=lambda e: (
                e.event_type == ObservableEventType.THRESHOLD_EXCEEDED
                and e.data.get("metric_name") == "memory_usage"
                and e.data.get("metric_value", 0) > 85
            ),
            severity="warning",
            message_template="内存使用率过高: {metric_value}%",
            cooldown_minutes=5,
        )

        # 错误率告警
        alerting_observer.add_alert_rule(
            name="high_error_rate",
            condition=lambda e: (
                e.event_type == ObservableEventType.ERROR_OCCURRED
                and e.data.get("error_count", 1) > 10
            ),
            severity="error",
            message_template="错误率过高: {error_count} 个错误",
            cooldown_minutes=2,
        )

        # 响应时间告警
        alerting_observer.add_alert_rule(
            name="slow_response",
            condition=lambda e: (
                e.event_type == ObservableEventType.PERFORMANCE_DEGRADATION
                and e.data.get("type") == "response_time"
                and e.data.get("value", 0) > 2000
            ),
            severity="warning",
            message_template="响应时间过慢: {value}ms",
            cooldown_minutes=3,
        )

        logger.info("告警规则配置完成")

    async def start(self) -> None:
        """启动观察者系统"""
        if not self._initialized:
            await self.initialize()

        if self._running:
            return

        self._running = True
        logger.info("观察者系统已启动")

        # 启动定期任务
        asyncio.create_task(self._periodic_metrics_collection())
        asyncio.create_task(self._periodic_performance_check())

    async def stop(self) -> None:
        """停止观察者系统"""
        self._running = False
        logger.info("观察者系统已停止")

    async def _periodic_metrics_collection(self) -> None:
        """定期收集系统指标"""
        while self._running:
            try:
                # 收集系统指标
                system_subject = self._subjects["system_metrics"]
                if isinstance(system_subject, SystemMetricsSubject):
                    await system_subject.collect_metrics()

                # 等待30秒
                await asyncio.sleep(30)

            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                logger.error(f"收集系统指标失败: {e}")
                await asyncio.sleep(5)

    async def _periodic_performance_check(self) -> None:
        """定期检查性能"""
        while self._running:
            try:
                # 检查预测性能
                prediction_subject = self._subjects["prediction_metrics"]
                if isinstance(prediction_subject, PredictionMetricsSubject):
                    await prediction_subject.check_performance_degradation()

                # 等待60秒
                await asyncio.sleep(60)

            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                logger.error(f"性能检查失败: {e}")
                await asyncio.sleep(5)

    # 便捷方法
    def get_observer(self, name: str) -> Optional[Observer]:
        """获取观察者"""
        return self._observers.get(name)

    def get_subject(self, name: str) -> Optional[Subject]:
        """获取被观察者"""
        return self._subjects.get(name)

    def get_metrics_observer(self) -> Optional[MetricsObserver]:
        """获取指标观察者"""
        return self._observers.get("metrics")

    def get_alerting_observer(self) -> Optional[AlertingObserver]:
        """获取告警观察者"""
        return self._observers.get("alerting")

    def get_system_metrics_subject(self) -> Optional[SystemMetricsSubject]:
        """获取系统指标被观察者"""
        return self._subjects.get("system_metrics")

    def get_prediction_metrics_subject(self) -> Optional[PredictionMetricsSubject]:
        """获取预测指标被观察者"""
        return self._subjects.get("prediction_metrics")

    def get_cache_subject(self) -> Optional[CacheSubject]:
        """获取缓存被观察者"""
        return self._subjects.get("cache")

    # 监控接口
    async def record_prediction(
        self,
        strategy_name: str,
        response_time_ms: float,
        success: bool = True,
        confidence: Optional[float] = None,
    ) -> None:
        """记录预测事件"""
        subject = self.get_prediction_metrics_subject()
        if subject:
            await subject.record_prediction(
                strategy_name=strategy_name,
                response_time_ms=response_time_ms,
                success=success,
                confidence=confidence,
            )

    async def record_cache_hit(self, cache_name: str, key: str) -> None:
        """记录缓存命中"""
        subject = self.get_cache_subject()
        if subject:
            await subject.record_cache_hit(cache_name, key)

    async def record_cache_miss(self, cache_name: str, key: str) -> None:
        """记录缓存未命中"""
        subject = self.get_cache_subject()
        if subject:
            await subject.record_cache_miss(cache_name, key)

    async def trigger_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        source: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """触发告警"""
        subject = self._subjects.get("alert")
        if subject and isinstance(subject, AlertSubject):
            await subject.trigger_alert(alert_type, severity, message, source, data)

    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        result = {}

        # 获取指标观察者的数据
        metrics_observer = self.get_metrics_observer()
        if metrics_observer:
            result["metrics"] = metrics_observer.get_metrics()

        # 获取系统指标
        system_subject = self.get_system_metrics_subject()
        if system_subject:
            result["system_metrics"] = system_subject.get_metrics()

        # 获取预测指标
        prediction_subject = self.get_prediction_metrics_subject()
        if prediction_subject:
            result["prediction_metrics"] = prediction_subject.get_prediction_metrics()

        # 获取缓存统计
        cache_subject = self.get_cache_subject()
        if cache_subject:
            result["cache_stats"] = cache_subject.get_cache_statistics()

        # 获取性能指标
        performance_observer = self._observers.get("performance")
        if performance_observer and isinstance(
            performance_observer, PerformanceObserver
        ):
            result["performance"] = performance_observer.get_performance_metrics()

        return result

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        result = {
            "initialized": self._initialized,
            "running": self._running,
            "observers": {},
            "subjects": {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        # 获取观察者状态
        for name, observer in self._observers.items():
            stats = observer.get_stats()
            stats["enabled"] = observer.is_enabled()
            result["observers"][name] = stats

        # 获取被观察者状态
        for name, subject in self._subjects.items():
            stats = subject.get_stats()
            stats["enabled"] = subject.is_enabled()
            result["subjects"][name] = stats

        # 获取告警历史
        alerting_observer = self.get_alerting_observer()
        if alerting_observer:
            result["recent_alerts"] = alerting_observer.get_alert_history(limit=10)
            result["alert_rules"] = alerting_observer.get_alert_rules()

        return result


# 全局实例
_observer_manager: Optional[ObserverManager] = None


def get_observer_manager() -> ObserverManager:
    """获取全局观察者管理器实例"""
    global _observer_manager
    if _observer_manager is None:
        _observer_manager = ObserverManager()
    return _observer_manager


# 便捷函数
async def initialize_observer_system() -> None:
    """初始化观察者系统"""
    manager = get_observer_manager()
    await manager.initialize()


async def start_observer_system() -> None:
    """启动观察者系统"""
    manager = get_observer_manager()
    await manager.start()


async def stop_observer_system() -> None:
    """停止观察者系统"""
    manager = get_observer_manager()
    await manager.stop()
