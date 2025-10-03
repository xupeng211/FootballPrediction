"""
FastAPI Query 参数修复示例

演示如何正确修复 FastAPI Query 参数错误
"""

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Query

app = FastAPI()

# ❌ 错误的 Query 参数格式 - 这会导致 TypeError: int() argument must be...
# @app.get("/wrong")
# async def wrong_endpoint(
#     limit=Query(10)  # 错误：缺少类型注解，缺少验证
# ):
#     pass


# ✅ 正确的 Query 参数格式
@app.get("/correct")
async def correct_endpoint(
    limit: int = Query(default=10, ge=1, le=100, description="返回记录数量限制")
):
    """
    正确的 Query 参数格式：
    1. 明确的类型注解 (int)
    2. 使用 default= 而不是直接传值
    3. 添加验证 (ge=1, le=100)
    4. 添加描述信息
    """
    return {"limit": limit, "message": "参数正确"}


# ✅ 更多正确的 Query 参数示例
@app.get("/examples")
async def query_examples(
    # 整数参数，带范围验证
    page: int = Query(default=1, ge=1, description="页码"),
    size: int = Query(default=20, ge=1, le=100, description="每页大小"),
    # 可选字符串参数
    search: Optional[str] = Query(default=None, description="搜索关键词"),
    # 可选日期参数
    start_date: Optional[datetime] = Query(default=None, description="开始日期"),
    # 布尔参数
    include_details: bool = Query(default=False, description="是否包含详细信息"),
):
    """
    多种类型的 Query 参数正确用法
    """
    return {
        "page": page,
        "size": size,
        "search": search,
        "start_date": start_date,
        "include_details": include_details,
    }


# ✅ 在使用 .limit() 时确保传入 int 类型
@app.get("/database_query")
async def database_query_example(
    limit: int = Query(default=10, ge=1, le=100, description="查询限制")
):
    """
    确保在数据库查询中正确使用 limit 参数
    """
    # ✅ 正确：limit 已经是 int 类型，可以直接使用
    # query = select(SomeModel).limit(limit)

    # ❌ 错误：如果 limit 不是 int 类型会导致错误
    # query = select(SomeModel).limit(str(limit))  # 这会出错

    return {"limit": limit, "type": type(limit).__name__}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
