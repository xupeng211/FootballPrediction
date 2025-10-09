"""

"""



















    """


    """

        """

        """






        """初始化默认告警渠道"""





        """初始化调度任务"""



        """

        """

        """

        """

        """


        """









        """


        """







        """


        """


        """


        """



        """更新规则引擎上下文"""



        """

        """



        """执行清理操作"""




        """


        """

        """

        """

        """


        """

        """


        """

        """


        """









        """

        """





        """向后兼容：获取抑制规则"""

        """向后兼容：获取聚合规则"""

        """向后兼容：移除旧的告警组"""

        """向后兼容：定期规则评估"""

        """向后兼容：定期清理"""

        """向后兼容：检查告警是否被抑制"""

        """向后兼容：检查是否是重复告警"""

        """向后兼容：聚合告警"""



    from ..models import Alert, AlertLevel, AlertStatus
        from monitoring.alerts.models import Alert, AlertLevel, AlertStatus
        from enum import Enum
        from datetime import datetime
        from typing import Any, Dict, Optional
                import hashlib
    from ...channels import AlertChannelManager, LogChannel
        from monitoring.alerts.channels import AlertChannelManager, LogChannel
    from ...metrics import PrometheusMetrics
        from monitoring.alerts.metrics import PrometheusMetrics
            from ...channels import PrometheusChannel
            from ...channels import WebhookChannel
            from ...channels import EmailChannel
            from ...channels import SlackChannel
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import logging
from .aggregator import AlertAggregator
from .deduplicator import AlertDeduplicator
from .rule_engine import AlertRuleEngine
from .scheduler import AlertScheduler, AlertTaskFactory

告警管理器（核心模块）
Alert Manager (Core Module)
告警系统的核心管理器，协调各个组件，保持向后兼容性。
Core alert manager that coordinates various components while maintaining backward compatibility.
# 尝试从不同位置导入模型和渠道
try:
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    try:
    except ImportError:
        # 创建基本类型
        class AlertLevel(Enum):
            CRITICAL = "critical"
            HIGH = "high"
            MEDIUM = "medium"
            LOW = "low"
        class AlertStatus(Enum):
            ACTIVE = "active"
            RESOLVED = "resolved"
            SUPPRESSED = "suppressed"
            SILENCED = "silenced"
        class Alert:
            def __init__(self, alert_id: str, title: str, message: str, level: AlertLevel, source: str, **kwargs):
                self.alert_id = alert_id
                self.title = title
                self.message = message
                self.level = level
                self.source = source
                self.status = AlertStatus.ACTIVE
                self.created_at = datetime.utcnow()
                self.labels = kwargs.get('labels', {})
                self.annotations = kwargs.get('annotations', {})
            @property
            def fingerprint(self) -> str:
                content = f"{self.title}:{self.source}:{self.level.value}"
                return hashlib.md5(content.encode()).hexdigest()
            def is_active(self) -> bool:
                return self.status == AlertStatus.ACTIVE
            def is_resolved(self) -> bool:
                return self.status == AlertStatus.RESOLVED
            def resolve(self):
                self.status = AlertStatus.RESOLVED
            def silence(self):
                self.status = AlertStatus.SILENCED
            def get_age(self):
                return datetime.utcnow() - self.created_at
            def get_duration(self):
                return None
# 尝试导入渠道管理器
try:
except ImportError:
    try:
    except ImportError:
        # 创建基本占位符
        class AlertChannelManager:
            def __init__(self):
                self.channels = {}
            def register_channel(self, channel):
                self.channels[channel.name] = channel
            async def send_to_all(self, alert, channels=None):
                return {name: True for name in self.channels.keys()}
        class LogChannel:
            def __init__(self, name, config):
                self.name = name
                self.config = config
