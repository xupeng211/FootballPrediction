"""
data.py
Data API 兼容层

此文件已被 data_api.py 替代。
This file has been replaced by data_api.py.

为了向后兼容，此文件重新导出 data_api 的路由器。
For backward compatibility, this file re-exports the router from data_api.
"""

import warnings

from .data_api import router

# 重新导出旧的名称以保持兼容性
data_router = router

__all__ = ["router", "data_router"]

warnings.warn(
    "直接从 data 导入已弃用。" "请从 api.data.endpoints 导入相关类。",
    DeprecationWarning,
    stacklevel=2,
)

# 从新模块导入所有内容
