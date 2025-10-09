"""
src/services/processing/processors/features 模块
统一导出接口
"""

# 由于模块尚未实现，使用占位符
try:
    from .calculator import Calculator
except ImportError:
    Calculator = None
# 由于模块尚未实现，使用占位符
try:
    from .aggregator import Aggregator
except ImportError:
    Aggregator = None
# 由于模块尚未实现，使用占位符
try:
    from .validator import Validator
except ImportError:
    Validator = None
# 由于模块尚未实现，使用占位符
try:
    from .processor import Processor
except ImportError:
    Processor = None

# 导出所有类
__all__ = ["calculator", "aggregator", "validator", "processor"]