# 尝试导入指标管理器
try:
except ImportError:
    try:
    except ImportError:
        # 创建基本占位符
        class PrometheusMetrics:
            def __init__(self, namespace="alerts"):
                self.namespace = namespace
            def record_alert_created(self, **kwargs): pass
            def record_alert_resolved(self, **kwargs): pass
            def record_notification_sent(self, channel, status): pass
            def update_system_info(self, info): pass
            def get_metrics_summary(self): return {}
logger = logging.getLogger(__name__)
class AlertManager:
    告警管理器
    Alert Manager
    告警系统的核心组件，负责协调告警的创建、评估、聚合和发送。
    Core component of the alert system, responsible for coordinating
    alert creation, evaluation, aggregation, and delivery.
    Attributes:
        rule_engine (AlertRuleEngine): 规则引擎 / Rule engine
        deduplicator (AlertDeduplicator): 去重器 / Deduplicator
        aggregator (AlertAggregator): 聚合器 / Aggregator
        scheduler (AlertScheduler): 调度器 / Scheduler
        channel_manager (AlertChannelManager): 渠道管理器 / Channel manager
        metrics (PrometheusMetrics): 指标管理器 / Metrics manager
        alerts (Dict[str, Alert]): 活跃告警 / Active alerts
        config (Dict[str, Any]): 配置 / Configuration
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        初始化告警管理器
        Initialize Alert Manager
        Args:
            config: 配置字典 / Configuration dictionary
        self.config = config or {}
        self.alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.max_history_size = self.config.get("max_history_size", 10000)
        # 初始化核心组件
        self.rule_engine = AlertRuleEngine()
        self.deduplicator = AlertDeduplicator(
            deduplication_window=timedelta(
                minutes=self.config.get("deduplication_minutes", 5)
            )
        )
        self.aggregator = AlertAggregator()
        self.scheduler = AlertScheduler()
        self.channel_manager = AlertChannelManager()
        self.metrics = PrometheusMetrics(
            namespace=self.config.get("metrics_namespace", "alerts")
        )
        # 初始化默认渠道
        self._init_default_channels()
        # 初始化调度任务
        self._init_scheduled_tasks()
        self.logger = logging.getLogger(__name__)
        # 更新系统信息
        self.metrics.update_system_info({
            "version": "1.0.0",
            "manager": "AlertManager",
            "initialized_at": datetime.utcnow().isoformat(),
        })
    def _init_default_channels(self):
        # 日志渠道（总是启用）
        log_channel = LogChannel(
            name="log",
            config=self.config.get("log_channel", {})
        )
        self.channel_manager.register_channel(log_channel)
        # Prometheus指标渠道
        if self.config.get("enable_prometheus", True):
            prometheus_channel = PrometheusChannel(
                name="prometheus",
                config=self.config.get("prometheus_channel", {})
            )
            self.channel_manager.register_channel(prometheus_channel)
        # Webhook渠道（如果配置了）
        webhook_config = self.config.get("webhook_channel")
        if webhook_config and webhook_config.get("url"):
            webhook_channel = WebhookChannel(
                name="webhook",
                config=webhook_config
            )
            self.channel_manager.register_channel(webhook_channel)
        # 邮件渠道（如果配置了）
        email_config = self.config.get("email_channel")
        if email_config and email_config.get("smtp_host"):
            email_channel = EmailChannel(
                name="email",
                config=email_config
            )
            self.channel_manager.register_channel(email_channel)
        # Slack渠道（如果配置了）
        slack_config = self.config.get("slack_channel")
        if slack_config and slack_config.get("webhook_url"):
            slack_channel = SlackChannel(
                name="slack",
                config=slack_config
            )
            self.channel_manager.register_channel(slack_channel)
    def _init_scheduled_tasks(self):
        # 规则评估任务
        rule_evaluation_task = AlertTaskFactory.create_periodic_rule_evaluation_task(
            self.rule_engine,
            self._update_rule_context,
            self.config.get("rule_evaluation_interval", 60)
        )
        self.scheduler.add_task(
            task_id="rule_evaluation",
            name="定期规则评估",
            func=rule_evaluation_task,
            interval=timedelta(seconds=self.config.get("rule_evaluation_interval", 60))
        )
        # 清理任务
        cleanup_task = AlertTaskFactory.create_periodic_cleanup_task(
            self._perform_cleanup,
            self.config.get("cleanup_interval", 3600)
        )
        self.scheduler.add_task(
            task_id="cleanup",
            name="定期清理",
            func=cleanup_task,
            interval=timedelta(seconds=self.config.get("cleanup_interval", 3600))
        )
        # 告警清理任务
        alert_cleanup_task = AlertTaskFactory.create_alert_cleanup_task(
            self.alerts,
            self.config.get("alert_retention_hours", 24)
        )
        self.scheduler.add_task(
            task_id="alert_cleanup",
            name="告警清理",
            func=alert_cleanup_task,
            interval=timedelta(seconds=self.config.get("cleanup_interval", 3600))
        )
    async def start(self):
        启动告警管理器
        Start Alert Manager
        启动后台调度器。
        Starts background scheduler.
        self.logger.info("Starting Alert Manager")
        await self.scheduler.start()
    async def stop(self):
        停止告警管理器
        Stop Alert Manager
        停止后台调度器。
        Stops background scheduler.
        self.logger.info("Stopping Alert Manager")
        await self.scheduler.stop()
    async def create_alert(
        self,
        title: str,
        message: str,
        level: AlertLevel,
        source: str,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
        channels: Optional[List[str]] = None,
    ) -> Optional[Alert]:
        创建告警
        Create Alert
        Args:
            title: 告警标题 / Alert title
            message: 告警消息 / Alert message
            level: 告警级别 / Alert level
            source: 告警源 / Alert source
            labels: 标签 / Labels
            annotations: 注释 / Annotations
            channels: 指定渠道 / Specific channels
        Returns:
            Optional[Alert]: 创建的告警对象 / Created alert object
        # 生成告警ID
        alert_id = f"alert_{int(datetime.utcnow().timestamp())}_{hash(title) % 10000}"
        # 创建告警对象
        alert = Alert(
            alert_id=alert_id,
            title=title,
            message=message,
            level=level,
            source=source,
            labels=labels or {},
            annotations=annotations or {},
        )
        # 检查是否应该处理告警
        should_process, reason = self.deduplicator.should_process_alert(alert)
        if not should_process:
            self.logger.info(f"Alert ignored: {alert_id} - {reason}")
            if "suppressed" in reason.lower():
                alert.status = AlertStatus.SUPPRESSED
            return alert
        # 添加到活跃告警
        self.alerts[alert_id] = alert
        self.alert_history.append(alert)
        # 限制历史记录大小
        if len(self.alert_history) > self.max_history_size:
            self.alert_history = self.alert_history[-self.max_history_size:]
        # 聚合告警
        self.aggregator.aggregate_alert(alert)
        # 发送告警
        await self._send_alert(alert, channels)
        # 记录指标
        self.metrics.record_alert_created(
            level=alert.level.value,
            alert_type=alert.type.value,
            source=alert.source
        )
        self.logger.info(f"Alert created: {alert_id}")
        return alert
    async def resolve_alert(self, alert_id: str) -> bool:
        解决告警
        Resolve Alert
        Args:
            alert_id: 告警ID / Alert ID
        Returns:
            bool: 是否成功解决 / Whether successfully resolved
        alert = self.alerts.get(alert_id)
        if not alert:
            self.logger.warning(f"Alert not found: {alert_id}")
            return False
        if alert.is_resolved():
            return True
        # 解决告警
        alert.resolve()
        # 更新相关组的统计
        for group in self.aggregator.groups.values():
            group.remove_alert(alert)
            group.update_status()
        # 记录指标
        duration = alert.get_duration()
        if duration:
            self.metrics.record_alert_resolved(
                level=alert.level.value,
                alert_type=alert.type.value,
                source=alert.source,
                duration_seconds=duration.total_seconds()
            )
        # 发送解决通知
        await self._send_alert(alert, None)
        self.logger.info(f"Alert resolved: {alert_id}")
        return True
    async def silence_alert(self, alert_id: str) -> bool:
        静默告警
        Silence Alert
        Args:
            alert_id: 告警ID / Alert ID
        Returns:
            bool: 是否成功静默 / Whether successfully silenced
        alert = self.alerts.get(alert_id)
        if not alert:
            return False
        alert.silence()
        self.logger.info(f"Alert silenced: {alert_id}")
        return True
    async def _send_alert(
        self,
        alert: Alert,
        channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        发送告警到渠道
        Send Alert to Channels
        Args:
            alert: 告警对象 / Alert object
            channels: 指定渠道 / Specific channels
        Returns:
            Dict[str, bool]: 发送结果 / Send results
        results = await self.channel_manager.send_to_all(alert, channels)
        # 记录发送结果
        for channel, success in results.items():
            status = "success" if success else "failed"
            self.metrics.record_notification_sent(channel, status)
        return results
    async def _update_rule_context(self):
        # 添加当前告警统计
        active_alerts = sum(1 for alert in self.alerts.values() if alert.is_active())
        context_data = {
            "active_alerts_count": active_alerts,
            "total_alerts_count": len(self.alerts),
            "timestamp": datetime.utcnow(),
        }
        # 按级别统计
        level_counts = {}
        for alert in self.alerts.values():
            if alert.is_active():
                level = alert.level.value
                level_counts[level] = level_counts.get(level, 0) + 1
        context_data["alert_counts_by_level"] = level_counts
        # 更新规则引擎
        self.rule_engine.update_context_variables(context_data)
    async def _handle_rule_triggered_alert(self, alert: Alert):
        处理规则触发的告警
        Handle Rule-Triggered Alert
        Args:
            alert: 告警对象 / Alert object
        # 添加到活跃告警
        self.alerts[alert.alert_id] = alert
        self.alert_history.append(alert)
        # 发送告警
        await self._send_alert(alert, None)
        # 记录指标
        self.metrics.record_alert_created(
            level=alert.level.value,
            alert_type=alert.type.value,
            source=alert.source
        )
    async def _perform_cleanup(self):
        # 清理过期的抑制规则
        self.deduplicator.cleanup_expired_rules()
        # 清理旧的告警组
        self.aggregator.remove_old_groups()
        # 清理规则引擎历史
        self.rule_engine.clear_history()
        self.logger.info("Periodic cleanup completed")
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        获取告警
        Get Alert
        Args:
            alert_id: 告警ID / Alert ID
        Returns:
            Optional[Alert]: 告警对象 / Alert object
        return self.alerts.get(alert_id)
    def get_active_alerts(self) -> List[Alert]:
        获取活跃告警
        Get Active Alerts
        Returns:
            List[Alert]: 活跃告警列表 / List of active alerts
        return [alert for alert in self.alerts.values() if alert.is_active()]
    def get_alerts_by_source(self, source: str) -> List[Alert]:
        根据来源获取告警
        Get Alerts by Source
        Args:
            source: 来源 / Source
        Returns:
            List[Alert]: 告警列表 / List of alerts
        return [alert for alert in self.alerts.values() if alert.source == source]
    def get_alerts_by_level(self, level: AlertLevel) -> List[Alert]:
        根据级别获取告警
        Get Alerts by Level
        Args:
            level: 告警级别 / Alert level
        Returns:
            List[Alert]: 告警列表 / List of alerts
        return [alert for alert in self.alerts.values() if alert.level == level]
    def search_alerts(
        self,
        query: Optional[str] = None,
        source: Optional[str] = None,
        level: Optional[AlertLevel] = None,
        status: Optional[AlertStatus] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Alert]:
        搜索告警
        Search Alerts
        Args:
            query: 查询字符串 / Query string
            source: 来源过滤 / Source filter
            level: 级别过滤 / Level filter
            status: 状态过滤 / Status filter
            start_time: 开始时间 / Start time
            end_time: 结束时间 / End time
            limit: 限制数量 / Limit
        Returns:
            List[Alert]: 匹配的告警列表 / List of matching alerts
        alerts = list(self.alerts.values())
        # 应用过滤条件
        if query:
            query_lower = query.lower()
            alerts = [
                alert for alert in alerts
                if query_lower in alert.title.lower()
                or query_lower in alert.message.lower()
            ]
        if source:
            alerts = [alert for alert in alerts if alert.source == source]
        if level:
            alerts = [alert for alert in alerts if alert.level == level]
        if status:
            alerts = [alert for alert in alerts if alert.status == status]
        if start_time:
            alerts = [alert for alert in alerts if alert.created_at >= start_time]
        if end_time:
            alerts = [alert for alert in alerts if alert.created_at <= end_time]
        # 按创建时间倒序排序
        alerts.sort(key=lambda x: x.created_at, reverse=True)
        # 限制数量
        return alerts[:limit]
    def get_statistics(self) -> Dict[str, Any]:
        获取统计信息
        Get Statistics
        Returns:
            Dict[str, Any]: 统计信息 / Statistics
        total_alerts = len(self.alerts)
        active_alerts = len(self.get_active_alerts())
        resolved_alerts = sum(1 for alert in self.alerts.values() if alert.is_resolved())
        # 按级别统计
        level_counts = {}
        for alert in self.alerts.values():
            if alert.is_active():
                level = alert.level.value
                level_counts[level] = level_counts.get(level, 0) + 1
        # 按来源统计
        source_counts = {}
        for alert in self.alerts.values():
            if alert.is_active():
                source = alert.source
                source_counts[source] = source_counts.get(source, 0) + 1
        # 获取各组件统计
        rule_stats = self.rule_engine.get_statistics()
        deduplication_stats = self.deduplicator.get_statistics()
        aggregation_stats = self.aggregator.get_statistics()
        scheduler_stats = self.scheduler.get_statistics()
        channel_status = self.channel_manager.get_channel_status()
        return {
            "alerts": {
                "total": total_alerts,
                "active": active_alerts,
                "resolved": resolved_alerts,
                "silenced": total_alerts - active_alerts - resolved_alerts,
                "by_level": level_counts,
                "by_source": source_counts,
            },
            "rules": rule_stats,
            "deduplication": deduplication_stats,
            "aggregation": aggregation_stats,
            "scheduler": scheduler_stats,
            "channels": channel_status,
            "metrics": self.metrics.get_metrics_summary(),
            "manager": {
                "history_size": len(self.alert_history),
                "config": {
                    "deduplication_minutes": self.config.get("deduplication_minutes", 5),
                    "rule_evaluation_interval": self.config.get("rule_evaluation_interval", 60),
                    "cleanup_interval": self.config.get("cleanup_interval", 3600),
                    "alert_retention_hours": self.config.get("alert_retention_hours", 24),
                }
            }
        }
    # 向后兼容性方法
    @property
    def suppression_rules(self):
        return self.deduplicator.suppression_rules
    @property
    def aggregation_rules(self):
        return self.aggregator.aggregation_rules
    def remove_old_groups(self, older_than: timedelta = timedelta(hours=24)):
        self.aggregator.remove_old_groups(older_than)
    async def _periodic_rule_evaluation(self):
        await self.scheduler.run_task_now("rule_evaluation")
    async def _periodic_cleanup(self):
        await self.scheduler.run_task_now("cleanup")
    def is_suppressed(self, alert: Alert):
        return self.deduplicator.is_suppressed(alert)
    def is_duplicate(self, alert: Alert):
        return self.deduplicator.is_duplicate(alert)
    def aggregate_alert(self, alert: Alert):
        return self.aggregator.aggregate_alert(alert)