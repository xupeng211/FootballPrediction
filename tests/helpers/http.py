"""HTTP 客户端测试桩"""

from typing import Any, Dict, Tuple

import httpx
from pytest import MonkeyPatch


class MockHTTPResponse:
    """脱离网络的响应对象"""

    def __init__(self, status_code: int = 200, json_data: Dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self._json_data = json_data or {"mock": True}
        self.text = str(self._json_data)

    def json(self) -> Dict[str, Any]:
        return self._json_data


def apply_http_mocks(monkeypatch: MonkeyPatch) -> None:
    """部分拦截 httpx.AsyncClient 的外部调用"""

    original_async_client = httpx.AsyncClient

    class MockingAsyncClient(original_async_client):
        """拦截外部请求但保留应用内调用"""

        def __init__(self, *args: Any, **kwargs: Any) -> None:  # pylint: disable=super-init-not-called
            self._mock_responses: Dict[Tuple[str, str], MockHTTPResponse] = kwargs.pop("mock_responses", {})
            super().__init__(*args, **kwargs)

        async def request(self, method: str, url: Any, *args: Any, **kwargs: Any) -> httpx.Response:  # type: ignore[override]
            request_url = httpx.URL(url)
            target_host = request_url.host or ""
            if target_host and target_host not in {"testserver", "localhost", "127.0.0.1"}:
                key = (method.upper(), str(request_url))
                if key in self._mock_responses:
                    payload = self._mock_responses[key]
                    return httpx.Response(status_code=payload.status_code, json=payload.json())
                return httpx.Response(status_code=200, json={"mock": True, "url": str(request_url)})
            return await super().request(method, url, *args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", MockingAsyncClient, raising=False)


__all__ = ["MockHTTPResponse", "apply_http_mocks"]
