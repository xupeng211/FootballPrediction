"""
观察者模式实现

用于监控和日志系统的通知机制
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
import asyncio
import logging

from src.core.logging import get_logger


class Observer(ABC):
    """观察者抽象基类"""

    @abstractmethod
    async def update(self, subject: "Subject", event_type: str, data: Any) -> None:
        """接收通知的抽象方法"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """获取观察者名称"""
        pass


class Subject(ABC):
    """被观察者抽象基类"""

    def __init__(self):
        self._observers: List[Observer] = []
        self._event_history: List[Dict[str, Any]] = []
        self.logger = get_logger(f"subject.{self.__class__.__name__}")

    def attach(self, observer: Observer) -> None:
        """添加观察者"""
        if observer not in self._observers:
            self._observers.append(observer)
            self.logger.debug(f"Attached observer: {observer.get_name()}")

    def detach(self, observer: Observer) -> None:
        """移除观察者"""
        if observer in self._observers:
            self._observers.remove(observer)
            self.logger.debug(f"Detached observer: {observer.get_name()}")

    async def notify(self, event_type: str, data: Any) -> None:
        """通知所有观察者"""
        event = {
            "timestamp": datetime.now(),
            "type": event_type,
            "data": data,
            "subject": self.__class__.__name__,
        }
        self._event_history.append(event)

        # 限制历史记录数量
        if len(self._event_history) > 1000:
            self._event_history = self._event_history[-500:]

        self.logger.debug(
            f"Notifying {len(self._observers)} observers of event: {event_type}"
        )

        # 并发通知所有观察者
        tasks = []
        for observer in self._observers:
            task = asyncio.create_task(
                self._notify_observer(observer, event_type, data)
            )
            tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _notify_observer(
        self, observer: Observer, event_type: str, data: Any
    ) -> None:
        """安全地通知单个观察者"""
        try:
            await observer.update(self, event_type, data)
        except Exception as e:
            self.logger.error(f"Error notifying observer {observer.get_name()}: {e}")

    def get_observers(self) -> List[str]:
        """获取所有观察者名称"""
        return [observer.get_name() for observer in self._observers]

    def get_event_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取事件历史"""
        if limit:
            return self._event_history[-limit:]
        return self._event_history.copy()


class MetricsObserver(Observer):
    """指标收集观察者"""

    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "event_counts": {},
            "last_events": {},
            "total_events": 0,
        }
        self.logger = get_logger("observer.metrics")

    async def update(self, subject: Subject, event_type: str, data: Any) -> None:
        """收集指标"""
        # 更新事件计数
        if event_type not in self.metrics["event_counts"]:
            self.metrics["event_counts"][event_type] = 0
        self.metrics["event_counts"][event_type] += 1

        # 记录最后事件
        self.metrics["last_events"][event_type] = {
            "timestamp": datetime.now(),
            "subject": subject.__class__.__name__,
            "data_summary": str(data)[:100] if data else None,
        }

        # 更新总计数
        self.metrics["total_events"] += 1

        self.logger.debug(f"Metrics updated for event: {event_type}")

    def get_name(self) -> str:
        return "MetricsObserver"

    def get_metrics(self) -> Dict[str, Any]:
        """获取收集的指标"""
        return self.metrics.copy()


class LoggingObserver(Observer):
    """日志记录观察者"""

    def __init__(self, log_level: int = logging.INFO):
        self.log_level = log_level
        self.logger = get_logger("observer.logging")

    async def update(self, subject: Subject, event_type: str, data: Any) -> None:
        """记录日志"""
        log_message = f"[{subject.__class__.__name__}] Event: {event_type}"

        if data:
            log_message += f" | Data: {str(data)[:200]}"

        if self.log_level >= logging.ERROR:
            self.logger.error(log_message)
        elif self.log_level >= logging.WARNING:
            self.logger.warning(log_message)
        elif self.log_level >= logging.INFO:
            self.logger.info(log_message)
        else:
            self.logger.debug(log_message)

    def get_name(self) -> str:
        return "LoggingObserver"


