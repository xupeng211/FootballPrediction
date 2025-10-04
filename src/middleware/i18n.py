"""
国际化中间件
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import os


class I18nMiddleware(BaseHTTPMiddleware):
    """国际化中间件 - 设置语言偏好"""

    async def dispatch(self, request: Request, call_next):
        # 从请求头获取语言偏好
        accept_language = request.headers.get("accept-language", "zh-CN")

        # 设置环境变量
        if "zh" in accept_language:
            os.environ["LANG"] = "zh_CN.UTF-8"
            os.environ["LC_ALL"] = "zh_CN.UTF-8"
            os.environ["LANGUAGE"] = "zh_CN:zh:en_US:en"

        response = await call_next(request)

        # 添加响应头表明支持的语言
        response.headers["Content-Language"] = "zh-CN"

        return response
