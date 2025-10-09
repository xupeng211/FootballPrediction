"""
src/monitoring/alerts/models/escalation_mod 模块
统一导出接口
"""

# 由于模块尚未实现，使用占位符
try:
    from .escalation_rules import Ruless
except ImportError:
    Ruless = None
# 由于模块尚未实现，使用占位符
try:
    from .escalation_engine import Engine
except ImportError:
    Engine = None
# 由于模块尚未实现，使用占位符
try:
    from .notification import Notification
except ImportError:
    Notification = None
# 由于模块尚未实现，使用占位符
try:
    from .escalation import Escalation
except ImportError:
    Escalation = None

# 导出所有类
__all__ = ["escalation_rules", "escalation_engine", "notification", "escalation"]
