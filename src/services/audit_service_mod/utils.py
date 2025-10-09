"""
审计工具函数
Audit Utilities

提供审计相关的工具函数。
"""

import hashlib
import json
import time
from typing import Any, Dict, Optional

from .models import AuditLog


def hash_sensitive_data(data: Any) -> str:
    """
    哈希敏感数据 / Hash Sensitive Data

    Args:
        data: 要哈希的数据 / Data to hash

    Returns:
        str: 哈希值 / Hash value
    """
    if data is None:
        return ""

    # 转换为字符串
    data_str = json.dumps(data, sort_keys=True, default=str)

    # 计算SHA256哈希
    return hashlib.sha256(data_str.encode()).hexdigest()


def sanitize_data(
    data: Dict[str, Any], sensitive_fields: set, mask_char: str = "*"
) -> Dict[str, Any]:
    """
    清理敏感数据 / Sanitize Sensitive Data

    Args:
        data: 原始数据 / Original data
        sensitive_fields: 敏感字段集合 / Sensitive fields set
        mask_char: 掩码字符 / Mask character

    Returns:
        Dict[str, Any]: 清理后的数据 / Sanitized data
    """
    if not data:
        return data

    sanitized = {}

    for key, value in data.items():
        # 检查是否是敏感字段
        if key.lower() in sensitive_fields:
            # 保留数据类型，但掩码处理
            if isinstance(value, str):
                sanitized[key] = mask_char * len(value) if len(value) > 0 else mask_char
            elif isinstance(value, (int, float)):
                sanitized[key] = 0
            elif isinstance(value, dict):
                sanitized[key] = sanitize_data(value, sensitive_fields, mask_char)
            elif isinstance(value, list):
                sanitized[key] = [mask_char] * len(value)
            else:
                sanitized[key] = mask_char
        else:
            sanitized[key] = value

    return sanitized


def calculate_operation_risk(
    action: str,
    resource_type: Optional[str] = None,
    table_name: Optional[str] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
) -> str:
    """
    计算操作风险等级 / Calculate Operation Risk Level

    Args:
        action: 操作类型 / Action type
        resource_type: 资源类型 / Resource type
        table_name: 表名 / Table name
        old_values: 旧值 / Old values
        new_values: 新值 / New values

    Returns:
        str: 风险等级 / Risk level (low, medium, high, critical)
    """
    # 敏感表集合
    sensitive_tables = {
        "users",
        "permissions",
        "tokens",
        "passwords",
        "api_keys",
        "user_profiles",
        "payment_info",
        "personal_data",
        "audit_logs",
    }

    # 敏感操作集合
    critical_actions = {"delete", "drop", "truncate", "reset"}
    high_risk_actions = {"create", "update", "import", "export"}

    # 检查敏感表
    if table_name and table_name.lower() in sensitive_tables:
        if action.lower() in critical_actions:
            return "critical"
        elif action.lower() in high_risk_actions:
            return "high"
        else:
            return "medium"

    # 检查敏感操作
    if action.lower() in critical_actions:
        return "high"
    elif action.lower() in high_risk_actions:
        return "medium"

    # 检查数据变更量
    if old_values and new_values:
        changes_count = sum(
            1
            for k in new_values
            if k not in old_values or old_values[k] != new_values[k]
        )
        if changes_count > 10:
            return "medium"
        elif changes_count > 5:
            return "low"

    return "low"


def format_audit_log_for_display(log: AuditLog) -> Dict[str, Any]:
    """
    格式化审计日志用于显示 / Format Audit Log for Display

    Args:
        log: 审计日志对象 / Audit log object

    Returns:
        Dict[str, Any]: 格式化的日志 / Formatted log
    """
    formatted = log.to_dict()

    # 格式化时间戳
    if formatted.get("timestamp"):
        try:
            from datetime import datetime

            if isinstance(formatted["timestamp"], str):
                formatted["timestamp"] = datetime.fromisoformat(formatted["timestamp"])
            formatted["timestamp_formatted"] = formatted["timestamp"].strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        except Exception:
            formatted["timestamp_formatted"] = formatted.get("timestamp")

    # 格式化持续时间
    if log.metadata and log.metadata.get("duration_ms"):
        duration_ms = log.metadata["duration_ms"]
        if duration_ms > 1000:
            formatted["duration_formatted"] = f"{duration_ms / 1000:.2f}s"
        else:
            formatted["duration_formatted"] = f"{duration_ms}ms"

    # 添加操作描述
    action_descriptions = {
        "create": "创建",
        "read": "读取",
        "update": "更新",
        "delete": "删除",
        "login": "登录",
        "logout": "登出",
        "export": "导出",
        "import": "导入",
        "access": "访问",
        "execute": "执行",
    }

    if formatted.get("action") in action_descriptions:
        formatted["action_description"] = action_descriptions[formatted["action"]]
    else:
        formatted["action_description"] = formatted.get("action", "")

    return formatted


def extract_resource_info(
    args: tuple, kwargs: dict, context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    从参数中提取资源信息 / Extract Resource Information from Arguments

    Args:
        args: 位置参数 / Positional arguments
        kwargs: 关键字参数 / Keyword arguments
        context: 上下文信息 / Context information

    Returns:
        Dict[str, Any]: 资源信息 / Resource information
    """
    resource_info = {}

    # 常见的资源ID参数名
    resource_id_params = [
        "resource_id",
        "id",
        "match_id",
        "user_id",
        "fixture_id",
        "prediction_id",
        "team_id",
        "league_id",
        "season_id",
    ]

    # 从位置参数查找
    if args and len(args) > 1:
        # 假设第二个参数是ID（常见模式）
        resource_info["resource_id"] = str(args[1])

    # 从关键字参数查找
    for param in resource_id_params:
        if param in kwargs:
            resource_info["resource_id"] = str(kwargs[param])
            break

    # 从上下文获取
    if context:
        if "resource_type" in context:
            resource_info["resource_type"] = context["resource_type"]
        if "table_name" in context:
            resource_info["table_name"] = context["table_name"]

    return resource_info


def validate_audit_compliance(log: AuditLog) -> Dict[str, Any]:
    """
    验证审计日志合规性 / Validate Audit Log Compliance

    Args:
        log: 审计日志 / Audit log

    Returns:
        Dict[str, Any]: 验证结果 / Validation result
    """
    issues = []
    warnings = []

    # 检查必需字段
    if not log.user_id:
        issues.append("缺少用户ID")

    if not log.action:
        issues.append("缺少操作类型")

    if not log.timestamp:
        issues.append("缺少时间戳")

    # 检查敏感操作
    if log.action in ["delete", "drop", "truncate"]:
        if not log.resource_id:
            warnings.append("敏感操作缺少资源ID")
        if log.severity not in ["high", "critical"]:
            warnings.append("敏感操作严重性级别过低")

    # 检查数据变更
    if log.action in ["create", "update"] and not log.new_values:
        warnings.append("创建/更新操作缺少新值记录")

    # 检查IP地址
    if log.action in ["login", "delete", "update"] and not log.ip_address:
        warnings.append("重要操作缺少IP地址记录")

    return {
        "is_compliant": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "score": 100 - (len(issues) * 20) - (len(warnings) * 5),
    }
