#!/usr/bin/env python3
"""
告警中心模块 (Alert Manager)
============================
功能:
1. 多渠道告警支持 (Email, Logger, Webhook)
2. 防止告警风暴 (同一类型 1 小时内只发送一次)
3. 集成到备份脚本、熔断器等关键模块

Author: Senior Full-Stack Architect & SRE
Version: 1.0.0
Date: 2025-12-30

使用示例:
>>> from src.ops.alert_manager import AlertManager, AlertSeverity
>>> manager = AlertManager()
>>> await manager.send_alert(
...     title="数据库备份失败",
...     message="无法连接到数据库服务器",
...     severity=AlertSeverity.CRITICAL
... )
"""

import asyncio
import json
import logging
import smtplib
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import formataddr
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


# ============================================
# 告警级别枚举
# ============================================


class AlertSeverity(Enum):
    """告警级别"""

    DEBUG = "debug"  # 调试信息
    INFO = "info"  # 一般信息
    WARNING = "warning"  # 警告
    ERROR = "error"  # 错误
    CRITICAL = "critical"  # 严重错误


# ============================================
# 告警数据模型
# ============================================


@dataclass
class Alert:
    """告警数据结构"""

    title: str  # 告警标题
    message: str  # 告警详情
    severity: AlertSeverity = AlertSeverity.INFO
    alert_type: str = "general"  # 告警类型 (用于去重)
    metadata: dict[str, Any] = field(default_factory=dict)  # 附加信息
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "message": self.message,
            "severity": self.severity.value,
            "alert_type": self.alert_type,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


# ============================================
# 告警通道抽象基类
# ============================================


class AlertChannel(ABC):
    """告警通道抽象基类"""

    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """
        发送告警

        Args:
            alert: 告警对象

        Returns:
            是否发送成功
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """获取通道名称"""
        pass


# ============================================
# Email 告警通道
# ============================================


class EmailAlertChannel(AlertChannel):
    """Email 告警通道 (SMTP)"""

    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        smtp_username: str | None = None,
        smtp_password: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
        to_emails: list[str] | None = None,
    ):
        """
        初始化 Email 告警通道

        Args:
            smtp_host: SMTP 服务器地址
            smtp_port: SMTP 端口
            smtp_username: SMTP 用户名
            smtp_password: SMTP 密码
            from_email: 发件人邮箱
            from_name: 发件人名称
            to_emails: 收件人邮箱列表
        """
        settings = get_settings()

        self.smtp_host = smtp_host or getattr(settings, "alert_smtp_host", None)
        self.smtp_port = smtp_port or getattr(settings, "alert_smtp_port", 587)
        self.smtp_username = smtp_username or getattr(settings, "alert_smtp_username", None)
        self.smtp_password = smtp_password or getattr(settings, "alert_smtp_password", None)
        self.from_email = from_email or getattr(settings, "alert_from_email", "alerts@footballprediction.local")
        self.from_name = from_name or getattr(settings, "alert_from_name", "FootballPrediction Alert")
        self.to_emails = to_emails or getattr(settings, "alert_to_emails", [])

        # 验证配置
        if not self.to_emails:
            logger.warning("Email 告警通道未配置收件人，将不会发送邮件")
        if not self.smtp_host:
            logger.warning("Email 告警通道未配置 SMTP 服务器")

    def get_name(self) -> str:
        return "Email"

    async def send(self, alert: Alert) -> bool:
        """发送 Email 告警"""
        if not self.smtp_host or not self.to_emails:
            logger.debug("Email 告警通道配置不完整，跳过发送")
            return False

        try:
            # 创建邮件
            msg = EmailMessage()
            msg["Subject"] = f"[{alert.severity.value.upper()}] {alert.title}"
            msg["From"] = formataddr((self.from_name, self.from_email))
            msg["To"] = ", ".join(self.to_emails)
            msg["Date"] = email.utils.format_datetime(datetime.now())

            # 构建邮件正文
            body = self._build_email_body(alert)
            msg.set_content(body, subtype="html")

            # 发送邮件 (在线程池中执行，避免阻塞)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_smtp, msg)

            logger.info(f"✓ Email 告警已发送: {alert.title}")
            return True

        except Exception as e:
            logger.error(f"Email 告警发送失败: {e}")
            return False

    def _send_smtp(self, msg: EmailMessage) -> None:
        """在单独线程中发送 SMTP"""
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
            server.starttls()
            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)

    def _build_email_body(self, alert: Alert) -> str:
        """构建 HTML 邮件正文"""
        severity_colors = {
            AlertSeverity.DEBUG: "#6c757d",
            AlertSeverity.INFO: "#17a2b8",
            AlertSeverity.WARNING: "#ffc107",
            AlertSeverity.ERROR: "#dc3545",
            AlertSeverity.CRITICAL: "#343a40",
        }

        color = severity_colors.get(alert.severity, "#6c757d")

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: {color}; color: white; padding: 15px; border-radius: 5px 5px 0 0; }}
        .content {{ background-color: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; }}
        .footer {{ margin-top: 20px; font-size: 12px; color: #6c757d; }}
        .metadata {{ background-color: #e9ecef; padding: 10px; border-radius: 5px; margin-top: 15px; }}
        .metadata table {{ width: 100%; border-collapse: collapse; }}
        .metadata td {{ padding: 5px; border-bottom: 1px solid #dee2e6; }}
        .metadata td:last-child {{ border-bottom: none; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 style="margin: 0;">⚠️ {alert.title}</h2>
            <p style="margin: 5px 0 0 0;">级别: {alert.severity.value.upper()}</p>
        </div>
        <div class="content">
            <p>{alert.message}</p>
        """

        if alert.metadata:
            html += """
            <div class="metadata">
                <strong>附加信息:</strong>
                <table>
            """
            for key, value in alert.metadata.items():
                html += f"<tr><td><strong>{key}:</strong></td><td>{value}</td></tr>"
            html += """
                </table>
            </div>
            """

        html += f"""
        </div>
        <div class="footer">
            <p>时间: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>FootballPrediction 自动告警系统</p>
        </div>
    </div>
</body>
</html>
"""
        return html


