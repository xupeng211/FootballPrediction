"""
src/collectors/odds/basic 模块
统一导出接口
"""

# 由于模块尚未实现，使用占位符
try:
    from .collector import Collector
except ImportError:
    Collector = None
# 由于模块尚未实现，使用占位符
try:
    from .parser import Parser
except ImportError:
    Parser = None
# 由于模块尚未实现，使用占位符
try:
    from .validator import Validator
except ImportError:
    Validator = None
# 由于模块尚未实现，使用占位符
try:
    from .storage import Storage
except ImportError:
    Storage = None

# 导出所有类
__all__ = ["collector", "parser", "validator", "storage"]
