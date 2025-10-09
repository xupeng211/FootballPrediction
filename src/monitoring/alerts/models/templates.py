"""
告警通知模板
Alert Notification Templates

定义各种渠道的通知模板和格式化工具。
Defines notification templates and formatting tools for various channels.
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from .enums import AlertChannel, AlertSeverity, AlertType


class BaseTemplate(ABC):
    """
    基础模板类
    Base Template Class

    定义模板的通用接口。
    Defines common interface for templates.
    """

    @abstractmethod
    def render(self, data: Dict[str, Any]) -> str:
        """
        渲染模板
        Render Template

        Args:
            data: 模板数据 / Template data

        Returns:
            str: 渲染结果 / Rendered result
        """
        pass


class EmailTemplate(BaseTemplate):
    """
    邮件模板类
    Email Template Class

    定义邮件通知的模板格式。
    Defines email notification template format.
    """

    def __init__(
        self,
        subject_template: str,
        body_template: str,
        html_template: Optional[str] = None,
    ):
        """
        初始化邮件模板
        Initialize Email Template

        Args:
            subject_template: 主题模板 / Subject template
            body_template: 正文模板 / Body template
            html_template: HTML模板 / HTML template
        """
        self.subject_template = subject_template
        self.body_template = body_template
        self.html_template = html_template

    def render(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        渲染邮件模板
        Render Email Template

        Args:
            data: 模板数据 / Template data

        Returns:
            Dict[str, str]: 渲染结果 / Rendered result
        """
        try:
            subject = self._format_string(self.subject_template, data)
            body = self._format_string(self.body_template, data)
            html = None

            if self.html_template:
                html = self._format_string(self.html_template, data)

            return {
                "subject": subject,
                "body": body,
                "html": html,
            }
        except Exception:
            # 格式化失败时的兜底处理
            return {
                "subject": f"Alert: {data.get('title', 'Unknown')}",
                "body": f"Alert details: {json.dumps(data, indent=2)}",
                "html": None,
            }

    def _format_string(self, template: str, data: Dict[str, Any]) -> str:
        """
        格式化字符串
        Format String

        Args:
            template: 模板字符串 / Template string
            data: 数据 / Data

        Returns:
            str: 格式化结果 / Formatted result
        """
        try:
            return template.format(**data)
        except KeyError as e:
            # 处理缺失的键
            return template.replace(f"{{{e.args[0]}}}", f"[MISSING: {e.args[0]}]")