# ============================================
# Logger 告警通道
# ============================================


class LoggerAlertChannel(AlertChannel):
    """Logger 告警通道 (文件日志)"""

    def __init__(
        self,
        log_file: Path | str | None = None,
        log_level: int = logging.WARNING,
    ):
        """
        初始化 Logger 告警通道

        Args:
            log_file: 日志文件路径
            log_level: 日志级别
        """
        settings = get_settings()
        project_root = Path(__file__).parent.parent.parent

        self.log_file = Path(log_file or project_root / "logs" / "alerts.log")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # 配置独立的 logger
        self.logger = logging.getLogger("alerts")
        self.logger.setLevel(logging.DEBUG)

        # 文件 handler
        file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        self.logger.addHandler(file_handler)

        # 控制台 handler (仅 ERROR 及以上)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        self.logger.addHandler(console_handler)

    def get_name(self) -> str:
        return "Logger"

    async def send(self, alert: Alert) -> bool:
        """记录告警到日志"""
        try:
            level_map = {
                AlertSeverity.DEBUG: logging.DEBUG,
                AlertSeverity.INFO: logging.INFO,
                AlertSeverity.WARNING: logging.WARNING,
                AlertSeverity.ERROR: logging.ERROR,
                AlertSeverity.CRITICAL: logging.CRITICAL,
            }

            level = level_map.get(alert.severity, logging.INFO)
            metadata_str = json.dumps(alert.metadata, ensure_ascii=False) if alert.metadata else "{}"

            self.logger.log(
                level,
                f"[{alert.alert_type}] {alert.title} - {alert.message} | Metadata: {metadata_str}",
            )

            return True

        except Exception as e:
            logger.error(f"Logger 告警记录失败: {e}")
            return False


# ============================================
# 告警管理器
# ============================================


