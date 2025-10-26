"""
高性能 Mock 对象
提供预配置的高性能 Mock 对象，用于测试环境
"""

from unittest.mock import Mock, AsyncMock
import asyncio
from typing import Any, Dict, List, Optional


class FastDatabaseManager:
    """高性能数据库管理器 Mock"""

    def __init__(self):
        self.session = Mock()
        self.engine = Mock()
        self.connection_pool = Mock()

    async def execute(self, query: str, params: Dict = None) -> Any:
        """模拟数据库查询执行"""
        return Mock()

    async def fetch_all(self, query: str, params: Dict = None) -> List[Dict]:
        """模拟获取所有结果"""
        return []

    async def fetch_one(self, query: str, params: Dict = None) -> Optional[Dict]:
        """模拟获取单个结果"""
        return None


class FastRedisManager:
    """高性能 Redis 管理器 Mock"""

    def __init__(self):
        self.client = Mock()
        self.connection_pool = Mock()

    async def get(self, key: str) -> Optional[str]:
        """模拟 Redis GET 操作"""
        return None

    async def set(self, key: str, value: str, expire: int = None) -> bool:
        """模拟 Redis SET 操作"""
        return True

    async def delete(self, key: str) -> bool:
        """模拟 Redis DELETE 操作"""
        return True

    async def exists(self, key: str) -> bool:
        """模拟 Redis EXISTS 操作"""
        return False


class FastAsyncSession:
    """高性能异步会话 Mock"""

    def __init__(self):
        self.session_id = "mock_session_12345"
        self.user_data = {}
        self.is_active = True

    async def get(self, key: str, default: Any = None) -> Any:
        """模拟会话数据获取"""
        return self.user_data.get(key, default)

    async def set(self, key: str, value: Any) -> None:
        """模拟会话数据设置"""
        self.user_data[key] = value

    async def delete(self, key: str) -> None:
        """模拟会话数据删除"""
        self.user_data.pop(key, None)

    async def clear(self) -> None:
        """模拟会话清空"""
        self.user_data.clear()

    async def destroy(self) -> None:
        """模拟会话销毁"""
        self.is_active = False


class FastHTTPClient:
    """高性能 HTTP 客户端 Mock"""

    def __init__(self):
        self.session = Mock()
        self.response_cache = {}

    async def get(self, url: str, headers: Dict = None, timeout: int = 30) -> Mock:
        """模拟 HTTP GET 请求"""
        response = Mock()
        response.status_code = 200
        response.json = AsyncMock(return_value={})
        response.text = ""
        response.headers = {}
        return response

    async def post(self, url: str, data: Dict = None, json: Dict = None,
                  headers: Dict = None, timeout: int = 30) -> Mock:
        """模拟 HTTP POST 请求"""
        response = Mock()
        response.status_code = 200
        response.json = AsyncMock(return_value={})
        response.text = ""
        response.headers = {}
        return response

    async def put(self, url: str, data: Dict = None, json: Dict = None,
                 headers: Dict = None, timeout: int = 30) -> Mock:
        """模拟 HTTP PUT 请求"""
        response = Mock()
        response.status_code = 200
        response.json = AsyncMock(return_value={})
        response.text = ""
        response.headers = {}
        return response

    async def delete(self, url: str, headers: Dict = None, timeout: int = 30) -> Mock:
        """模拟 HTTP DELETE 请求"""
        response = Mock()
        response.status_code = 204
        response.json = AsyncMock(return_value={})
        response.text = ""
        response.headers = {}
        return response