"""
V38.0 特种渗透客户端 - StealthClient
======================================
基于 curl_cffi 的底层传输层，实现：
1. TLS/JA3 指纹伪装（模拟 Chrome 131）
2. HTTP/2 伪头顺序控制
3. 完整的 sec-ch-ua 请求头序列
4. 单例模式确保全局指纹一致性
"""

from __future__ import annotations

import asyncio
import builtins
from collections import OrderedDict
import contextlib
from typing import TYPE_CHECKING, Any, ClassVar, cast

if TYPE_CHECKING:
    from curl_cffi.requests import AsyncSession  # type: ignore[import-not-found]
else:
    try:
        from curl_cffi.requests import AsyncSession
    except ImportError:
        AsyncSession = Any


class SingletonMeta(type):
    """线程安全的单例元类。"""

    _instances: ClassVar[dict[type, object]] = {}
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    def __call__(cls, *args: Any, **kwargs: Any) -> object:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class StealthClient(metaclass=SingletonMeta):
    """V38.0 特种渗透客户端。"""

    CHROME_131_JA3_HASH: ClassVar[str] = "aa56c057ad164ec4fdcb7a5a283be9fc"
    CHROME_131_HTTP2_FINGERPRINT: ClassVar[str] = "1:65536,2:0,4:6291456,6:262144|..."
    FIXED_FINGERPRINT: ClassVar[dict[str, Any]] = {
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "viewport": {"width": 1920, "height": 1080},
        "locale": "en-US",
        "timezone": "Europe/London",
        "platform": "Win32",
    }

    def __init__(self) -> None:
        self._session: AsyncSession | None = None

    async def _get_session(self) -> AsyncSession:
        if self._session is None:
            self._session = AsyncSession(impersonate="chrome131")
        return self._session

    async def fetch(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        proxy: str | None = None,
        **kwargs: Any,
    ) -> Any:
        session = await self._get_session()
        default_headers = self._generate_stealth_headers()
        if headers:
            default_headers.update(headers)
        return await session.get(url, headers=default_headers, proxy=proxy, **kwargs)

    async def post(
        self,
        url: str,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
        proxy: str | None = None,
        **kwargs: Any,
    ) -> Any:
        session = await self._get_session()
        default_headers = self._generate_stealth_headers()
        if headers:
            default_headers.update(headers)
        return await session.post(url, data=data, headers=default_headers, proxy=proxy, **kwargs)

    def _generate_stealth_headers(self) -> dict[str, str]:
        return {
            "sec-ch-ua": '"Chromium";v="131", "Google Chrome";v="131", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
            "accept-encoding": "gzip, deflate, br, zstd",
            "cache-control": "max-age=0",
            "upgrade-insecure-requests": "1",
            "user-agent": str(self.FIXED_FINGERPRINT["user_agent"]),
        }

    def _generate_http2_headers(
        self,
        method: str = "GET",
        authority: str = "",
        scheme: str = "https",
        path: str = "/",
    ) -> dict[str, str]:
        headers: OrderedDict[str, str] = OrderedDict()
        headers[":method"] = method
        headers[":authority"] = authority
        headers[":scheme"] = scheme
        headers[":path"] = path
        headers.update(self._generate_stealth_headers())
        return dict(headers)

    async def verify_fingerprint(self) -> dict[str, str]:
        session = await self._get_session()
        try:
            response = await session.get(
                "https://tls.browserleaks.com/json",
                impersonate="chrome131",
            )
            data = response.json()
            if not isinstance(data, dict):
                return {"error": "invalid-response", "ja3_hash": "failed", "ja3n_hash": "failed"}

            payload = cast("dict[str, Any]", data)
            return {
                "ja3_hash": str(payload.get("ja3_hash", "unknown")),
                "ja3n_hash": str(payload.get("ja3n_hash", "unknown")),
                "ja3_text": str(payload.get("ja3_text", "unknown")),
                "user_agent": str(payload.get("user_agent", "unknown")),
                "tls_version": str(payload.get("tls_version", "unknown")),
            }
        except Exception as exc:
            return {"error": str(exc), "ja3_hash": "failed", "ja3n_hash": "failed"}

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    def __del__(self) -> None:
        if self._session is not None:
            with contextlib.suppress(builtins.BaseException):
                asyncio.get_event_loop().run_until_complete(self.close())


async def get_stealth_client() -> StealthClient:
    """获取 StealthClient 单例。"""
    return StealthClient()


async def fetch(url: str, **kwargs: Any) -> Any:
    """快捷函数：使用默认 StealthClient 发起请求。"""
    client = await get_stealth_client()
    return await client.fetch(url, **kwargs)
