"""
足球预测系统基础服务模块

注意：此文件已被重构为使用统一的基础服务类。
为了向后兼容性，这里保留原有的导入。

推荐使用：from src.services.base_unified import BaseService, SimpleService
"""

# 为了向后兼容，从新的统一基类导入
from .base_unified import BaseService, SimpleService
from .base_unified import BaseService as AbstractBaseService  # 兼容原有的抽象基类名称

# 保持向后兼容的导出
__all__ = ["BaseService", "AbstractBaseService", "SimpleService"]

# 添加弃用警告
import warnings

warnings.warn(
    "src.services.base 已被弃用，请使用 src.services.base_unified 中的统一基础服务类",
    DeprecationWarning,
    stacklevel=2,
)
