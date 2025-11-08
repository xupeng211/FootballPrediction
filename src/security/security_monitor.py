#!/usr/bin/env python3
"""
实时安全监控系统
提供安全事件监控、威胁检测、自动化响应等功能
"""

import asyncio
import ipaddress
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

try:
    import geoip2.database

    GEOIP_AVAILABLE = True
except ImportError:
    GEOIP_AVAILABLE = False

from src.core.logger import get_logger

logger = get_logger(__name__)


class SecurityEventType(Enum):
    """安全事件类型"""

    AUTHENTICATION_FAILURE = "auth_failure"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    SUSPICIOUS_REQUEST = "suspicious_request"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INJECTION_ATTEMPT = "injection_attempt"
    XSS_ATTEMPT = "xss_attempt"
    CSRF_ATTEMPT = "csrf_attempt"
    BRUTE_FORCE = "brute_force"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    DATA_EXFILTRATION = "data_exfiltration"
    MALICIOUS_IP = "malicious_ip"
    UNUSUAL_TRAFFIC = "unusual_traffic"


class ThreatLevel(Enum):
    """威胁等级"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """安全事件"""

    event_id: str
    event_type: SecurityEventType
    threat_level: ThreatLevel
    timestamp: datetime
    source_ip: str
    user_agent: str
    request_path: str
    request_method: str
    user_id: str | None
    session_id: str | None
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)
    geo_location: dict[str, str] = field(default_factory=dict)
    is_resolved: bool = False
    response_action: str | None = None


@dataclass
class SecurityMetrics:
    """安全指标"""

    total_events: int = 0
    events_by_type: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    events_by_level: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    events_by_hour: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    top_source_ips: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    blocked_ips: set[str] = field(default_factory=set)
    auto_responses: int = 0
    manual_interventions: int = 0


class ThreatDetector:
    """威胁检测器"""

    def __init__(self):
        self.suspicious_patterns = {
            "sql_injection": [
                r"(?i)(union\s+select|drop\s+table|delete\s+from|insert\s+into)",
                r"(?i)(exec\s*\(|xp_cmdshell|sp_oacreate)",
                r"(?i)(or\s+1\s*=\s*1|and\s+1\s*=\s*1)",
                r"(?i)(--|#|/\*|\*/)",
            ],
            "xss": [
                r"(?i)(<script|</script|javascript:|vbscript:)",
                r"(?i)(onload\s*=|onerror\s*=|onclick\s*=)",
                r"(?i)(<iframe|<object|<embed)",
                r"(?i)(alert\(|confirm\(|prompt\()",
            ],
            "path_traversal": [
                r"(?i)(\.\./|\.\.\\|%2e%2e%2f|%2e%2e%5c)",
                r"(?i)(/etc/passwd|/proc/version|/windows/system32)",
                r"(?i)(file://|ftp://|http://)",
            ],
            "command_injection": [
                r"(?i)(;|\||&|`|\$\(|\$\{)",
                r"(?i)(nc\s|netcat|wget\s|curl\s)",
                r"(?i)(rm\s-rf|dd\s|/dev/zero)",
            ],
        }

        self.malicious_user_agents = [
            r"(?i)(sqlmap|nmap|nikto|burp|owasp)",
            r"(?i)(scanner|crawler|bot|spider)",
            r"(?i)(hack|exploit|payload|malware)",
        ]

        self.rate_limit_thresholds = {
            "requests_per_minute": 100,
            "failed_auth_per_minute": 10,
            "suspicious_requests_per_minute": 5,
        }

    def detect_injection_attempts(self, data: str) -> list[str]:
        """检测注入攻击尝试"""
        detected_attacks = []

        for attack_type, patterns in self.suspicious_patterns.items():
            for pattern in patterns:
                if re.search(pattern, data):
                    detected_attacks.append(attack_type)
                    break

        return detected_attacks

    def detect_malicious_user_agent(self, user_agent: str) -> bool:
        """检测恶意用户代理"""
        for pattern in self.malicious_user_agents:
            if re.search(pattern, user_agent):
                return True
        return False

    def detect_brute_force(self, ip_events: list[SecurityEvent]) -> bool:
        """检测暴力破解攻击"""
        recent_auth_failures = [
            event
            for event in ip_events
            if event.event_type == SecurityEventType.AUTHENTICATION_FAILURE
            and event.timestamp > datetime.now() - timedelta(minutes=10)
        ]

        return len(recent_auth_failures) >= 5

    def detect_anomalous_behavior(
        self, user_events: list[SecurityEvent]
    ) -> dict[str, Any]:
        """检测异常行为"""
        if len(user_events) < 5:
            return {"is_anomalous": False}

        # 检测时间模式异常
        hours = [event.timestamp.hour for event in user_events]
        unique_hours = len(set(hours))

        # 检测地理位置异常
        countries = set(event.geo_location.get("country", "") for event in user_events)

        # 检测请求模式异常
        endpoints = set(event.request_path for event in user_events)

        anomaly_score = 0
        reasons = []

        if unique_hours > 16:  # 16小时以上活动
            anomaly_score += 30
            reasons.append("unusual_time_pattern")

        if len(countries) > 3:  # 多个国家
            anomaly_score += 25
            reasons.append("multiple_countries")

        if len(endpoints) > 50:  # 大量不同端点
            anomaly_score += 20
            reasons.append("excessive_endpoints")

        return {
            "is_anomalous": anomaly_score >= 40,
            "score": anomaly_score,
            "reasons": reasons,
        }

    def classify_threat_level(
        self, event_type: SecurityEventType, context: dict[str, Any]
    ) -> ThreatLevel:
        """分类威胁等级"""
        base_levels = {
            SecurityEventType.AUTHENTICATION_FAILURE: ThreatLevel.LOW,
            SecurityEventType.UNAUTHORIZED_ACCESS: ThreatLevel.MEDIUM,
            SecurityEventType.SUSPICIOUS_REQUEST: ThreatLevel.MEDIUM,
            SecurityEventType.RATE_LIMIT_EXCEEDED: ThreatLevel.MEDIUM,
            SecurityEventType.INJECTION_ATTEMPT: ThreatLevel.HIGH,
            SecurityEventType.XSS_ATTEMPT: ThreatLevel.HIGH,
            SecurityEventType.CSRF_ATTEMPT: ThreatLevel.HIGH,
            SecurityEventType.BRUTE_FORCE: ThreatLevel.HIGH,
            SecurityEventType.ANOMALOUS_BEHAVIOR: ThreatLevel.MEDIUM,
            SecurityEventType.DATA_EXFILTRATION: ThreatLevel.CRITICAL,
            SecurityEventType.MALICIOUS_IP: ThreatLevel.HIGH,
            SecurityEventType.UNUSUAL_TRAFFIC: ThreatLevel.MEDIUM,
        }

        base_level = base_levels.get(event_type, ThreatLevel.LOW)

        # 根据上下文调整威胁等级
        if context.get("repeat_offender", False):
            base_level = (
                ThreatLevel.HIGH
                if base_level != ThreatLevel.CRITICAL
                else ThreatLevel.CRITICAL
            )

        if context.get("admin_target", False):
            base_level = (
                ThreatLevel.HIGH
                if base_level != ThreatLevel.CRITICAL
                else ThreatLevel.CRITICAL
            )

        if context.get("data_access", False):
            base_level = (
                ThreatLevel.MEDIUM if base_level == ThreatLevel.LOW else base_level
            )

        return base_level


class SecurityMonitor:
    """安全监控器"""

    def __init__(self, geoip_db_path: str | None = None):
        self.events: deque[SecurityEvent] = deque(maxlen=10000)
        self.ip_events: dict[str, list[SecurityEvent]] = defaultdict(list)
        self.user_events: dict[str, list[SecurityEvent]] = defaultdict(list)
        self.metrics = SecurityMetrics()
        self.threat_detector = ThreatDetector()
        self.blocked_ips: dict[str, datetime] = {}
        self.geoip_reader = None

        # 初始化GeoIP数据库
        try:
            if geoip_db_path:
                self.geoip_reader = geoip2.database.Reader(geoip_db_path)
        except Exception as e:
            logger.warning(f"GeoIP数据库初始化失败: {e}")

        # 启动监控任务
        self._monitor_task = None
        self._cleanup_task = None

    async def start_monitoring(self):
        """启动安全监控"""
        logger.info("启动安全监控系统...")

        self._monitor_task = asyncio.create_task(self._monitor_security_events())
        self._cleanup_task = asyncio.create_task(self._cleanup_old_events())

        logger.info("✅ 安全监控系统已启动")

    async def stop_monitoring(self):
        """停止安全监控"""
        logger.info("停止安全监控系统...")

        if self._monitor_task:
            self._monitor_task.cancel()

        if self._cleanup_task:
            self._cleanup_task.cancel()

        logger.info("✅ 安全监控系统已停止")

    async def log_security_event(
        self,
        event_type: SecurityEventType,
        source_ip: str,
        request_path: str,
        request_method: str,
        user_agent: str,
        user_id: str | None = None,
        session_id: str | None = None,
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> SecurityEvent:
        """记录安全事件"""

        # 生成事件ID
        event_id = f"sec_{int(time.time() * 1000)}_{hash(source_ip) % 10000}"

        # 获取地理位置信息
        geo_location = await self._get_geo_location(source_ip)

        # 检测威胁等级
        context = {
            "repeat_offender": source_ip in self.blocked_ips,
            "admin_target": "/admin" in request_path or "/api/v1/admin" in request_path,
            "data_access": "api/v1/" in request_path
            and request_method in ["POST", "PUT", "DELETE"],
        }
        threat_level = self.threat_detector.classify_threat_level(event_type, context)

        # 创建安全事件
        event = SecurityEvent(
            event_id=event_id,
            event_type=event_type,
            threat_level=threat_level,
            timestamp=datetime.now(),
            source_ip=source_ip,
            user_agent=user_agent,
            request_path=request_path,
            request_method=request_method,
            user_id=user_id,
            session_id=session_id,
            description=description,
            metadata=metadata or {},
            geo_location=geo_location,
        )

        # 存储事件
        self.events.append(event)
        self.ip_events[source_ip].append(event)
        if user_id:
            self.user_events[user_id].append(event)

        # 更新指标
        self._update_metrics(event)

        # 自动响应
        await self._auto_respond(event)

        logger.warning(
            f"安全事件记录: {event_type.value} from {source_ip} - {threat_level.value}"
        )

        return event

    async def analyze_request_security(
        self,
        source_ip: str,
        request_path: str,
        request_method: str,
        user_agent: str,
        request_data: str | None = None,
        headers: dict[str, str] | None = None,
        user_id: str | None = None,
    ) -> list[SecurityEvent]:
        """分析请求安全性"""
        events = []

        # 检测注入攻击
        if request_data:
            injection_attacks = self.threat_detector.detect_injection_attempts(
                request_data
            )
            for attack_type in injection_attacks:
                event = await self.log_security_event(
                    SecurityEventType.INJECTION_ATTEMPT,
                    source_ip,
                    request_path,
                    request_method,
                    user_agent,
                    user_id,
                    description=f"检测到{attack_type}攻击尝试",
                    metadata={
                        "attack_type": attack_type,
                        "payload": request_data[:200],
                    },
                )
                events.append(event)

        # 检测恶意用户代理
        if self.threat_detector.detect_malicious_user_agent(user_agent):
            event = await self.log_security_event(
                SecurityEventType.SUSPICIOUS_REQUEST,
                source_ip,
                request_path,
                request_method,
                user_agent,
                user_id,
                description="检测到恶意用户代理",
                metadata={"user_agent": user_agent},
            )
            events.append(event)

        # 检测路径遍历
        if request_path:
            path_attacks = self.threat_detector.detect_injection_attempts(request_path)
            if path_attacks:
                event = await self.log_security_event(
                    SecurityEventType.SUSPICIOUS_REQUEST,
                    source_ip,
                    request_path,
                    request_method,
                    user_agent,
                    user_id,
                    description="检测到路径遍历攻击尝试",
                    metadata={"path": request_path},
                )
                events.append(event)

        # 检测暴力破解
        ip_recent_events = self.ip_events[source_ip][-10:]  # 最近10个事件
        if self.threat_detector.detect_brute_force(ip_recent_events):
            event = await self.log_security_event(
                SecurityEventType.BRUTE_FORCE,
                source_ip,
                request_path,
                request_method,
                user_agent,
                user_id,
                description="检测到暴力破解攻击",
                metadata={
                    "recent_failures": len(
                        [
                            e
                            for e in ip_recent_events
                            if e.event_type == SecurityEventType.AUTHENTICATION_FAILURE
                        ]
                    )
                },
            )
            events.append(event)

        # 检测异常行为
        if user_id:
            user_recent_events = self.user_events[user_id][-20:]  # 最近20个事件
            anomaly_result = self.threat_detector.detect_anomalous_behavior(
                user_recent_events
            )
            if anomaly_result["is_anomalous"]:
                event = await self.log_security_event(
                    SecurityEventType.ANOMALOUS_BEHAVIOR,
                    source_ip,
                    request_path,
                    request_method,
                    user_agent,
                    user_id,
                    description=f"检测到异常行为: {', '.join(anomaly_result['reasons'])}",
                    metadata=anomaly_result,
                )
                events.append(event)

        return events

    async def block_ip(
        self, ip_address: str, duration_hours: int = 24, reason: str = ""
    ) -> bool:
        """阻止IP地址"""
        try:
            # 验证IP地址
            ip = ipaddress.ip_address(ip_address)

            # 检查是否为私有IP
            if ip.is_private:
                logger.warning(f"不阻止私有IP地址: {ip_address}")
                return False

            # 添加到阻止列表
            unblock_time = datetime.now() + timedelta(hours=duration_hours)
            self.blocked_ips[ip_address] = unblock_time
            self.metrics.blocked_ips.add(ip_address)

            # 记录阻止事件
            await self.log_security_event(
                SecurityEventType.MALICIOUS_IP,
                ip_address,
                "/blocked",
                "BLOCK",
                "SecurityMonitor",
                description=f"IP地址已被阻止: {reason}",
                metadata={
                    "duration_hours": duration_hours,
                    "unblock_time": unblock_time.isoformat(),
                },
            )

            logger.warning(
                f"IP地址已阻止: {ip_address} ({duration_hours}小时) - {reason}"
            )
            return True

        except ValueError as e:
            logger.error(f"无效的IP地址: {ip_address} - {e}")
            return False

    async def unblock_ip(self, ip_address: str) -> bool:
        """解除IP阻止"""
        if ip_address in self.blocked_ips:
            del self.blocked_ips[ip_address]
            self.metrics.blocked_ips.discard(ip_address)

            logger.info(f"IP地址已解除阻止: {ip_address}")
            return True

        return False

    def is_ip_blocked(self, ip_address: str) -> bool:
        """检查IP是否被阻止"""
        if ip_address in self.blocked_ips:
            # 检查阻止是否已过期
            if datetime.now() > self.blocked_ips[ip_address]:
                del self.blocked_ips[ip_address]
                self.metrics.blocked_ips.discard(ip_address)
                return False
            return True

        return False

    def get_security_dashboard(self) -> dict[str, Any]:
        """获取安全仪表板数据"""
        now = datetime.now()

        # 计算最近24小时的事件
        recent_events = [
            event
            for event in self.events
            if event.timestamp > now - timedelta(hours=24)
        ]

        # 威胁等级分布
        threat_distribution = defaultdict(int)
        for event in recent_events:
            threat_distribution[event.threat_level.value] += 1

        # 事件类型分布
        type_distribution = defaultdict(int)
        for event in recent_events:
            type_distribution[event.event_type.value] += 1

        # 地理位置分布
        geo_distribution = defaultdict(int)
        for event in recent_events:
            country = event.geo_location.get("country", "Unknown")
            geo_distribution[country] += 1

        # 时间序列数据（过去24小时）
        hourly_data = defaultdict(int)
        for event in recent_events:
            hour = event.timestamp.hour
            hourly_data[hour] += 1

        return {
            "summary": {
                "total_events_24h": len(recent_events),
                "blocked_ips": len(self.blocked_ips),
                "auto_responses": self.metrics.auto_responses,
                "critical_threats": threat_distribution["critical"],
                "high_threats": threat_distribution["high"],
            },
            "threat_distribution": dict(threat_distribution),
            "type_distribution": dict(type_distribution),
            "geo_distribution": dict(geo_distribution),
            "hourly_data": dict(hourly_data),
            "top_attacker_ips": dict(
                sorted(
                    self.metrics.top_source_ips.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:10]
            ),
            "recent_events": [
                {
                    "event_id": event.event_id,
                    "type": event.event_type.value,
                    "level": event.threat_level.value,
                    "timestamp": event.timestamp.isoformat(),
                    "source_ip": event.source_ip,
                    "description": event.description,
                    "resolved": event.is_resolved,
                }
                for event in sorted(
                    recent_events, key=lambda x: x.timestamp, reverse=True
                )[:20]
            ],
            "blocked_ips_list": [
                {
                    "ip": ip,
                    "unblock_time": unblock_time.isoformat(),
                    "remaining_hours": max(
                        0, (unblock_time - now).total_seconds() / 3600
                    ),
                }
                for ip, unblock_time in self.blocked_ips.items()
            ],
        }

    async def _auto_respond(self, event: SecurityEvent):
        """自动响应安全事件"""
        if event.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            # 自动阻止高风险IP
            if event.source_ip not in self.blocked_ips:
                await self.block_ip(
                    event.source_ip,
                    duration_hours=24,
                    reason=f"自动响应: {event.event_type.value}",
                )
                event.response_action = "IP_BLOCKED"
                self.metrics.auto_responses += 1

    async def _get_geo_location(self, ip_address: str) -> dict[str, str]:
        """获取IP地理位置"""
        if not self.geoip_reader:
            return {}

        try:
            response = self.geoip_reader.city(ip_address)
            return {
                "country": response.country.name or "Unknown",
                "city": response.city.name or "Unknown",
                "latitude": str(response.location.latitude),
                "longitude": str(response.location.longitude),
            }
        except Exception as e:
            logger.debug(f"GeoIP查询失败 {ip_address}: {e}")
            return {}

    def _update_metrics(self, event: SecurityEvent):
        """更新安全指标"""
        self.metrics.total_events += 1
        self.metrics.events_by_type[event.event_type.value] += 1
        self.metrics.events_by_level[event.threat_level.value] += 1
        self.metrics.events_by_hour[str(event.timestamp.hour)] += 1
        self.metrics.top_source_ips[event.source_ip] += 1

    async def _monitor_security_events(self):
        """监控安全事件"""
        while True:
            try:
                # 定期检查和处理安全事件
                await asyncio.sleep(60)  # 每分钟检查一次

                # 清理过期的IP阻止
                current_time = datetime.now()
                expired_ips = [
                    ip
                    for ip, unblock_time in self.blocked_ips.items()
                    if current_time > unblock_time
                ]

                for ip in expired_ips:
                    await self.unblock_ip(ip)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"安全监控任务错误: {e}")
                await asyncio.sleep(60)

    async def _cleanup_old_events(self):
        """清理旧事件"""
        while True:
            try:
                # 每小时清理一次超过7天的事件
                await asyncio.sleep(3600)

                cutoff_time = datetime.now() - timedelta(days=7)

                # 清理内存中的事件
                initial_count = len(self.events)
                self.events = deque(
                    [event for event in self.events if event.timestamp > cutoff_time],
                    maxlen=10000,
                )

                # 清理IP事件映射
                for ip in list(self.ip_events.keys()):
                    self.ip_events[ip] = [
                        event
                        for event in self.ip_events[ip]
                        if event.timestamp > cutoff_time
                    ]
                    if not self.ip_events[ip]:
                        del self.ip_events[ip]

                # 清理用户事件映射
                for user_id in list(self.user_events.keys()):
                    self.user_events[user_id] = [
                        event
                        for event in self.user_events[user_id]
                        if event.timestamp > cutoff_time
                    ]
                    if not self.user_events[user_id]:
                        del self.user_events[user_id]

                cleaned_count = initial_count - len(self.events)
                if cleaned_count > 0:
                    logger.info(f"清理了 {cleaned_count} 个过期安全事件")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"事件清理任务错误: {e}")
                await asyncio.sleep(3600)


# 全局安全监控实例
_global_security_monitor: SecurityMonitor | None = None


def get_security_monitor() -> SecurityMonitor:
    """获取全局安全监控实例"""
    global _global_security_monitor
    if _global_security_monitor is None:
        _global_security_monitor = SecurityMonitor()
    return _global_security_monitor


async def initialize_security_monitoring(geoip_db_path: str | None = None):
    """初始化安全监控系统"""
    monitor = get_security_monitor()
    await monitor.start_monitoring()
    return monitor


if __name__ == "__main__":

    async def demo_security_monitoring():
        """演示安全监控功能"""
        print("🔒 演示实时安全监控系统")

        # 初始化监控系统
        monitor = await initialize_security_monitoring()

        # 模拟一些安全事件
        await monitor.log_security_event(
            SecurityEventType.AUTHENTICATION_FAILURE,
            "192.168.1.100",
            "/api/v1/auth/login",
            "POST",
            "Mozilla/5.0",
            user_id="test_user",
            description="登录失败",
        )

        await monitor.log_security_event(
            SecurityEventType.SUSPICIOUS_REQUEST,
            "10.0.0.50",
            "/api/v1/users/../etc/passwd",
            "GET",
            "sqlmap/1.0",
            description="路径遍历尝试",
        )

        # 获取安全仪表板
        dashboard = monitor.get_security_dashboard()
        print(f"📊 安全仪表板: {dashboard['summary']}")

        # 停止监控
        await monitor.stop_monitoring()
        print("✅ 安全监控演示完成")

    asyncio.run(demo_security_monitoring())
