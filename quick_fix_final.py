#!/usr/bin/env python3
"""
快速修复最后的10个文件
"""

# 修复内容
fixes = {
    "src/utils/response.py": '''from typing import Any, Dict, List, Optional

"""
HTTP响应工具模块
"""

def success_response(data: Any = None, message: str = "Success") -> Dict[str, Any]:
    """创建成功响应"""
    return {
        "success": True,
        "message": message,
        "data": data
    }

def error_response(message: str, status_code: int = 400) -> Dict[str, Any]:
    """创建错误响应"""
    return {
        "success": False,
        "error": message,
        "status_code": status_code
    }

def paginated_response(
    items: List[Any],
    total: int,
    page: int = 1,
    page_size: int = 10
) -> Dict[str, Any]:
    """创建分页响应"""
    return {
        "items": items,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "has_next": page * page_size < total,
            "has_prev": page > 1
        }
    }
''',

    "src/utils/cached_operations.py": '''from typing import Any, Callable, TypeVar
import functools
import time

T = TypeVar('T')

def cached(ttl: int = 300, max_size: int = 128):
    """缓存装饰器"""
    cache = {}

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # 创建缓存键
            cache_key = str(args) + str(sorted(kwargs.items()))

            # 检查缓存
            if cache_key in cache:
                item, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl:
                    return item
                else:
                    del cache[cache_key]

            # 执行函数并缓存结果
            result = func(*args, **kwargs)

            # 添加到缓存
            if len(cache) >= max_size:
                # 删除最旧的项
                oldest_key = min(cache.keys(), key=lambda k: cache[k][1])
                del cache[oldest_key]

            cache[cache_key] = (result, time.time())
            return result

        return wrapper
    return decorator
''',

    "src/utils/predictions.py": '''from typing import Any, Dict, List
from datetime import datetime
from enum import Enum

class PredictionResult(Enum):
    """预测结果枚举"""
    HOME_WIN = "home_win"
    AWAY_WIN = "away_win"
    DRAW = "draw"

class Prediction:
    """预测模型基类"""

    def predict(self, match_data: Dict[str, Any]) -> PredictionResult:
        """预测比赛结果"""
        raise NotImplementedError

    def predict_proba(self, match_data: Dict[str, Any]) -> Dict[str, float]:
        """预测概率"""
        raise NotImplementedError

def create_simple_prediction(home_score: int, away_score: int) -> PredictionResult:
    """创建简单预测"""
    if home_score > away_score:
        return PredictionResult.HOME_WIN
    elif away_score > home_score:
        return PredictionResult.AWAY_WIN
    else:
        return PredictionResult.DRAW
''',

    "src/utils/cache_decorators.py": '''from typing import Any, Callable, Optional
import functools
import time
import hashlib
import json

def cache_key_from_args(*args, **kwargs) -> str:
    """从参数生成缓存键"""
    key_data = str(args) + str(sorted(kwargs.items()))
    return hashlib.md5(key_data.encode()).hexdigest()

def cache_result(ttl: int = 300, cache_key_func: Callable = None):
    """缓存结果装饰器"""
    cache = {}

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                cache_key = cache_key_from_args(*args, **kwargs)

            # 检查缓存
            if cache_key in cache:
                item, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl:
                    return item
                else:
                    del cache[cache_key]

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache[cache_key] = (result, time.time())
            return result

        return wrapper
    return decorator

def async_cache_result(ttl: int = 300, cache_key_func: Callable = None):
    """异步缓存结果装饰器"""
    cache = {}

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                cache_key = cache_key_from_args(*args, **kwargs)

            # 检查缓存
            if cache_key in cache:
                item, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl:
                    return item
                else:
                    del cache[cache_key]

            # 执行异步函数并缓存结果
            result = await func(*args, **kwargs)
            cache[cache_key] = (result, time.time())
            return result

        return wrapper
    return decorator
''',

    "src/utils/formatters.py": '''from typing import Any, Dict
from datetime import datetime

def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化日期时间"""
    return dt.strftime(format_str)

def format_currency(amount: float, currency: str = "USD") -> str:
    """格式化货币"""
    return f"{currency} {amount:,.2f}"

def format_percentage(value: float, decimals: int = 2) -> str:
    """格式化百分比"""
    return f"{value:.{decimals}%"

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"
''',
}

# 写入修复后的文件
for file_path, content in fixes.items():
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✓ 修复: {file_path}")

print("\n修复完成！")