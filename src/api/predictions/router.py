"""
预测API路由器
Predictions API Router

提供预测相关的API路由。
"""

from fastapi import APIRouter

# 创建一个空的路由器，避免导入错误
router = APIRouter()


# 添加一个简单的健康检查路由
@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "predictions"}
