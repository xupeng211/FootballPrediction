"""
动态认证模块 - Token Manager
Dynamic Authentication Module - Token Manager

该模块实现了动态认证管理系统，支持：
1. 多种认证提供者 (AuthProvider Protocol)
2. Token 缓存和自动刷新机制
3. FotMob 认证实现
4. TTL 过期处理
5. 线程安全的并发访问

作者: Lead Collector Engineer
创建时间: 2025-12-06
版本: 1.0.0
"""

import asyncio
import re
import time
from abc import abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, dict, Optional, Protocol, runtime_checkable

import aiohttp


class TokenType(Enum):
    """Token 类型"""

    BEARER = "bearer"
    API_KEY = "api_key"
    CUSTOM_HEADER = "custom_header"


@dataclass
class Token:
    """
    认证令牌数据类

    Attributes:
        value: 令牌值
        token_type: 令牌类型
        headers: 关联的HTTP头部
        expires_at: 过期时间戳
        created_at: 创建时间戳
        usage_count: 使用次数
        provider: 提供者名称
    """

    value: str
    token_type: TokenType
    headers: dict[str, str] = field(default_factory=dict)
    expires_at: Optional[float] = None
    created_at: float = field(default_factory=time.monotonic)
    usage_count: int = 0
    provider: str = "unknown"

    def __post_init__(self) -> None:
        """初始化后处理"""
        if isinstance(self.token_type, str):
            self.token_type = TokenType(self.token_type.lower())

    @property
    def is_expired(self) -> bool:
        """检查令牌是否过期"""
        if self.expires_at is None:
            return False
        return time.monotonic() >= self.expires_at

    @property
    def is_valid(self) -> bool:
        """检查令牌是否有效（未过期且值不为空）"""
        return not self.is_expired and bool(self.value)

    @property
    def ttl(self) -> Optional[float]:
        """获取剩余生存时间（秒）"""
        if self.expires_at is None:
            return None
        return max(0.0, self.expires_at - time.monotonic())

    def record_usage(self) -> None:
        """记录令牌使用"""
        self.usage_count += 1

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "value": (
                self.value[:20] + "..." if len(self.value) > 20 else self.value
            ),  # 隐藏完整token
            "token_type": self.token_type.value,
            "headers": self.headers,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "usage_count": self.usage_count,
            "provider": self.provider,
            "is_expired": self.is_expired,
            "is_valid": self.is_valid,
            "ttl": self.ttl,
        }

    def __str__(self) -> str:
        return f"Token({self.provider}, {self.token_type.value}, valid={self.is_valid})"

    def __repr__(self) -> str:
        return self.__str__()


