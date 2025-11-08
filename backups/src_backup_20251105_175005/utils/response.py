"""
API响应工具类

提供统一的API响应格式
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class APIResponseModel(BaseModel):
    """API响应Pydantic模型"""

    success: bool
    message: str
    data: Any | None = None
    code: str | None = None


class APIResponse:
    """API响应格式化工具"""

    @staticmethod
    def success(data: Any = None, message: str = "操作成功") -> dict[str, Any]:
        """
        成功响应

        Args:
            data: 响应数据
            message: 响应消息

        Returns:
            Dict[str, Any]: 格式化的成功响应
        """
        response = {
            "success": True,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }

        if data is not None:
            response["data"] = data

        return response

    @staticmethod
    def success_response(data: Any = None, message: str = "操作成功") -> dict[str, Any]:
        """成功响应（别名方法）"""
        return APIResponse.success(data, message)

    @staticmethod
    def error(
        message: str = "操作失败", code: int | None = None, data: Any = None
    ) -> dict[str, Any]:
        """
        错误响应

        Args:
            message: 错误消息
            code: 错误代码
            data: 附加数据

        Returns:
            Dict[str, Any]: 格式化的错误响应
        """
        response = {
            "success": False,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }

        if code is not None:
            response["code"] = code
        else:
            response["code"] = 500  # 默认错误代码

        if data is not None:
            response["data"] = data

        return response

    @staticmethod
    def error_response(
        message: str = "操作失败", code: int | None = None, data: Any = None
    ) -> dict[str, Any]:
        """错误响应（别名方法）"""
        return APIResponse.error(message, code, data)


# 为了向后兼容,提供一个ResponseUtils别名
ResponseUtils = APIResponse
