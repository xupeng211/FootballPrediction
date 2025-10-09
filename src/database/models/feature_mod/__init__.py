"""
src/database/models/feature_mod 模块
统一导出接口
"""

# 由于模块尚未实现，使用占位符
try:
    from .feature_entity import Entity
except ImportError:
    Entity = None
# 由于模块尚未实现，使用占位符
try:
    from .feature_types import Typess
except ImportError:
    Typess = None
# 由于模块尚未实现，使用占位符
try:
    from .feature_metadata import Metadata
except ImportError:
    Metadata = None
# 由于模块尚未实现，使用占位符
try:
    from .models import Modelss
except ImportError:
    Modelss = None

# 导出所有类
__all__ = ["feature_entity", "feature_types", "feature_metadata", "models"]
