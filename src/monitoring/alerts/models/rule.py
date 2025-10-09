"""
告警规则实体类
Alert Rule Entity

定义告警触发条件和行为的数据结构。
Defines the data structure for alert trigger conditions and actions.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from .enums import AlertChannel, AlertLevel


class AlertRule:
    """
    告警规则类
    Alert Rule Class

    定义告警触发的条件和行为。
    Defines conditions and actions for alert triggering.

    Attributes:
        rule_id (str): 规则ID / Rule ID
        name (str): 规则名称 / Rule name
        description (str): 规则描述 / Rule description
        condition (str): 告警条件 / Alert condition
        level (AlertLevel): 告警级别 / Alert level
        channels (List[AlertChannel]): 告警渠道 / Alert channels
        throttle_seconds (int): 去重时间 / Deduplication time
        enabled (bool): 是否启用 / Whether enabled
        labels (Dict[str, str]): 规则标签 / Rule labels
        annotations (Dict[str, str]): 规则注释 / Rule annotations
        last_fired (Optional[datetime]): 最后触发时间 / Last fired time
        fire_count (int): 触发次数 / Fire count
    """

    def __init__(
        self,
        rule_id: str,
        name: str,
        condition: str,
        level: AlertLevel,
        channels: List[AlertChannel],
        description: Optional[str] = None,
        throttle_seconds: int = 300,  # 5分钟内去重
        enabled: bool = True,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
    ):
        """
        初始化告警规则
        Initialize Alert Rule

        Args:
            rule_id: 规则ID / Rule ID
            name: 规则名称 / Rule name
            condition: 告警条件 / Alert condition
            level: 告警级别 / Alert level
            channels: 告警渠道 / Alert channels
            description: 规则描述 / Rule description
            throttle_seconds: 去重时间 / Deduplication time
            enabled: 是否启用 / Whether enabled
            labels: 规则标签 / Rule labels
            annotations: 规则注释 / Rule annotations
        """
        self.rule_id = rule_id
        self.name = name
        self.description = description or name
        self.condition = condition
        self.level = level
        self.channels = channels
        self.throttle_seconds = throttle_seconds
        self.enabled = enabled
        self.labels = labels or {}
        self.annotations = annotations or {}
        self.last_fired: Optional[datetime] = None
        self.fire_count = 0

    def should_fire(self, last_fire_time: Optional[datetime] = None) -> bool:
        """
        检查是否应该触发告警
        Check if Alert Should Fire

        Args:
            last_fire_time: 上次触发时间 / Last fire time

        Returns:
            bool: 是否应该触发 / Whether should fire
        """
        if not self.enabled:
            return False

        now = datetime.utcnow()

        # 检查去重时间
        if self.throttle_seconds > 0:
            check_time = last_fire_time or self.last_fired
            if check_time:
                time_since_last = now - check_time
                if time_since_last.total_seconds() < self.throttle_seconds:
                    return False

        return True

    def record_fire(self) -> None:
        """
        记录触发
        Record Fire

        更新触发信息。
        Updates firing information.
        """
        self.last_fired = datetime.utcnow()
        self.fire_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        Convert to Dictionary Format

        Returns:
            Dict[str, Any]: 字典表示 / Dictionary representation
        """
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "condition": self.condition,
            "level": self.level.value,
            "channels": [c.value for c in self.channels],
            "throttle_seconds": self.throttle_seconds,
            "enabled": self.enabled,
            "labels": self.labels,
            "annotations": self.annotations,
            "last_fired": self.last_fired.isoformat() if self.last_fired else None,
            "fire_count": self.fire_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AlertRule":
        """
        从字典创建告警规则
        Create Alert Rule from Dictionary

        Args:
            data: 字典数据 / Dictionary data

        Returns:
            AlertRule: 告警规则对象 / Alert rule object
        """
        last_fired = None
        if data.get("last_fired"):
            if isinstance(data["last_fired"], str):
                last_fired = datetime.fromisoformat(data["last_fired"])
            else:
                last_fired = data["last_fired"]

        rule = cls(
            rule_id=data["rule_id"],
            name=data["name"],
            condition=data["condition"],
            level=AlertLevel(data["level"]),
            channels=[AlertChannel(c) for c in data["channels"]],
            description=data.get("description"),
            throttle_seconds=data.get("throttle_seconds", 300),
            enabled=data.get("enabled", True),
            labels=data.get("labels", {}),
            annotations=data.get("annotations", {}),
        )

        rule.last_fired = last_fired
        rule.fire_count = data.get("fire_count", 0)

        return rule

    def enable(self) -> None:
        """
        启用规则
        Enable Rule
        """
        self.enabled = True

    def disable(self) -> None:
        """
        禁用规则
        Disable Rule
        """
        self.enabled = False

    def update_throttle(self, seconds: int) -> None:
        """
        更新去重时间
        Update Throttle Time

        Args:
            seconds: 去重时间（秒）/ Throttle time in seconds
        """
        self.throttle_seconds = max(0, seconds)

    def add_channel(self, channel: AlertChannel) -> None:
        """
        添加告警渠道
        Add Alert Channel

        Args:
            channel: 告警渠道 / Alert channel
        """
        if channel not in self.channels:
            self.channels.append(channel)

    def remove_channel(self, channel: AlertChannel) -> None:
        """
        移除告警渠道
        Remove Alert Channel

        Args:
            channel: 告警渠道 / Alert channel
        """
        if channel in self.channels:
            self.channels.remove(channel)

    def reset_fire_count(self) -> None:
        """
        重置触发计数
        Reset Fire Count
        """
        self.fire_count = 0
        self.last_fired = None

    def get_fire_rate(self) -> float:
        """
        获取触发频率
        Get Fire Rate

        Returns:
            float: 每分钟触发次数 / Fires per minute
        """
        if self.fire_count == 0 or not self.last_fired:
            return 0.0

        # 计算从第一次触发到现在的时长（分钟）
        time_diff_minutes = (datetime.utcnow() - self.last_fired).total_seconds() / 60
        if time_diff_minutes <= 0:
            return float(self.fire_count)

        return self.fire_count / time_diff_minutes

    def __str__(self) -> str:
        """
        字符串表示
        String Representation

        Returns:
            str: 字符串 / String
        """
        return f"AlertRule({self.name}: {self.condition})"

    def __repr__(self) -> str:
        """
        对象表示
        Object Representation

        Returns:
            str: 对象字符串 / Object string
        """
        return (
            f"AlertRule(id={self.rule_id}, name={self.name}, "
            f"level={self.level.value}, enabled={self.enabled})"
        )