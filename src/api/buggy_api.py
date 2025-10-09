
router = APIRouter()


# 1. ✅ 修复后的 FastAPI Query 参数
@router.get("/fixed_query")
async def fixed_query(
    limit: int = Query(default=10, ge=1, le=100, description="返回记录数量限制"),
):
    """
    修复后的 Query 参数：
    1. 添加了明确的类型注解 (int)
    2. 使用 default= 而不是直接传值
    3. 添加了验证 (ge=1, le=100)
    4. 添加了描述信息
    """
    return {"limit": limit, "type": type(limit).__name__}


# ✅ 修复后的版本 - 原来的 buggy_query
@router.get("/buggy_query")
async def buggy_query(
    limit: int = Query(default=10, ge=1, le=100, description="返回记录数量限制"),
):
    """
    修复后的 Query 参数：
    1. 添加了明确的类型注解 (int)
    2. 使用 default= 而不是直接传值
    3. 添加了验证范围 (ge=1, le=100)
    4. 添加了描述信息
    """
    # 确保返回的 limit 是 int 类型，避免 TypeError
    return {"limit": int(limit), "type": type(limit).__name__}




class SomeAsyncService:
    async def get_status(self):
        return "real_status"


service = SomeAsyncService()


@router.get("/buggy_async")
async def buggy_async():
    status = await service.get_status()
    return {"status": status}
