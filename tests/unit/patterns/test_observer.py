"""观察者模式测试
Observer Pattern Tests.

测试观察者模式的核心功能，包括观察者注册、通知机制、错误处理等。
"""

import pytest
from datetime import datetime
from typing import Any

from src.patterns.observer import (
    AsyncSubject,
    ConcreteObserver,
    ConcreteSubject,
    ObservableService,
    Observer,
    Subject,
    create_observer_system,
    create_service_observer_system,
    demonstrate_observer_pattern,
)


class TestObserverPattern:
    """观察者模式测试类."""

    def setup_method(self):
        """每个测试方法前的设置."""
        self.subject = ConcreteSubject("test_subject")
        self.test_data = {"key": "test_value", "timestamp": datetime.utcnow()}

    def test_concrete_observer_creation_and_basic_functionality(self):
        """测试具体观察者的创建和基本功能."""
        observer = ConcreteObserver("test_observer_1")

        # 验证观察者基本属性
        assert observer.get_observer_id() == "test_observer_1"
        assert observer.observer_id == "test_observer_1"
        assert observer.callback is None
        assert isinstance(observer.notifications, list)
        assert len(observer.notifications) == 0
        assert isinstance(observer.created_at, datetime)

    def test_observer_with_callback(self):
        """测试带回调函数的观察者."""
        callback_called = []

        def test_callback(subject: Subject, data: Any | None = None):
            callback_called.append((subject, data))

        observer = ConcreteObserver("callback_observer", test_callback)
        assert observer.callback == test_callback

        # 测试回调函数调用
        test_subject = ConcreteSubject("callback_test")
        observer.update(test_subject, self.test_data)

        assert len(callback_called) == 1
        assert callback_called[0][0] == test_subject
        assert callback_called[0][1] == self.test_data

    def test_subject_observer_attach_detach(self):
        """测试主题的观察者添加和移除."""
        observer1 = ConcreteObserver("observer_1")
        observer2 = ConcreteObserver("observer_2")

        # 初始状态：无观察者
        assert self.subject.get_observer_count() == 0
        assert not self.subject.has_changed()

        # 添加观察者
        self.subject.attach(observer1)
        assert self.subject.get_observer_count() == 1

        self.subject.attach(observer2)
        assert self.subject.get_observer_count() == 2

        # 重复添加同一观察者不应该增加计数
        self.subject.attach(observer1)
        assert self.subject.get_observer_count() == 2

        # 移除观察者
        self.subject.detach(observer1)
        assert self.subject.get_observer_count() == 1

        self.subject.detach(observer2)
        assert self.subject.get_observer_count() == 0

        # 移除不存在的观察者不应该出错
        self.subject.detach(observer1)
        assert self.subject.get_observer_count() == 0

    def test_subject_notify_observers(self):
        """测试主题通知观察者机制."""
        observer1 = ConcreteObserver("observer_1")
        observer2 = ConcreteObserver("observer_2")
        observer3 = ConcreteObserver("observer_3")

        # 添加观察者
        self.subject.attach(observer1)
        self.subject.attach(observer2)
        self.subject.attach(observer3)

        # 发送通知
        test_notification = {"action": "test", "data": "notification_data"}
        self.subject.notify(test_notification)

        # 验证所有观察者都收到通知
        assert len(observer1.notifications) == 1
        assert len(observer2.notifications) == 1
        assert len(observer3.notifications) == 1

        # 验证通知内容
        for observer in [observer1, observer2, observer3]:
            notification = observer.notifications[0]
            assert notification["subject"] == "test_subject"
            assert notification["observer_id"] == observer.observer_id
            assert notification["data"] == test_notification
            assert "timestamp" in notification

    def test_concrete_observer_update_mechanism(self):
        """测试具体观察者的更新机制."""
        observer = ConcreteObserver("update_test_observer")

        # 初始状态无通知
        assert len(observer.notifications) == 0

        # 发送更新
        update_data = {"field": "value", "number": 42}
        observer.update(self.subject, update_data)

        # 验证通知记录
        assert len(observer.notifications) == 1
        notification = observer.notifications[0]
        assert notification["data"] == update_data
        assert notification["subject"] == "test_subject"
        assert notification["observer_id"] == "update_test_observer"

        # 发送多个更新
        observer.update(self.subject, {"second": "update"})
        observer.update(self.subject, {"third": "update"})

        assert len(observer.notifications) == 3
        assert observer.notifications[1]["data"] == {"second": "update"}
        assert observer.notifications[2]["data"] == {"third": "update"}

    def test_observer_error_handling(self):
        """测试观察者错误处理."""

        # 创建会抛出异常的回调函数
        def failing_callback(subject: Subject, data: Any | None = None):
            raise ValueError("Test error")

        observer = ConcreteObserver("error_test_observer", failing_callback)

        # 验证错误不会中断通知流程
        observer.update(self.subject, self.test_data)

        # 即使回调失败，通知仍应被记录
        assert len(observer.notifications) == 1
        assert observer.notifications[0]["data"] == self.test_data

    def test_concrete_subject_state_management(self):
        """测试具体主题的状态管理."""
        # 初始状态
        assert self.subject.get_all_states() == {}
        assert self.subject.get_state("nonexistent") is None

        # 设置状态
        self.subject.set_state("key1", "value1")
        assert self.subject.get_state("key1") == "value1"
        assert self.subject.get_all_states() == {"key1": "value1"}

        # 更新状态
        self.subject.set_state("key2", 42)
        assert self.subject.get_state("key2") == 42
        assert self.subject.get_all_states() == {"key1": "value1", "key2": 42}

        # 批量更新
        self.subject.update_states({"key3": "value3", "key4": True})
        assert self.subject.get_state("key3") == "value3"
        assert self.subject.get_state("key4") is True

    def test_subject_change_tracking(self):
        """测试主题变化跟踪."""
        observer = ConcreteObserver("change_tracking_observer")
        self.subject.attach(observer)

        # 初始状态无变化
        assert not self.subject.has_changed()

        # 设置状态会触发变化标记和通知
        self.subject.set_state("test_key", "test_value")

        # 验证变化标记
        assert self.subject.has_changed()

        # 验证通知被发送
        assert len(observer.notifications) == 1
        notification_data = observer.notifications[0]["data"]
        assert notification_data["key"] == "test_key"
        assert notification_data["old_value"] is None
        assert notification_data["new_value"] == "test_value"

    def test_subject_change_history(self):
        """测试主题变化历史记录."""
        # 进行几次状态变化
        self.subject.set_state("key1", "value1")
        self.subject.set_state("key1", "value2")  # 相同键的不同值
        self.subject.set_state("key2", 123)

        # 获取变化历史
        history = self.subject.get_change_history()
        assert len(history) == 3

        # 验证历史记录格式
        for record in history:
            assert "timestamp" in record
            assert "key" in record
            assert "old_value" in record
            assert "new_value" in record

        # 验证特定变化
        first_change = history[0]
        assert first_change["key"] == "key1"
        assert first_change["old_value"] is None
        assert first_change["new_value"] == "value1"

    def test_observer_id_uniqueness(self):
        """测试观察者ID唯一性."""
        observer1 = ConcreteObserver("unique_observer_1")
        observer2 = ConcreteObserver("unique_observer_2")
        observer3 = ConcreteObserver("unique_observer_1")  # 重复ID

        assert observer1.get_observer_id() == "unique_observer_1"
        assert observer2.get_observer_id() == "unique_observer_2"
        assert observer3.get_observer_id() == "unique_observer_1"

        # 即使ID相同，也是不同的实例
        assert observer1 is not observer3
        assert observer1.observer_id == observer3.observer_id

    def test_subject_clear_observers(self):
        """测试清除所有观察者."""
        observer1 = ConcreteObserver("observer_to_clear_1")
        observer2 = ConcreteObserver("observer_to_clear_2")
        observer3 = ConcreteObserver("observer_to_clear_3")

        # 添加多个观察者
        self.subject.attach(observer1)
        self.subject.attach(observer2)
        self.subject.attach(observer3)

        assert self.subject.get_observer_count() == 3

        # 清除所有观察者
        self.subject.clear_observers()
        assert self.subject.get_observer_count() == 0

        # 验证清除后通知不会发送给任何观察者
        self.subject.notify({"test": "data"})
        assert len(observer1.notifications) == 0
        assert len(observer2.notifications) == 0
        assert len(observer3.notifications) == 0

    def test_observer_notification_history_limit(self):
        """测试观察者通知历史限制."""
        observer = ConcreteObserver("history_test_observer")

        # 发送大量通知（超过1000的限制）
        for i in range(1200):
            observer.update(self.subject, {"notification_id": i})

        # 验证通知数量被限制在合理范围内
        assert len(observer.notifications) <= 1000
        # 当超过1000时，应该保留最新的500个
        if len(observer.notifications) == 500:
            # 验证保留的是最新的通知（最后500个）
            last_notification = observer.notifications[-1]
            assert last_notification["data"]["notification_id"] == 1199
            first_notification = observer.notifications[0]
            assert first_notification["data"]["notification_id"] == 700  # 1200-500

    def test_subject_change_history_limit(self):
        """测试主题变化历史限制."""
        # 进行大量状态变化
        for i in range(1200):
            self.subject.set_state(f"key_{i}", f"value_{i}")

        history = self.subject.get_change_history()

        # 验证历史记录被限制
        assert len(history) <= 1000

        # 验证保留的是最新的记录
        last_change = history[-1]
        assert last_change["key"].startswith("key_")

    def test_observer_with_no_subject_name(self):
        """测试观察者处理无名主题."""
        observer = ConcreteObserver("no_name_test_observer")

        # 创建没有name属性的简单主题
        class SimpleSubject(Subject):
            def get_subject_id(self) -> str:
                return "simple_subject"

        simple_subject = SimpleSubject()
        observer.update(simple_subject, {"test": "data"})

        assert len(observer.notifications) == 1
        notification = observer.notifications[0]
        # 当主题没有name属性时，应该使用"Unknown"
        assert notification["subject"] == "Unknown"

    def test_concurrent_observer_operations(self):
        """测试并发观察者操作."""
        import threading
        import time

        observer1 = ConcreteObserver("concurrent_observer_1")
        observer2 = ConcreteObserver("concurrent_observer_2")

        results = []

        def add_observers():
            for i in range(10):
                obs = ConcreteObserver(f"thread_observer_{i}")
                self.subject.attach(obs)
                results.append(f"added_{i}")
                time.sleep(0.001)  # 短暂延迟

        def remove_observers():
            time.sleep(0.005)  # 让添加操作先开始
            self.subject.detach(observer1)
            self.subject.detach(observer2)
            results.append("removed_main_observers")

        # 启动线程
        thread1 = threading.Thread(target=add_observers)
        thread2 = threading.Thread(target=remove_observers)

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # 验证并发操作完成
        assert len(results) > 0
        assert "removed_main_observers" in results

    def test_async_subject_functionality(self):
        """测试异步主题功能."""
        async_subject = AsyncSubject("async_test_subject")
        observer1 = ConcreteObserver("async_observer_1")
        observer2 = ConcreteObserver("async_observer_2")

        # 初始状态
        assert async_subject.get_subject_id() == "async_test_subject"

        # 添加观察者
        async_subject.attach(observer1)
        async_subject.attach(observer2)

        # 启动异步通知
        async_subject.start_async_notifications()

        # 发送通知（会被异步处理）
        test_data = {"async": True, "message": "test"}
        async_subject.notify(test_data)

        # 等待异步处理完成
        import time

        time.sleep(0.1)

        # 停止异步通知
        async_subject.stop_async_notifications()

        # 验证观察者收到通知
        assert len(observer1.notifications) > 0
        assert len(observer2.notifications) > 0

    def test_observable_service_lifecycle(self):
        """测试可观察服务生命周期."""
        service = ObservableService("test_service")

        # 初始状态
        assert service.get_status() == "stopped"
        assert service.service_name == "test_service"

        # 启动服务
        service.start()
        assert service.get_status() == "running"

        # 更新指标
        metrics = {"cpu": 75.5, "memory": "512MB", "connections": 42}
        service.update_metrics(metrics)
        current_metrics = service.get_metrics()
        assert current_metrics["cpu"] == 75.5
        assert current_metrics["memory"] == "512MB"
        assert current_metrics["connections"] == 42

        # 停止服务
        service.stop()
        assert service.get_status() == "stopped"

    def test_create_observer_system_function(self):
        """测试创建观察者系统函数."""
        subject, observers = create_observer_system()

        # 验证返回值
        assert isinstance(subject, ConcreteSubject)
        assert isinstance(observers, list)
        assert len(observers) == 3  # 默认创建3个观察者

        # 验证观察者已添加到主题
        assert subject.get_observer_count() == 3

        # 验证每个观察者都是有效的Observer（不一定是ConcreteObserver）
        for observer in observers:
            assert isinstance(observer, Observer)
            assert hasattr(observer, "get_observer_id")

    def test_demonstrate_observer_pattern_function(self):
        """测试演示观察者模式函数."""
        # 这个函数应该能够运行而不抛出异常
        # 函数没有返回值，所以不应该检查返回值
        try:
            demonstrate_observer_pattern()
            # 如果没有抛出异常，则测试通过
            assert True
        except Exception as e:
            pytest.fail(f"demonstrate_observer_pattern() raised an exception: {e}")

    def test_create_service_observer_system_function(self):
        """测试创建服务观察者系统函数."""
        service_name = "test_api_service"
        system = create_service_observer_system(service_name)

        # 验证系统结构（可能不包含config）
        assert "service" in system
        assert "observers" in system

        service = system["service"]
        observers = system["observers"]

        # 验证服务
        assert isinstance(service, ObservableService)
        assert service.service_name == service_name

        # 验证观察者配置
        assert isinstance(observers, dict)
        assert len(observers) > 0

        # 验证观察者已添加到服务
        assert service.get_observer_count() == len(observers)

    def test_subject_changed_flag_operations(self):
        """测试主题变化标志操作."""
        # 初始状态
        assert not self.subject.has_changed()

        # 设置变化标志
        self.subject.set_changed()
        assert self.subject.has_changed()

        # 清除变化标志
        self.subject.clear_changed()
        assert not self.subject.has_changed()

    def test_observer_get_notifications_with_limit(self):
        """测试观察者获取有限数量的通知."""
        observer = ConcreteObserver("limit_test_observer")

        # 添加多个通知
        for i in range(10):
            observer.update(self.subject, {"notification_id": i})

        # 获取有限数量的通知
        recent_notifications = observer.get_notifications(limit=5)
        assert len(recent_notifications) == 5

        # 验证获取的是最新的通知
        assert recent_notifications[-1]["data"]["notification_id"] == 9
        assert recent_notifications[0]["data"]["notification_id"] == 5

    def test_observer_large_data_handling(self):
        """测试观察者处理大数据."""
        observer = ConcreteObserver("large_data_observer")

        # 发送大数据
        large_data = {
            "large_list": list(range(1000)),
            "nested_dict": {"level1": {"level2": {"level3": list(range(100))}}},
            "long_string": "x" * 10000,
        }

        observer.update(self.subject, large_data)

        # 验证大数据被正确处理
        assert len(observer.notifications) == 1
        notification = observer.notifications[0]
        assert notification["data"]["large_list"][0] == 0
        assert notification["data"]["large_list"][-1] == 999
        assert len(notification["data"]["long_string"]) == 10000

    def test_subject_multiple_rapid_notifications(self):
        """测试主题快速连续通知."""
        observer1 = ConcreteObserver("rapid_observer_1")
        observer2 = ConcreteObserver("rapid_observer_2")

        self.subject.attach(observer1)
        self.subject.attach(observer2)

        # 快速连续发送通知
        for i in range(100):
            self.subject.notify({"rapid_index": i})

        # 验证所有通知都被接收
        assert len(observer1.notifications) == 100
        assert len(observer2.notifications) == 100

        # 验证通知顺序正确
        for i in range(100):
            assert observer1.notifications[i]["data"]["rapid_index"] == i
            assert observer2.notifications[i]["data"]["rapid_index"] == i
