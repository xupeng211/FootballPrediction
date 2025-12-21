"""
FootballPrediction V7.0 通用工具模块
"""

from .logger import setup_logger, get_logger
from .database import DatabaseManager, get_db_manager, database_connection

# 保持现有工具类的兼容性
import sys
from pathlib import Path

# 将项目根目录添加到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入现有工具类
try:
    from src.utils.file_utils import FileUtils
    from src.utils.data_validator import DataValidator
    from src.utils.time_utils import TimeUtils
    from src.utils.crypto_utils import CryptoUtils
    from src.utils.string_utils import StringUtils
    from src.utils.dict_utils import DictUtils

    _HAS_COMPATIBILITY_UTILS = True
except ImportError:
    _HAS_COMPATIBILITY_UTILS = False
    # 创建空的兼容性类
    class FileUtils: pass
    class DataValidator: pass
    class TimeUtils: pass
    class CryptoUtils: pass
    class StringUtils: pass
    class DictUtils: pass

__all__ = [
    # 新模块
    'setup_logger',
    'get_logger',
    'DatabaseManager',
    'get_db_manager',
    'database_connection',
]

# 如果兼容性工具类可用，添加到导出列表
if _HAS_COMPATIBILITY_UTILS:
    __all__.extend([
        'FileUtils',
        'DataValidator',
        'TimeUtils',
        'CryptoUtils',
        'StringUtils',
        'DictUtils',
    ])
