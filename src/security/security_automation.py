#!/usr/bin/env python3
"""
安全自动化响应系统
提供自动化安全响应、威胁缓解、安全策略执行等功能
"""

import asyncio
import json
import subprocess
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from src.core.logger import get_logger
from src.security.security_monitor import (
    SecurityEvent,
    SecurityEventType,
    ThreatLevel,
    get_security_monitor,
)

logger = get_logger(__name__)


class ResponseAction(Enum):
    """响应动作类型"""

    BLOCK_IP = "block_ip"
    RATE_LIMIT = "rate_limit"
    LOGOUT_USER = "logout_user"
    DISABLE_ACCOUNT = "disable_account"
    NOTIFY_ADMIN = "notify_admin"
    SCAN_SYSTEM = "scan_system"
    BACKUP_DATA = "backup_data"
    ISOLATE_SERVICE = "isolate_service"
    UPDATE_FIREWALL = "update_firewall"
    ENFORCE_PASSWORD_CHANGE = "enforce_password_change"


class ResponsePriority(Enum):
    """响应优先级"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ResponseRule:
    """响应规则"""

    rule_id: str
    name: str
    trigger_event_types: list[SecurityEventType]
    trigger_threat_levels: list[ThreatLevel]
    conditions: dict[str, Any]
    actions: list[ResponseAction]
    priority: ResponsePriority
    enabled: bool = True
    cooldown_minutes: int = 30
    max_executions_per_hour: int = 10
    description: str = ""


@dataclass
class ResponseExecution:
    """响应执行记录"""

    execution_id: str
    rule_id: str
    event_id: str
    actions: list[ResponseAction]
    execution_time: datetime
    success: bool
    error_message: str | None = None
    duration_ms: int = 0
    affected_resources: dict[str, Any] = None


class SecurityAction(ABC):
    """安全动作基类"""

    def __init__(self, name: str):
        self.name = name
        self.last_execution = {}

    @abstractmethod
    async def execute(
        self, event: SecurityEvent, context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        执行安全动作

        Args:
            event: 触发的安全事件
            context: 执行上下文

        Returns:
            执行结果
        """
        pass

    @abstractmethod
    def can_execute(self, event: SecurityEvent, context: dict[str, Any]) -> bool:
        """检查是否可以执行该动作"""
        pass

    def get_cooldown_key(self, event: SecurityEvent) -> str:
        """获取冷却期键"""
        return f"{self.name}:{event.source_ip}"


class BlockIPAction(SecurityAction):
    """IP阻止动作"""

    def __init__(self):
        super().__init__("block_ip")

    async def execute(
        self, event: SecurityEvent, context: dict[str, Any]
    ) -> dict[str, Any]:
        """执行IP阻止"""
        monitor = get_security_monitor()

        # 获取阻止时长
        duration_hours = context.get("duration_hours", 24)
        if event.threat_level == ThreatLevel.CRITICAL:
            duration_hours = 72
        elif event.threat_level == ThreatLevel.HIGH:
            duration_hours = 48

        success = await monitor.block_ip(
            event.source_ip,
            duration_hours=duration_hours,
            reason=f"自动化响应: {event.event_type.value}",
        )

        return {
            "success": success,
            "ip_blocked": event.source_ip,
            "duration_hours": duration_hours,
            "action": "IP_BLOCKED",
        }

    def can_execute(self, event: SecurityEvent, context: dict[str, Any]) -> bool:
        """检查是否可以阻止IP"""
        # 不阻止私有IP
        try:
            import ipaddress

            ip = ipaddress.ip_address(event.source_ip)
            if ip.is_private:
                return False
        except ValueError:
            return False

        # 检查是否已经被阻止
        monitor = get_security_monitor()
        return not monitor.is_ip_blocked(event.source_ip)