class AlertingObserver(Observer):
    """告警通知观察者"""

    def __init__(self):
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self.alert_history: List[Dict[str, Any]] = []
        self.logger = get_logger("observer.alerting")

    def add_alert_rule(self, event_type: str, condition: str, message: str) -> None:
        """添加告警规则"""
        self.alert_rules[event_type] = {
            "condition": condition,
            "message": message,
            "created_at": datetime.now(),
        }
        self.logger.info(f"Added alert rule for event: {event_type}")

    async def update(self, subject: Subject, event_type: str, data: Any) -> None:
        """检查并触发告警"""
        if event_type in self.alert_rules:
            rule = self.alert_rules[event_type]

            # 简单的条件检查（可以根据需要扩展）
            should_alert = self._evaluate_condition(rule["condition"], data)

            if should_alert:
                alert = {
                    "timestamp": datetime.now(),
                    "subject": subject.__class__.__name__,
                    "event_type": event_type,
                    "message": rule["message"],
                    "data": data,
                }

                self.alert_history.append(alert)

                # 记录告警
                self.logger.warning(
                    f"ALERT: {rule['message']} | Event: {event_type} | Subject: {subject.__class__.__name__}"
                )

                # 限制告警历史
                if len(self.alert_history) > 100:
                    self.alert_history = self.alert_history[-50:]

    def _evaluate_condition(self, condition: str, data: Any) -> bool:
        """评估告警条件（简单实现）"""
        # 这里可以实现更复杂的条件评估逻辑
        if condition == "always":
            return True
        elif condition == "error" and isinstance(data, dict) and data.get("error"):
            return True
        elif condition == "timeout" and isinstance(data, dict) and data.get("timeout"):
            return True

        return False

    def get_name(self) -> str:
        return "AlertingObserver"

    def get_alert_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取告警历史"""
        if limit:
            return self.alert_history[-limit:]
        return self.alert_history.copy()


class ObservableService(Subject):
    """可观察的服务基类"""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name
        self._metrics = {"calls": 0, "errors": 0, "last_activity": None}

    async def on_service_start(self) -> None:
        """服务启动事件"""
        await self.notify("service.start", {"service": self.service_name})
        self._metrics["last_activity"] = datetime.now()  # type: ignore

    async def on_service_stop(self) -> None:
        """服务停止事件"""
        await self.notify("service.stop", {"service": self.service_name})
        self._metrics["last_activity"] = datetime.now()  # type: ignore

    async def on_service_error(self, error: Exception) -> None:
        """服务错误事件"""
        self._metrics["errors"] += 1  # type: ignore
        await self.notify(
            "service.error",
            {
                "service": self.service_name,
                "error": str(error),
                "error_type": type(error).__name__,
            },
        )

    async def on_operation_start(self, operation: str, params: Dict[str, Any]) -> None:
        """操作开始事件"""
        self._metrics["calls"] += 1  # type: ignore
        await self.notify(
            "operation.start",
            {"service": self.service_name, "operation": operation, "params": params},
        )

    async def on_operation_complete(
        self, operation: str, result: Any, duration: float
    ) -> None:
        """操作完成事件"""
        await self.notify(
            "operation.complete",
            {
                "service": self.service_name,
                "operation": operation,
                "duration": duration,
                "result_type": type(result).__name__,
            },
        )

    def get_service_metrics(self) -> Dict[str, Any]:
        """获取服务指标"""
        return self._metrics.copy()


# 示例使用
class PredictionService(ObservableService):
    """预测服务示例"""

    def __init__(self):
        super().__init__("PredictionService")

    async def predict_match(self, match_id: int) -> Dict[str, Any]:
        """预测比赛"""
        await self.on_operation_start("predict_match", {"match_id": match_id})

        try:
            # 模拟预测逻辑
            await asyncio.sleep(0.1)
            prediction = {
                "match_id": match_id,
                "prediction": "home_win",
                "confidence": 0.75,
            }

            await self.on_operation_complete("predict_match", prediction, 0.1)
            return prediction

        except Exception as e:
            await self.on_service_error(e)
            raise


# 工厂函数
def create_observer_system() -> Dict[str, Observer]:
    """创建观察者系统"""
    return {
        "metrics": MetricsObserver(),
        "logging": LoggingObserver(),
        "alerting": AlertingObserver(),
    }


# 便捷函数
async def setup_service_observers(
    service: ObservableService, observers: List[Observer]
) -> None:
    """为服务设置观察者"""
    for observer in observers:
        service.attach(observer)
        await service.notify("observer.attached", {"observer": observer.get_name()})
