"""
Severity and Compliance Analysis

提供审计事件严重性评估和合规性分类功能。
Provides audit event severity assessment and compliance classification.
"""

from typing import Any, Dict, Optional
from datetime import datetime

from src.core.logging import get_logger
from .models import AuditSeverity


class SeverityAnalyzer:
    """
    严重性分析器

    负责评估审计事件的严重性和合规性分类。
    """

    def __init__(self):
        """初始化严重性分析器"""
        self.logger = get_logger(__name__)

        # 合规类别映射
        self.compliance_mapping = {
            "users": "user_management",
            "permissions": "access_control",
            "tokens": "authentication",
            "payment": "financial",
            "personal_data": "privacy",
        }


def _determine_severity(
    self,
    action: str,
    table_name: Optional[str] = None,
    error: Optional[str] = None,
) -> str:
    """
    确定严重性级别 / Determine Severity Level

    Args:
        action: 动作 / Action
        table_name: 表名 / Table name
        error: 错误信息 / Error message

    Returns:
        严重性级别 / Severity level
    """
    if error:
        return "critical"

    # 基于动作确定
    high_severity_actions = ["delete", "export", "import", "admin"]
    if action in high_severity_actions:
        return "high"

    # 基于表名确定
    if table_name:
        high_severity_tables = ["users", "permissions", "tokens"]
        if table_name in high_severity_tables:
            return "high"

    return "medium"


def _determine_compliance_category(
    self,
    table_name: Optional[str] = None,
    action: Optional[str] = None,
) -> Optional[str]:
    """
    确定合规类别 / Determine Compliance Category

    Args:
        table_name: 表名 / Table name
        action: 动作 / Action

    Returns:
        合规类别 / Compliance category
    """
    if table_name and table_name in self.compliance_mapping:
        return self.compliance_mapping[table_name]  # type: ignore

    if action and action in ["login", "logout", "access"]:
        return "authentication"

    return None