class SlackTemplate(BaseTemplate):
    """
    Slack模板类
    Slack Template Class

    定义Slack通知的模板格式。
    Defines Slack notification template format.
    """

    def __init__(
        self,
        message_template: str,
        emoji_map: Optional[Dict[AlertSeverity, str]] = None,
        color_map: Optional[Dict[AlertSeverity, str]] = None,
    ):
        """
        初始化Slack模板
        Initialize Slack Template

        Args:
            message_template: 消息模板 / Message template
            emoji_map: 表情映射 / Emoji mapping
            color_map: 颜色映射 / Color mapping
        """
        self.message_template = message_template
        self.emoji_map = emoji_map or {
            AlertSeverity.LOW: ":information_source:",
            AlertSeverity.MEDIUM: ":warning:",
            AlertSeverity.HIGH: ":exclamation:",
            AlertSeverity.CRITICAL: ":rotating_light:",
        }
        self.color_map = color_map or {
            AlertSeverity.LOW: "#36a64f",  # green
            AlertSeverity.MEDIUM: "#ff9500",  # orange
            AlertSeverity.HIGH: "#ff0000",  # red
            AlertSeverity.CRITICAL: "#8b0000",  # dark red
        }

    def render(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        渲染Slack模板
        Render Slack Template

        Args:
            data: 模板数据 / Template data

        Returns:
            Dict[str, Any]: Slack消息格式 / Slack message format
        """
        try:
            # 获取严重程度
            severity = AlertSeverity(data.get("severity", "low"))
            emoji = self.emoji_map.get(severity, ":information_source:")
            color = self.color_map.get(severity, "#36a64f")

            # 格式化消息
            message = self._format_string(self.message_template, data)

            # 构建Slack消息
            slack_message = {
                "text": f"{emoji} {message}",
                "attachments": [
                    {
                        "color": color,
                        "fields": [
                            {"title": "Alert ID", "value": data.get("alert_id", "N/A"), "short": True},
                            {"title": "Severity", "value": severity.value.upper(), "short": True},
                            {"title": "Source", "value": data.get("source", "N/A"), "short": True},
                            {"title": "Time", "value": data.get("created_at", "N/A"), "short": True},
                        ],
                        "text": data.get("message", ""),
                    }
                ],
            }

            # 添加标签和注释
            if data.get("labels"):
                labels_text = "\n".join([f"• {k}: {v}" for k, v in data["labels"].items()])
                slack_message["attachments"][0]["fields"].append({
                    "title": "Labels",
                    "value": labels_text,
                    "short": False,
                })

            return slack_message

        except Exception as e:
            # 格式化失败时的兜底处理
            return {
                "text": f"Alert: {data.get('title', 'Unknown')}",
                "attachments": [
                    {
                        "color": "#ff0000",
                        "text": f"Error formatting alert: {str(e)}\n\nData: {json.dumps(data, indent=2)}",
                    }
                ],
            }

    def _format_string(self, template: str, data: Dict[str, Any]) -> str:
        """
        格式化字符串
        Format String

        Args:
            template: 模板字符串 / Template string
            data: 数据 / Data

        Returns:
            str: 格式化结果 / Formatted result
        """
        try:
            return template.format(**data)
        except KeyError as e:
            return template.replace(f"{{{e.args[0]}}}", f"[MISSING: {e.args[0]}]")


class WebhookTemplate(BaseTemplate):
    """
    Webhook模板类
    Webhook Template Class

    定义Webhook通知的模板格式。
    Defines Webhook notification template format.
    """

    def __init__(self, payload_template: Optional[Dict[str, Any]] = None):
        """
        初始化Webhook模板
        Initialize Webhook Template

        Args:
            payload_template: 载荷模板 / Payload template
        """
        self.payload_template = payload_template or {
            "alert_id": "{alert_id}",
            "title": "{title}",
            "message": "{message}",
            "severity": "{severity}",
            "source": "{source}",
            "timestamp": "{created_at}",
            "labels": "{labels}",
            "annotations": "{annotations}",
        }

    def render(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        渲染Webhook模板
        Render Webhook Template

        Args:
            data: 模板数据 / Template data

        Returns:
            Dict[str, Any]: Webhook载荷 / Webhook payload
        """
        try:
            # 深度格式化载荷
            payload = self._format_dict(self.payload_template, data)
            return payload
        except Exception as e:
            # 格式化失败时的兜底处理
            return {
                "error": f"Template formatting failed: {str(e)}",
                "original_data": data,
                "timestamp": datetime.utcnow().isoformat(),
            }

    def _format_dict(self, template: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化字典
        Format Dictionary

        Args:
            template: 模板字典 / Template dictionary
            data: 数据 / Data

        Returns:
            Dict[str, Any]: 格式化结果 / Formatted result
        """
        result = {}
        for key, value in template.items():
            if isinstance(value, str):
                result[key] = self._format_string(value, data)
            elif isinstance(value, dict):
                result[key] = self._format_dict(value, data)
            elif isinstance(value, list):
                result[key] = [self._format_item(item, data) for item in value]
            else:
                result[key] = value
        return result

    def _format_item(self, item: Any, data: Dict[str, Any]) -> Any:
        """
        格式化单项
        Format Item

        Args:
            item: 项目 / Item
            data: 数据 / Data

        Returns:
            Any: 格式化结果 / Formatted result
        """
        if isinstance(item, str):
            return self._format_string(item, data)
        elif isinstance(item, dict):
            return self._format_dict(item, data)
        elif isinstance(item, list):
            return [self._format_item(i, data) for i in item]
        else:
            return item

    def _format_string(self, template: str, data: Dict[str, Any]) -> str:
        """
        格式化字符串
        Format String

        Args:
            template: 模板字符串 / Template string
            data: 数据 / Data

        Returns:
            str: 格式化结果 / Formatted result
        """
        try:
            return template.format(**data)
        except KeyError as e:
            return template.replace(f"{{{e.args[0]}}}", f"[MISSING: {e.args[0]}]")


class SMSTemplate(BaseTemplate):
    """
    短信模板类
    SMS Template Class

    定义短信通知的模板格式。
    Defines SMS notification template format.
    """

    def __init__(self, message_template: str, max_length: int = 160):
        """
        初始化短信模板
        Initialize SMS Template

        Args:
            message_template: 消息模板 / Message template
            max_length: 最大长度 / Maximum length
        """
        self.message_template = message_template
        self.max_length = max_length

    def render(self, data: Dict[str, Any]) -> str:
        """
        渲染短信模板
        Render SMS Template

        Args:
            data: 模板数据 / Template data

        Returns:
            str: 短信内容 / SMS content
        """
        try:
            message = self._format_string(self.message_template, data)

            # 确保不超过最大长度
            if len(message) > self.max_length:
                # 截断并添加省略号
                message = message[: self.max_length - 3] + "..."

            return message
        except Exception:
            # 格式化失败时的兜底处理
            return f"ALERT: {data.get('title', 'Unknown')} - {data.get('severity', 'unknown')} severity"


class TemplateManager:
    """
    模板管理器
    Template Manager

    管理各种通知模板。
    Manages various notification templates.
    """

    def __init__(self):
        """
        初始化模板管理器
        Initialize Template Manager
        """
        self.templates: Dict[AlertChannel, Dict[str, BaseTemplate]] = {
            AlertChannel.EMAIL: {},
            AlertChannel.SLACK: {},
            AlertChannel.WEBHOOK: {},
            AlertChannel.SMS: {},
        }
        self._load_default_templates()

    def _load_default_templates(self) -> None:
        """
        加载默认模板
        Load Default Templates
        """
        # 邮件模板
        email_subject = "🚨 Alert: {title}"
        email_body = """
Alert Details:
- ID: {alert_id}
- Title: {title}
- Severity: {severity}
- Source: {source}
- Time: {created_at}

Message:
{message}

Labels:
{labels}

Annotations:
{annotations}
""".strip()

        self.templates[AlertChannel.EMAIL]["default"] = EmailTemplate(
            subject_template=email_subject,
            body_template=email_body,
        )

        # Slack模板
        slack_message = "*{title}* from `{source}`"
        self.templates[AlertChannel.SLACK]["default"] = SlackTemplate(
            message_template=slack_message,
        )

        # Webhook模板
        self.templates[AlertChannel.WEBHOOK]["default"] = WebhookTemplate()

        # 短信模板
        sms_message = "Alert: {title} ({severity}) from {source}"
        self.templates[AlertChannel.SMS]["default"] = SMSTemplate(
            message_template=sms_message,
        )

    def add_template(self, channel: AlertChannel, name: str, template: BaseTemplate) -> None:
        """
        添加模板
        Add Template

        Args:
            channel: 渠道 / Channel
            name: 模板名称 / Template name
            template: 模板对象 / Template object
        """
        if channel not in self.templates:
            self.templates[channel] = {}
        self.templates[channel][name] = template

    def get_template(self, channel: AlertChannel, name: str = "default") -> Optional[BaseTemplate]:
        """
        获取模板
        Get Template

        Args:
            channel: 渠道 / Channel
            name: 模板名称 / Template name

        Returns:
            Optional[BaseTemplate]: 模板对象 / Template object
        """
        return self.templates.get(channel, {}).get(name)

    def list_templates(self, channel: Optional[AlertChannel] = None) -> Dict[str, List[str]]:
        """
        列出模板
        List Templates

        Args:
            channel: 渠道 / Channel

        Returns:
            Dict[str, List[str]]: 模板列表 / Template list
        """
        if channel:
            return {channel.value: list(self.templates.get(channel, {}).keys())}

        return {
            channel.value: list(templates.keys())
            for channel, templates in self.templates.items()
        }

    def render_template(
        self, channel: AlertChannel, data: Dict[str, Any], template_name: str = "default"
    ) -> Any:
        """
        渲染模板
        Render Template

        Args:
            channel: 渠道 / Channel
            data: 数据 / Data
            template_name: 模板名称 / Template name

        Returns:
            Any: 渲染结果 / Rendered result
        """
        template = self.get_template(channel, template_name)
        if not template:
            raise ValueError(f"Template not found for channel {channel.value} and name {template_name}")

        return template.render(data)

    def _format_string(self, template: str, data: Dict[str, Any]) -> str:
        """
        格式化字符串
        Format String

        Args:
            template: 模板字符串 / Template string
            data: 数据 / Data

        Returns:
            str: 格式化结果 / Formatted result
        """
        try:
            return template.format(**data)
        except KeyError as e:
            return template.replace(f"{{{e.args[0]}}}", f"[MISSING: {e.args[0]}]")