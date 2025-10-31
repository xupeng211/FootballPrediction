"""
观察者模式模块
Observer Pattern Module

提供观察者模式的实现，定义对象间的一对多依赖关系.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import threading
import queue
import json


class Observer(ABC):
    """观察者抽象基类

    定义观察者的更新接口.
    """

    @abstractmethod
    def update(self, subject: 'Subject', data: Optional[Any] = None) -> None:
        """接收主题更新的通知

        Args:
            subject: 发出通知的主题
            data: 更新的数据
        """
        pass

    @abstractmethod
    def get_observer_id(self) -> str:
        """获取观察者ID"""
        pass


class Subject(ABC):
    """主题抽象基类

    管理观察者并发出通知.
    """

    def __init__(self):
        """初始化主题"""
        self._observers: List[Observer] = []
        self._changed = False
        self._lock = threading.Lock()

    def attach(self, observer: Observer) -> None:
        """添加观察者

        Args:
            observer: 要添加的观察者
        """
        with self._lock:
            if observer not in self._observers:
                self._observers.append(observer)

    def detach(self, observer: Observer) -> None:
        """移除观察者

        Args:
            observer: 要移除的观察者
        """
        with self._lock:
            if observer in self._observers:
                self._observers.remove(observer)

    def notify(self, data: Optional[Any] = None) -> None:
        """通知所有观察者

        Args:
            data: 要传递的数据
        """
        with self._lock:
            observers_copy = self._observers.copy()

        for observer in observers_copy:
            try:
                observer.update(self, data)
            except Exception as e:
                print(f"通知观察者失败 {observer.get_observer_id()}: {e}")

    def clear_observers(self) -> None:
        """清除所有观察者"""
        with self._lock:
            self._observers.clear()

    def get_observer_count(self) -> int:
        """获取观察者数量"""
        return len(self._observers)

    def has_changed(self) -> bool:
        """检查是否发生变化"""
        return self._changed

    def set_changed(self) -> None:
        """标记为已变化"""
        self._changed = True

    def clear_changed(self) -> None:
        """清除变化标记"""
        self._changed = False


class ConcreteSubject(Subject):
    """具体主题类

    实现具体的状态管理逻辑.
    """

    def __init__(self, name: str = "ConcreteSubject"):
        """初始化具体主题

        Args:
            name: 主题名称
        """
        super().__init__()
        self.name = name
        self._state: Dict[str, Any] = {}
        self._history: List[Dict[str, Any]] = []

    def get_state(self, key: str) -> Any:
        """获取状态值

        Args:
            key: 状态键

        Returns:
            Any: 状态值
        """
        return self._state.get(key)

    def set_state(self, key: str, value: Any) -> None:
        """设置状态值

        Args:
            key: 状态键
            value: 状态值
        """
        old_value = self._state.get(key)
        self._state[key] = value

        if old_value != value:
            self.set_changed()
            self._record_change(key, old_value, value)
            self.notify({"key": key, "old_value": old_value, "new_value": value})

    def get_all_states(self) -> Dict[str, Any]:
        """获取所有状态

        Returns:
            Dict[str, Any]: 所有状态
        """
        return self._state.copy()

    def update_states(self, states: Dict[str, Any]) -> None:
        """批量更新状态

        Args:
            states: 要更新的状态字典
        """
        for key, value in states.items():
            self.set_state(key, value)

    def _record_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """记录状态变化

        Args:
            key: 状态键
            old_value: 旧值
            new_value: 新值
        """
        change_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "key": key,
            "old_value": old_value,
            "new_value": new_value
        }
        self._history.append(change_record)

        # 保持历史记录在合理大小
        if len(self._history) > 1000:
            self._history = self._history[-500:]

    def get_change_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取变化历史

        Args:
            limit: 返回记录数限制

        Returns:
            List[Dict[str, Any]]: 变化历史记录
        """
        return self._history[-limit:]


