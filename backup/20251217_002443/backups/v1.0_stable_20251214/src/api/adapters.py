"""adapters 主模块.

外部API适配器接口
Provides external API adapter interfaces.
"""

# 从子模块导入路由器
from .adapters.router import router

# 导出所有公共接口
__all__ = ["router"]
