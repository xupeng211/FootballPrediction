"""P4-2: Request ID 中间件
为每个请求生成唯一标识符，支持链路追踪.
"""

import uuid
from contextvars import ContextVar
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# 上下文变量用于存储当前请求的 ID
request_id_context: ContextVar[str] = ContextVar("request_id", default="")

# 请求头名称
REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Request ID 中间件

    为每个请求生成唯一标识符，支持分布式链路追踪：
    1. 检查请求头中的 X-Request-ID
    2. 如果不存在则生成新的 UUID
    3. 存储在上下文变量中供日志使用
    4. 在响应头中返回 Request ID
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并注入 Request ID"""

        # 1. 获取或生成 Request ID
        incoming_request_id = request.headers.get(REQUEST_ID_HEADER)

        if incoming_request_id:
            # 使用传入的 Request ID
            request_id = incoming_request_id
            is_generated = False
        else:
            # 生成新的 Request ID
            request_id = str(uuid.uuid4())
            is_generated = True

        # 2. 存储到上下文变量中
        request_id_context.set(request_id)

        # 3. 将 Request ID 添加到请求状态中，供其他中间件/路由使用
        request.state.request_id = request_id

        # 4. 调用下一个中间件/路由处理器
        response = await call_next(request)

        # 5. 在响应头中返回 Request ID
        response.headers[REQUEST_ID_HEADER] = request_id

        # 6. 可选：添加调试头标识是否为生成的 ID
        if is_generated:
            response.headers["X-Request-ID-Generated"] = "true"

        return response


def get_request_id() -> str:
    """获取当前请求的 ID

    在日志记录时调用此函数获取当前请求的 ID。
    如果不在请求上下文中，返回空字符串。

    Returns:
        str: 当前请求的 ID
    """
    return request_id_context.get("")


def add_request_id_middleware(app: FastAPI) -> None:
    """向 FastAPI 应用添加 Request ID 中间件

    Args:
        app: FastAPI 应用实例
    """
    app.add_middleware(RequestIDMiddleware)


# 用于日志格式化的函数
def request_id_formatter(record: dict) -> str:
    """日志记录器格式化器，添加 Request ID

    Args:
        record: loguru 日志记录

    Returns:
        str: 包含 Request ID 的格式化字符串
    """
    request_id = get_request_id()
    if request_id:
        return f"[{request_id}] {record['message']}"
    return record["message"]


# 导出主要接口
__all__ = [
    "RequestIDMiddleware",
    "get_request_id",
    "add_request_id_middleware",
    "request_id_formatter",
    "REQUEST_ID_HEADER",
    "request_id_context",
]
