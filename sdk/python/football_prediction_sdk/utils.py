#!/usr/bin/env python3
"""工具函数模块
Football Prediction SDK - 工具函数和装饰器.

Author: Claude Code
Version: 1.0.0
"""

import hashlib
import json
import random
import time
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

from .exceptions import RateLimitError, ValidationError


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_status_codes: list[int] | None = None
):
    """带退避策略的重试装饰器.

    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        exponential_base: 指数退避基数
        jitter: 是否添加随机抖动
        retryable_status_codes: 可重试的HTTP状态码列表

    Returns:
        装饰器函数

    Example:
        @retry_with_backoff(max_retries=5, base_delay=2.0)
        def make_api_request():
            return requests.get("https://api.example.com")
    """
    if retryable_status_codes is None:
        retryable_status_codes = [429, 500, 502, 503, 504]

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except requests.exceptions.RequestException as e:
                    last_exception = e

                    # 检查是否应该重试
                    if attempt == max_retries:
                        break

                    should_retry = False
                    if hasattr(e, 'response') and e.response is not None:
                        status_code = e.response.status_code
                        if status_code in retryable_status_codes:
                            should_retry = True

                        # 处理限流错误
                        if status_code == 429:
                            retry_after = extract_retry_after(e.response)
                            if retry_after:
                                delay = min(retry_after, max_delay)
                                time.sleep(delay)
                                continue

                    if not should_retry:
                        break

                    # 计算延迟时间
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )

                    # 添加随机抖动
                    if jitter:
                        jitter_amount = delay * 0.1 * random.random()
                        delay = delay + jitter_amount

                    time.sleep(delay)

            raise last_exception

        return wrapper
    return decorator


def extract_retry_after(response: requests.Response) -> int | None:
    """从响应中提取重试等待时间.

    Args:
        response: HTTP响应对象

    Returns:
        Optional[int]: 重试等待时间（秒），如果没有则返回None
    """
    # 1. 优先使用Retry-After头
    if "Retry-After" in response.headers:
        try:
            return int(response.headers["Retry-After"])
        except ValueError:
            pass

    # 2. 尝试解析Retry-After头中的HTTP日期
    if "Retry-After" in response.headers:
        try:
            retry_date = datetime.strptime(response.headers["Retry-After"], "%a, %d %b %Y %H:%M:%S GMT")
            now = datetime.utcnow()
            delta = retry_date - now
            if delta.total_seconds() > 0:
                return int(delta.total_seconds())
        except ValueError:
            pass

    # 3. 使用错误响应中的信息
    try:
        error_data = response.json()
        details = error_data.get("error", {}).get("details", {})
        if "retry_after" in details:
            return int(details["retry_after"])
    except (json.JSONDecodeError, KeyError):
        pass

    # 4. 使用X-RateLimit-Reset计算
    if "X-RateLimit-Reset" in response.headers:
        try:
            reset_time = int(response.headers["X-RateLimit-Reset"])
            current_time = int(time.time())
            return max(1, reset_time - current_time)
        except ValueError:
            pass

    return None


def validate_request_data(data: dict[str, Any], required_fields: list[str] = None) -> None:
    """验证请求数据.

    Args:
        data: 要验证的数据字典
        required_fields: 必填字段列表

    Raises:
        ValidationError: 验证失败时抛出
    """
    if not isinstance(data, dict):
        raise ValidationError("请求数据必须是字典格式")

    if required_fields:
        missing_fields = [field for field in required_fields
                         if field not in data or data[field] is None or data[field] == ""]
        if missing_fields:
            raise ValidationError(f"缺少必填字段: {', '.join(missing_fields)}")


def validate_date_string(date_string: str, format_name: str = "ISO 8601") -> datetime:
    """验证日期字符串格式.

    Args:
        date_string: 日期字符串
        format_name: 格式名称

    Returns:
        datetime: 解析后的日期时间对象

    Raises:
        ValidationError: 日期格式错误时抛出
    """
    if not date_string:
        raise ValidationError(f"{format_name}日期字符串不能为空")

    try:
        # 尝试ISO 8601格式
        if date_string.endswith('Z'):
            return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        else:
            return datetime.fromisoformat(date_string)
    except ValueError as e:
        raise ValidationError(f"{format_name}日期格式错误: {str(e)}")