class RateLimitAction(SecurityAction):
    """速率限制动作"""

    def __init__(self):
        super().__init__("rate_limit")

    async def execute(
        self, event: SecurityEvent, context: dict[str, Any]
    ) -> dict[str, Any]:
        """执行速率限制"""
        # 这里应该与实际的速率限制系统集成
        # 模拟实现

        limit_requests_per_minute = context.get("limit_requests", 10)
        duration_minutes = context.get("duration_minutes", 30)

        # 在实际实现中，这里会调用Redis或其他限流服务
        logger.info(
            f"对IP {event.source_ip} 实施速率限制: {limit_requests_per_minute} req/min, 持续 {duration_minutes} 分钟"
        )

        return {
            "success": True,
            "ip_limited": event.source_ip,
            "limit_requests": limit_requests_per_minute,
            "duration_minutes": duration_minutes,
            "action": "RATE_LIMITED",
        }

    def can_execute(self, event: SecurityEvent, context: dict[str, Any]) -> bool:
        """检查是否可以实施速率限制"""
        # 检查是否已经有速率限制
        return True  # 简化实现，实际应该检查现有限流状态


class NotifyAdminAction(SecurityAction):
    """管理员通知动作"""

    def __init__(self):
        super().__init__("notify_admin")

    async def execute(
        self, event: SecurityEvent, context: dict[str, Any]
    ) -> dict[str, Any]:
        """发送管理员通知"""
        notification_methods = context.get("methods", ["email", "slack"])
        severity = context.get("severity", event.threat_level.value)

        results = {}

        if "email" in notification_methods:
            email_result = await self._send_email_notification(event, severity)
            results["email"] = email_result

        if "slack" in notification_methods:
            slack_result = await self._send_slack_notification(event, severity)
            results["slack"] = slack_result

        if "webhook" in notification_methods:
            webhook_result = await self._send_webhook_notification(event, severity)
            results["webhook"] = webhook_result

        return {
            "success": any(results.values()),
            "notifications": results,
            "action": "ADMIN_NOTIFIED",
        }

    def can_execute(self, event: SecurityEvent, context: dict[str, Any]) -> bool:
        """检查是否可以发送通知"""
        # 检查通知频率限制
        cooldown_key = self.get_cooldown_key(event)
        if cooldown_key in self.last_execution:
            last_time = self.last_execution[cooldown_key]
            if datetime.now() - last_time < timedelta(minutes=5):
                return False

        return True

    async def _send_email_notification(
        self, event: SecurityEvent, severity: str
    ) -> bool:
        """发送邮件通知"""
        try:
            # 这里应该使用实际的邮件配置
            # 模拟实现
            subject = f"🚨 安全告警 - {severity.upper()}"
            body = f"""
            安全事件详情:

            事件类型: {event.event_type.value}
            威胁等级: {event.threat_level.value}
            源IP: {event.source_ip}
            请求路径: {event.request_path}
            用户ID: {event.user_id or '未知'}
            时间: {event.timestamp.isoformat()}
            描述: {event.description}

            请立即登录安全控制面板查看详情。
            """

            logger.info(f"发送安全告警邮件: {subject}")
            return True

        except Exception as e:
            logger.error(f"邮件通知发送失败: {e}")
            return False

    async def _send_slack_notification(
        self, event: SecurityEvent, severity: str
    ) -> bool:
        """发送Slack通知"""
        try:
            # 这里应该使用实际的Slack Webhook
            webhook_url = "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"

            message = {
                "text": f"🚨 安全告警 - {severity.upper()}",
                "attachments": [
                    {
                        "color": (
                            "danger" if severity in ["high", "critical"] else "warning"
                        ),
                        "fields": [
                            {
                                "title": "事件类型",
                                "value": event.event_type.value,
                                "short": True,
                            },
                            {"title": "源IP", "value": event.source_ip, "short": True},
                            {
                                "title": "威胁等级",
                                "value": event.threat_level.value,
                                "short": True,
                            },
                            {
                                "title": "请求路径",
                                "value": event.request_path,
                                "short": True,
                            },
                        ],
                        "text": f"描述: {event.description}",
                    }
                ],
            }

            # 模拟发送
            logger.info(f"发送Slack通知: {message['text']}")
            return True

        except Exception as e:
            logger.error(f"Slack通知发送失败: {e}")
            return False

    async def _send_webhook_notification(
        self, event: SecurityEvent, severity: str
    ) -> bool:
        """发送Webhook通知"""
        try:
            # 这里应该使用实际的Webhook URL
            webhook_url = "https://your-security-system.com/webhook"

            payload = {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "threat_level": event.threat_level.value,
                "source_ip": event.source_ip,
                "timestamp": event.timestamp.isoformat(),
                "description": event.description,
                "metadata": event.metadata,
            }

            # 模拟发送
            logger.info(f"发送Webhook通知: {webhook_url}")
            return True

        except Exception as e:
            logger.error(f"Webhook通知发送失败: {e}")
            return False


