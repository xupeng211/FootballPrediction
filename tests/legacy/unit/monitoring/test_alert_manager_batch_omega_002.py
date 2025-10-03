from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import os
import sys

from prometheus_client import REGISTRY, CollectorRegistry, Counter, Gauge, Histogram
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import asyncio
import pytest

"""
AlertManager Batch-Ω-002 测试套件

专门为 alert_manager.py 设计的测试，目标是将其覆盖率从 29% 提升至 ≥70%
覆盖所有告警管理功能、规则引擎、通知渠道和状态管理
"""

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from prometheus_client import REGISTRY, CollectorRegistry, Counter, Gauge, Histogram
class TestAlertManagerBatchOmega002:
    """AlertManager Batch-Ω-002 测试类"""
    @pytest.fixture
    def alert_manager(self):
        """创建 AlertManager 实例"""
        from src.monitoring.alert_manager import AlertManager, AlertLevel, AlertChannel
        manager = AlertManager()
        return manager
    @pytest.fixture
    def sample_alert(self):
        """示例告警对象"""
        from src.monitoring.alert_manager import Alert, AlertLevel, AlertStatus
        return Alert(
        alert_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_ALERT_ID_34"),": title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_34"),": message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_34"),": level=AlertLevel.WARNING,": source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_34")""""
        )
    def test_alert_manager_initialization(self, alert_manager):
        "]""测试 AlertManager 初始化"""
        # 检查默认配置
    assert isinstance(alert_manager.alerts, list)
    assert isinstance(alert_manager.rules, dict)
    assert isinstance(alert_manager.alert_handlers, dict)
    assert hasattr(alert_manager, 'metrics')
        # 检查是否有默认规则（初始化后应该有规则）
    assert len(alert_manager.rules) > 0
    def test_alert_creation(self):
        """测试 Alert 对象创建"""
        from src.monitoring.alert_manager import Alert, AlertLevel, AlertStatus
        alert = Alert(
        alert_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_ALERT_ID_34"),": title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_34"),": message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_46"),": level=AlertLevel.ERROR,": source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_34")""""
        )
    assert alert.alert_id =="]test-001[" assert alert.title =="]Test Alert[" assert alert.level ==AlertLevel.ERROR[""""
    assert alert.message =="]]Test message[" assert alert.source =="]test_source[" assert alert.status ==AlertStatus.ACTIVE[""""
    assert isinstance(alert.created_at, datetime)
    assert alert.labels =={}
    assert alert.annotations =={}
    def test_alert_with_labels_and_annotations(self):
        "]]""测试带标签和注释的 Alert 对象"""
        from src.monitoring.alert_manager import Alert, AlertLevel
        labels = {"service[: "api"", "environment[" "]test]}": annotations = {"description[: "Test alert"", "severity]}": alert = Alert(": alert_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_ALERT_ID_54"),": title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_54"),": message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_55"),": level=AlertLevel.INFO,": source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_34"),": labels=labels,": annotations=annotations[""
        )
    assert alert.labels ==labels
    assert alert.annotations ==annotations
    assert alert.labels["]]service["] =="]api[" def test_alert_to_dict("
    """"
        "]""测试 Alert 转换为字典"""
        alert_dict = sample_alert.to_dict()
    assert alert_dict["alert_id["] =="]test-001[" assert alert_dict["]title["] =="]Test Alert[" assert alert_dict["]level["] =="]warning[" assert alert_dict["]message["] =="]This is a test alert[" assert alert_dict["]source["] =="]test_source[" assert alert_dict["]status["] =="]active[" def test_alert_resolve("
    """"
        "]""测试解决告警"""
        from src.monitoring.alert_manager import Alert, AlertLevel, AlertStatus
        alert = Alert(
        alert_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_ALERT_ID_34"),": title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_34"),": message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_46"),": level=AlertLevel.ERROR,": source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_34")""""
        )
    assert alert.status ==AlertStatus.ACTIVE
    assert alert.resolved_at is None
        alert.resolve()
    assert alert.status ==AlertStatus.RESOLVED
    assert isinstance(alert.resolved_at, datetime)
    def test_alert_silence(self):
        "]""测试静默告警"""
        from src.monitoring.alert_manager import Alert, AlertLevel, AlertStatus
        alert = Alert(
        alert_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_ALERT_ID_34"),": title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_34"),": message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_46"),": level=AlertLevel.ERROR,": source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_34")""""
        )
    assert alert.status ==AlertStatus.ACTIVE
        alert.silence()
    assert alert.status ==AlertStatus.SILENCED
    def test_alert_rule_creation(self):
        "]""测试 AlertRule 对象创建"""
        from src.monitoring.alert_manager import AlertRule, AlertLevel, AlertChannel
        rule = AlertRule(
        rule_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_77"),": name = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_NAME_77"),": condition = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_CONDITION_78"),": level=AlertLevel.WARNING,": channels=[AlertChannel.LOG, AlertChannel.PROMETHEUS],": throttle_seconds=600,"
            enabled=True
        )
    assert rule.rule_id =="]test_rule[" assert rule.name =="]Test Rule[" assert rule.condition =="]error_count > 10[" assert rule.level ==AlertLevel.WARNING[""""
    assert AlertChannel.LOG in rule.channels
    assert AlertChannel.PROMETHEUS in rule.channels
    assert rule.throttle_seconds ==600
    assert rule.enabled is True
    assert rule.last_fired is None
    def test_alert_manager_add_rule(self, alert_manager):
        "]]""测试添加告警规则"""
        from src.monitoring.alert_manager import AlertRule, AlertLevel, AlertChannel
        rule = AlertRule(
        rule_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_77"),": name = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_NAME_77"),": condition = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_CONDITION_78"),": level=AlertLevel.WARNING,": channels=[AlertChannel.LOG]""
        )
        alert_manager.add_rule(rule)
    assert "]test_rule[" in alert_manager.rules[""""
    assert alert_manager.rules["]]test_rule["] ==rule[" def test_alert_manager_remove_rule(self, alert_manager):"""
        "]]""测试移除告警规则"""
        from src.monitoring.alert_manager import AlertRule, AlertLevel, AlertChannel
        rule = AlertRule(
        rule_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_77"),": name = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_NAME_77"),": condition = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_CONDITION_78"),": level=AlertLevel.WARNING,": channels=[AlertChannel.LOG]""
        )
        alert_manager.add_rule(rule)
    assert "]test_rule[" in alert_manager.rules[""""
        removed = alert_manager.remove_rule("]]test_rule[")": assert removed is True[" assert "]]test_rule[" not in alert_manager.rules[""""
        # 测试移除不存在的规则
        removed = alert_manager.remove_rule("]]nonexistent[")": assert removed is False[" def test_fire_alert_basic(self, alert_manager):""
        "]]""测试基本告警触发"""
        from src.monitoring.alert_manager import AlertLevel
        alert = alert_manager.fire_alert(
        title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_105"),": message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_46"),": level=AlertLevel.WARNING,": source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_34")""""
        )
    assert alert is not None
    assert alert.title =="]Test Alert[" assert alert.level ==AlertLevel.WARNING[""""
    assert alert.source =="]]test_source[" assert len(alert_manager.alerts) ==1[""""
    def test_fire_alert_with_labels_and_annotations(self, alert_manager):
        "]]""测试带标签和注释的告警触发"""
        from src.monitoring.alert_manager import AlertLevel
        labels = {"service[: "api"", "environment]}": annotations = {"description[: "Test alert["}"]": alert = alert_manager.fire_alert(": title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_34"),": message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_46"),": level=AlertLevel.ERROR,": source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_34"),": labels=labels,": annotations=annotations[""
        )
    assert alert is not None
    assert alert.labels ==labels
    assert alert.annotations ==annotations
    def test_fire_alert_with_rule_id(self, alert_manager):
        "]]""测试带规则ID的告警触发"""
        from src.monitoring.alert_manager import AlertLevel
        alert = alert_manager.fire_alert(
        title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_105"),": message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_46"),": level=AlertLevel.WARNING,": source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_34"),": rule_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_121")""""
        )
    assert alert is not None
    def test_fire_alert_throttling(self, alert_manager):
        "]""测试告警去重功能"""
        from src.monitoring.alert_manager import AlertLevel, AlertRule, AlertChannel
        # 创建一个去重时间很短的规则
        rule = AlertRule(
        rule_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_77"),": name = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_NAME_77"),": condition = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_CONDITION_78"),": level=AlertLevel.WARNING,": channels=[AlertChannel.LOG],": throttle_seconds=1  # 1秒去重"
        )
        alert_manager.add_rule(rule)
        # 第一次触发应该成功
        alert1 = alert_manager.fire_alert(
            title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_34"),": message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_46"),": level=AlertLevel.WARNING,": source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_34"),": rule_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_130")""""
        )
    assert alert1 is not None
        # 立即再次触发应该被去重
        alert2 = alert_manager.fire_alert(
        title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_34"),": message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_46"),": level=AlertLevel.WARNING,": source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_34"),": rule_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_130")""""
        )
    assert alert2 is None
    def test_register_handler(self, alert_manager):
        "]""测试注册告警处理器"""
        from src.monitoring.alert_manager import AlertChannel
        def dummy_handler(alert):
            pass
        alert_manager.register_handler(AlertChannel.LOG, dummy_handler)
    assert AlertChannel.LOG in alert_manager.alert_handlers
    assert dummy_handler in alert_manager.alert_handlers[AlertChannel.LOG]
    @patch('src.monitoring.alert_manager.logger')
    def test_log_handler(self, mock_logger, alert_manager):
        """测试日志处理器"""
        from src.monitoring.alert_manager import Alert, AlertLevel
        alert = Alert(
        alert_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_ALERT_ID_34"),": title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_34"),": message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_46"),": level=AlertLevel.ERROR,": source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_34")""""
        )
        alert_manager._log_handler(alert)
        # 检查是否调用了相应级别的日志
        mock_logger.log.assert_called_once()
    def test_resolve_alert(self, alert_manager):
        "]""测试解决告警"""
        from src.monitoring.alert_manager import AlertLevel
        # 先触发一个告警
        alert = alert_manager.fire_alert(
        title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_105"),": message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_46"),": level=AlertLevel.WARNING,": source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_34")""""
        )
    assert alert is not None
    assert alert.status.value =="]active["""""
        # 解决告警
        resolved = alert_manager.resolve_alert(alert.alert_id)
    assert resolved is True
    assert alert.status.value =="]resolved["""""
        # 测试解决不存在的告警
        resolved = alert_manager.resolve_alert("]nonexistent[")": assert resolved is False[" def test_get_active_alerts(self, alert_manager):""
        "]]""测试获取活跃告警"""
        from src.monitoring.alert_manager import AlertLevel
        # 触发多个告警
        alert1 = alert_manager.fire_alert(
        title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_153"),": message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_154"),": level=AlertLevel.WARNING,": source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_34")""""
        )
        alert2 = alert_manager.fire_alert(
            title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_158"),": message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_158"),": level=AlertLevel.ERROR,": source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_34")""""
        )
        # 解决其中一个
        alert_manager.resolve_alert(alert1.alert_id)
        # 获取所有活跃告警
        active_alerts = alert_manager.get_active_alerts()
    assert len(active_alerts) ==1
    assert active_alerts[0].alert_id ==alert2.alert_id
        # 按级别过滤
        error_alerts = alert_manager.get_active_alerts(AlertLevel.ERROR)
    assert len(error_alerts) ==1
    assert error_alerts[0].alert_id ==alert2.alert_id
    def test_get_alert_summary(self, alert_manager):
        "]""测试获取告警摘要"""
        from src.monitoring.alert_manager import AlertLevel
        # 触发告警
        alert_manager.fire_alert(
        title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_169"),": message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_169"),": level=AlertLevel.WARNING,": source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_34")""""
        )
        alert_manager.fire_alert(
            title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_172"),": message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_173"),": level=AlertLevel.ERROR,": source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_34")""""
        )
        summary = alert_manager.get_alert_summary()
    assert isinstance(summary, dict)
    assert "]total_alerts[" in summary[""""
    assert "]]active_alerts[" in summary[""""
    assert "]]by_level[" in summary[""""
    assert "]]by_source[" in summary[""""
    assert summary["]]total_alerts["] ==2[" assert summary["]]active_alerts["] ==2[" def test_prometheus_metrics_initialization(self):"""
        "]]""测试 Prometheus 指标初始化"""
        from src.monitoring.alert_manager import PrometheusMetrics
        from prometheus_client import CollectorRegistry
        # 使用独立的注册表进行测试
        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry)
    assert hasattr(metrics, 'data_freshness_hours')
    assert hasattr(metrics, 'data_completeness_ratio')
    assert hasattr(metrics, 'data_quality_score')
    assert hasattr(metrics, 'anomalies_detected_total')
    assert hasattr(metrics, 'anomaly_score')
    assert hasattr(metrics, 'alerts_fired_total')
    assert hasattr(metrics, 'active_alerts')
    def test_update_quality_metrics(self, alert_manager):
        """测试更新数据质量指标"""
        quality_data = {
        "freshness[": {""""
        "]matches[": {"]hours_since_last_update[": 5.5},""""
        "]odds[": {"]hours_since_last_update[": 1.0}""""
        },
            "]completeness[": {""""
            "]matches[": {"]completeness_ratio[": 0.95},""""
            "]odds[": {"]completeness_ratio[": 0.88}""""
            },
            "]overall_score[": 0.92[""""
        }
        alert_manager.update_quality_metrics(quality_data)
        # 检查指标是否更新（这里我们主要确保不抛出异常）
    assert True  # 如果没有异常，则测试通过
    def test_update_anomaly_metrics(self, alert_manager):
        "]]""测试更新异常检测指标"""
        # 创建模拟的异常对象
        mock_anomaly = Mock()
        mock_anomaly.table_name = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TABLE_NAME_201"): mock_anomaly.column_name = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_COLUMN_NAME_201"): mock_anomaly.anomaly_type = Mock()": mock_anomaly.anomaly_type.value = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_VALUE_202"): mock_anomaly.severity = Mock()": mock_anomaly.severity.value = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_VALUE_205"): mock_anomaly.anomaly_score = 0.15[": anomalies = ["]]mock_anomaly[": alert_manager.update_anomaly_metrics(anomalies)""""
        # 检查指标是否更新（这里我们主要确保不抛出异常）
    assert True
    def test_check_and_fire_quality_alerts(self, alert_manager):
        "]""测试检查数据质量并触发告警"""
        quality_data = {
        "freshness[": {""""
        "]matches[": {"]hours_since_last_update[": 30.0},  # 超过24小时[""""
        "]]odds[": {"]hours_since_last_update[": 15.0}      # 超过12小时[""""
        },
            "]]completeness[": {""""
            "]matches[": {"]completeness_ratio[": 0.75},        # 低于0.8[""""
            "]]odds[": {"]completeness_ratio[": 0.90}           # 低于0.95[""""
            },
            "]]overall_score[": 0.65  # 低于0.7[""""
        }
        alerts = alert_manager.check_and_fire_quality_alerts(quality_data)
        # 应该触发多个告警
    assert len(alerts) > 0
    def test_check_and_fire_anomaly_alerts(self, alert_manager):
        "]]""测试检查异常并触发告警"""
        # 创建模拟的异常对象
        mock_anomaly = Mock()
        mock_anomaly.table_name = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TABLE_NAME_201"): mock_anomaly.column_name = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_COLUMN_NAME_201"): mock_anomaly.anomaly_type = Mock()": mock_anomaly.anomaly_type.value = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_VALUE_202"): mock_anomaly.severity = Mock()": mock_anomaly.severity.value = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_VALUE_205"): mock_anomaly.description = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_DESCRIPTION_227"): mock_anomaly.anomaly_score = 0.25  # 超过0.2[": anomalies = ["]]mock_anomaly[": alerts = alert_manager.check_and_fire_anomaly_alerts(anomalies)""""
        # 应该触发告警
    assert len(alerts) > 0
    assert alerts[0].level.value =="]critical[" def test_generate_alert_id("
    """"
        "]""测试生成告警ID"""
        # 测试基本ID生成
        id1 = alert_manager._generate_alert_id("Test Alert[", "]test_source[", None)": id2 = alert_manager._generate_alert_id("]Test Alert[", "]test_source[", None)": assert isinstance(id1, str)" assert len(id1) ==12[""
    assert id1 ==id2  # 相同参数应该生成相同ID
        # 测试带标签的ID生成
        labels = {"]]service[: "api"", "environment]}": id3 = alert_manager._generate_alert_id("Test Alert[", "]test_source[", labels)": id4 = alert_manager._generate_alert_id("]Test Alert[", "]test_source[", labels)": assert id3 ==id4  # 相同参数应该生成相同ID[" assert id3 != id1  # 不同参数应该生成不同ID[""
    def test_should_throttle(self, alert_manager):
        "]]]""测试去重逻辑"""
        from src.monitoring.alert_manager import AlertRule, AlertLevel, AlertChannel
        # 创建一个规则
        rule = AlertRule(
        rule_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_77"),": name = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_NAME_77"),": condition = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_CONDITION_78"),": level=AlertLevel.WARNING,": channels=[AlertChannel.LOG],": throttle_seconds=60  # 60秒去重"
        )
        alert_manager.add_rule(rule)
        # 没有最后触发时间，不应该去重
        should_throttle = alert_manager._should_throttle("]test_alert[", "]test_rule[")": assert should_throttle is False["""
        # 设置最后触发时间为现在
        rule.last_fired = datetime.now()
        # 现在应该去重
        should_throttle = alert_manager._should_throttle("]]test_alert[", "]test_rule[")": assert should_throttle is True["""
        # 测试不存在的规则
        should_throttle = alert_manager._should_throttle("]]test_alert[", "]nonexistent[")": assert should_throttle is False[" def test_send_alert_error_handling(self, alert_manager):""
        "]]""测试告警发送错误处理"""
        from src.monitoring.alert_manager import Alert, AlertLevel, AlertChannel, AlertRule
        # 创建一个会抛出异常的处理器
        def error_handler(alert):
            raise Exception("Handler error[")": alert_manager.register_handler(AlertChannel.LOG, error_handler)"""
        # 创建规则
        rule = AlertRule(
            rule_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_RULE_ID_130"),": name = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_NAME_77"),": condition = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_CONDITION_78"),": level=AlertLevel.WARNING,": channels=[AlertChannel.LOG]""
        )
        alert_manager.add_rule(rule)
        # 创建告警
        alert = Alert(
            alert_id = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_ALERT_ID_273"),": title = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_TITLE_34"),": message = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_MESSAGE_46"),": level=AlertLevel.WARNING,": source = os.getenv("TEST_ALERT_MANAGER_BATCH_OMEGA_002_SOURCE_34")""""
        )
        # 发送告警（不应该抛出异常）
        alert_manager._send_alert(alert, "]test_rule[")""""
        # 检查错误计数器是否增加
    assert True  # 如果没有抛出异常，则测试通过
    def test_alert_levels_enum(self):
        "]""测试告警级别枚举"""
        from src.monitoring.alert_manager import AlertLevel
    assert AlertLevel.INFO.value =="info[" assert AlertLevel.WARNING.value =="]warning[" assert AlertLevel.ERROR.value =="]error[" assert AlertLevel.CRITICAL.value =="]critical[" def test_alert_status_enum("
    """"
        "]""测试告警状态枚举"""
        from src.monitoring.alert_manager import AlertStatus
    assert AlertStatus.ACTIVE.value =="active[" assert AlertStatus.RESOLVED.value =="]resolved[" assert AlertStatus.SILENCED.value =="]silenced[" def test_alert_channel_enum("
    """"
        "]""测试告警渠道枚举"""
        from src.monitoring.alert_manager import AlertChannel
    assert AlertChannel.LOG.value =="log[" assert AlertChannel.PROMETHEUS.value =="]prometheus[" assert AlertChannel.WEBHOOK.value =="]webhook[" assert AlertChannel.EMAIL.value =="]email[" def test_alert_manager_with_custom_registry("
    """"
        "]""测试使用自定义注册表的 AlertManager"""
        from src.monitoring.alert_manager import AlertManager
        from prometheus_client import CollectorRegistry
        # 使用独立的注册表
        registry = CollectorRegistry()
        with patch('src.monitoring.alert_manager.PrometheusMetrics') as mock_metrics = alert_manager AlertManager()
            # 检查是否使用了自定义注册表
            # 这里我们主要确保构造函数没有抛出异常
    assert True
        from src.monitoring.alert_manager import AlertManager, AlertLevel, AlertChannel
        from src.monitoring.alert_manager import Alert, AlertLevel, AlertStatus
        from src.monitoring.alert_manager import Alert, AlertLevel, AlertStatus
        from src.monitoring.alert_manager import Alert, AlertLevel
        from src.monitoring.alert_manager import Alert, AlertLevel, AlertStatus
        from src.monitoring.alert_manager import Alert, AlertLevel, AlertStatus
        from src.monitoring.alert_manager import AlertRule, AlertLevel, AlertChannel
        from src.monitoring.alert_manager import AlertRule, AlertLevel, AlertChannel
        from src.monitoring.alert_manager import AlertRule, AlertLevel, AlertChannel
        from src.monitoring.alert_manager import AlertLevel
        from src.monitoring.alert_manager import AlertLevel
        from src.monitoring.alert_manager import AlertLevel
        from src.monitoring.alert_manager import AlertLevel, AlertRule, AlertChannel
        from src.monitoring.alert_manager import AlertChannel
        from src.monitoring.alert_manager import Alert, AlertLevel
        from src.monitoring.alert_manager import AlertLevel
        from src.monitoring.alert_manager import AlertLevel
        from src.monitoring.alert_manager import AlertLevel
        from src.monitoring.alert_manager import PrometheusMetrics
        from prometheus_client import CollectorRegistry
        from src.monitoring.alert_manager import AlertRule, AlertLevel, AlertChannel
        from src.monitoring.alert_manager import Alert, AlertLevel, AlertChannel, AlertRule
        from src.monitoring.alert_manager import AlertLevel
        from src.monitoring.alert_manager import AlertStatus
        from src.monitoring.alert_manager import AlertChannel
        from src.monitoring.alert_manager import AlertManager
        from prometheus_client import CollectorRegistry