def validate_probability(value: float, field_name: str = "probability") -> float:
    """验证概率值.

    Args:
        value: 概率值
        field_name: 字段名称

    Returns:
        float: 验证后的概率值

    Raises:
        ValidationError: 概率值无效时抛出
    """
    if not isinstance(value, (int, float)):
        raise ValidationError(f"{field_name}必须是数字类型")

    if not 0.0 <= value <= 1.0:
        raise ValidationError(f"{field_name}必须在0.0到1.0之间")

    return float(value)


def validate_confidence_score(value: float) -> float:
    """验证置信度分数.

    Args:
        value: 置信度分数

    Returns:
        float: 验证后的置信度分数

    Raises:
        ValidationError: 置信度分数无效时抛出
    """
    return validate_probability(value, "confidence_score")


def sanitize_string(value: str, max_length: int = None, allow_empty: bool = True) -> str:
    """清理和验证字符串.

    Args:
        value: 输入字符串
        max_length: 最大长度限制
        allow_empty: 是否允许空字符串

    Returns:
        str: 清理后的字符串

    Raises:
        ValidationError: 字符串无效时抛出
    """
    if not isinstance(value, str):
        raise ValidationError("输入必须是字符串类型")

    # 去除首尾空白字符
    cleaned = value.strip()

    if not allow_empty and not cleaned:
        raise ValidationError("字符串不能为空")

    if max_length and len(cleaned) > max_length:
        raise ValidationError(f"字符串长度不能超过{max_length}个字符")

    return cleaned


def generate_request_id() -> str:
    """生成唯一的请求ID.

    Returns:
        str: 请求ID
    """
    timestamp = datetime.now().isoformat()
    random_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
    return f"req_{timestamp}_{random_str}"


def build_url(base_url: str, path: str) -> str:
    """构建完整的URL.

    Args:
        base_url: 基础URL
        path: 路径

    Returns:
        str: 完整的URL
    """
    return urljoin(base_url.rstrip('/') + '/', path.lstrip('/'))


def parse_api_error(response: requests.Response) -> dict[str, Any]:
    """解析API错误响应.

    Args:
        response: HTTP响应对象

    Returns:
        Dict[str, Any]: 错误信息字典
    """
    try:
        error_data = response.json()
        return {
            "status_code": response.status_code,
            "error_code": error_data.get("error", {}).get("code"),
            "message": error_data.get("error", {}).get("message"),
            "details": error_data.get("error", {}).get("details", {}),
            "request_id": error_data.get("meta", {}).get("request_id"),
            "timestamp": error_data.get("meta", {}).get("timestamp")
        }
    except (json.JSONDecodeError, KeyError):
        return {
            "status_code": response.status_code,
            "message": response.text or "未知错误",
            "error_code": None,
            "details": {},
            "request_id": None,
            "timestamp": datetime.now().isoformat()
        }


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小.

    Args:
        size_bytes: 字节数

    Returns:
        str: 格式化的文件大小
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """遮蔽敏感数据.

    Args:
        data: 敏感数据字符串
        mask_char: 遮蔽字符
        visible_chars: 保留可见的字符数

    Returns:
        str: 遮蔽后的字符串
    """
    if len(data) <= visible_chars:
        return mask_char * len(data)

    visible_part = data[-visible_chars:] if len(data) > visible_chars else data
    masked_part = mask_char * (len(data) - visible_chars)
    return masked_part + visible_part


def calculate_hash(data: Any, algorithm: str = "sha256") -> str:
    """计算数据哈希值.

    Args:
        data: 要计算哈希的数据
        algorithm: 哈希算法

    Returns:
        str: 十六进制哈希值
    """
    if isinstance(data, (dict, list)):
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    else:
        data_str = str(data)

    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data_str.encode('utf-8'))
    return hash_obj.hexdigest()


