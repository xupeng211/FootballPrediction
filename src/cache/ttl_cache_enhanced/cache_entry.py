from typing import Any

"" "" 缓
"" Cache Entry Definition

"" 定
"" "" import timeclass CacheEntry:
    "" "" 缓
"" 存储缓存的值,过期时间,访问次数等信息.
    Stores cached value, expiration time, access count, etc.
    "" __slots__ = ("key", "value", "expires_at", "access_count", "last_access")

    def __init__(self,)
    "key": str,
    "value": Any,
    "ttl": float | None = None,
    
:
        "" 初始化缓存条目

        Args:
    "key": 缓存键
    "value": 缓存值
    "ttl": 生存时间(秒)
        "" self.key = keyself.value = value

        self.expires_at = time.time() + ttl if ttl else Noneself.access_count = 0

        self.last_access = time.time()

    def is_expired(self) -> bool:
        "" 检查是否过期

        Returns:
    "bool": 是否已过期
        "" return self.expires_at is not None and time.time() > self.expires_at

    def access(self) -> Any:
        "" 访问缓存项

        更新访问统计并返回值.

        Returns:
    "Any": 缓存值
        "" self.access_count += 1
        self.last_access = time.time()
        return self.value

    def update_ttl(self, ttl: float | None = None) -> None:
        "" 更新过期时间

        Args:
    "ttl": 新的TTL(秒)
,None表示永不过期
        "" if ttl is not Noneself.expires_at = time.time() + ttl

        elseself.expires_at = None


    def get_remaining_ttl(self) -> int | None:
        "" 获取剩余TTL

        Returns:
            Optional[int]: 剩余秒数,None表示永不过期
        "" if self.expires_at is Nonereturn None

        remaining = int(self.expires_at - time.time())

        return remaining if remaining > 0 else 0

    def __lt__(self, other: "" 用于堆排序,比较过期时间)

        过期时间早的条目更小.
        "" if self.expires_at is None and other.expires_at is Nonereturn False

        if self.expires_at is Nonereturn False

        if other.expires_at is Nonereturn True

        return self.expires_at < other.expires_at

    def __repr__(self) -> str:
        """字符串表示"" ttl_str = f"TTL={self.get_remaining_ttl())
}s" if self.expires_at else "TTL=∞ return (
            f"CacheEntry(key={self.key}, value={type(self.value)))
.__name__}, {ttl_str 

""" """