class ConcreteObserver(Observer):
    """具体观察者类

    实现具体的观察逻辑.
    """

    def __init__(self, observer_id: str, callback: Optional[Callable] = None):
        """初始化具体观察者

        Args:
            observer_id: 观察者ID
            callback: 自定义回调函数
        """
        self.observer_id = observer_id
        self.callback = callback
        self.notifications: List[Dict[str, Any]] = []
        self.created_at = datetime.utcnow()

    def update(self, subject: Subject, data: Optional[Any] = None) -> None:
        """接收更新通知

        Args:
            subject: 发出通知的主题
            data: 更新的数据
        """
        notification = {
            "timestamp": datetime.utcnow().isoformat(),
            "subject": getattr(subject, 'name', 'Unknown'),
            "observer_id": self.observer_id,
            "data": data
        }

        self.notifications.append(notification)

        # 保持通知记录在合理大小
        if len(self.notifications) > 1000:
            self.notifications = self.notifications[-500:]

        if self.callback:
            try:
                self.callback(subject, data)
            except Exception as e:
                print(f"回调执行失败 {self.observer_id}: {e}")

        print(f"观察者 {self.observer_id} 收到来自 {getattr(subject, 'name', 'Unknown')} 的通知")

    def get_observer_id(self) -> str:
        """获取观察者ID"""
        return self.observer_id

    def get_notifications(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取通知记录

        Args:
            limit: 返回记录数限制

        Returns:
            List[Dict[str, Any]]: 通知记录
        """
        return self.notifications[-limit:]

    def clear_notifications(self) -> None:
        """清除通知记录"""
        self.notifications.clear()


class LoggingObserver(Observer):
    """日志观察者

    将通知记录到日志.
    """

    def __init__(self, observer_id: str = "logging_observer"):
        """初始化日志观察者

        Args:
            observer_id: 观察者ID
        """
        self.observer_id = observer_id
        self.log_entries: List[Dict[str, Any]] = []

    def update(self, subject: Subject, data: Optional[Any] = None) -> None:
        """记录日志

        Args:
            subject: 发出通知的主题
            data: 更新的数据
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "observer_id": self.observer_id,
            "subject": getattr(subject, 'name', 'Unknown'),
            "data": data
        }

        self.log_entries.append(log_entry)
        print(f"[LOG] {json.dumps(log_entry, ensure_ascii=False)}")

    def get_observer_id(self) -> str:
        """获取观察者ID"""
        return self.observer_id

    def get_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取日志记录

        Args:
            limit: 返回记录数限制

        Returns:
            List[Dict[str, Any]]: 日志记录
        """
        return self.log_entries[-limit:]


class MetricsObserver(Observer):
    """指标观察者

    收集指标数据.
    """

    def __init__(self, observer_id: str = "metrics_observer"):
        """初始化指标观察者

        Args:
            observer_id: 观察者ID
        """
        self.observer_id = observer_id
        self.metrics: Dict[str, Any] = {
            "notification_count": 0,
            "subjects_notified": set(),
            "last_notification": None
        }

    def update(self, subject: Subject, data: Optional[Any] = None) -> None:
        """更新指标

        Args:
            subject: 发出通知的主题
            data: 更新的数据
        """
        self.metrics["notification_count"] += 1
        self.metrics["subjects_notified"].add(getattr(subject, 'name', 'Unknown'))
        self.metrics["last_notification"] = {
            "timestamp": datetime.utcnow().isoformat(),
            "subject": getattr(subject, 'name', 'Unknown'),
            "data": data
        }

    def get_observer_id(self) -> str:
        """获取观察者ID"""
        return self.observer_id

    def get_metrics(self) -> Dict[str, Any]:
        """获取指标数据

        Returns:
            Dict[str, Any]: 指标数据
        """
        result = self.metrics.copy()
        result["subjects_notified"] = list(result["subjects_notified"])
        return result

    def reset_metrics(self) -> None:
        """重置指标"""
        self.metrics = {
            "notification_count": 0,
            "subjects_notified": set(),
            "last_notification": None
        }


class AlertingObserver(Observer):
    """告警观察者

    根据条件触发告警.
    """

    def __init__(self, observer_id: str = "alerting_observer",
                 alert_conditions: Optional[List[Callable]] = None):
        """初始化告警观察者

        Args:
            observer_id: 观察者ID
            alert_conditions: 告警条件函数列表
        """
        self.observer_id = observer_id
        self.alert_conditions = alert_conditions or []
        self.alerts: List[Dict[str, Any]] = []

    def add_alert_condition(self, condition: Callable) -> None:
        """添加告警条件

        Args:
            condition: 告警条件函数，返回True时触发告警
        """
        self.alert_conditions.append(condition)

    def update(self, subject: Subject, data: Optional[Any] = None) -> None:
        """检查告警条件

        Args:
            subject: 发出通知的主题
            data: 更新的数据
        """
        for i, condition in enumerate(self.alert_conditions):
            try:
                if condition(subject, data):
                    alert = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "observer_id": self.observer_id,
                        "subject": getattr(subject, 'name', 'Unknown'),
                        "condition_id": i,
                        "data": data,
                        "message": f"告警条件 {i} 被触发"
                    }
                    self.alerts.append(alert)
                    print(f"[ALERT] {json.dumps(alert, ensure_ascii=False)}")
            except Exception as e:
                print(f"告警条件检查失败 {i}: {e}")

    def get_observer_id(self) -> str:
        """获取观察者ID"""
        return self.observer_id

    def get_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取告警记录

        Args:
            limit: 返回记录数限制

        Returns:
            List[Dict[str, Any]]: 告警记录
        """
        return self.alerts[-limit:]


