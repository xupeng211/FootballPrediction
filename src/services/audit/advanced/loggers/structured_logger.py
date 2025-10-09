"""
结构化日志器
Structured Logger

提供结构化的审计日志记录功能。
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from src.core.logging import get_logger

from ..models import AuditLog

logger = get_logger(__name__)


class StructuredLogger:
    """
    结构化日志器 / Structured Logger

    提供标准化的结构化日志格式和输出。
    Provides standardized structured log format and output.
    """

    def __init__(self):
        """初始化结构化日志器 / Initialize Structured Logger"""
        self.logger = get_logger(f"audit.{self.__class__.__name__}")

        # 创建专用的审计日志记录器
        self.audit_logger = logging.getLogger("audit.structured")

        # 配置日志格式
        self._setup_logger()

    def _setup_logger(self) -> None:
        """设置日志器 / Setup Logger"""
        try:
            # 创建格式化器
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

            # 如果没有处理器，添加控制台处理器
            if not self.audit_logger.handlers:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                self.audit_logger.addHandler(console_handler)
                self.audit_logger.setLevel(logging.INFO)

        except Exception as e:
            self.logger.error(f"设置结构化日志器失败: {e}")

    def log_audit_event(self, audit_log: AuditLog) -> None:
        """
        记录审计事件 / Log Audit Event

        Args:
            audit_log: 审计日志 / Audit log
        """
        try:
            # 构建结构化日志消息
            structured_message = self._build_structured_message(audit_log)

            # 根据严重性选择日志级别
            level = self._get_log_level(audit_log.severity)

            # 记录日志
            self.audit_logger.log(level, structured_message)

        except Exception as e:
            self.logger.error(f"记录结构化审计日志失败: {e}")

    def _build_structured_message(self, audit_log: AuditLog) -> str:
        """
        构建结构化消息 / Build Structured Message

        Args:
            audit_log: 审计日志 / Audit log

        Returns:
            str: 结构化消息 / Structured message
        """
        # 构建基础消息结构
        message = {
            "event_type": "audit_log",
            "timestamp": audit_log.timestamp.isoformat() if audit_log.timestamp else datetime.now().isoformat(),
            "event_id": audit_log.id,
            "user": {
                "id": audit_log.user_id,
                "username": audit_log.username,
                "role": audit_log.user_role,
                "session_id": audit_log.session_id,
            },
            "action": {
                "type": audit_log.action.value if audit_log.action else "unknown",
                "resource_type": audit_log.resource_type,
                "resource_id": audit_log.resource_id,
                "description": audit_log.description,
            },
            "context": {
                "ip_address": audit_log.ip_address,
                "user_agent": audit_log.user_agent,
                "request_id": audit_log.request_id,
                "correlation_id": audit_log.correlation_id,
            },
            "severity": audit_log.severity.value if audit_log.severity else "unknown",
            "data_changes": {
                "old_values": audit_log.old_values,
                "new_values": audit_log.new_values,
                "table_name": audit_log.table_name,
            },
            "compliance": {
                "category": audit_log.compliance_category,
            },
            "metadata": audit_log.metadata,
        }

        # 清理空值
        message = self._clean_empty_values(message)

        # 转换为JSON字符串
        return json.dumps(message, ensure_ascii=False, default=str)

    def _get_log_level(self, severity) -> int:
        """
        获取日志级别 / Get Log Level

        Args:
            severity: 严重性 / Severity

        Returns:
            int: 日志级别 / Log level
        """
        if not severity:
            return logging.INFO

        severity_value = severity.value if hasattr(severity, 'value') else str(severity)

        if severity_value == "critical":
            return logging.CRITICAL
        elif severity_value == "high":
            return logging.ERROR
        elif severity_value == "medium":
            return logging.WARNING
        else:
            return logging.INFO

    def _clean_empty_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理空值 / Clean Empty Values

        Args:
            data: 数据字典 / Data dictionary

        Returns:
            Dict[str, Any]: 清理后的数据 / Cleaned data
        """
        if isinstance(data, dict):
            return {
                key: self._clean_empty_values(value)
                for key, value in data.items()
                if value is not None and value != ""
            }
        elif isinstance(data, list):
            return [self._clean_empty_values(item) for item in data if item is not None]
        else:
            return data

    def log_security_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """
        记录安全事件 / Log Security Event

        Args:
            event_type: 事件类型 / Event type
            details: 事件详情 / Event details
        """
        try:
            security_message = {
                "event_type": "security_event",
                "timestamp": datetime.now().isoformat(),
                "security_event_type": event_type,
                "details": details,
                "severity": details.get("severity", "medium"),
            }

            # 清理空值
            security_message = self._clean_empty_values(security_message)

            # 根据严重性选择日志级别
            severity = details.get("severity", "medium")
            level = self._get_log_level(severity)

            self.audit_logger.log(level, json.dumps(security_message, ensure_ascii=False, default=str))

        except Exception as e:
            self.logger.error(f"记录安全事件失败: {e}")

    def log_compliance_event(self, compliance_type: str, details: Dict[str, Any]) -> None:
        """
        记录合规事件 / Log Compliance Event

        Args:
            compliance_type: 合规类型 / Compliance type
            details: 事件详情 / Event details
        """
        try:
            compliance_message = {
                "event_type": "compliance_event",
                "timestamp": datetime.now().isoformat(),
                "compliance_type": compliance_type,
                "details": details,
                "regulation": details.get("regulation"),
                "requirement": details.get("requirement"),
            }

            # 清理空值
            compliance_message = self._clean_empty_values(compliance_message)

            self.audit_logger.info(json.dumps(compliance_message, ensure_ascii=False, default=str))

        except Exception as e:
            self.logger.error(f"记录合规事件失败: {e}")

    def log_performance_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        记录性能指标 / Log Performance Metrics

        Args:
            metrics: 性能指标 / Performance metrics
        """
        try:
            performance_message = {
                "event_type": "performance_metrics",
                "timestamp": datetime.now().isoformat(),
                "metrics": metrics,
                "service": "audit_service",
            }

            # 清理空值
            performance_message = self._clean_empty_values(performance_message)

            self.audit_logger.info(json.dumps(performance_message, ensure_ascii=False, default=str))

        except Exception as e:
            self.logger.error(f"记录性能指标失败: {e}")

    def log_error_event(self, error: Exception, context: Dict[str, Any]) -> None:
        """
        记录错误事件 / Log Error Event

        Args:
            error: 错误对象 / Error object
            context: 上下文信息 / Context information
        """
        try:
            error_message = {
                "event_type": "error_event",
                "timestamp": datetime.now().isoformat(),
                "error": {
                    "type": type(error).__name__,
                    "message": str(error),
                    "traceback": self._get_traceback(error),
                },
                "context": context,
                "severity": "error",
            }

            # 清理空值
            error_message = self._clean_empty_values(error_message)

            self.audit_logger.error(json.dumps(error_message, ensure_ascii=False, default=str))

        except Exception as e:
            self.logger.error(f"记录错误事件失败: {e}")

    def _get_traceback(self, error: Exception) -> Optional[str]:
        """
        获取错误堆栈 / Get Error Traceback

        Args:
            error: 错误对象 / Error object

        Returns:
            Optional[str]: 堆栈信息 / Traceback information
        """
        try:
            import traceback
            return traceback.format_exc()
        except:
            return None

    def log_custom_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        记录自定义事件 / Log Custom Event

        Args:
            event_type: 事件类型 / Event type
            data: 事件数据 / Event data
        """
        try:
            custom_message = {
                "event_type": "custom_event",
                "timestamp": datetime.now().isoformat(),
                "custom_event_type": event_type,
                "data": data,
            }

            # 清理空值
            custom_message = self._clean_empty_values(custom_message)

            # 根据数据中的严重性确定日志级别
            severity = data.get("severity", "info")
            level = self._get_log_level(severity)

            self.audit_logger.log(level, json.dumps(custom_message, ensure_ascii=False, default=str))

        except Exception as e:
            self.logger.error(f"记录自定义事件失败: {e}")

    def create_audit_trail(self, events: List[Dict[str, Any]]) -> str:
        """
        创建审计跟踪 / Create Audit Trail

        Args:
            events: 事件列表 / Events list

        Returns:
            str: 审计跟踪ID / Audit trail ID
        """
        try:
            import uuid
            trail_id = str(uuid.uuid4())

            trail_message = {
                "event_type": "audit_trail",
                "trail_id": trail_id,
                "timestamp": datetime.now().isoformat(),
                "events_count": len(events),
                "events": events,
            }

            # 清理空值
            trail_message = self._clean_empty_values(trail_message)

            self.audit_logger.info(json.dumps(trail_message, ensure_ascii=False, default=str))

            return trail_id

        except Exception as e:
            self.logger.error(f"创建审计跟踪失败: {e}")
            return ""

    def log_data_access(self, user_id: str, resource: str, access_type: str, details: Dict[str, Any]) -> None:
        """
        记录数据访问 / Log Data Access

        Args:
            user_id: 用户ID / User ID
            resource: 资源 / Resource
            access_type: 访问类型 / Access type
            details: 详细信息 / Details
        """
        try:
            access_message = {
                "event_type": "data_access",
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "resource": resource,
                "access_type": access_type,
                "details": details,
                "severity": "info",
            }

            # 清理空值
            access_message = self._clean_empty_values(access_message)

            self.audit_logger.info(json.dumps(access_message, ensure_ascii=False, default=str))

        except Exception as e:
            self.logger.error(f"记录数据访问失败: {e}")

    def log_system_event(self, system_name: str, event_type: str, details: Dict[str, Any]) -> None:
        """
        记录系统事件 / Log System Event

        Args:
            system_name: 系统名称 / System name
            event_type: 事件类型 / Event type
            details: 详细信息 / Details
        """
        try:
            system_message = {
                "event_type": "system_event",
                "timestamp": datetime.now().isoformat(),
                "system_name": system_name,
                "system_event_type": event_type,
                "details": details,
            }

            # 清理空值
            system_message = self._clean_empty_values(system_message)

            # 根据事件类型确定日志级别
            if event_type in ["error", "failure", "critical"]:
                level = logging.ERROR
            elif event_type in ["warning", "alert"]:
                level = logging.WARNING
            else:
                level = logging.INFO

            self.audit_logger.log(level, json.dumps(system_message, ensure_ascii=False, default=str))

        except Exception as e:
            self.logger.error(f"记录系统事件失败: {e}")

    def export_logs_to_json(self, logs: List[Dict[str, Any]], output_file: Optional[str] = None) -> str:
        """
        导出日志到JSON / Export Logs to JSON

        Args:
            logs: 日志列表 / Logs list
            output_file: 输出文件 / Output file

        Returns:
            str: JSON字符串或文件路径 / JSON string or file path
        """
        try:
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "total_logs": len(logs),
                "logs": logs,
            }

            json_data = json.dumps(export_data, ensure_ascii=False, indent=2, default=str)

            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(json_data)
                self.logger.info(f"日志已导出到文件: {output_file}")
                return output_file
            else:
                return json_data

        except Exception as e:
            self.logger.error(f"导出日志失败: {e}")
            return ""

    def set_log_level(self, level: str) -> None:
        """
        设置日志级别 / Set Log Level

        Args:
            level: 日志级别 / Log level
        """
        try:
            log_level = getattr(logging, level.upper(), logging.INFO)
            self.audit_logger.setLevel(log_level)
            self.logger.info(f"结构化日志器级别已设置为: {level}")
        except Exception as e:
            self.logger.error(f"设置日志级别失败: {e}")

    def get_logger_stats(self) -> Dict[str, Any]:
        """
        获取日志器统计信息 / Get Logger Statistics

        Returns:
            Dict[str, Any]: 统计信息 / Statistics
        """
        try:
            return {
                "logger_name": self.audit_logger.name,
                "level": self.audit_logger.level,
                "handlers_count": len(self.audit_logger.handlers),
                "effective_level": self.audit_logger.getEffectiveLevel(),
                "is_enabled_for_info": self.audit_logger.isEnabledFor(logging.INFO),
                "is_enabled_for_error": self.audit_logger.isEnabledFor(logging.ERROR),
            }
        except Exception as e:
            self.logger.error(f"获取日志器统计信息失败: {e}")
            return {}