class AlertManager:
    """
    告警管理器

    功能:
    - 多通道告警分发
    - 防止告警风暴 (1小时内同类告警只发送一次)
    - 线程安全
    """

    # 单例实例
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        channels: list[AlertChannel] | None = None,
        rate_limit_seconds: int = 3600,  # 1小时
    ):
        """
        初始化告警管理器

        Args:
            channels: 告警通道列表
            rate_limit_seconds: 同类告警的最小间隔时间（秒）
        """
        # 防止重复初始化
        if hasattr(self, "_initialized"):
            return

        self.channels = channels or []
        self.rate_limit_seconds = rate_limit_seconds

        # 告警历史 {alert_type: last_sent_timestamp}
        self._alert_history: dict[str, float] = {}
        self._history_lock = threading.Lock()

        # 如果没有提供通道，使用默认通道
        if not self.channels:
            self._init_default_channels()

        self._initialized = True
        logger.info(f"告警管理器已初始化: {len(self.channels)} 个通道")

    def _init_default_channels(self) -> None:
        """初始化默认通道"""
        # Logger 通道 (始终启用)
        self.channels.append(LoggerAlertChannel())

        # Email 通道 (如果配置了)
        try:
            settings = get_settings()
            if hasattr(settings, "alert_smtp_host") and settings.alert_smtp_host:
                self.channels.append(EmailAlertChannel())
        except Exception as e:
            logger.debug(f"Email 告警通道初始化失败: {e}")

    def _should_send_alert(self, alert: Alert) -> bool:
        """
        检查是否应该发送告警（防止告警风暴）

        Args:
            alert: 告警对象

        Returns:
            是否应该发送
        """
        with self._history_lock:
            now = time.time()
            last_sent = self._alert_history.get(alert.alert_type, 0)

            # CRITICAL 级别不受限
            if alert.severity == AlertSeverity.CRITICAL:
                self._alert_history[alert.alert_type] = now
                return True

            # 检查是否在限流期内
            if now - last_sent < self.rate_limit_seconds:
                remaining = int(self.rate_limit_seconds - (now - last_sent))
                logger.debug(f"告警 [{alert.alert_type}] 在限流期内，剩余 {remaining} 秒")
                return False

            # 更新最后发送时间
            self._alert_history[alert.alert_type] = now
            return True

    async def send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        alert_type: str = "general",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, bool]:
        """
        发送告警

        Args:
            title: 告警标题
            message: 告警详情
            severity: 告警级别
            alert_type: 告警类型 (用于去重)
            metadata: 附加信息

        Returns:
            各通道发送结果 {channel_name: success}
        """
        alert = Alert(
            title=title,
            message=message,
            severity=severity,
            alert_type=alert_type,
            metadata=metadata or {},
        )

        # 检查是否应该发送
        if not self._should_send_alert(alert):
            logger.info(f"告警 [{alert_type}] 已被限流器拦截")
            return {}

        # 分发到所有通道
        results = {}
        for channel in self.channels:
            try:
                success = await channel.send(alert)
                results[channel.get_name()] = success
            except Exception as e:
                logger.error(f"告警通道 [{channel.get_name()}] 发送失败: {e}")
                results[channel.get_name()] = False

        return results

    def send_alert_sync(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        alert_type: str = "general",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, bool]:
        """
        同步发送告警 (用于非异步环境)

        Args:
            同 send_alert

        Returns:
            各通道发送结果
        """
        return asyncio.run(self.send_alert(title, message, severity, alert_type, metadata))

    def clear_history(self, alert_type: str | None = None) -> None:
        """
        清除告警历史

        Args:
            alert_type: 告警类型，None 表示清除所有
        """
        with self._history_lock:
            if alert_type:
                self._alert_history.pop(alert_type, None)
            else:
                self._alert_history.clear()
        logger.info(f"告警历史已清除: {alert_type or '全部'}")

    def get_history(self) -> dict[str, float]:
        """获取告警历史"""
        with self._history_lock:
            return self._alert_history.copy()

    def get_status(self) -> dict[str, Any]:
        """获取告警管理器状态"""
        return {
            "channels": [channel.get_name() for channel in self.channels],
            "rate_limit_seconds": self.rate_limit_seconds,
            "alert_history_size": len(self._alert_history),
            "alert_history": {
                alert_type: datetime.fromtimestamp(timestamp).isoformat()
                for alert_type, timestamp in self._alert_history.items()
            },
        }


# ============================================
# 全局实例
# ============================================


_alert_manager: AlertManager | None = None


def get_alert_manager() -> AlertManager:
    """获取全局告警管理器实例"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


# ============================================
# 便捷函数
# ============================================


async def send_alert(
    title: str,
    message: str,
    severity: AlertSeverity = AlertSeverity.INFO,
    alert_type: str = "general",
    metadata: dict[str, Any] | None = None,
) -> dict[str, bool]:
    """发送告警（便捷函数）"""
    manager = get_alert_manager()
    return await manager.send_alert(title, message, severity, alert_type, metadata)


def send_alert_sync(
    title: str,
    message: str,
    severity: AlertSeverity = AlertSeverity.INFO,
    alert_type: str = "general",
    metadata: dict[str, Any] | None = None,
) -> dict[str, bool]:
    """发送告警（同步便捷函数）"""
    manager = get_alert_manager()
    return manager.send_alert_sync(title, message, severity, alert_type, metadata)


# ============================================
# 测试代码
# ============================================


if __name__ == "__main__":
    import sys

    async def main():
        """测试告警管理器"""
        logging.basicConfig(level=logging.DEBUG)

        manager = AlertManager()

        # 测试各级别告警
        print("\n=== 测试告警管理器 ===\n")

        print("1. 发送 INFO 告警...")
        await manager.send_alert(
            title="测试信息告警",
            message="这是一条测试信息",
            severity=AlertSeverity.INFO,
            alert_type="test_info",
        )

        print("\n2. 发送 WARNING 告警...")
        await manager.send_alert(
            title="测试警告",
            message="这是一条测试警告",
            severity=AlertSeverity.WARNING,
            alert_type="test_warning",
        )

        print("\n3. 发送 ERROR 告警...")
        await manager.send_alert(
            title="测试错误",
            message="这是一条测试错误",
            severity=AlertSeverity.ERROR,
            alert_type="test_error",
            metadata={"service": "test", "host": "localhost"},
        )

        print("\n4. 发送 CRITICAL 告警...")
        await manager.send_alert(
            title="测试严重错误",
            message="这是一条测试严重错误",
            severity=AlertSeverity.CRITICAL,
            alert_type="test_critical",
            metadata={"traceback": "AssertionError: Test failed"},
        )

        print("\n5. 测试限流器 (再次发送 INFO 告警)...")
        await manager.send_alert(
            title="测试信息告警",
            message="这应该被限流器拦截",
            severity=AlertSeverity.INFO,
            alert_type="test_info",
        )

        print("\n6. 获取告警管理器状态...")
        status = manager.get_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))

    asyncio.run(main())
