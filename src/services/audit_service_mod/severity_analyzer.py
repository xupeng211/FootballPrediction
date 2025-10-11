"""
Severity and Compliance Analysis

提供严重性和合规性分析功能。
Provides severity and compliance analysis functionality.
"""

from typing import Any, Dict, Optional

from src.core.logging import get_logger


class SeverityAnalyzer:
    """
    严重性分析器

    提供操作严重性评估和合规性分析。
    Provides operation severity assessment and compliance analysis.
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
        确定严重性级别

        Args:
            action: 动作
            table_name: 表名
            error: 错误信息

        Returns:
            严重性级别
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
        确定合规类别

        Args:
            table_name: 表名
            action: 动作

        Returns:
            合规类别
        """
        if table_name and table_name in self.compliance_mapping:
            return self.compliance_mapping[table_name]  # type: ignore[no-any-return]

        if action and action in ["login", "logout", "access"]:
            return "authentication"

        return None
