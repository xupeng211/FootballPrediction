"""
足球预测系统数据验证工具模块

提供数据验证相关的工具函数。
"""

import re
from typing import Any, Dict, List


class DataValidator:
    """数据验证工具类"""

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """验证邮箱格式"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """验证URL格式"""
        pattern = (
            r"^https?://"  # http:// 或 https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+"
            r"[A-Z]{2,6}\.?|"  # 域名
            r"localhost|"  # localhost
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP地址
            r"(?::\d+)?"  # 可选端口
            r"(?:/?|[/?]\S+)$"  # 路径
        )
        return bool(re.match(pattern, url, re.IGNORECASE))

    @staticmethod
    def validate_required_fields(
        data: Dict[str, Any], required_fields: List[str]
    ) -> List[str]:
        """验证必需字段 - 检查数据完整性，返回缺失字段列表用于错误提示"""
        missing_fields = []
        for field in required_fields:
            # 检查字段是否存在且不为None，确保数据有效性
            if field not in data or data[field] is None:
                missing_fields.append(field)
        return missing_fields

    @staticmethod
    def validate_data_types(
        data: Dict[str, Any], type_specs: Dict[str, type]
    ) -> List[str]:
        """验证数据类型 - 确保输入数据符合预期类型，防止运行时类型错误"""
        invalid_fields = []
        for field, expected_type in type_specs.items():
            if field in data and not isinstance(data[field], expected_type):
                # 提供详细的类型不匹配信息，便于调试
                invalid_fields.append(
                    f"{field}: 期望 {expected_type.__name__}, "
                    f"实际 {type(data[field]).__name__}"
                )
        return invalid_fields