def chunk_list(items: list[Any], chunk_size: int) -> list[list[Any]]:
    """将列表分割成块.

    Args:
        items: 要分割的列表
        chunk_size: 每块的大小

    Returns:
        List[List[Any]]: 分割后的列表块
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def merge_dicts(*dicts: dict[str, Any]) -> dict[str, Any]:
    """合并多个字典.

    Args:
        *dicts: 要合并的字典

    Returns:
        Dict[str, Any]: 合并后的字典
    """
    result = {}
    for d in dicts:
        if isinstance(d, dict):
            result.update(d)
    return result


def safe_get_nested_value(data: dict[str, Any], key_path: str, default: Any = None) -> Any:
    """安全获取嵌套字典的值.

    Args:
        data: 数据字典
        key_path: 键路径，用点号分隔
        default: 默认值

    Returns:
        Any: 获取到的值或默认值

    Example:
        data = {"user": {"profile": {"name": "John"}}}
        name = safe_get_nested_value(data, "user.profile.name", "Unknown")
    """
    keys = key_path.split('.')
    current = data

    try:
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    except (TypeError, KeyError):
        return default


def rate_limit_handler(response: requests.Response) -> RateLimitError | None:
    """处理限流响应.

    Args:
        response: HTTP响应对象

    Returns:
        Optional[RateLimitError]: 如果是限流错误则返回RateLimitError对象，否则返回None
    """
    if response.status_code != 429:
        return None

    try:
        error_data = response.json()
        error_info = error_data.get("error", {})
        details = error_info.get("details", {})

        return RateLimitError(
            message=error_info.get("message", "请求频率超限"),
            error_code=error_info.get("code"),
            details=details,
            response=response,
            retry_after=details.get("retry_after"),
            limit=details.get("limit"),
            window=details.get("window")
        )

    except (json.JSONDecodeError, KeyError):
        return RateLimitError(
            message="请求频率超限",
            response=response,
            retry_after=extract_retry_after(response)
        )


def is_valid_url(url: str) -> bool:
    """验证URL格式.

    Args:
        url: URL字符串

    Returns:
        bool: 是否为有效URL
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def convert_timestamp(timestamp: str | int | float | datetime) -> datetime:
    """转换时间戳为datetime对象.

    Args:
        timestamp: 时间戳（字符串、Unix时间戳或datetime对象）

    Returns:
        datetime: datetime对象
    """
    if isinstance(timestamp, datetime):
        return timestamp
    elif isinstance(timestamp, (int, float)):
        return datetime.fromtimestamp(timestamp)
    elif isinstance(timestamp, str):
        # 尝试ISO 8601格式
        if timestamp.endswith('Z'):
            return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            return datetime.fromisoformat(timestamp)
    else:
        raise ValueError(f"不支持的时间戳格式: {type(timestamp)}")


class Timer:
    """计时器上下文管理器."""

    def __init__(self, name: str = "Timer"):
        self.name = name
        self.start_time = None
        self.end_time = None
        self.elapsed = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.elapsed = self.end_time - self.start_time

    def __str__(self) -> str:
        if self.elapsed is not None:
            return f"{self.name}: {self.elapsed:.3f}s"
        return f"{self.name}: Not finished"

    @property
    def elapsed_ms(self) -> float:
        """获取经过的毫秒数."""
        return (self.elapsed or 0) * 1000


class RateLimiter:
    """简单的速率限制器."""

    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []

    def is_allowed(self) -> bool:
        """检查是否允许进行调用."""
        now = time.time()

        # 清理过期的调用记录
        self.calls = [call_time for call_time in self.calls
                     if now - call_time < self.time_window]

        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True

        return False

    def wait_time(self) -> float:
        """获取需要等待的时间."""
        if not self.calls:
            return 0

        oldest_call = min(self.calls)
        return max(0, self.time_window - (time.time() - oldest_call))

    def reset(self) -> None:
        """重置速率限制器."""
        self.calls.clear()
