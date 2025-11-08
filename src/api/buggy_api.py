from fastapi import APIRouter, Query

router = APIRouter()


async def fixed_query(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,  # TODO: 将魔法数字 100 提取为常量
        description="返回记录数量限制",  # TODO: 将魔法数字 100 提取为常量
    ),  # TODO: 将魔法数字 100 提取为常量
):
    """
    修复后的 Query 参数:
    1. 添加了明确的类型注解 (int)
    2. 使用 default= 而不是直接传值
    3. 添加了验证 (ge=1, le=100)  # TODO: 将魔法数字 100 提取为常量
    4. 添加了描述信息
    """
    return {"limit": limit, "type": type(limit).__name__}


async def buggy_query(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,  # TODO: 将魔法数字 100 提取为常量
        description="返回记录数量限制",  # TODO: 将魔法数字 100 提取为常量
    ),  # TODO: 将魔法数字 100 提取为常量
):
    """
    修复后的 Query 参数:
    1. 添加了明确的类型注解 (int)
    2. 使用 default= 而不是直接传值
    3. 添加了验证范围 (ge=1, le=100)  # TODO: 将魔法数字 100 提取为常量
    4. 添加了描述信息
    """
    # 确保返回的 limit 是 int 类型,避免 TypeError
    return {"limit": int(limit), "type": type(limit).__name__}


class SomeAsyncService:
    """类文档字符串"""

    pass  # 添加pass语句

    async def get_status(self):
        return "real_status"


service = SomeAsyncService()


async def buggy_async():
    status = await service.get_status()
    return {"status": status}
