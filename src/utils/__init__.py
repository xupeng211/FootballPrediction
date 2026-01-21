"""
FootballPrediction V7.0 通用工具模块
"""

from .database import DatabaseManager, database_connection, get_db_manager
from .logger import get_logger, setup_logger

# 新增：重试装饰器
try:
    from .retry import (
        retry_db_connection,
        retry_on_connection_error,
        retry_on_timeout,
        retry_redis_connection,
        with_retry,
    )

    _HAS_RETRY = True
except ImportError:
    _HAS_RETRY = False

# 保持现有工具类的兼容性
from pathlib import Path
import sys

# 将项目根目录添加到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入现有工具类
try:
    from src.utils.crypto_utils import CryptoUtils
    from src.utils.data_validator import OldDataValidator  # 重命名避免冲突
    from src.utils.dict_utils import DictUtils
    from src.utils.file_utils import FileUtils
    from src.utils.string_utils import StringUtils
    from src.utils.time_utils import TimeUtils

    _HAS_COMPATIBILITY_UTILS = True
except ImportError:
    _HAS_COMPATIBILITY_UTILS = False

    # 创建空的兼容性类
    class FileUtils:
        pass

    class OldDataValidator:
        pass

    class TimeUtils:
        pass

    class CryptoUtils:
        pass

    class StringUtils:
        pass

    class DictUtils:
        pass


__all__ = [
    "DatabaseManager",
    "database_connection",
    "get_db_manager",
    "get_logger",
    # 新模块
    "setup_logger",
]

# 如果重试装饰器可用，添加到导出列表
if _HAS_RETRY:
    __all__.extend(
        [
            "retry_db_connection",
            "retry_on_connection_error",
            "retry_on_timeout",
            "retry_redis_connection",
            "with_retry",
        ]
    )

# 如果兼容性工具类可用，添加到导出列表
if _HAS_COMPATIBILITY_UTILS:
    __all__.extend(
        [
            "CryptoUtils",
            "DictUtils",
            "FileUtils",
            "OldDataValidator",  # 使用新名称避免与 data.validators 冲突
            "StringUtils",
            "TimeUtils",
        ]
    )
