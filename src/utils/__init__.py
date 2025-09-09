"""
AICultureKit 工具模块

提供系统中使用的工具函数和辅助类，包括：
- 文件处理工具
- 数据验证工具
- 时间处理工具
- 加密工具
- 字符串处理工具
"""

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class FileUtils:
    """文件处理工具类"""

    @staticmethod
    def ensure_dir(path: Union[str, Path]) -> Path:
        """确保目录存在"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def read_json(file_path: Union[str, Path]) -> Dict[str, Any]:
        """读取JSON文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise FileNotFoundError(f"无法读取JSON文件 {file_path}: {e}")

    @staticmethod
    def write_json(
        data: Dict[str, Any], file_path: Union[str, Path], ensure_dir: bool = True
    ) -> None:
        """写入JSON文件"""
        file_path = Path(file_path)
        if ensure_dir:
            file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def get_file_hash(file_path: Union[str, Path]) -> str:
        """获取文件MD5哈希值"""
        hash_md5 = hashlib.md5(usedforsecurity=False)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    @staticmethod
    def get_file_size(file_path: Union[str, Path]) -> int:
        """获取文件大小（字节）"""
        return os.path.getsize(file_path)


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


class TimeUtils:
    """时间处理工具类"""

    @staticmethod
    def now_utc() -> datetime:
        """获取当前UTC时间"""
        return datetime.now(timezone.utc)

    @staticmethod
    def timestamp_to_datetime(timestamp: float) -> datetime:
        """时间戳转datetime"""
        return datetime.fromtimestamp(timestamp, timezone.utc)

    @staticmethod
    def datetime_to_timestamp(dt: datetime) -> float:
        """datetime转时间戳"""
        return dt.timestamp()

    @staticmethod
    def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """格式化日期时间"""
        return dt.strftime(format_str)

    @staticmethod
    def parse_datetime(
        date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S"
    ) -> datetime:
        """解析日期时间字符串"""
        return datetime.strptime(date_str, format_str)


class CryptoUtils:
    """加密工具类"""

    @staticmethod
    def generate_uuid() -> str:
        """生成UUID"""
        return str(uuid.uuid4())

    @staticmethod
    def generate_short_id(length: int = 8) -> str:
        """生成短ID"""
        return str(uuid.uuid4()).replace("-", "")[:length]

    @staticmethod
    def hash_string(text: str, algorithm: str = "md5") -> str:
        """字符串哈希"""
        if algorithm == "md5":
            return hashlib.md5(text.encode("utf-8"), usedforsecurity=False).hexdigest()
        elif algorithm == "sha256":
            return hashlib.sha256(text.encode("utf-8")).hexdigest()
        else:
            raise ValueError(f"不支持的哈希算法: {algorithm}")

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> str:
        """密码哈希（简单实现，生产环境建议使用bcrypt）"""
        if salt is None:
            salt = CryptoUtils.generate_short_id()

        salted_password = f"{password}{salt}"
        return hashlib.sha256(salted_password.encode("utf-8")).hexdigest()


class StringUtils:
    """字符串处理工具类"""

    @staticmethod
    def truncate(text: str, length: int, suffix: str = "...") -> str:
        """截断字符串"""
        if len(text) <= length:
            return text
        return text[: length - len(suffix)] + suffix

    @staticmethod
    def slugify(text: str) -> str:
        """转换为URL友好的字符串"""
        # 简单实现，生产环境可能需要更复杂的处理
        text = re.sub(r"[^\w\s-]", "", text.lower())
        return re.sub(r"[-\s]+", "-", text).strip("-")

    @staticmethod
    def camel_to_snake(name: str) -> str:
        """驼峰命名转下划线命名"""
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    @staticmethod
    def snake_to_camel(name: str) -> str:
        """下划线命名转驼峰命名"""
        components = name.split("_")
        return components[0] + "".join(x.title() for x in components[1:])

    @staticmethod
    def clean_text(text: str) -> str:
        """清理文本（移除多余空白等）"""
        # 移除多余的空白字符
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def extract_numbers(text: str) -> List[float]:
        """从文本中提取数字"""
        pattern = r"-?\d+\.?\d*"
        numbers = re.findall(pattern, text)
        return [float(num) for num in numbers if num]


class DictUtils:
    """字典处理工具类"""

    @staticmethod
    def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并字典 - 递归合并嵌套字典，dict2的值会覆盖dict1中的同名键"""
        result = dict1.copy()
        for key, value in dict2.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                # 如果两边都是字典，则递归合并，保持嵌套结构
                result[key] = DictUtils.deep_merge(result[key], value)
            else:
                # 非字典值直接覆盖，确保最新值优先
                result[key] = value
        return result

    @staticmethod
    def flatten_dict(
        d: Dict[str, Any], parent_key: str = "", sep: str = "."
    ) -> Dict[str, Any]:
        """扁平化嵌套字典 - 将多层嵌套结构转为单层，便于配置管理和数据传输"""
        items: List[tuple] = []
        for k, v in d.items():
            # 构建新的键名，使用分隔符连接层级关系
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                # 递归处理嵌套字典，保持层级关系的可追溯性
                items.extend(DictUtils.flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    @staticmethod
    def filter_none_values(d: Dict[str, Any]) -> Dict[str, Any]:
        """过滤掉值为None的键值对"""
        return {k: v for k, v in d.items() if v is not None}


__all__ = [
    "FileUtils",
    "DataValidator",
    "TimeUtils",
    "CryptoUtils",
    "StringUtils",
    "DictUtils",
]
