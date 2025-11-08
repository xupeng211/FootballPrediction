"""
输入验证和安全检查工具
Input Validation and Security Check Tools

提供企业级的输入验证、SQL注入防护、XSS防护等功能。
"""

import html
import re
from typing import Any

from fastapi import HTTPException, status
from pydantic import BaseModel, Field, field_validator

# ============================================================================
# 基础验证器
# ============================================================================


class BaseValidator:
    """基础验证器"""

    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """清理字符串输入"""
        if not isinstance(value, str):
            raise ValueError("输入必须是字符串")

        # 限制长度
        if len(value) > max_length:
            value = value[:max_length]

        # HTML转义防止XSS
        value = html.escape(value)

        # 移除潜在的危险字符
        dangerous_chars = ["<", ">", "&", '"', "'", "\x00", "\n", "\r", "\t"]
        for char in dangerous_chars:
            value = value.replace(char, "")

        return value.strip()

    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式"""
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(email_pattern, email) is not None

    @staticmethod
    def validate_username(username: str) -> bool:
        """验证用户名格式"""
        # 用户名只能包含字母、数字、下划线，3-50字符
        username_pattern = r"^[a-zA-Z0-9_]{3,50}$"
        return re.match(username_pattern, username) is not None

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, list[str]]:
        """验证密码强度"""
        errors = []

        if len(password) < 8:
            errors.append("密码长度至少8位")

        if len(password) > 128:
            errors.append("密码长度不能超过128位")

        if not re.search(r"[A-Z]", password):
            errors.append("密码必须包含至少一个大写字母")

        if not re.search(r"[a-z]", password):
            errors.append("密码必须包含至少一个小写字母")

        if not re.search(r"\d", password):
            errors.append("密码必须包含至少一个数字")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("密码必须包含至少一个特殊字符")

        # 检查常见弱密码
        weak_passwords = [
            "password",
            "123456",
            "123456789",
            "qwerty",
            "abc123",
            "password123",
            "admin",
            "root",
            "user",
            "test",
        ]
        if password.lower() in weak_passwords:
            errors.append("密码过于简单，请使用更复杂的密码")

        return len(errors) == 0, errors

    @staticmethod
    def validate_numeric_range(
        value: int | float,
        min_val: float | None = None,
        max_val: float | None = None,
    ) -> bool:
        """验证数值范围"""
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            return False

        if min_val is not None and num_value < min_val:
            return False

        if max_val is not None and num_value > max_val:
            return False

        return True

    @staticmethod
    def validate_date_range(
        date_str: str, min_year: int = 1900, max_year: int = 2100
    ) -> bool:
        """验证日期范围"""
        date_pattern = r"^\d{4}-\d{2}-\d{2}$"
        if not re.match(date_pattern, date_str):
            return False

        try:
            year, month, day = map(int, date_str.split("-"))
            return min_year <= year <= max_year
        except ValueError:
            return False


# ============================================================================
# SQL注入防护
# ============================================================================


class SQLInjectionProtector:
    """SQL注入防护器"""

    # 危险SQL关键字
    DANGEROUS_SQL_KEYWORDS = [
        "DROP",
        "DELETE",
        "INSERT",
        "UPDATE",
        "ALTER",
        "CREATE",
        "TRUNCATE",
        "EXEC",
        "EXECUTE",
        "UNION",
        "SELECT",
        "FROM",
        "WHERE",
        "JOIN",
        "INNER",
        "OUTER",
        "LEFT",
        "RIGHT",
        "HAVING",
        "GROUP",
        "ORDER",
        "LIMIT",
        "OFFSET",
    ]

    # SQL注入特征模式
    SQL_INJECTION_PATTERNS = [
        r"(\%27)|(\')|(\-\-)|(\%23)|(#)",  # SQL注释
        r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))",  # 等号后跟注释
        r"\w*((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))",  # OR
        r"((\%27)|(\'))union",  # UNION注入
        r"exec(\s|\+)+(s|x)p\w+",  # EXECUTE
        r"UNION.*SELECT",  # UNION SELECT
        r"INSERT.*INTO",  # INSERT INTO
        r"DELETE.*FROM",  # DELETE FROM
        r"UPDATE.*SET",  # UPDATE SET
        r"DROP.*TABLE",  # DROP TABLE
    ]

    @classmethod
    def is_sql_injection(cls, input_str: str) -> tuple[bool, str]:
        """检测SQL注入"""
        if not isinstance(input_str, str):
            return False, ""

        input_upper = input_str.upper()

        # 检查危险关键字
        for keyword in cls.DANGEROUS_SQL_KEYWORDS:
            if keyword in input_upper:
                return True, f"检测到危险SQL关键字: {keyword}"

        # 检查SQL注入模式
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE):
                return True, f"检测到SQL注入模式: {pattern}"

        return False, ""

    @classmethod
    def sanitize_sql_input(cls, input_str: str) -> str:
        """清理SQL输入"""
        if not isinstance(input_str, str):
            return ""

        # 移除危险字符
        dangerous_chars = ["'", '"', ";", "--", "/*", "*/", "xp_", "sp_"]
        sanitized = input_str

        for char in dangerous_chars:
            sanitized = sanitized.replace(char, "")

        return sanitized.strip()


# ============================================================================
# XSS防护
# ============================================================================


class XSSProtector:
    """XSS防护器"""

    # XSS攻击模式
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",  # Script标签
        r"javascript:",  # JavaScript协议
        r"on\w+\s*=",  # 事件处理器
        r"<iframe[^>]*>",  # iframe标签
        r"<object[^>]*>",  # object标签
        r"<embed[^>]*>",  # embed标签
        r"<link[^>]*>",  # link标签
        r"<meta[^>]*>",  # meta标签
        r"expression\s*\(",  # CSS表达式
        r"@import",  # CSS导入
        r"<style[^>]*>.*?</style>",  # Style标签
    ]

    @classmethod
    def is_xss_attack(cls, input_str: str) -> tuple[bool, str]:
        """检测XSS攻击"""
        if not isinstance(input_str, str):
            return False, ""

        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE | re.DOTALL):
                return True, f"检测到XSS攻击模式: {pattern}"

        return False, ""

    @classmethod
    def sanitize_html_input(cls, input_str: str) -> str:
        """清理HTML输入"""
        if not isinstance(input_str, str):
            return ""

        # HTML转义
        sanitized = html.escape(input_str)

        # 移除残留的危险标签
        for pattern in cls.XSS_PATTERNS:
            sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE | re.DOTALL)

        return sanitized


# ============================================================================
# 文件上传安全检查
# ============================================================================


class FileUploadValidator:
    """文件上传验证器"""

    # 允许的文件类型
    ALLOWED_EXTENSIONS = {
        "image": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
        "document": [".pdf", ".doc", ".docx", ".txt"],
        "data": [".csv", ".json", ".xml"],
    }

    # 危险文件扩展名
    DANGEROUS_EXTENSIONS = [
        ".exe",
        ".bat",
        ".cmd",
        ".com",
        ".pif",
        ".scr",
        ".vbs",
        ".js",
        ".jar",
        ".php",
        ".asp",
        ".aspx",
        ".jsp",
        ".sh",
        ".ps1",
        ".py",
        ".rb",
        ".pl",
    ]

    # 最大文件大小（字节）
    MAX_FILE_SIZES = {
        "image": 10 * 1024 * 1024,  # 10MB
        "document": 50 * 1024 * 1024,  # 50MB
        "data": 100 * 1024 * 1024,  # 100MB
    }

    @classmethod
    def validate_file_extension(
        cls, filename: str, file_type: str = "image"
    ) -> tuple[bool, str]:
        """验证文件扩展名"""
        if not isinstance(filename, str):
            return False, "文件名必须是字符串"

        # 检查是否为危险文件
        file_ext = cls.get_file_extension(filename).lower()
        if file_ext in cls.DANGEROUS_EXTENSIONS:
            return False, f"不允许上传 {file_ext} 文件"

        # 检查是否为允许的类型
        allowed_exts = cls.ALLOWED_EXTENSIONS.get(file_type, [])
        if file_ext not in allowed_exts:
            return False, f"不支持的文件类型: {file_ext}"

        return True, ""

    @classmethod
    def get_file_extension(cls, filename: str) -> str:
        """获取文件扩展名"""
        return "." + filename.split(".")[-1] if "." in filename else ""

    @classmethod
    def validate_file_size(
        cls, file_size: int, file_type: str = "image"
    ) -> tuple[bool, str]:
        """验证文件大小"""
        max_size = cls.MAX_FILE_SIZES.get(file_type, 10 * 1024 * 1024)

        if file_size > max_size:
            return False, f"文件大小超过限制 ({max_size // (1024 * 1024)}MB)"

        return True, ""

    @classmethod
    def validate_filename(cls, filename: str) -> tuple[bool, str]:
        """验证文件名"""
        if not isinstance(filename, str):
            return False, "文件名必须是字符串"

        # 检查文件名长度
        if len(filename) > 255:
            return False, "文件名过长"

        # 检查危险字符
        dangerous_chars = ["..", "/", "\\", ":", "*", "?", '"', "<", ">", "|"]
        for char in dangerous_chars:
            if char in filename:
                return False, f"文件名包含非法字符: {char}"

        return True, ""


# ============================================================================
# 综合验证模型
# ============================================================================


class SecureUserInput(BaseModel):
    """安全的用户输入模型"""

    text_input: str = Field(..., min_length=1, max_length=1000, description="文本输入")
    email: str | None = Field(None, description="邮箱地址")
    number_input: float | None = Field(None, ge=0, le=1000000, description="数字输入")

    @field_validator("text_input")
    @classmethod
    def sanitize_text_input(cls, v):
        """清理文本输入"""
        validator = BaseValidator()
        return validator.sanitize_string(v, max_length=1000)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v):
        """验证邮箱格式"""
        if v is not None:
            validator = BaseValidator()
            if not validator.validate_email(v):
                raise ValueError("邮箱格式无效")
        return v


class SecureFileUpload(BaseModel):
    """安全的文件上传模型"""

    filename: str = Field(..., description="文件名")
    file_size: int = Field(..., ge=0, description="文件大小（字节）")
    file_type: str = Field(default="image", description="文件类型")

    @field_validator("filename")
    @classmethod
    def validate_filename_safe(cls, v):
        """验证文件名安全性"""
        is_valid, error_msg = FileUploadValidator.validate_filename(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v

    @field_validator("file_type")
    @classmethod
    def validate_file_type(cls, v):
        """验证文件类型"""
        if v not in FileUploadValidator.ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {v}")
        return v


# ============================================================================
# 综合安全检查函数
# ============================================================================


def comprehensive_security_check(
    input_data: dict[str, Any], context: str = "general"
) -> dict[str, Any]:
    """综合安全检查"""
    issues = []
    sanitized_data = {}

    for key, value in input_data.items():
        if isinstance(value, str):
            # SQL注入检查
            is_sql_injection, sql_msg = SQLInjectionProtector.is_sql_injection(value)
            if is_sql_injection:
                issues.append(f"字段 '{key}': {sql_msg}")

            # XSS检查
            is_xss, xss_msg = XSSProtector.is_xss_attack(value)
            if is_xss:
                issues.append(f"字段 '{key}': {xss_msg}")

            # 清理输入
            sanitized_value = XSSProtector.sanitize_html_input(value)
            sanitized_value = SQLInjectionProtector.sanitize_sql_input(sanitized_value)
            sanitized_data[key] = sanitized_value

        else:
            sanitized_data[key] = value

    return {
        "is_safe": len(issues) == 0,
        "issues": issues,
        "sanitized_data": sanitized_data,
        "context": context,
    }


def validate_api_input(input_data: Any, validator_class: type) -> Any:
    """验证API输入"""
    try:
        if isinstance(input_data, dict):
            return validator_class(**input_data)
        elif isinstance(input_data, validator_class):
            return input_data
        else:
            raise ValueError("输入数据格式不正确")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"输入验证失败: {str(e)}"
        ) from e
