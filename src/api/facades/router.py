"""
基本路由器 - facades
自动生成以解决导入问题
"""

from fastapi import APIRouter

router = APIRouter(
    prefix="/facades",
    tags=["facades"]
)

@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok", "module": "facades"}
