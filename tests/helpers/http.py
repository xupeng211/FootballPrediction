"""HTTP 客户端测试桩"""

import asyncio
from typing import Any, Dict, Tuple

import httpx
from pytest import MonkeyPatch


class MockHTTPResponse:
    """脱离网络的响应对象"""

    def __init__(
        self, status_code: int = 200, json_data: Dict[str, Any] | None = None
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data or {"mock": True}
        self.text = str(self._json_data)

    def json(self) -> Dict[str, Any]:
        return self._json_data


_LOCAL_PREFIXES = ("http://testserver", "https://testserver")


def apply_http_mocks(
    monkeypatch: MonkeyPatch,
    responses: Dict[Tuple[str, str], MockHTTPResponse],
) -> None:
    """
    应用多个 HTTP mock

    Args:
        monkeypatch: pytest monkeypatch fixture
        responses: {(method, url): MockHTTPResponse}
    """

    def mock_request(method: str, url: Any, **kwargs: Any) -> MockHTTPResponse:
        url_str = str(url)
        key = (method.upper(), url_str)
        return responses.get(key, MockHTTPResponse(status_code=404))

    # Mock common HTTP client methods
    for method in ["get", "post", "put", "delete", "patch"]:
        for client_class in [httpx.Client, httpx.AsyncClient]:
            if not hasattr(client_class, method):
                continue

            original = getattr(client_class, method)

            if asyncio.iscoroutinefunction(original):

                async def async_wrapper(
                    self,
                    url,
                    *args,
                    _method=method,
                    _original=original,
                    **kwargs,
                ):
                    url_str = str(url)
                    if url_str.startswith(_LOCAL_PREFIXES) or url_str.startswith("/"):
                        return await _original(self, url, *args, **kwargs)
                    return mock_request(_method, url, **kwargs)

                monkeypatch.setattr(client_class, method, async_wrapper)
            else:

                def sync_wrapper(
                    self,
                    url,
                    *args,
                    _method=method,
                    _original=original,
                    **kwargs,
                ):
                    url_str = str(url)
                    if url_str.startswith(_LOCAL_PREFIXES) or url_str.startswith("/"):
                        return _original(self, url, *args, **kwargs)
                    return mock_request(_method, url, **kwargs)

                monkeypatch.setattr(client_class, method, sync_wrapper)


__all__ = [
    "MockHTTPResponse",
    "apply_http_mocks",
]
