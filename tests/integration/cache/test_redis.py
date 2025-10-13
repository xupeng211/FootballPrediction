"""
Redis 缓存集成测试
测试 Redis 缓存的各种功能和模式
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Optional


class TestRedisIntegration:
    """Redis 集成测试"""

    @pytest.mark.asyncio
    async def test_basic_operations(self, test_redis):
        """测试基本的 Redis 操作"""
        # SET 和 GET
        await test_redis.set("test_key", "test_value")
        value = await test_redis.get("test_key")
        assert value == "test_value"

        # SETEX（带过期时间）
        await test_redis.setex("temp_key", 1, "temp_value")
        value = await test_redis.get("temp_key")
        assert value == "temp_value"

        # 等待过期
        await asyncio.sleep(1.1)
        value = await test_redis.get("temp_key")
        assert value is None

        # EXISTS
        exists = await test_redis.exists("test_key")
        assert exists == 1

        not_exists = await test_redis.exists("non_existent_key")
        assert not_exists == 0

        # DEL
        deleted = await test_redis.delete("test_key")
        assert deleted == 1

        value = await test_redis.get("test_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_json_operations(self, test_redis):
        """测试 JSON 操作"""
        # 存储 JSON 对象
        user_data = {
            "id": 123,
            "username": "test_user",
            "email": "test@example.com",
            "preferences": {"theme": "dark", "notifications": True},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # 存储为 JSON 字符串
        await test_redis.set("user:123", json.dumps(user_data))

        # 获取并解析
        stored_data = await test_redis.get("user:123")
        parsed_data = json.loads(stored_data)

        assert parsed_data["id"] == 123
        assert parsed_data["username"] == "test_user"
        assert parsed_data["preferences"]["theme"] == "dark"

        # 部分更新（需要读取-修改-写入）
        user_data["preferences"]["theme"] = "light"
        user_data["last_login"] = datetime.now(timezone.utc).isoformat()
        await test_redis.set("user:123", json.dumps(user_data))

        # 验证更新
        updated_data = json.loads(await test_redis.get("user:123"))
        assert updated_data["preferences"]["theme"] == "light"
        assert "last_login" in updated_data

    @pytest.mark.asyncio
    async def test_list_operations(self, test_redis):
        """测试列表操作"""
        # LPUSH 和 RPUSH
        await test_redis.delete("test_list")

        await test_redis.lpush("test_list", "item1", "item2")
        await test_redis.rpush("test_list", "item3", "item4")

        # LLEN
        length = await test_redis.llen("test_list")
        assert length == 4

        # LRANGE
        items = await test_redis.lrange("test_list", 0, -1)
        assert items == ["item2", "item1", "item3", "item4"]

        # LINDEX
        item = await test_redis.lindex("test_list", 0)
        assert item == "item2"

        # LPOP
        popped = await test_redis.lpop("test_list")
        assert popped == "item2"

        # RPOP
        popped = await test_redis.rpop("test_list")
        assert popped == "item4"

        # 验证剩余项
        items = await test_redis.lrange("test_list", 0, -1)
        assert items == ["item1", "item3"]

    @pytest.mark.asyncio
    async def test_set_operations(self, test_redis):
        """测试集合操作"""
        # SADD
        await test_redis.delete("test_set")
        await test_redis.sadd("test_set", "member1", "member2", "member3")

        # SCARD
        count = await test_redis.scard("test_set")
        assert count == 3

        # SMEMBERS
        members = await test_redis.smembers("test_set")
        assert "member1" in members
        assert "member2" in members
        assert "member3" in members

        # SISMEMBER
        is_member = await test_redis.sismember("test_set", "member2")
        assert is_member == 1

        not_member = await test_redis.sismember("test_set", "member5")
        assert not_member == 0

        # SREM
        removed = await test_redis.srem("test_set", "member2")
        assert removed == 1

        # 验证移除
        is_member = await test_redis.sismember("test_set", "member2")
        assert is_member == 0

    @pytest.mark.asyncio
    async def test_sorted_set_operations(self, test_redis):
        """测试有序集合操作"""
        # ZADD
        await test_redis.delete("leaderboard")
        await test_redis.zadd(
            "leaderboard",
            {"player1": 1000, "player2": 1500, "player3": 800, "player4": 2000},
        )

        # ZCARD
        count = await test_redis.zcard("leaderboard")
        assert count == 4

        # ZRANGE（按分数范围）
        leaders = await test_redis.zrange("leaderboard", 0, -1, withscores=True)
        assert leaders[0][0] == "player3" and leaders[0][1] == 800.0
        assert leaders[-1][0] == "player4" and leaders[-1][1] == 2000.0

        # ZREVRANGE（倒序）
        top_players = await test_redis.zrevrange("leaderboard", 0, 2, withscores=True)
        assert top_players[0][0] == "player4"
        assert top_players[0][1] == 2000.0

        # ZSCORE
        score = await test_redis.zscore("leaderboard", "player2")
        assert score == 1500.0

        # ZINCRBY
        new_score = await test_redis.zincrby("leaderboard", 100, "player1")
        assert new_score == 1100.0

        # ZRANK（排名）
        rank = await test_redis.zrank("leaderboard", "player4")
        assert rank == 3  # 最高分

    @pytest.mark.asyncio
    async def test_hash_operations(self, test_redis):
        """测试哈希操作"""
        # HSET
        await test_redis.delete("user_profile:1")
        await test_redis.hset(
            "user_profile:1",
            mapping={
                "username": "john_doe",
                "email": "john@example.com",
                "age": "30",
                "city": "New York",
            },
        )

        # HGET
        username = await test_redis.hget("user_profile:1", "username")
        assert username == "john_doe"

        # HGETALL
        profile = await test_redis.hgetall("user_profile:1")
        assert profile["username"] == "john_doe"
        assert profile["email"] == "john@example.com"
        assert profile["age"] == "30"

        # HEXISTS
        exists = await test_redis.hexists("user_profile:1", "email")
        assert exists == 1

        not_exists = await test_redis.hexists("user_profile:1", "phone")
        assert not_exists == 0

        # HINCRBY
        new_age = await test_redis.hincrby("user_profile:1", "age", 1)
        assert new_age == 31

        # HDEL
        deleted = await test_redis.hdel("user_profile:1", "city")
        assert deleted == 1

        # 验证删除
        city = await test_redis.hget("user_profile:1", "city")
        assert city is None

    @pytest.mark.asyncio
    async def test_cache_patterns(self, test_redis):
        """测试缓存模式"""

        # Cache-Aside 模式
        async def get_user_from_db(user_id: int) -> dict:
            # 模拟数据库查询
            await asyncio.sleep(0.1)  # 模拟延迟
            return {
                "id": user_id,
                "username": f"user_{user_id}",
                "email": f"user{user_id}@example.com",
            }

        async def get_user_cached(user_id: int) -> Optional[dict]:
            cache_key = f"user:{user_id}"
            # 先从缓存获取
            cached_data = await test_redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data)

            # 缓存未命中，从数据库获取
            user_data = await get_user_from_db(user_id)
            if user_data:
                # 写入缓存，设置过期时间
                await test_redis.setex(
                    cache_key,
                    3600,  # 1小时
                    json.dumps(user_data),
                )
            return user_data

        # 测试缓存
        user_id = 123

        # 第一次调用（缓存未命中）
        start_time = asyncio.get_event_loop().time()
        user1 = await get_user_cached(user_id)
        first_call_time = asyncio.get_event_loop().time() - start_time

        # 第二次调用（缓存命中）
        start_time = asyncio.get_event_loop().time()
        user2 = await get_user_cached(user_id)
        second_call_time = asyncio.get_event_loop().time() - start_time

        # 验证结果一致
        assert user1 == user2
        assert user1["username"] == "user_123"

        # 验证缓存提升了性能
        assert second_call_time < first_call_time / 2

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, test_redis):
        """测试缓存失效"""

        # 写-失效模式
        async def update_user_in_db(user_id: int, data: dict):
            # 模拟数据库更新
            await asyncio.sleep(0.1)
            return True

        async def update_user(user_id: int, data: dict):
            cache_key = f"user:{user_id}"

            # 1. 更新数据库
            await update_user_in_db(user_id, data)

            # 2. 删除缓存
            await test_redis.delete(cache_key)

        # 初始化缓存
        await test_redis.setex(
            "user:456",
            3600,
            json.dumps({"id": 456, "username": "old_name", "email": "old@example.com"}),
        )

        # 验证缓存存在
        cached = await test_redis.get("user:456")
        assert cached is not None

        # 更新用户（会删除缓存）
        await update_user(456, {"username": "new_name", "email": "new@example.com"})

        # 验证缓存已删除
        cached = await test_redis.get("user:456")
        assert cached is None

    @pytest.mark.asyncio
    async def test_rate_limiting(self, test_redis):
        """测试限流功能"""

        # 滑动窗口限流
        async def is_allowed(user_id: str, limit: int, window: int) -> bool:
            key = f"rate_limit:{user_id}"
            current_time = asyncio.get_event_loop().time()

            # 使用管道提高性能
            pipe = test_redis.pipeline()

            # 清理过期记录
            pipe.zremrangebyscore(key, 0, current_time - window)

            # 添加当前请求
            pipe.zadd(key, {str(current_time): current_time})

            # 获取当前窗口内的请求数
            pipe.zcard(key)

            # 设置过期时间
            pipe.expire(key, window)

            results = await pipe.execute()
            request_count = results[2]

            return request_count <= limit

        # 测试限流
        user_id = "test_user"
        limit = 5
        window = 10  # 10秒窗口

        # 前5个请求应该通过
        for i in range(5):
            allowed = await is_allowed(user_id, limit, window)
            assert allowed is True, f"Request {i + 1} should be allowed"

        # 第6个请求应该被拒绝
        allowed = await is_allowed(user_id, limit, window)
        assert allowed is False

    @pytest.mark.asyncio
    async def test_distributed_lock(self, test_redis):
        """测试分布式锁"""
        import uuid

        lock_key = "distributed_lock:resource1"
        lock_value = str(uuid.uuid4())
        lock_ttl = 10

        async def acquire_lock(key: str, value: str, ttl: int) -> bool:
            # 使用 SET NX EX 原子操作
            _result = await test_redis.set(key, value, ex=ttl, nx=True)
            return result

        async def release_lock(key: str, value: str) -> bool:
            # Lua 脚本确保原子性
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            _result = await test_redis.eval(lua_script, 1, key, value)
            return _result == 1

        # 获取锁
        acquired = await acquire_lock(lock_key, lock_value, lock_ttl)
        assert acquired is True

        # 尝试再次获取锁（应该失败）
        lock_value2 = str(uuid.uuid4())
        acquired2 = await acquire_lock(lock_key, lock_value2, lock_ttl)
        assert acquired2 is False

        # 释放锁
        released = await release_lock(lock_key, lock_value)
        assert released is True

        # 现在应该可以获取锁
        acquired3 = await acquire_lock(lock_key, lock_value2, lock_ttl)
        assert acquired3 is True

    @pytest.mark.asyncio
    async def test_pub_sub(self, test_redis):
        """测试发布订阅"""
        # 创建发布者和订阅者
        pub = test_redis
        sub = test_redis.pubsub()

        await sub.subscribe("test_channel")

        # 等待订阅生效
        await asyncio.sleep(0.1)

        # 发布消息
        messages = [
            {"type": "notification", "message": "Hello World"},
            {"type": "alert", "level": "warning", "message": "System overload"},
            {"type": "update", "data": {"id": 123, "status": "completed"}},
        ]

        for msg in messages:
            await pub.publish("test_channel", json.dumps(msg))

        # 接收消息
        received_messages = []
        async for message in sub.listen():
            if message["type"] == "message":
                _data = json.loads(message["data"])
                received_messages.append(data)
                if len(received_messages) >= len(messages):
                    break

        # 验证消息
        assert len(received_messages) == 3
        assert received_messages[0]["type"] == "notification"
        assert received_messages[1]["level"] == "warning"
        assert received_messages[2]["data"]["id"] == 123

        # 清理
        await sub.unsubscribe("test_channel")
        await sub.close()

    @pytest.mark.asyncio
    async def test_pipeline_operations(self, test_redis):
        """测试管道操作"""
        # 准备数据
        await test_redis.delete("test_pipe")

        # 使用管道执行多个命令
        pipe = test_redis.pipeline()
        pipe.set("test_pipe:1", "value1")
        pipe.set("test_pipe:2", "value2")
        pipe.set("test_pipe:3", "value3")
        pipe.get("test_pipe:1")
        pipe.get("test_pipe:2")
        pipe.get("test_pipe:3")

        results = await pipe.execute()

        # 验证结果
        assert results[0] is True  # SET result
        assert results[1] is True
        assert results[2] is True
        assert results[3] == "value1"  # GET result
        assert results[4] == "value2"
        assert results[5] == "value3"

    @pytest.mark.asyncio
    async def test_memory_management(self, test_redis):
        """测试内存管理"""
        # 获取内存信息
        info = await test_redis.info("memory")
        assert "used_memory" in info

        # 存储大量数据
        large_data = "x" * 1000  # 1KB
        keys = []

        for i in range(100):
            key = f"large_data:{i}"
            await test_redis.set(key, large_data)
            keys.append(key)

        # 检查内存使用增加
        info_after = await test_redis.info("memory")
        assert info_after["used_memory"] > info["used_memory"]

        # 清理数据
        for key in keys:
            await test_redis.delete(key)

        # 验证清理后的内存（可能不会立即释放）
        await test_redis.dbsize()
        initial_keys = await test_redis.keys("*")
        assert "large_data:" not in str(initial_keys)
