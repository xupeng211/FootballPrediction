"""
src/data/collectors/streaming 模块
统一导出接口
"""

# 由于模块尚未实现，使用占位符
try:
    from .kafka_collector import Collector
except ImportError:
    Collector = None
# 由于模块尚未实现，使用占位符
try:
    from .websocket_collector import Collector
except ImportError:
    Collector = None
# 由于模块尚未实现，使用占位符
try:
    from .processor import Processor
except ImportError:
    Processor = None
# 由于模块尚未实现，使用占位符
try:
    from .manager import Manager
except ImportError:
    Manager = None

# 导出所有类
__all__ = ["kafka_collector", "websocket_collector", "processor", "manager"]
