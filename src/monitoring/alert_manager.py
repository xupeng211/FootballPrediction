"""
告警管理器（向后兼容）
Alert Manager (Backward Compatible)

为了保持向后兼容性，此文件重新导出新的模块化告警管理器组件。
同时提供与旧版本API兼容的接口。

Provides backward compatible exports for the modular alert manager components
and maintains compatibility with old version APIs.
"""

# 导入重构后的模块化组件
    # 核心管理器
    AlertManager as _AlertManager,
    AlertRuleEngine,
    AlertAggregator,
    AlertChannelManager,

    # 模型
    Alert as _Alert,
    AlertRule as _AlertRule,
    AlertSeverity,
    AlertType,
    AlertLevel,
    AlertStatus,
    AlertChannel,

    # 指标
    PrometheusMetrics,

    # 渠道
    LogChannel,
    PrometheusChannel,
    WebhookChannel,
    EmailChannel,
    SlackChannel,
)

# 保持向后兼容的导入

logger = logging.getLogger(__name__)

# 向后兼容的包装类
class AlertManager(_AlertManager):
    """
    告警管理器（向后兼容包装器）
    Alert Manager (Backward compatibility wrapper)

    注意：此类继承自重构后的模块化管理器。
    建议直接使用 alert_manager_mod.AlertManager 获取最新功能。
    """

    # 向后兼容：保持旧的方法名
    async def create_alert(
        self,
        title: str,
        message: str,
        level: AlertLevel,
        source: str,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
        channels: Optional[List[str]] = None,
        # 旧版本参数
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> Optional[_Alert]:
        """
        创建告警（向后兼容方法）
        Create Alert (Backward compatibility method)
        """
        # 处理旧版本参数
        if alert_type:
            # 将 alert_type 转换为标签
            labels = labels or {}
            labels["alert_type"] = alert_type

        if severity:
            # 将 severity 映射到 level
            severity_mapping = {
                "low": AlertLevel.INFO,
                "medium": AlertLevel.WARNING,
                "high": AlertLevel.ERROR,
                "critical": AlertLevel.CRITICAL,
            }
            if severity in severity_mapping:
                level = severity_mapping[severity]

        # 调用新方法
        return await super().create_alert(
            title=title,
            message=message,
            level=level,
            source=source,
            labels=labels,
            annotations=annotations,
            channels=channels,
        )

    async def get_alerts(
        self,
        active_only: bool = True,
        source: Optional[str] = None,
        level: Optional[AlertLevel] = None,
        limit: int = 100,
        # 旧版本参数
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[_Alert]:
        """
        获取告警列表（向后兼容方法）
        Get Alerts (Backward compatibility method)
        """
        status = AlertStatus.ACTIVE if active_only else None
        return self.search_alerts(
            source=source,
            level=level,
            status=status,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    async def get_alert_count(self, active_only: bool = True) -> int:
        """
        获取告警数量（向后兼容方法）
        Get Alert Count (Backward compatibility method)
        """
        if active_only:
            return len(self.get_active_alerts())
        else:
            return len(self.alerts)

    async def silence_all(self, source: Optional[str] = None) -> int:
        """
        静默所有告警（向后兼容方法）
        Silence All Alerts (Backward compatibility method)
        """
        alerts = self.get_active_alerts()
        if source:
            alerts = [a for a in alerts if a.source == source]

        silenced_count = 0
        for alert in alerts:
            if await self.silence_alert(alert.alert_id):
                silenced_count += 1

        return silenced_count

    async def resolve_all(self, source: Optional[str] = None) -> int:
        """
        解决所有告警（向后兼容方法）
        Resolve All Alerts (Backward compatibility method)
        """
        alerts = self.get_active_alerts()
        if source:
            alerts = [a for a in alerts if a.source == source]

        resolved_count = 0
        for alert in alerts:
            if await self.resolve_alert(alert.alert_id):
                resolved_count += 1

        return resolved_count


class Alert(_Alert):
    """
    告警对象（向后兼容包装器）
    Alert Object (Backward compatibility wrapper)
    """
    pass  # 直接继承，所有功能都在基类中实现


class AlertRule(_AlertRule):
    """
    告警规则（向后兼容包装器）
    Alert Rule (Backward compatibility wrapper)
    """
    pass  # 直接继承，所有功能都在基类中实现


# 向后兼容：保持旧的常量
DEFAULT_THROTTLE_SECONDS = 300
DEFAULT_RETENTION_HOURS = 24
DEFAULT_EVALUATION_INTERVAL = 60

# 向后兼容：保持旧的工厂函数
def create_alert_manager(
    config: Optional[Dict[str, Any]] = None
) -> AlertManager:
    """
    创建告警管理器（向后兼容函数）
    Create Alert Manager (Backward compatibility function)
    """
    return AlertManager(config)


def create_alert_rule(
    rule_id: str,
    name: str,
    condition: str,
    level: AlertLevel,
    channels: Optional[List[str]] = None,
    throttle_seconds: int = DEFAULT_THROTTLE_SECONDS,
    enabled: bool = True,
) -> AlertRule:
    """
    创建告警规则（向后兼容函数）
    Create Alert Rule (Backward compatibility function)
    """
    # 转换渠道名称
    channel_objects = []
    if channels:
        for channel_name in channels:
            try:
                channel_objects.append(AlertChannel(channel_name))
            except ValueError:
                logger.warning(f"Unknown alert channel: {channel_name}")

    return AlertRule(
        rule_id=rule_id,
        name=name,
        condition=condition,
        level=level,
        channels=channel_objects,
        throttle_seconds=throttle_seconds,
        enabled=enabled,
    )


# 向后兼容：保持旧的快捷函数
async def send_alert(
    manager: AlertManager,
    title: str,
    message: str,
    level: AlertLevel,
    source: str,
    labels: Optional[Dict[str, str]] = None,
    channels: Optional[List[str]] = None,
) -> Optional[Alert]:
    """
    发送告警（向后兼容函数）
    Send Alert (Backward compatibility function)
    """
    return await manager.create_alert(
        title=title,
        message=message,
        level=level, timedelta


        source=source,
        labels=labels,
        channels=channels,
    )


# 导出所有公共接口以保持向后兼容
__all__ = [
    # 核心类
    "AlertManager",
    "AlertRuleEngine",
    "AlertAggregator",
    "AlertChannelManager",

    # 模型
    "Alert",
    "AlertRule",
    "AlertSeverity",
    "AlertType",
    "AlertLevel",
    "AlertStatus",
    "AlertChannel",

    # 指标
    "PrometheusMetrics",

    # 渠道
    "LogChannel",
    "PrometheusChannel",
    "WebhookChannel",
    "EmailChannel",
    "SlackChannel",

    # 向后兼容
    "create_alert_manager",
    "create_alert_rule",
    "send_alert",
    "DEFAULT_THROTTLE_SECONDS",
    "DEFAULT_RETENTION_HOURS",
    "DEFAULT_EVALUATION_INTERVAL",
]