@runtime_checkable
class AuthProvider(Protocol):
    """
    认证提供者协议

    定义了获取认证令牌的标准接口
    """

    @abstractmethod
    async def get_token(self) -> Token:
        """
        获取认证令牌

        Returns:
            Token: 认证令牌对象

        Raises:
            AuthenticationError: 认证失败
        """
        ...

    @abstractmethod
    async def refresh_token(self, old_token: Optional[Token] = None) -> Token:
        """
        刷新认证令牌

        Args:
            old_token: 旧的令牌（可选）

        Returns:
            Token: 新的认证令牌

        Raises:
            AuthenticationError: 认证失败
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """获取提供者名称"""
        ...


class AuthenticationError(Exception):
    """认证错误基类"""

    pass


class TokenExpiredError(AuthenticationError):
    """令牌过期错误"""

    pass


class TokenRefreshError(AuthenticationError):
    """令牌刷新错误"""

    pass


class TokenManager:
    """
    令牌管理器

    负责管理不同的认证提供者，处理令牌的缓存和自动刷新
    """

    def __init__(
        self,
        default_ttl: float = 3600.0,  # 1小时
        cache_refresh_threshold: float = 300.0,  # 5分钟内过期时刷新
        max_retry_attempts: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        初始化令牌管理器

        Args:
            default_ttl: 默认令牌生存时间（秒）
            cache_refresh_threshold: 缓存刷新阈值（秒）
            max_retry_attempts: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self.default_ttl = default_ttl
        self.cache_refresh_threshold = cache_refresh_threshold
        self.max_retry_attempts = max_retry_attempts
        self.retry_delay = retry_delay

        # 令牌缓存: {provider_name: Token}
        self.token_cache: dict[str, Token] = {}
        # 提供者缓存: {provider_name: AuthProvider}
        self.provider_cache: dict[str, AuthProvider] = {}
        self.lock = asyncio.Lock()

    async def register_provider(self, provider: AuthProvider) -> None:
        """
        注册认证提供者

        Args:
            provider: 认证提供者实例
        """
        async with self.lock:
            provider_name = provider.provider_name
            if provider_name not in self.token_cache:
                # 存储provider引用
                self.provider_cache[provider_name] = provider

                # 预先获取一个令牌
                try:
                    token = await provider.get_token()
                    self.token_cache[provider_name] = token
                    print(f"🔑 Registered provider: {provider_name}")
                except Exception as e:
                    print(f"❌ Failed to register provider {provider_name}: {e}")
                    raise AuthenticationError(
                        f"Failed to register provider {provider_name}: {e}"
                    )

    async def get_token(self, provider_name: str, force_refresh: bool = False) -> Token:
        """
        获取认证令牌

        Args:
            provider_name: 提供者名称
            force_refresh: 是否强制刷新

        Returns:
            Token: 认证令牌

        Raises:
            AuthenticationError: 认证失败
            TokenRefreshError: 令牌刷新失败
        """
        async with self.lock:
            if provider_name not in self.token_cache:
                raise AuthenticationError(f"Provider {provider_name} not registered")

            cached_token = self.token_cache[provider_name]

            # 检查是否需要刷新
            should_refresh = (
                force_refresh
                or not cached_token.is_valid
                or (
                    cached_token.ttl and cached_token.ttl < self.cache_refresh_threshold
                )
            )

            if should_refresh:
                print(f"🔄 Refreshing token for provider: {provider_name}")
                # 这里需要重新获取provider实例进行刷新
                # 实际实现中应该保存provider引用
                provider = self._get_provider_by_name(provider_name)
                if not provider:
                    raise AuthenticationError(
                        f"Provider {provider_name} not found for refresh"
                    )

                try:
                    new_token = await self._retry_token_refresh(provider, cached_token)
                    self.token_cache[provider_name] = new_token
                    print(f"✅ Token refreshed for provider: {provider_name}")
                    return new_token
                except Exception as e:
                    print(f"❌ Failed to refresh token for {provider_name}: {e}")
                    if not cached_token.is_valid:
                        # 缓存的token也无效了，抛出异常
                        raise TokenRefreshError(
                            f"Failed to refresh token for {provider_name}: {e}"
                        )
                    # 返回旧token（虽然快过期但仍然有效）
                    print(f"⚠️ Using old token for {provider_name} (will expire soon)")
                    return cached_token
            else:
                cached_token.record_usage()
                if cached_token.usage_count % 10 == 0:  # 每10次使用打印一次
                    print(
                        f"📊 Token usage for {provider_name}: {cached_token.usage_count} times"
                    )
                return cached_token

    def _get_provider_by_name(self, provider_name: str) -> Optional[AuthProvider]:
        """
        根据名称获取提供者实例

        Args:
            provider_name: 提供者名称

        Returns:
            Optional[AuthProvider]: 提供者实例，如果不存在返回None
        """
        return self.provider_cache.get(provider_name)

    async def _retry_token_refresh(
        self, provider: AuthProvider, old_token: Optional[Token] = None
    ) -> Token:
        """
        重试令牌刷新

        Args:
            provider: 认证提供者
            old_token: 旧令牌

        Returns:
            Token: 新令牌

        Raises:
            TokenRefreshError: 刷新失败
        """
        last_error = None

        for attempt in range(self.max_retry_attempts):
            try:
                new_token = await provider.refresh_token(old_token)
                return new_token
            except Exception as e:
                last_error = e
                print(f"⚠️ Token refresh attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (2**attempt))  # 指数退避

        raise TokenRefreshError(
            f"Token refresh failed after {self.max_retry_attempts} attempts: {last_error}"
        )

    async def invalidate_token(self, provider_name: str) -> None:
        """
        使令牌失效

        Args:
            provider_name: 提供者名称
        """
        async with self.lock:
            if provider_name in self.token_cache:
                del self.token_cache[provider_name]
                print(f"🗑️ Invalidated token for provider: {provider_name}")

    async def get_token_info(
        self, provider_name: Optional[str] = None
    ) -> dict[str, Any]:
        """
        获取令牌信息

        Args:
            provider_name: 提供者名称，None表示获取所有

        Returns:
            dict[str, Any]: 令牌信息
        """
        async with self.lock:
            if provider_name:
                if provider_name in self.token_cache:
                    return self.token_cache[provider_name].to_dict()
                else:
                    return {"error": f"Provider {provider_name} not found"}
            else:
                return {
                    name: token.to_dict() for name, token in self.token_cache.items()
                }

    async def get_stats(self) -> dict[str, Any]:
        """
        获取管理器统计信息

        Returns:
            dict[str, Any]: 统计信息
        """
        async with self.lock:
            total_providers = len(self.token_cache)
            valid_tokens = sum(
                1 for token in self.token_cache.values() if token.is_valid
            )
            expired_tokens = total_providers - valid_tokens

            total_usage = sum(token.usage_count for token in self.token_cache.values())

            return {
                "total_providers": total_providers,
                "valid_tokens": valid_tokens,
                "expired_tokens": expired_tokens,
                "total_usage": total_usage,
                "cache_refresh_threshold": self.cache_refresh_threshold,
                "default_ttl": self.default_ttl,
            }


class FotMobAuthProvider:
    """
    FotMob 认证提供者

    模拟从 FotMob 首页 HTML 中提取认证签名的逻辑
    """

    def __init__(
        self,
        base_url: str = "https://www.fotmob.com",
        timeout: float = 10.0,
        token_ttl: float = 3600.0,  # 1小时
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    ):
        """
        初始化 FotMob 认证提供者

        Args:
            base_url: FotMob 基础URL
            timeout: 请求超时时间
            token_ttl: 令牌生存时间
            user_agent: 用户代理字符串
        """
        self.base_url = base_url
        self.timeout = timeout
        self.token_ttl = token_ttl
        self.user_agent = user_agent

    @property
    def provider_name(self) -> str:
        """获取提供者名称"""
        return "fotmob"

    async def get_token(self) -> Token:
        """
        获取 FotMob 认证令牌

        Returns:
            Token: 认证令牌

        Raises:
            AuthenticationError: 认证失败
        """
        try:
            # 模拟从 FotMob 首页提取 token
            html_content = await self._fetch_fotmob_homepage()
            token_data = self._extract_token_from_html(html_content)

            if not token_data:
                raise AuthenticationError(
                    "Failed to extract token from FotMob homepage"
                )

            token = Token(
                value=token_data["value"],
                token_type=TokenType.CUSTOM_HEADER,
                headers=token_data["headers"],
                expires_at=time.monotonic() + self.token_ttl,
                provider=self.provider_name,
            )

            print(f"🔑 Obtained FotMob token: {token.value[:20]}...")
            return token

        except Exception as e:
            print(f"❌ Failed to get FotMob token: {e}")
            raise AuthenticationError(f"Failed to get FotMob token: {e}")

    async def refresh_token(self, old_token: Optional[Token] = None) -> Token:
        """
        刷新 FotMob 认证令牌

        Args:
            old_token: 旧令牌（可选）

        Returns:
            Token: 新的认证令牌

        Raises:
            TokenRefreshError: 刷新失败
        """
        try:
            print("🔄 Refreshing FotMob token...")
            new_token = await self.get_token()
            print("✅ FotMob token refreshed successfully")
            return new_token
        except Exception as e:
            print(f"❌ Failed to refresh FotMob token: {e}")
            raise TokenRefreshError(f"Failed to refresh FotMob token: {e}")

    async def _fetch_fotmob_homepage(self) -> str:
        """
        获取 FotMob 首页 HTML

        Returns:
            str: HTML 内容

        Raises:
            AuthenticationError: 获取失败
        """
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)

            headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.base_url, headers=headers) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        raise AuthenticationError(
                            f"HTTP {response.status}: Failed to fetch FotMob homepage"
                        )

        except aiohttp.ClientError as e:
            raise AuthenticationError(
                f"Network error while fetching FotMob homepage: {e}"
            )

    def _extract_token_from_html(self, html_content: str) -> Optional[dict[str, Any]]:
        """
        从 HTML 内容中提取认证令牌

        Args:
            html_content: HTML 内容

        Returns:
            Optional[dict[str, Any]]: 令牌数据，如果提取失败返回None
        """
        try:
            # 模拟从 HTML 中提取认证信息
            # 实际实现中，这些值会从 HTML 的 JavaScript 或 meta 标签中提取

            # 模拟提取 x-mas header
            x_mas_match = re.search(r'"x-mas":"([^"]+)"', html_content)
            x_mas_value = (
                x_mas_match.group(1) if x_mas_match else self._generate_mock_x_mas()
            )

            # 模拟提取 x-foo signature
            x_foo_match = re.search(r'"x-foo":"([^"]+)"', html_content)
            x_foo_value = (
                x_foo_match.group(1) if x_foo_match else self._generate_mock_x_foo()
            )

            # 模拟提取 client version
            version_match = re.search(r'"clientVersion":"([^"]+)"', html_content)
            client_version = (
                version_match.group(1) if version_match else "production:mock_version"
            )

            if not x_mas_value or not x_foo_value:
                print("⚠️ Token extraction incomplete, using mock values")

            token_data = {
                "value": f"{x_mas_value}:{x_foo_value}",
                "headers": {
                    "x-mas": x_mas_value,
                    "x-foo": x_foo_value,
                    "x-client-version": client_version,
                },
            }

            return token_data

        except Exception as e:
            print(f"⚠️ Token extraction failed, using mock values: {e}")
            return self._generate_mock_token_data()

    def _generate_mock_x_mas(self) -> str:
        """生成模拟的 x-mas 值"""
        import hashlib
        import random

        timestamp = int(time.time())
        random_str = f"fotmob_{timestamp}_{random.randint(1000, 9999)}"
        return hashlib.sha256(random_str.encode()).hexdigest()[:32]

    def _generate_mock_x_foo(self) -> str:
        """生成模拟的 x-foo 签名"""
        import hashlib
        import base64

        payload = f"fotmob_auth_{int(time.time())}".encode()
        signature = hashlib.sha256(payload).digest()
        return base64.b64encode(signature).decode()[:40]

    def _generate_mock_token_data(self) -> dict[str, Any]:
        """生成模拟令牌数据"""
        x_mas = self._generate_mock_x_mas()
        x_foo = self._generate_mock_x_foo()

        return {
            "value": f"{x_mas}:{x_foo}",
            "headers": {
                "x-mas": x_mas,
                "x-foo": x_foo,
                "x-client-version": "production:mock_version",
            },
        }


class MockAuthProvider:
    """
    模拟认证提供者（用于测试）
    """

    def __init__(
        self, provider_name: str, token_value: str = "mock_token", ttl: float = 300.0
    ):
        """
        初始化模拟认证提供者

        Args:
            provider_name: 提供者名称
            token_value: 令牌值
            ttl: 生存时间
        """
        self._provider_name = provider_name
        self.token_value = token_value
        self.ttl = ttl

    @property
    def provider_name(self) -> str:
        """获取提供者名称"""
        return self._provider_name

    async def get_token(self) -> Token:
        """获取模拟令牌"""
        return Token(
            value=self.token_value,
            token_type=TokenType.BEARER,
            expires_at=time.monotonic() + self.ttl,
            provider=self.provider_name,
        )

    async def refresh_token(self, old_token: Optional[Token] = None) -> Token:
        """刷新模拟令牌"""
        new_value = f"{self.token_value}_refreshed_{int(time.time())}"
        return Token(
            value=new_value,
            token_type=TokenType.BEARER,
            expires_at=time.monotonic() + self.ttl,
            provider=self.provider_name,
        )


# 全局令牌管理器实例
_token_manager: Optional[TokenManager] = None


async def get_token_manager() -> TokenManager:
    """
    获取全局令牌管理器实例

    Returns:
        TokenManager: 令牌管理器实例
    """
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
    return _token_manager


async def close_token_manager():
    """关闭令牌管理器"""
    global _token_manager
    if _token_manager:
        _token_manager = None


# 便利函数
def create_token_manager(
    default_ttl: float = 3600.0, cache_refresh_threshold: float = 300.0, **kwargs
) -> TokenManager:
    """
    创建令牌管理器的便利函数

    Args:
        default_ttl: 默认令牌生存时间
        cache_refresh_threshold: 缓存刷新阈值
        **kwargs: 其他参数

    Returns:
        TokenManager: 令牌管理器实例
    """
    return TokenManager(default_ttl, cache_refresh_threshold, **kwargs)


def create_fotmob_provider(**kwargs) -> FotMobAuthProvider:
    """
    创建 FotMob 认证提供者的便利函数

    Args:
        **kwargs: FotMobAuthProvider 参数

    Returns:
        FotMobAuthProvider: FotMob 认证提供者实例
    """
    return FotMobAuthProvider(**kwargs)


def create_mock_provider(provider_name: str, **kwargs) -> MockAuthProvider:
    """
    创建模拟认证提供者的便利函数

    Args:
        provider_name: 提供者名称
        **kwargs: MockAuthProvider 参数

    Returns:
        MockAuthProvider: 模拟认证提供者实例
    """
    return MockAuthProvider(provider_name, **kwargs)


# 模块导出
__all__ = [
    "Token",
    "TokenType",
    "AuthProvider",
    "TokenManager",
    "FotMobAuthProvider",
    "MockAuthProvider",
    "AuthenticationError",
    "TokenExpiredError",
    "TokenRefreshError",
    "get_token_manager",
    "close_token_manager",
    "create_token_manager",
    "create_fotmob_provider",
    "create_mock_provider",
]
