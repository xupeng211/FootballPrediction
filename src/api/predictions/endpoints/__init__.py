"""
预测API端点模块
Prediction API Endpoints Module

导出所有预测相关的API端点。
"""


from .admin import router as admin_router
from .batch import router as batch_router
from .single import router as single_router
from .stats import router as stats_router
from .streaming import router as streaming_router

# 将所有路由器组合成一个列表
routers = [
    single_router,
    batch_router,
    stats_router,
    streaming_router,
    admin_router,
]

__all__ = ["routers"]
