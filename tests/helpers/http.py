"""
HTTP客户端测试辅助工具
提供HTTP请求的Mock和测试辅助功能
"""

import json
from typing import Any, Dict, Optional


class MockHTTPResponse:
    """模拟HTTP响应对象"""

    def __init__(
        self,
        status_code: int = 200,
        json_data: Optional[Dict[str, Any]] = None,
        text: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data or {"mock": True}
        self.text = text or json.dumps(self._json_data)
        self.headers = headers or {"content-type": "application/json"}

    def json(self) -> Dict[str, Any]:
        """返回JSON数据"""
        return self._json_data

    def raise_for_status(self) -> None:
        """检查状态码，如果错误则抛出异常"""
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    @property
    def content(self) -> bytes:
        """返回响应内容字节"""
        return self.text.encode("utf-8")


class MockHTTPClient:
    """模拟HTTP客户端"""

    def __init__(self):
        self.responses = {}
        self.request_history = []

    def set_response(self, method: str, url: str, response: MockHTTPResponse) -> None:
        """设置模拟响应"""
        key = f"{method.upper()}:{url}"
        self.responses[key] = response

    def get(self, url: str, **kwargs) -> MockHTTPResponse:
        """模拟GET请求"""
        key = f"GET:{url}"
        self.request_history.append(("GET", url, kwargs))
        return self.responses.get(key, MockHTTPResponse())

    def post(self, url: str, **kwargs) -> MockHTTPResponse:
        """模拟POST请求"""
        key = f"POST:{url}"
        self.request_history.append(("POST", url, kwargs))
        return self.responses.get(key, MockHTTPResponse(status_code=201))

    def put(self, url: str, **kwargs) -> MockHTTPResponse:
        """模拟PUT请求"""
        key = f"PUT:{url}"
        self.request_history.append(("PUT", url, kwargs))
        return self.responses.get(key, MockHTTPResponse())

    def delete(self, url: str, **kwargs) -> MockHTTPResponse:
        """模拟DELETE请求"""
        key = f"DELETE:{url}"
        self.request_history.append(("DELETE", url, kwargs))
        return self.responses.get(key, MockHTTPResponse(status_code=204))


class MockAsyncHTTPClient:
    """模拟异步HTTP客户端"""

    def __init__(self):
        self.client = MockHTTPClient()

    async def get(self, url: str, **kwargs) -> MockHTTPResponse:
        """异步GET请求"""
        return self.client.get(url, **kwargs)

    async def post(self, url: str, **kwargs) -> MockHTTPResponse:
        """异步POST请求"""
        return self.client.post(url, **kwargs)

    async def put(self, url: str, **kwargs) -> MockHTTPResponse:
        """异步PUT请求"""
        return self.client.put(url, **kwargs)

    async def delete(self, url: str, **kwargs) -> MockHTTPResponse:
        """异步DELETE请求"""
        return self.client.delete(url, **kwargs)


def apply_http_mocks():
    """应用HTTP mock装饰器"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            # 创建mock客户端
            mock_client = MockHTTPClient()

            # 设置常见响应
            mock_client.set_response("GET", "/api/health", MockHTTPResponse({"status": "healthy"}))

            mock_client.set_response(
                "POST",
                "/api/predictions",
                MockHTTPResponse(status_code=201, json_data={"id": 1, "prediction": "win"}),
            )

            return func(mock_client, *args, **kwargs)

        return wrapper

    return decorator


# 全局mock实例
mock_http_client = MockHTTPClient()
mock_async_http_client = MockAsyncHTTPClient()
