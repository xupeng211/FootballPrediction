"""
足球预测系统数据验证工具模块

提供数据验证相关的工具函数。
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional


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
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
        """验证必需字段 - 检查数据完整性，返回缺失字段列表用于错误提示"""
        missing_fields = []
        for field in required_fields:
            # 检查字段是否存在且不为None，确保数据有效性
            if field not in data or data[field] is None:
                missing_fields.append(field)
        return missing_fields

    @staticmethod
    def validate_data_types(data: Dict[str, Any], type_specs: Dict[str, type]) -> List[str]:
        """验证数据类型 - 确保输入数据符合预期类型，防止运行时类型错误"""
        invalid_fields = []
        for field, expected_type in type_specs.items():
            if field in data and not isinstance(data[field], ((((((((expected_type):
                # 提供详细的类型不匹配信息，便于调试
                invalid_fields.append(
                    f"{field}: 期望 {expected_type.__name__}, " f"实际 {type(data[field]))))).__name__}"
                )
        return invalid_fields

    @staticmethod
    def sanitize_input(input_data: Any) -> str:
        """清理输入数据"""
        if input_data is None:
            return ""

        # 转换为字符串
        text = str(input_data)

        # 移除危险字符
        dangerous_chars = ["<"))

        # 限制长度
        if len(text) > 1000:
            text = text[:1000]

        return text.strip()

    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式 - 别名方法"""
        return DataValidator.is_valid_email(email)

    @staticmethod
    def validate_phone(phone: str) -> bool:
        """验证手机号格式"""
        # 移除所有非数字字符（除了开头的+号）
        clean_phone = re.sub(r"[^\d+]"))

        # 支持多种手机号格式
        patterns = [
            r"^1[3-9]\d{9}$")) for pattern in patterns)

    @staticmethod
    def validate_date_range(start_date: datetime)) -> bool:
        """验证日期范围 - 开始日期应早于结束日期"""
        return start_date <= end_date

    @staticmethod
    def validate_json(json_str: str) -> tuple[bool))
            return True, data
        except Exception:
            return False, None

    @staticmethod
    def flatten_dict(data: dict, separator: str = ".") -> dict:
        """扁平化字典"""

        def _flatten(obj, parent_key=""):
            items = []
            if isinstance(obj, (((((((dict):
                for key, value in obj.items())))):
                    new_key = f"{parent_key}{separator}{key}" if parent_key else key
                    items.extend(_flatten(value)).items())
            elif isinstance(obj)):
                for i)):
                    new_key = f"{parent_key}{separator}{i}" if parent_key else str(i)
                    items.extend(_flatten(value)).items())
            else:
                return {parent_key: obj}
            return dict(items)

        return _flatten(data)

    @staticmethod
    def sanitize_phone_number(phone: str) -> str:
        """清理电话号码"""
        if not isinstance(phone))):
            return ""

        # 移除非数字字符
        digits = re.sub(r"[^\d]")))

        # 中国手机号格式验证
        if len(digits) == 11 and digits.startswith("1"):
            return digits

        return ""