class EventQueue:
    """事件队列

    异步处理观察者通知.
    """

    def __init__(self, max_size: int = 1000):
        """初始化事件队列

        Args:
            max_size: 队列最大大小
        """
        self._queue = queue.Queue(maxsize=max_size)
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """启动事件处理"""
        if not self._running:
            self._running = True
            self._worker_thread = threading.Thread(target=self._process_events, daemon=True)
            self._worker_thread.start()

    def stop(self) -> None:
        """停止事件处理"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)

    def put_event(self, observer: Observer, subject: Subject, data: Any) -> None:
        """添加事件到队列

        Args:
            observer: 观察者
            subject: 主题
            data: 数据
        """
        try:
            event = {"observer": observer, "subject": subject, "data": data}
            self._queue.put_nowait(event)
        except queue.Full:
            print("事件队列已满，丢弃事件")

    def _process_events(self) -> None:
        """处理事件队列"""
        while self._running:
            try:
                event = self._queue.get(timeout=1.0)
                observer = event["observer"]
                subject = event["subject"]
                data = event["data"]

                try:
                    observer.update(subject, data)
                except Exception as e:
                    print(f"异步通知处理失败: {e}")

                self._queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"事件处理错误: {e}")


class AsyncSubject(Subject):
    """异步主题

    使用队列异步通知观察者.
    """

    def __init__(self, name: str = "AsyncSubject", queue_size: int = 1000):
        """初始化异步主题

        Args:
            name: 主题名称
            queue_size: 事件队列大小
        """
        super().__init__()
        self.name = name
        self.event_queue = EventQueue(queue_size)

    def start_async_notifications(self) -> None:
        """启动异步通知"""
        self.event_queue.start()

    def stop_async_notifications(self) -> None:
        """停止异步通知"""
        self.event_queue.stop()

    def notify(self, data: Optional[Any] = None) -> None:
        """异步通知观察者

        Args:
            data: 要传递的数据
        """
        with self._lock:
            observers_copy = self._observers.copy()

        for observer in observers_copy:
            self.event_queue.put_event(observer, self, data)


# 便捷函数
def create_observer_system() -> tuple[ConcreteSubject, List[Observer]]:
    """创建观察者系统

    Returns:
        tuple[ConcreteSubject, List[Observer]]: 主题和观察者列表
    """
    subject = ConcreteSubject("演示主题")

    # 创建不同类型的观察者
    logging_observer = LoggingObserver("系统日志")
    metrics_observer = MetricsObserver("系统指标")
    alerting_observer = AlertingObserver("系统告警")

    # 添加告警条件
    alerting_observer.add_alert_condition(
        lambda subject, data: data and isinstance(data, dict) and
        data.get("key") == "error_count" and data.get("new_value", 0) > 10
    )

    observers = [logging_observer, metrics_observer, alerting_observer]

    # 注册观察者
    for observer in observers:
        subject.attach(observer)

    return subject, observers


def demonstrate_observer_pattern():
    """演示观察者模式的使用"""
    print("=== 观察者模式演示 ===")

    subject, observers = create_observer_system()
    print(f"创建了主题: {subject.name}")
    print(f"注册了 {len(observers)} 个观察者")

    # 模拟状态变化
    print("\n--- 模拟状态变化 ---")
    subject.set_state("status", "running")
    subject.set_state("user_count", 100)
    subject.set_state("error_count", 5)

    # 触发告警
    print("\n--- 触发告警 ---")
    subject.set_state("error_count", 15)

    # 显示指标
    metrics_observer = observers[1]
    print(f"\n指标统计: {metrics_observer.get_metrics()}")

    # 显示告警
    alerting_observer = observers[2]
    alerts = alerting_observer.get_alerts()
    print(f"告警数量: {len(alerts)}")
    for alert in alerts:
        print(f"  - {alert['message']}")


# 可观察服务实现
class ObservableService(Subject):
    """可观察服务类

    提供服务级别的观察者功能.
    """

    def __init__(self, service_name: str):
        """初始化可观察服务

        Args:
            service_name: 服务名称
        """
        super().__init__()
        self.service_name = service_name
        self._status = "stopped"
        self._metrics = {}

    def start(self):
        """启动服务"""
        self._status = "running"
        self.notify({"event": "service_started", "service": self.service_name})

    def stop(self):
        """停止服务"""
        self._status = "stopped"
        self.notify({"event": "service_stopped", "service": self.service_name})

    def update_metrics(self, metrics: Dict[str, Any]):
        """更新服务指标

        Args:
            metrics: 指标数据
        """
        self._metrics.update(metrics)
        self.notify({
            "event": "metrics_updated",
            "service": self.service_name,
            "metrics": metrics
        })

    def get_status(self) -> str:
        """获取服务状态"""
        return self._status

    def get_metrics(self) -> Dict[str, Any]:
        """获取服务指标"""
        return self._metrics.copy()


def create_observer_system(service_name: str) -> Dict[str, Any]:
    """创建观察者系统

    Args:
        service_name: 服务名称

    Returns:
        Dict[str, Any]: 观察者系统组件
    """
    # 创建可观察服务
    service = ObservableService(service_name)

    # 创建观察者
    logging_observer = LoggingObserver(f"{service_name}_logger")
    metrics_observer = MetricsObserver(f"{service_name}_metrics")
    alerting_observer = AlertingObserver(f"{service_name}_alerts")

    # 注册观察者
    service.attach(logging_observer)
    service.attach(metrics_observer)
    service.attach(alerting_observer)

    return {
        "service": service,
        "observers": {
            "logging": logging_observer,
            "metrics": metrics_observer,
            "alerting": alerting_observer
        }
    }


def setup_service_observers(service: ObservableService) -> Dict[str, Any]:
    """设置服务观察者

    Args:
        service: 要设置观察者的服务

    Returns:
        Dict[str, Any]: 配置的观察者
    """
    observers = {}

    # 根据服务类型配置不同的观察者
    if "api" in service.service_name.lower():
        logging_observer = LoggingObserver(f"{service.service_name}_api_logger")
        metrics_observer = MetricsObserver(f"{service.service_name}_api_metrics")
        alerting_observer = AlertingObserver(f"{service.service_name}_api_alerts")

        service.attach(logging_observer)
        service.attach(metrics_observer)
        service.attach(alerting_observer)

        observers.update({
            "logging": logging_observer,
            "metrics": metrics_observer,
            "alerting": alerting_observer
        })

    elif "database" in service.service_name.lower():
        logging_observer = LoggingObserver(f"{service.service_name}_db_logger")
        metrics_observer = MetricsObserver(f"{service.service_name}_db_metrics")

        service.attach(logging_observer)
        service.attach(metrics_observer)

        observers.update({
            "logging": logging_observer,
            "metrics": metrics_observer
        })

    else:
        # 默认配置
        logging_observer = LoggingObserver(f"{service.service_name}_logger")
        service.attach(logging_observer)

        observers["logging"] = logging_observer

    return observers


# 导出的公共接口
__all__ = [
    "Observer",
    "Subject",
    "ConcreteSubject",
    "ConcreteObserver",
    "LoggingObserver",
    "MetricsObserver",
    "AlertingObserver",
    "ObservableService",
    "EventQueue",
    "AsyncSubject",
    "create_observer_system",
    "setup_service_observers",
    "demonstrate_observer_pattern"
]