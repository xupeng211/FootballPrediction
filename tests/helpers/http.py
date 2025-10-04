"""HTTP 客户端测试桩"""

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

    def mock_request(method: str, url: str, **kwargs: Any) -> MockHTTPResponse:
        key = (method.upper(), url)
        return responses.get(key, MockHTTPResponse(status_code=404))

    # Mock common HTTP client methods
    for method in ["get", "post", "put", "delete", "patch"]:
        for client_class in [httpx.Client, httpx.AsyncClient]:
            if hasattr(client_class, method):
                monkeypatch.setattr(
                    client_class,
                    method,
                    lambda self, url, method=method, **kwargs: mock_request(
                        method, url, **kwargs
                    ),
                )


__all__ = [
    "MockHTTPResponse",
    "apply_http_mocks",
]
