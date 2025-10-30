"""
数据验证工具类
DataValidator

提供各种数据验证方法。
"""

import re
from typing import Any, Optional


class DataValidator:
    """数据验证工具类"""

    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式"""
        if not isinstance(email, str):
            return False

        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_phone(phone: str) -> bool:
        """验证手机号格式"""
        if not isinstance(phone, str):
            return False

        # 移除所有非数字字符（除了开头的+号）
        clean_phone = re.sub(r"[^\d+]", "", phone)

        # 支持多种手机号格式
        patterns = [
            r"^1[3-9]\d{9}$",  # 中国手机号
            r"^\+\d{10,15}$"   # 国际号码
        ]

        return any(bool(re.match(pattern, clean_phone)) for pattern in patterns)

    @staticmethod
    def validate_url(url: str) -> bool:
        """验证URL格式"""
        if not isinstance(url, str):
            return False

        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(pattern, url))

    @staticmethod
    def validate_id_card(id_card: str) -> bool:
        """验证身份证号"""
        if not isinstance(id_card, str):
            return False

        # 18位身份证
        pattern18 = r'^[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$'
        # 15位身份证
        pattern15 = r'^[1-9]\d{5}\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}$'

        return bool(re.match(pattern18, id_card) or re.match(pattern15, id_card))

    @staticmethod
    def sanitize_input(input_data: Any) -> str:
        """清理输入数据"""
        if input_data is None:
            return ""

        # 转换为字符串
        text = str(input_data)

        # 移除危险字符
        dangerous_chars = ["<", ">", "&", "\"", "'"]
        for char in dangerous_chars:
            text = text.replace(char, "")

        # 限制长度
        if len(text) > 1000:
            text = text[:1000]

        return text.strip()

    @staticmethod
    def validate_username(username: str) -> bool:
        """验证用户名格式"""
        if not isinstance(username, str):
            return False

        # 用户名长度4-20位，只能包含字母、数字、下划线
        pattern = r'^[a-zA-Z0-9_]{4,20}$'
        return bool(re.match(pattern, username))

    @staticmethod
    def validate_password_strength(password: str) -> dict:
        """验证密码强度"""
        if not isinstance(password, str):
            return {"valid": False, "strength": 0, "issues": ["密码不能为空"]}

        issues = []
        strength = 0

        if len(password) < 8:
            issues.append("密码长度至少8位")
        else:
            strength += 1

        if not re.search(r'[a-z]', password):
            issues.append("密码必须包含小写字母")
        else:
            strength += 1

        if not re.search(r'[A-Z]', password):
            issues.append("密码必须包含大写字母")
        else:
            strength += 1

        if not re.search(r'\d', password):
            issues.append("密码必须包含数字")
        else:
            strength += 1

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            issues.append("密码必须包含特殊字符")
        else:
            strength += 1

        return {
            "valid": len(issues) == 0,
            "strength": strength,
            "issues": issues
        }

    @staticmethod
    def validate_positive_number(value: Any) -> bool:
        """验证正数"""
        try:
            num = float(value)
            return num > 0
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_required_fields(data: dict, required_fields: list) -> dict:
        """验证必填字段"""
        if not isinstance(data, dict):
            return {"valid": False, "missing": ["数据格式错误"]}

        missing = []
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                missing.append(field)

        return {
            "valid": len(missing) == 0,
            "missing": missing
        }