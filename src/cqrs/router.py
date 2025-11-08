from fastapi import APIRouter

"""
基本路由器 - cqrs
自动生成以解决导入问题
"""

router = APIRouter(prefix="/cqrs", tags=["cqrs"])


async def health_check():
    """健康检查端点"""
    return {"status": "ok", "module": "cqrs"}
