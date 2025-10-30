# TODO: Consider creating a fixture for 7 repeated Mock creations

# TODO: Consider creating a fixture for 7 repeated Mock creations


"""
高性能 Mock 对象
优化的 mock 实现,提升测试执行速度
"""


class FastDatabaseManager:
    """快速数据库管理器 Mock"""

    def __init__(self):
        self.session_count = 0
        self.transaction_count = 0

    def get_async_session(self):
        """获取异步会话"""
        self.session_count += 1
        return FastAsyncSessionContext()

    def get_session(self):
        """获取同步会话"""
        self.session_count += 1
        return MagicMock()


class FastAsyncSessionContext:
    """快速异步会话上下文"""

    def __init__(self):
        self.session = FastAsyncSession()

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class FastAsyncSession:
    """快速异步会话 Mock"""

    def __init__(self):
        self._data = {}
        self.committed = False
        self.rolled_back = False

    # 使用简单的 MagicMock 而不是 AsyncMock 来提升性能
    def execute(self, query):
        """执行查询"""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_result.fetchall.return_value = []
        return mock_result

    def add(self, obj):
        """添加对象"""
        pass

    def commit(self):
        """提交事务"""
        self.committed = True

    def rollback(self):
        """回滚事务"""
        self.rolled_back = True

    def refresh(self, obj):
        """刷新对象"""
        pass

    def close(self):
        """关闭会话"""
        pass

    def delete(self, obj):
        """删除对象"""
        pass

    def query(self, model):
        """查询"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_query.all.return_value = []
        return mock_query


class FastRedisManager:
    """快速 Redis 管理器 Mock"""

    def __init__(self):
        self._data = {}
        self.expiry = {}
        self.operation_count = 0

    def get(self, key):
        """获取值"""
        self.operation_count += 1
        return self.data.get(key)

    def set(self, key, value, ex=None):
        """设置值"""
        self.operation_count += 1
        self.data[key] = value
        if ex:
            self.expiry[key] = ex
        return True

    def delete(self, key):
        """删除键"""
        self.operation_count += 1
        self.data.pop(key, None)
        self.expiry.pop(key, None)
        return True

    def exists(self, key):
        """检查键是否存在"""
        self.operation_count += 1
        return key in self.data

    def expire(self, key, seconds):
        """设置过期时间"""
        self.operation_count += 1
        if key in self.data:
            self.expiry[key] = seconds
            return True
        return False

    def ttl(self, key):
        """获取剩余时间"""
        self.operation_count += 1
        return self.expiry.get(key, -1)

    def incr(self, key):
        """递增"""
        self.operation_count += 1
        self.data[key] = self.data.get(key, 0) + 1
        return self.data[key]

    def decr(self, key):
        """递减"""
        self.operation_count += 1
        self.data[key] = self.data.get(key, 0) - 1
        return self.data[key]

    def hgetall(self, key):
        """获取所有哈希字段"""
        self.operation_count += 1
        return self.data.get(key, {})

    def hset(self, key, field, value):
        """设置哈希字段"""
        self.operation_count += 1
        if key not in self.data:
            self.data[key] = {}
        self.data[key][field] = value
        return True

    def zadd(self, key, score, member):
        """添加到有序集合"""
        self.operation_count += 1
        return 1

    def zrange(self, key, start, end):
        """获取有序集合范围"""
        self.operation_count += 1
        return []

    def ping(self):
        """Ping"""
        self.operation_count += 1
        return True

    def keys(self, pattern):
        """获取键列表"""
        self.operation_count += 1
        return list(self.data.keys())

    def flushall(self):
        """清空所有数据"""
        self.data.clear()
        self.expiry.clear()
        return True


class FastHTTPClient:
    """快速 HTTP 客户端 Mock"""

    def __init__(self):
        self.request_count = 0
        self.responses = []

    def get(self, url, **kwargs):
        """GET 请求"""
        self.request_count += 1
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {}
        response.text = ""
        return response

    def post(self, url, **kwargs):
        """POST 请求"""
        self.request_count += 1
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {}
        return response

    def put(self, url, **kwargs):
        """PUT 请求"""
        self.request_count += 1
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {}
        return response

    def delete(self, url, **kwargs):
        """DELETE 请求"""
        self.request_count += 1
        response = MagicMock()
        response.status_code = 204
        return response


# 预创建的实例,供测试直接使用
FAST_DB_MANAGER = FastDatabaseManager()
FAST_REDIS_MANAGER = FastRedisManager()
FAST_HTTP_CLIENT = FastHTTPClient()


def get_fast_db_manager():
    """获取快速数据库管理器实例"""
    return FAST_DB_MANAGER


def get_fast_redis_manager():
    """获取快速 Redis 管理器实例"""
    return FAST_REDIS_MANAGER


def get_fast_http_client():
    """获取快速 HTTP 客户端实例"""
    return FAST_HTTP_CLIENT
