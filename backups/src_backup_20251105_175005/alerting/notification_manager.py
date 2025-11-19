#!/usr/bin/env python3
"""多渠道通知管理器
Multi-channel Notification Manager.

支持邮件、Slack,企业微信,钉钉等多种通知渠道
"""

import json
import smtplib
from dataclasses import dataclass
from datetime import datetime
from email.mime.html import MIMEText as MIMEHtml
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import aiohttp
import jinja2

from src.alerting.alert_engine import Alert, AlertSeverity
from src.core.config import get_config
from src.core.logging_system import get_logger

logger = get_logger(__name__)


@dataclass
class NotificationChannel:
    """类文档字符串."""

    pass  # 添加pass语句
    """通知渠道配置"""

    id: str
    name: str
    type: str  # email, slack, wechat, dingtalk
    enabled: bool
    config: dict[str, Any]
    filters: dict[str, Any] | None = None  # 告警过滤条件


class EmailClient:
    """类文档字符串."""

    pass  # 添加pass语句
    """邮件通知客户端"""

    def __init__(self, config: dict[str, Any]):
        """函数文档字符串."""
        # 添加pass语句
        self.smtp_server = config.get("smtp_server", "smtp.gmail.com")
        self.smtp_port = config.get("smtp_port", 587)
        self.username = config.get("username")
        self.password = config.get("password")
        self.from_email = config.get("from_email", self.username)
        self.use_tls = config.get("use_tls", True)
        self.logger = get_logger(self.__class__.__name__)

    async def send_alert_email(self, alert: Alert, recipients: list[str]) -> bool:
        """发送告警邮件."""
        try:
            # 创建邮件内容
            subject = f"[{alert.severity.value.upper()}] {alert.title}"

            # 渲染HTML模板
            html_content = self._render_email_template(alert)
            text_content = self._render_text_template(alert)

            # 创建邮件消息
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = ", ".join(recipients)
            msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")

            # 添加文本内容
            msg.attach(MIMEText(text_content, "plain", "utf-8"))

            # 添加HTML内容
            msg.attach(MIMEHtml(html_content, "html", "utf-8"))

            # 发送邮件
            await self._send_email(msg, recipients)

            self.logger.info(f"告警邮件已发送: {alert.id} -> {recipients}")
            return True

        except Exception as e:
            self.logger.error(f"发送告警邮件失败: {e}")
            return False

    def _render_email_template(self, alert: Alert) -> str:
        """渲染邮件HTML模板."""
        template_str = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            {% if alert.severity.value == 'critical' %}
            background: linear-gradient(135deg, #ff4d4f, #ff7875);
            {% elif alert.severity.value == 'error' %}
            background: linear-gradient(135deg, #ff7875, #ffa940);
            {% elif alert.severity.value == 'warning' %}
            background: linear-gradient(135deg, #faad14, #ffc53d);
            {% else %}
            background: linear-gradient(135deg, #1890ff, #40a9ff);
            {% endif %}
            color: white; padding: 30px; text-align: center; }
        .content { padding: 30px; }
        .alert-info {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            margin: 20px 0;
        }
        .severity-badge{
    display: inline-block;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: bold;
    color: white;
    text-transform: uppercase;
    margin: 5px 0;
    {% if alert.severity.value == 'critical' %;
}
            background-color: #ff4d4f;
            {% elif alert.severity.value == 'error' %}
            background-color: #ff7875;
            {% elif alert.severity.value == 'warning' %}
            background-color: #faad14;
            {% else %}
            background-color: #1890ff;
            {% endif %}
        }
        .footer {
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 12px;
        }
        .details {
            background: #fff1f0;
            border-left: 4px solid #ff4d4f;
            padding: 15px;
            margin: 15px 0;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            margin: 8px 0;
        }
        .action-buttons { margin: 20px 0; }
                .btn {
            display: inline-block;
            padding: 10px 20px;
            margin: 5px;
            text-decoration: none;
            border-radius: 4px;
            font-weight: bold;
        }
        .btn-primary { background: #1890ff; color: white; }
        .btn-secondary { background: #f5f5f5; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 质量监控告警</h1>
            <p>{{ alert.title }}</p>
        </div>

        <div class="content">
            <div class="severity-badge">{{ alert.severity.value }}</div>

            <div class="alert-info">
                <h3>告警详情</h3>
                <p><strong>告警消息:</strong> {{ alert.message }}</p>
                <p><strong>告警类型:</strong> {{ alert.type.value }}</p>
                <p><strong>告警源:</strong> {{ alert.source }}</p>
    <p><strong>触发时间:</strong> {{ alert.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</p>;

                {% if alert.current_value is not none and alert.threshold is not none %}
                <div class="metric">
                    <span>当前值:</span>
                    <strong>{{ "%.2f"|format(alert.current_value) }}</strong>
                </div>
                <div class="metric">
                    <span>阈值:</span>
                    <strong>{{ "%.2f"|format(alert.threshold) }}</strong>
                </div>
                {% endif %}
            </div>

            {% if alert.details %}
            <div class="details">
                <h4>详细信息</h4>
                {% for key, value in alert.details.items() %}
                <p><strong>{{ key }}:</strong> {{ value }}</p>
                {% endfor %}
            </div>
            {% endif %}

            <div class="action-buttons">
                <a href="#" class="btn btn-primary">查看详情</a>
                <a href="#" class="btn btn-secondary">确认告警</a>
            </div>
        </div>

        <div class="footer">
            <p>此邮件由足球预测系统质量监控自动发送</p>
            <p>发送时间: {{ "now"|strftime("%Y-%m-%d %H:%M:%S") }}</p>
        </div>
    </div>
</body>
</html>
        """

        template = jinja2.Template(template_str)
        return template.render(alert=alert, now=datetime.now())

    def _render_text_template(self, alert: Alert) -> str:
        """渲染纯文本模板."""
        template_str = """
质量监控告警通知

告警标题: {{ alert.title }}
严重程度: {{ alert.severity.value.upper() }}
告警类型: {{ alert.type.value }}
告警消息: {{ alert.message }}
告警源: {{ alert.source }}
触发时间: {{ alert.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}

{% if alert.current_value is not none and alert.threshold is not none %}
当前值: {{ "%.2f"|format(alert.current_value) }}
阈值: {{ "%.2f"|format(alert.threshold) }}
{% endif %}

{% if alert.details %}
详细信息:
{% for key, value in alert.details.items() %}
{{ key }}: {{ value }}
{% endfor %}
{% endif %}

---
此邮件由足球预测系统质量监控自动发送
发送时间: {{ "now"|strftime("%Y-%m-%d %H:%M:%S") }}
        """

        template = jinja2.Template(template_str)
        return template.render(alert=alert, now=datetime.now())

    async def _send_email(self, msg: MIMEMultipart, recipients: list[str]):
        """发送邮件."""
        # 在实际实现中,这里应该使用异步SMTP库
        # 目前使用同步方式作为示例
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            if self.use_tls:
                server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg, to_addrs=recipients)


class SlackClient:
    """类文档字符串."""

    pass  # 添加pass语句
    """Slack通知客户端"""

    def __init__(self, config: dict[str, Any]):
        """函数文档字符串."""
        # 添加pass语句
        self.webhook_url = config.get("webhook_url")
        self.channel = config.get("channel", "#quality-alerts")
        self.username = config.get("username", "Quality Monitor")
        self.icon_emoji = config.get("icon_emoji", ":robot_face:")
        self.logger = get_logger(self.__class__.__name__)

    async def send_alert_slack(self, alert: Alert) -> bool:
        """发送Slack告警通知."""
        try:
            # 构建Slack消息
            payload = self._build_slack_message(alert)

            # 发送HTTP请求
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 200:
                        self.logger.info(f"Slack告警已发送: {alert.id}")
                        return True
                    else:
                        self.logger.error(f"Slack发送失败: {response.status}")
                        return False

        except Exception as e:
            self.logger.error(f"发送Slack告警失败: {e}")
            return False

    def _build_slack_message(self, alert: Alert) -> dict[str, Any]:
        """构建Slack消息格式."""
        # 根据严重程度选择颜色
        color_map = {
            AlertSeverity.CRITICAL: "#ff0000",
            AlertSeverity.ERROR: "#ff6600",
            AlertSeverity.WARNING: "#ffaa00",
            AlertSeverity.INFO: "#0066cc",
        }
        color = color_map.get(alert.severity, "#666666")

        # 构建消息
        message = {
            "channel": self.channel,
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "attachments": [
                {
                    "color": color,
                    "title": f"[{alert.severity.value.upper()}] {alert.title}",
                    "text": alert.message,
                    "fields": [
                        {"title": "告警类型", "value": alert.type.value, "short": True},
                        {"title": "告警源", "value": alert.source, "short": True},
                        {
                            "title": "触发时间",
                            "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                            "short": True,
                        },
                    ],
                    "footer": "质量监控系统",
                    "ts": int(alert.timestamp.timestamp()),
                }
            ],
        }

        # 添加当前值和阈值信息
        if alert.current_value is not None and alert.threshold is not None:
            message["attachments"][0]["fields"].append(
                {
                    "title": "当前值 / 阈值",
                    "value": f"{alert.current_value:.2f} / {alert.threshold:.2f}",
                    "short": True,
                }
            )

        # 添加详细信息
        if alert.details:
            details_text = "\n".join(
                [f"• {key}: {value}" for key, value in alert.details.items()]
            )
            message["attachments"][0]["fields"].append(
                {"title": "详细信息", "value": details_text, "short": False}
            )

        return message


class WeChatClient:
    """类文档字符串."""

    pass  # 添加pass语句
    """企业微信通知客户端"""

    def __init__(self, config: dict[str, Any]):
        """函数文档字符串."""
        # 添加pass语句
        self.webhook_url = config.get("webhook_url")
        self.mentioned_list = config.get("mentioned_list", [])
        self.logger = get_logger(self.__class__.__name__)

    async def send_alert_wechat(self, alert: Alert) -> bool:
        """发送企业微信告警通知."""
        try:
            # 构建企业微信消息
            payload = self._build_wechat_message(alert)

            # 发送HTTP请求
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("errcode") == 0:
                            self.logger.info(f"企业微信告警已发送: {alert.id}")
                            return True
                        else:
                            self.logger.error(f"企业微信发送失败: {result}")
                            return False
                    else:
                        self.logger.error(f"企业微信发送失败: {response.status}")
                        return False

        except Exception as e:
            self.logger.error(f"发送企业微信告警失败: {e}")
            return False

    def _build_wechat_message(self, alert: Alert) -> dict[str, Any]:
        """构建企业微信消息格式."""
        # 根据严重程度选择颜色
        color_map = {
            AlertSeverity.CRITICAL: "warning",
            AlertSeverity.ERROR: "warning",
            AlertSeverity.WARNING: "info",
            AlertSeverity.INFO: "comment",
        }
        color = color_map.get(alert.severity, "info")

        # 构建Markdown内容
        content = f"""
## <font color="{color}">[{alert.severity.value.upper()}] {alert.title}</font>

**告警消息:** {alert.message}

**告警详情:**
- 告警类型: {alert.type.value}
- 告警源: {alert.source}
- 触发时间: {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")}
"""

        # 添加当前值和阈值信息
        if alert.current_value is not None and alert.threshold is not None:
            content += (
                f"- 当前值: {alert.current_value:.2f}\n- 阈值: {alert.threshold:.2f}\n"
            )

        # 添加详细信息
        if alert.details:
            content += "\n**详细信息:**\n"
            for key, value in alert.details.items():
                content += f"- {key}: {value}\n"

        message = {"msgtype": "markdown", "markdown": {"content": content}}

        # 添加@用户
        if self.mentioned_list:
            message["markdown"].get("mentioned_list", []).extend(self.mentioned_list)

        return message


class DingTalkClient:
    """类文档字符串."""

    pass  # 添加pass语句
    """钉钉通知客户端"""

    def __init__(self, config: dict[str, Any]):
        """函数文档字符串."""
        # 添加pass语句
        self.webhook_url = config.get("webhook_url")
        self.secret = config.get("secret")
        self.at_mobiles = config.get("at_mobiles", [])
        self.is_at_all = config.get("is_at_all", False)
        self.logger = get_logger(self.__class__.__name__)

    async def send_alert_dingtalk(self, alert: Alert) -> bool:
        """发送钉钉告警通知."""
        try:
            # 构建钉钉消息
            payload = self._build_dingtalk_message(alert)

            # 发送HTTP请求
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("errcode") == 0:
                            self.logger.info(f"钉钉告警已发送: {alert.id}")
                            return True
                        else:
                            self.logger.error(f"钉钉发送失败: {result}")
                            return False
                    else:
                        self.logger.error(f"钉钉发送失败: {response.status}")
                        return False

        except Exception as e:
            self.logger.error(f"发送钉钉告警失败: {e}")
            return False

    def _build_dingtalk_message(self, alert: Alert) -> dict[str, Any]:
        """构建钉钉消息格式."""
        # 根据严重程度选择表情符号
        emoji_map = {
            AlertSeverity.CRITICAL: "🚨",
            AlertSeverity.ERROR: "❌",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.INFO: "ℹ️",
        }
        emoji = emoji_map.get(alert.severity, "📢")

        # 构建Markdown内容
        text = f"""
### {emoji} [{alert.severity.value.upper()}] {alert.title}

**告警消息:** {alert.message}

**告警详情:**
- 告警类型: {alert.type.value}
- 告警源: {alert.source}
- 触发时间: {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")}
"""

        # 添加当前值和阈值信息
        if alert.current_value is not None and alert.threshold is not None:
            text += (
                f"- 当前值: {alert.current_value:.2f}\n- 阈值: {alert.threshold:.2f}\n"
            )

        # 添加详细信息
        if alert.details:
            text += "\n**详细信息:**\n"
            for key, value in alert.details.items():
                text += f"- {key}: {value}\n"

        message = {
            "msgtype": "markdown",
            "markdown": {"title": f"质量监控告警: {alert.title}", "text": text},
            "at": {"atMobiles": self.at_mobiles, "isAtAll": self.is_at_all},
        }

        return message


class NotificationManager:
    """类文档字符串."""

    pass  # 添加pass语句
    """通知管理器"""

    def __init__(self):
        """函数文档字符串."""
        # 添加pass语句
        self.channels: dict[str, NotificationChannel] = {}
        self.clients: dict[str, Any] = {}
        self.config = get_config()
        self.logger = get_logger(self.__class__.__name__)

        # 加载通知渠道配置
        self._load_notification_channels()

    def _load_notification_channels(self):
        """函数文档字符串."""
        # 添加pass语句
        """加载通知渠道配置"""
        try:
            # 默认通知渠道配置
            default_channels = [
                NotificationChannel(
                    id="log", name="日志记录", type="log", enabled=True, config={}
                )
            ]

            # 尝试从配置文件加载渠道
            config_file = Path("config/notification_channels.json")
            if config_file.exists():
                with open(config_file, encoding="utf-8") as f:
                    channels_config = json.load(f)

                for channel_config in channels_config:
                    channel = NotificationChannel(**channel_config)
                    self.channels[channel.id] = channel

                    # 初始化客户端
                    self._initialize_client(channel)

            # 添加默认渠道
            for channel in default_channels:
                if channel.id not in self.channels:
                    self.channels[channel.id] = channel

            self.logger.info(f"已加载 {len(self.channels)} 个通知渠道")

        except Exception as e:
            self.logger.error(f"加载通知渠道配置失败: {e}")

    def _initialize_client(self, channel: NotificationChannel):
        """函数文档字符串."""
        # 添加pass语句
        """初始化通知客户端"""
        try:
            if channel.type == "email" and channel.enabled:
                self.clients[channel.id] = EmailClient(channel.config)
            elif channel.type == "slack" and channel.enabled:
                self.clients[channel.id] = SlackClient(channel.config)
            elif channel.type == "wechat" and channel.enabled:
                self.clients[channel.id] = WeChatClient(channel.config)
            elif channel.type == "dingtalk" and channel.enabled:
                self.clients[channel.id] = DingTalkClient(channel.config)

            self.logger.info(f"通知客户端已初始化: {channel.type} - {channel.id}")

        except Exception as e:
            self.logger.error(f"初始化通知客户端失败 {channel.id}: {e}")

    async def send_alert_notification(self, alert: Alert) -> dict[str, bool]:
        """发送告警通知到所有启用的渠道."""
        results = {}

        try:
            # 检查告警是否应该发送到此渠道
            for channel_id, channel in self.channels.items():
                if not channel.enabled:
                    continue

                # 检查过滤条件
                if not self._should_send_alert(alert, channel):
                    continue

                # 发送通知
                success = await self._send_to_channel(alert, channel)
                results[channel_id] = success

            self.logger.info(f"告警通知发送完成: {alert.id}, 结果: {results}")

        except Exception as e:
            self.logger.error(f"发送告警通知失败: {e}")

        return results

    def _should_send_alert(self, alert: Alert, channel: NotificationChannel) -> bool:
        """检查告警是否应该发送到指定渠道."""
        try:
            # 如果没有过滤条件,默认发送
            if not channel.filters:
                return True

            filters = channel.filters

            # 严重程度过滤
            if "severities" in filters:
                allowed_severities = filters["severities"]
                if alert.severity.value not in allowed_severities:
                    return False

            # 告警类型过滤
            if "types" in filters:
                allowed_types = filters["types"]
                if alert.type.value not in allowed_types:
                    return False

            # 时间过滤
            if "active_hours" in filters:
                active_hours = filters["active_hours"]
                current_hour = datetime.now().hour
                if current_hour not in active_hours:
                    return False

            return True

        except Exception as e:
            self.logger.error(f"检查告警过滤条件失败: {e}")
            return True  # 出错时默认发送

    async def _send_to_channel(
        self, alert: Alert, channel: NotificationChannel
    ) -> bool:
        """发送告警到指定渠道."""
        try:
            # 检查发送条件
            if not self._should_send_alert(alert, channel):
                return False

            # 日志记录
            self.logger.warning(
                f"告警通知 [{alert.severity.value.upper()}] {alert.title}: {alert.message}"
            )

            if channel.type == "email":
                client = self.clients.get(channel.id)
                if client and channel.config.get("recipients"):
                    return await client.send_alert_email(
                        alert, channel.config["recipients"]
                    )

            elif channel.type == "slack":
                client = self.clients.get(channel.id)
                if client:
                    return await client.send_alert_slack(alert)

            elif channel.type == "wechat":
                client = self.clients.get(channel.id)
                if client:
                    return await client.send_alert_wechat(alert)

            elif channel.type == "dingtalk":
                client = self.clients.get(channel.id)
                if client:
                    return await client.send_alert_dingtalk(alert)

            else:
                self.logger.warning(f"未知的通知渠道类型: {channel.type}")
                return False

        except Exception as e:
            self.logger.error(f"发送告警到渠道 {channel.id} 失败: {e}")
            return False

        def add_channel(self, channel: NotificationChannel):
                """添加新的通知渠道."""
                self.channels[channel.id] = channel
                self._initialize_client(channel)
                self.logger.info(f"已添加通知渠道: {channel.id}")

        def remove_channel(self, channel_id: str):
                """移除通知渠道."""
                if channel_id in self.channels:
                    del self.channels[channel_id]
                    if channel_id in self.clients:
                        del self.clients[channel_id]
                    self.logger.info(f"已移除通知渠道: {channel_id}")

        def get_channel_status(self) -> dict[str, dict[str, Any]]:
                """获取所有渠道的状态."""
                status = {}
                for channel_id, channel in self.channels.items():
                    status[channel_id] = {
                        "name": channel.name,
                        "type": channel.type,
                        "enabled": channel.enabled,
                        "has_client": channel_id in self.clients,
                    }
                return status


# 全局通知管理器实例
notification_manager = NotificationManager()
