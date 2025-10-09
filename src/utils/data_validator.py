



    """数据验证工具类"""

        """验证邮箱格式"""

        """验证URL格式"""

        """验证必需字段 - 检查数据完整性,返回缺失字段列表用于错误提示"""

        """验证数据类型 - 确保输入数据符合预期类型,防止运行时类型错误"""

        """清理输入数据"""





        """验证邮箱格式 - 别名方法"""

        """验证手机号格式"""



        """验证日期范围 - 开始日期应早于结束日期"""



import re

足球预测系统数据验证工具模块
提供数据验证相关的工具函数.
class DataValidator:
    @staticmethod
    def is_valid_email(email: str) -> bool:
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))
    @staticmethod
    def is_valid_url(url: str) -> bool:
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
        missing_fields = []
        for field in required_fields:
            # 检查字段是否存在且不为None,确保数据有效性
            if field not in data or data[field] is None:
                missing_fields.append(field)
        return missing_fields
    @staticmethod
    def validate_data_types(
        data: Dict[str, Any], type_specs: Dict[str, type]
    ) -> List[str]:
        invalid_fields = []
        for field, expected_type in type_specs.items():
            if field in data and not isinstance(data[field], expected_type):
                # 提供详细的类型不匹配信息,便于调试
                invalid_fields.append(
                    f"{field}: 期望 {expected_type.__name__}, "
                    f"实际 {type(data[field]).__name__}"
                )
        return invalid_fields
    @staticmethod
    def sanitize_input(input_data: Any) -> str:
        if input_data is None:
            return ""
        # 转换为字符串
        text = str(input_data)
        # 移除危险字符
        dangerous_chars = ["<", ">", '"', "'", "&", "\x00", "\r", "\n"]
        for char in dangerous_chars:
            text = text.replace(char, "")
        # 限制长度
        if len(text) > 1000:
            text = text[:1000]
        return text.strip()
    @staticmethod
    def validate_email(email: str) -> bool:
        return DataValidator.is_valid_email(email)
    @staticmethod
    def validate_phone(phone: str) -> bool:
        # 移除所有非数字字符(除了开头的+号)
        clean_phone = re.sub(r"[^\d+]", "", phone)
        # 支持多种手机号格式
        patterns = [
            r"^1[3-9]\d{9}$",  # 中国手机号(11位)
            r"^\+\d{8,15}$",  # 国际格式(+号开头)
            r"^\d{8,15}$",  # 纯数字格式(8-15位)
        ]
        return any(bool(re.match(pattern, clean_phone)) for pattern in patterns)
    @staticmethod
    def validate_date_range(start_date: datetime, end_date: datetime) -> bool:
        return start_date <= end_date