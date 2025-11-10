"""
数据验证工具类
DataValidator

提供各种数据验证方法.
"""

import re
from typing import Any


class DataValidator:
    """类文档字符串"""

    pass  # 添加pass语句
    """数据验证工具类"""

    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式"""
        if not isinstance(email, str):
            return False

        # 基本格式验证
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, email):
            return False

        # 额外验证：不允许连续的点号
        if ".." in email:
            return False

        # 额外验证：域名不能以点号开始或结束
        domain = email.split("@")[1]
        if domain.startswith(".") or domain.endswith("."):
            return False

        # 额外验证：不能以点号或连字符开始或结束
        if domain.startswith("-") or domain.endswith("-"):
            return False

        return True

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
            r"^\+\d{10,15}$",  # 国际号码
        ]

        return any(bool(re.match(pattern, clean_phone)) for pattern in patterns)

    @staticmethod
    def validate_url(url: str) -> bool:
        """验证URL格式"""
        if not isinstance(url, str):
            return False

        pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        return bool(re.match(pattern, url))

    @staticmethod
    def validate_id_card(id_card: str) -> bool:
        """验证身份证号"""
        if not isinstance(id_card, str):
            return False

        # 18位身份证
        pattern18 = (
            r"^[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$"
        )
        # 15位身份证
        pattern15 = r"^[1-9]\d{5}\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}$"

        # 基本格式验证
        if not (re.match(pattern18, id_card) or re.match(pattern15, id_card)):
            return False

        # 18位身份证需要验证校验码
        if len(id_card) == 18:
            return DataValidator._validate_id_card_checksum(id_card)

        # 15位身份证直接返回True（格式已验证）
        return True

    @staticmethod
    def _validate_id_card_checksum(id_card: str) -> bool:
        """验证18位身份证校验码"""
        # 权重因子
        weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        # 校验码对应表
        check_codes = ["1", "0", "x", "9", "8", "7", "6", "5", "4", "3", "2"]

        total = 0
        for i in range(17):
            total += int(id_card[i]) * weights[i]

        # 计算校验码
        check_code = check_codes[total % 11]

        # 比较校验码（不区分大小写）
        return id_card[17].upper() == check_code

    @staticmethod
    def sanitize_input(input_data: Any) -> str:
        """清理输入数据"""
        if input_data is None:
            return ""

        # 转换为字符串
        text = str(input_data)

        # 移除危险字符
        dangerous_chars = ["<", ">", "&", '"', "'", """, """]
        for char in dangerous_chars:
            text = text.replace(char, "")

        # 移除明确的HTML标签和JavaScript模式
        # 使用更精确的模式避免误伤普通文本
        import re

        # 移除HTML标签
        text = re.sub(r"<[^>]+>", "", text)

        # 移除JavaScript协议
        text = re.sub(r"javascript:", "", text, flags=re.IGNORECASE)

        # 移除HTML事件处理器属性
        text = re.sub(
            r'\s+on\w+\s*=\s*["\'][^"\']*["\']', "", text, flags=re.IGNORECASE
        )

        # 限制长度
        if len(text) > 1000:
            text = text[:1000]

        return text.strip()

    @staticmethod
    def validate_username(username: str) -> bool:
        """验证用户名格式"""
        if not isinstance(username, str):
            return False

        # 用户名长度4-20位,只能包含字母,数字,下划线
        pattern = r"^[a-zA-Z0-9_]{4,20}$"
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

        if not re.search(r"[a-z]", password):
            issues.append("密码必须包含小写字母")
        else:
            strength += 1

        if not re.search(r"[A-Z]", password):
            issues.append("密码必须包含大写字母")
        else:
            strength += 1

        if not re.search(r"\d", password):
            issues.append("密码必须包含数字")
        else:
            strength += 1

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            issues.append("密码必须包含特殊字符")
        else:
            strength += 1

        return {"valid": len(issues) == 0, "strength": strength, "issues": issues}

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

        return {"valid": len(missing) == 0, "missing": missing}


# 便捷函数，用于直接导入使用
def validate_email(email: str) -> bool:
    """邮箱验证便捷函数"""
    return DataValidator.validate_email(email)


def validate_password_strength(password: str) -> dict:
    """密码强度验证便捷函数"""
    result = DataValidator.validate_password_strength(password)
    if not result["valid"]:
        raise ValueError("；".join(result["issues"]))
