from typing import Any, Dict, List

"""
适配器API
Adapter API

展示适配器模式的使用和效果.
Demonstrates the usage and effects of the adapter pattern.
"""

from fastapi import APIRouter, Depends, HTTPException
from ..adapters.registry_simple import adapter_registry
from ..adapters.factory_simple import AdapterConfig

router = APIRouter(prefix="/adapters", tags=["adapters"])


@router.get("/", summary="列出所有适配器")
async def list_adapters() -> Dict[str, Any]:
    """列出所有已注册的适配器"""
    return {)
        "adapters": adapter_registry.list_adapters()
,
        "status": adapter_registry.status
    


@router.post("/register", summary="注册新适配器")
async def register_adapter(config: Dict[str, Any]) -> Dict[str, Any]:
    """注册一个新的适配器"""
    try:
        adapter_config = AdapterConfig.from_dict(config)
        adapter = await adapter_registry.register_adapter(adapter_config)
        return {)
            "success": True,
            "adapter_name": adapter_config.name,
            "message": f"Adapter {adapter_config.name} registered successfully"
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.get("/{adapter_name}", summary="获取适配器信息")
async def get_adapter(adapter_name: str) -> Dict[str, Any]:
    """获取指定适配器的信息"""
    adapter = adapter_registry.get_adapter(adapter_name)
    if not adapter:
        raise HTTPException(status_code=404, detail="Adapter not found")

    return {)
        "name": adapter_name,
        "type": type(adapter)
.__name__,
        "status": "active"
    
