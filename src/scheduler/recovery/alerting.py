"""
告警处理
Alert Handling

负责处理恢复过程中的告警通知。
"""

from datetime import timedelta
from typing import Dict
from typing import List
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List

from .models import FailureType, TaskFailure

logger = logging.getLogger(__name__)


class AlertManager:
    """告警管理器"""

    def __init__(self):
        """初始化告警管理器"""
        self.handlers: List[Callable[[Dict[str, Any]], None]] = []
        self.alert_history: List[Dict[str, Any]] = []
        self.suppression_rules: Dict[str, Dict[str, Any]] = {}

    def register_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        注册告警处理器

        Args:
            handler: 告警处理函数
        """
        self.handlers.append(handler)
        logger.info(f"告警处理器已注册: {handler.__name__}")

    def unregister_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        取消注册告警处理器

        Args:
            handler: 告警处理函数
        """
        if handler in self.handlers:
            self.handlers.remove(handler)
            logger.info(f"告警处理器已取消注册: {handler.__name__}")

    def send_alert(
        self,
        level: str,
        message: str,
        details: Dict[str, Any] | None = None,
        source: str = "recovery_handler",
    ) -> bool:
        """
        发送告警

        Args:
            level: 告警级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: 告警消息
            details: 详细信息
            source: 告警来源

        Returns:
            bool: 是否成功发送
        """
        # 检查抑制规则
        if self._is_suppressed(level, message, details):
            logger.debug(f"告警已被抑制: {level} - {message}")
            return False

        alert_data = {
            "level": level,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "id": self._generate_alert_id(),
        }

        # 记录告警
        self.alert_history.append(alert_data)
        self._cleanup_old_alerts()

        # 记录日志
        log_level = self._get_log_level(level)
        logger.log(log_level, f"发送告警: {level} - {message}")

        # 调用注册的告警处理器
        success_count = 0
        for handler in self.handlers:
            try:
                handler(alert_data)
                success_count += 1
            except Exception as e:
                logger.error(f"告警处理器执行失败: {e}")

        return success_count > 0

    def check_retry_threshold(
        self, task: Any, failure: TaskFailure, config: Dict[str, Any]
    ) -> None:
        """
        检查重试阈值并发送告警

        Args:
            task: 任务对象
            failure: 失败记录
            config: 配置信息
        """
        alert_threshold = config.get("alert_threshold", 3)

        if task.retry_count >= alert_threshold:
            self.send_alert(
                level="WARNING",
                message=f"任务 {task.task_id} 连续失败 {task.retry_count} 次",
                details={
                    "task_id": task.task_id,
                    "task_name": getattr(task, "name", "unknown"),
                    "failure_type": failure.failure_type.value,
                    "error_message": failure.error_message,
                    "retry_count": task.retry_count,
                    "max_retries": config.get("max_retries", 3),
                },
                source="retry_threshold",
            )

    def check_failure_patterns(
        self, task_id: str, failure_patterns: Dict[str, List[FailureType]]
    ) -> None:
        """
        检查失败模式并发送告警

        Args:
            task_id: 任务ID
            failure_patterns: 失败模式记录
        """
        if task_id not in failure_patterns:
            return

        recent_failures = failure_patterns[task_id]

        # 检查是否有重复的失败类型
        if len(recent_failures) >= 3:
            last_three = recent_failures[-3:]
            if len(set(last_three)) == 1:  # 连续三次同类型失败
                self.send_alert(
                    level="HIGH",
                    message=f"任务 {task_id} 连续发生 {last_three[0].value} 类型失败",
                    details={
                        "task_id": task_id,
                        "pattern": "连续同类型失败",
                        "failure_type": last_three[0].value,
                        "count": 3,
                    },
                    source="failure_pattern",
                )

    def request_manual_intervention(self, task: Any, failure: TaskFailure) -> None:
        """
        发送人工干预请求

        Args:
            task: 任务对象
            failure: 失败记录
        """
        self.send_alert(
            level="CRITICAL",
            message=f"任务 {task.task_id} 需要人工干预",
            details={
                "task_id": task.task_id,
                "failure_type": failure.failure_type.value,
                "error_message": failure.error_message,
                "action_required": "请检查任务配置和系统状态",
                "context": failure.context,
            },
            source="manual_intervention",
        )

    def add_suppression_rule(
        self,
        name: str,
        pattern: str,
        duration_minutes: int = 60,
        max_alerts: int = 1,
    ) -> None:
        """
        添加告警抑制规则

        Args:
            name: 规则名称
            pattern: 匹配模式
            duration_minutes: 抑制持续时间（分钟）
            max_alerts: 最大告警次数
        """
        self.suppression_rules[name] = {
            "pattern": pattern.lower(),
            "start_time": None,
            "end_time": None,
            "count": 0,
            "max_alerts": max_alerts,
            "duration_minutes": duration_minutes,
        }
        logger.info(f"添加告警抑制规则: {name}")

    def _is_suppressed(
        self, level: str, message: str, details: Dict[str, Any] | None
    ) -> bool:
        """检查告警是否被抑制"""
        message_lower = message.lower()

        for name, rule in self.suppression_rules.items():
            if rule["pattern"] in message_lower:
                # 检查时间窗口
                now = datetime.now()
                if rule["start_time"] and now < rule["end_time"]:
                    if rule["count"] >= rule["max_alerts"]:
                        return True

                # 开始新的抑制窗口
                rule["start_time"] = now
                rule["end_time"] = now + timedelta(minutes=rule["duration_minutes"])
                rule["count"] += 1

        return False

    def _generate_alert_id(self) -> str:
        """生成告警ID"""
        import uuid

        return str(uuid.uuid4())[:8]

    def _get_log_level(self, level: str) -> int:
        """获取日志级别"""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        return level_map.get(level.upper(), logging.INFO)

    def _cleanup_old_alerts(self, keep_count: int = 1000) -> None:
        """清理旧的告警记录"""
        if len(self.alert_history) > keep_count:
            self.alert_history = self.alert_history[-keep_count:]

    def get_alert_statistics(self) -> Dict[str, Any]:
        """获取告警统计信息"""
        if not self.alert_history:
            return {
                "total_alerts": 0,
                "by_level": {},
                "by_source": {},
                "recent_24h": 0,
            }

        # 按级别统计
        by_level = {}
        for alert in self.alert_history:
            level = alert["level"]
            by_level[level] = by_level.get(level, 0) + 1

        # 按来源统计
        by_source = {}
        for alert in self.alert_history:
            source = alert["source"]
            by_source[source] = by_source.get(source, 0) + 1

        # 最近24小时
        now = datetime.now()
        recent_24h = sum(
            1
            for alert in self.alert_history
            if now - datetime.fromisoformat(alert["timestamp"]) <= timedelta(hours=24)
        )

        return {
            "total_alerts": len(self.alert_history),
            "by_level": by_level,
            "by_source": by_source,
            "recent_24h": recent_24h,
            "suppression_rules": len(self.suppression_rules),
        }