class ScanSystemAction(SecurityAction):
    """系统扫描动作"""

    def __init__(self):
        super().__init__("scan_system")

    async def execute(
        self, event: SecurityEvent, context: dict[str, Any]
    ) -> dict[str, Any]:
        """执行系统扫描"""
        scan_types = context.get("scan_types", ["security", "malware", "integrity"])

        results = {}

        for scan_type in scan_types:
            if scan_type == "security":
                results["security"] = await self._run_security_scan()
            elif scan_type == "malware":
                results["malware"] = await self._run_malware_scan()
            elif scan_type == "integrity":
                results["integrity"] = await self._run_integrity_scan()

        return {"success": True, "scan_results": results, "action": "SYSTEM_SCANNED"}

    def can_execute(self, event: SecurityEvent, context: dict[str, Any]) -> bool:
        """检查是否可以执行系统扫描"""
        # 检查扫描频率限制
        cooldown_key = self.get_cooldown_key(event)
        if cooldown_key in self.last_execution:
            last_time = self.last_execution[cooldown_key]
            if datetime.now() - last_time < timedelta(hours=1):
                return False

        return True

    async def _run_security_scan(self) -> dict[str, Any]:
        """运行安全扫描"""
        try:
            # 使用bandit进行安全扫描
            result = subprocess.run(
                ["bandit", "-r", "src/", "-f", "json"],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                return {"status": "success", "issues_found": 0}
            else:
                issues = json.loads(result.stdout)
                return {
                    "status": "issues_found",
                    "issues_count": len(issues.get("results", [])),
                }

        except subprocess.TimeoutExpired:
            return {"status": "timeout"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _run_malware_scan(self) -> dict[str, Any]:
        """运行恶意软件扫描"""
        try:
            # 模拟恶意软件扫描
            logger.info("开始恶意软件扫描...")
            await asyncio.sleep(5)  # 模拟扫描时间

            return {"status": "success", "threats_detected": 0}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _run_integrity_scan(self) -> dict[str, Any]:
        """运行完整性扫描"""
        try:
            # 模拟文件完整性扫描
            logger.info("开始文件完整性扫描...")
            await asyncio.sleep(3)  # 模拟扫描时间

            return {"status": "success", "integrity_violations": 0}

        except Exception as e:
            return {"status": "error", "error": str(e)}


class SecurityAutomationEngine:
    """安全自动化引擎"""

    def __init__(self):
        self.rules: list[ResponseRule] = []
        self.actions: dict[str, SecurityAction] = {}
        self.executions: list[ResponseExecution] = []
        self.rule_executions: dict[str, list[datetime]] = defaultdict(list)

        # 注册默认动作
        self._register_default_actions()

        # 加载默认规则
        self._load_default_rules()

        # 启动自动化引擎
        self._engine_task = None

    def _register_default_actions(self):
        """注册默认安全动作"""
        self.actions["block_ip"] = BlockIPAction()
        self.actions["rate_limit"] = RateLimitAction()
        self.actions["notify_admin"] = NotifyAdminAction()
        self.actions["scan_system"] = ScanSystemAction()

    def _load_default_rules(self):
        """加载默认响应规则"""
        default_rules = [
            ResponseRule(
                rule_id="auto_block_high_threat",
                name="自动阻止高威胁IP",
                trigger_event_types=[
                    SecurityEventType.INJECTION_ATTEMPT,
                    SecurityEventType.XSS_ATTEMPT,
                ],
                trigger_threat_levels=[ThreatLevel.HIGH, ThreatLevel.CRITICAL],
                conditions={},
                actions=[ResponseAction.BLOCK_IP, ResponseAction.NOTIFY_ADMIN],
                priority=ResponsePriority.HIGH,
                description="检测到注入或XSS攻击时自动阻止IP并通知管理员",
            ),
            ResponseRule(
                rule_id="brute_force_response",
                name="暴力破解响应",
                trigger_event_types=[SecurityEventType.BRUTE_FORCE],
                trigger_threat_levels=[ThreatLevel.HIGH],
                conditions={},
                actions=[
                    ResponseAction.BLOCK_IP,
                    ResponseAction.RATE_LIMIT,
                    ResponseAction.NOTIFY_ADMIN,
                ],
                priority=ResponsePriority.HIGH,
                description="检测到暴力破解攻击时阻止IP、限速并通知管理员",
            ),
            ResponseRule(
                rule_id="data_exfiltration_response",
                name="数据泄露响应",
                trigger_event_types=[SecurityEventType.DATA_EXFILTRATION],
                trigger_threat_levels=[ThreatLevel.CRITICAL],
                conditions={},
                actions=[
                    ResponseAction.BLOCK_IP,
                    ResponseAction.NOTIFY_ADMIN,
                    ResponseAction.SCAN_SYSTEM,
                ],
                priority=ResponsePriority.CRITICAL,
                description="检测到数据泄露时阻止IP、通知管理员并扫描系统",
            ),
            ResponseRule(
                rule_id="unusual_behavior_scan",
                name="异常行为扫描",
                trigger_event_types=[SecurityEventType.ANOMALOUS_BEHAVIOR],
                trigger_threat_levels=[ThreatLevel.MEDIUM, ThreatLevel.HIGH],
                conditions={"score_threshold": 50},
                actions=[ResponseAction.NOTIFY_ADMIN, ResponseAction.SCAN_SYSTEM],
                priority=ResponsePriority.MEDIUM,
                description="检测到异常行为时通知管理员并扫描系统",
            ),
            ResponseRule(
                rule_id="rate_limit_suspicious",
                name="可疑请求限速",
                trigger_event_types=[SecurityEventType.SUSPICIOUS_REQUEST],
                trigger_threat_levels=[ThreatLevel.MEDIUM],
                conditions={"repeat_offender": True},
                actions=[ResponseAction.RATE_LIMIT],
                priority=ResponsePriority.MEDIUM,
                description="对重复的可疑请求实施速率限制",
            ),
        ]

        self.rules.extend(default_rules)

    async def start_automation(self):
        """启动自动化引擎"""
        logger.info("启动安全自动化引擎...")

        # 监听安全事件
        monitor = get_security_monitor()
        self._engine_task = asyncio.create_task(self._monitor_events(monitor))

        logger.info("✅ 安全自动化引擎已启动")

    async def stop_automation(self):
        """停止自动化引擎"""
        logger.info("停止安全自动化引擎...")

        if self._engine_task:
            self._engine_task.cancel()

        logger.info("✅ 安全自动化引擎已停止")

    async def process_security_event(
        self, event: SecurityEvent
    ) -> list[ResponseExecution]:
        """处理安全事件"""
        executions = []

        # 查找匹配的规则
        matching_rules = self._find_matching_rules(event)

        # 按优先级排序
        matching_rules.sort(
            key=lambda r: self._priority_value(r.priority), reverse=True
        )

        for rule in matching_rules:
            # 检查规则执行频率限制
            if not self._can_execute_rule(rule):
                continue

            # 执行规则动作
            rule_executions = await self._execute_rule(rule, event)
            executions.extend(rule_executions)

        return executions

    def _find_matching_rules(self, event: SecurityEvent) -> list[ResponseRule]:
        """查找匹配的规则"""
        matching_rules = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            # 检查事件类型匹配
            if event.event_type not in rule.trigger_event_types:
                continue

            # 检查威胁等级匹配
            if event.threat_level not in rule.trigger_threat_levels:
                continue

            # 检查条件匹配
            if not self._check_conditions(rule.conditions, event):
                continue

            matching_rules.append(rule)

        return matching_rules

    def _check_conditions(
        self, conditions: dict[str, Any], event: SecurityEvent
    ) -> bool:
        """检查规则条件"""
        for key, value in conditions.items():
            if key == "repeat_offender" and value:
                # 检查是否为重复违规者
                monitor = get_security_monitor()
                if event.source_ip not in monitor.blocked_ips:
                    return False
            elif key == "score_threshold" and "anomaly_score" in event.metadata:
                if event.metadata["anomaly_score"] < value:
                    return False

        return True

    def _can_execute_rule(self, rule: ResponseRule) -> bool:
        """检查是否可以执行规则"""
        # 检查冷却期
        now = datetime.now()
        recent_executions = [
            exec_time
            for exec_time in self.rule_executions[rule.rule_id]
            if now - exec_time < timedelta(minutes=rule.cooldown_minutes)
        ]

        if len(recent_executions) > 0:
            return False

        # 检查每小时执行次数限制
        hour_ago = now - timedelta(hours=1)
        hourly_executions = [
            exec_time
            for exec_time in self.rule_executions[rule.rule_id]
            if exec_time > hour_ago
        ]

        return len(hourly_executions) < rule.max_executions_per_hour

    async def _execute_rule(
        self, rule: ResponseRule, event: SecurityEvent
    ) -> list[ResponseExecution]:
        """执行规则动作"""
        executions = []
        execution_id = (
            f"exec_{int(datetime.now().timestamp() * 1000)}_{hash(rule.rule_id) % 1000}"
        )

        start_time = datetime.now()
        affected_resources = {}

        for action in rule.actions:
            if action not in self.actions:
                logger.warning(f"未知动作: {action}")
                continue

            action_instance = self.actions[action]

            # 检查动作是否可以执行
            if not action_instance.can_execute(event, {"rule": rule}):
                continue

            try:
                # 执行动作
                result = await action_instance.execute(event, {"rule": rule})

                # 记录执行时间
                action_instance.last_execution[
                    action_instance.get_cooldown_key(event)
                ] = datetime.now()

                # 收集受影响的资源
                if result.get("ip_blocked"):
                    affected_resources.setdefault("blocked_ips", []).append(
                        result["ip_blocked"]
                    )
                if result.get("ip_limited"):
                    affected_resources.setdefault("limited_ips", []).append(
                        result["ip_limited"]
                    )

                # 记录执行结果
                execution = ResponseExecution(
                    execution_id=f"{execution_id}_{action.value}",
                    rule_id=rule.rule_id,
                    event_id=event.event_id,
                    actions=[action],
                    execution_time=start_time,
                    success=result.get("success", False),
                    error_message=result.get("error"),
                    duration_ms=int(
                        (datetime.now() - start_time).total_seconds() * 1000
                    ),
                    affected_resources=affected_resources,
                )
                executions.append(execution)

                logger.info(
                    f"执行安全动作: {action.value} - {result.get('action', 'unknown')}"
                )

            except Exception as e:
                logger.error(f"安全动作执行失败 {action.value}: {e}")

                execution = ResponseExecution(
                    execution_id=f"{execution_id}_{action.value}",
                    rule_id=rule.rule_id,
                    event_id=event.event_id,
                    actions=[action],
                    execution_time=start_time,
                    success=False,
                    error_message=str(e),
                    duration_ms=int(
                        (datetime.now() - start_time).total_seconds() * 1000
                    ),
                )
                executions.append(execution)

        # 记录规则执行时间
        self.rule_executions[rule.rule_id].append(start_time)
        self.executions.extend(executions)

        return executions

    def _priority_value(self, priority: ResponsePriority) -> int:
        """获取优先级数值"""
        priority_values = {
            ResponsePriority.LOW: 1,
            ResponsePriority.MEDIUM: 2,
            ResponsePriority.HIGH: 3,
            ResponsePriority.CRITICAL: 4,
        }
        return priority_values.get(priority, 0)

    async def _monitor_events(self, monitor):
        """监控安全事件"""
        while True:
            try:
                # 获取新的安全事件
                # 在实际实现中，这里应该使用事件队列或回调机制
                await asyncio.sleep(1)  # 简化实现

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"安全事件监控错误: {e}")
                await asyncio.sleep(1)

    def add_rule(self, rule: ResponseRule):
        """添加响应规则"""
        self.rules.append(rule)
        logger.info(f"添加安全响应规则: {rule.name}")

    def remove_rule(self, rule_id: str) -> bool:
        """移除响应规则"""
        for i, rule in enumerate(self.rules):
            if rule.rule_id == rule_id:
                del self.rules[i]
                logger.info(f"移除安全响应规则: {rule_id}")
                return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """启用规则"""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                rule.enabled = True
                logger.info(f"启用安全响应规则: {rule_id}")
                return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """禁用规则"""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                rule.enabled = False
                logger.info(f"禁用安全响应规则: {rule_id}")
                return True
        return False

    def get_automation_status(self) -> dict[str, Any]:
        """获取自动化状态"""
        now = datetime.now()
        recent_executions = [
            exec
            for exec in self.executions
            if exec.execution_time > now - timedelta(hours=24)
        ]

        return {
            "total_rules": len(self.rules),
            "enabled_rules": len([r for r in self.rules if r.enabled]),
            "registered_actions": list(self.actions.keys()),
            "executions_24h": len(recent_executions),
            "successful_executions_24h": len(
                [e for e in recent_executions if e.success]
            ),
            "failed_executions_24h": len(
                [e for e in recent_executions if not e.success]
            ),
            "rules": [
                {
                    "rule_id": rule.rule_id,
                    "name": rule.name,
                    "enabled": rule.enabled,
                    "priority": rule.priority.value,
                    "trigger_types": [t.value for t in rule.trigger_event_types],
                    "actions": [a.value for a in rule.actions],
                }
                for rule in self.rules
            ],
            "recent_executions": [
                {
                    "execution_id": exec.execution_id,
                    "rule_id": exec.rule_id,
                    "actions": [a.value for a in exec.actions],
                    "execution_time": exec.execution_time.isoformat(),
                    "success": exec.success,
                    "duration_ms": exec.duration_ms,
                }
                for exec in sorted(
                    recent_executions, key=lambda x: x.execution_time, reverse=True
                )[:20]
            ],
        }


# 全局自动化引擎实例
_global_automation_engine: SecurityAutomationEngine | None = None


def get_automation_engine() -> SecurityAutomationEngine:
    """获取全局自动化引擎实例"""
    global _global_automation_engine
    if _global_automation_engine is None:
        _global_automation_engine = SecurityAutomationEngine()
    return _global_automation_engine


async def initialize_security_automation():
    """初始化安全自动化系统"""
    engine = get_automation_engine()
    await engine.start_automation()
    return engine


if __name__ == "__main__":

    async def demo_security_automation():
        """演示安全自动化功能"""
        print("🤖 演示安全自动化响应系统")

        # 初始化自动化引擎
        engine = await initialize_security_automation()

        # 获取自动化状态
        status = engine.get_automation_status()
        print(
            f"📊 自动化状态: {status['enabled_rules']}/{status['total_rules']} 规则已启用"
        )

        # 停止自动化引擎
        await engine.stop_automation()
        print("✅ 安全自动化演示完成")

    asyncio.run(demo_security_automation())
