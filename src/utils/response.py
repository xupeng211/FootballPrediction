"""
API响应工具类

提供统一的API响应格式
"""

from typing import Any, Dict, Optional


class APIResponse:
    """API响应格式化工具"""

    @staticmethod
    def success(data: Any = None, message: str = "操作成功") -> Dict[str, Any]:
        """
        成功响应

        Args:
            data: 响应数据
            message: 响应消息

        Returns:
            Dict[str, Any]: 格式化的成功响应
        """
        response = {"success": True, "message": message}

        if data is not None:
            response["data"] = data

        return response

    @staticmethod
    def error(
        message: str = "操作失败", code: Optional[str] = None, data: Any = None
    ) -> Dict[str, Any]:
        """
        错误响应

        Args:
            message: 错误消息
            code: 错误代码
            data: 附加数据

        Returns:
            Dict[str, Any]: 格式化的错误响应
        """
        response = {"success": False, "message": message}

        if code is not None:
            response["code"] = code

        if data is not None:
            response["data"] = data

        return response
