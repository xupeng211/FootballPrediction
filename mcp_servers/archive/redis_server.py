#!/usr/bin/env python3
"""
Redis MCP Server for Football Prediction System
为Claude提供Redis缓存管理能力
"""

import asyncio
import redis
import json
import os
import logging
from typing import List, Dict, Any
from mcp.server import Server
from mcp.types import Resource, Tool, TextContent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedisMCPServer:
    def __init__(self):
        self.server = Server("redis-mcp")
        self.redis_client = None
        self.redis_config = self.get_redis_config()

    @staticmethod
    def get_redis_config() -> Dict[str, Any]:
        """从环境变量获取Redis配置"""
        return {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", 6379)),
            "db": int(os.getenv("REDIS_DB", 0)),
            "password": os.getenv("REDIS_PASSWORD", ""),
            "decode_responses": True
        }

    def connect(self) -> bool:
        """连接到Redis"""
        try:
            self.redis_client = redis.Redis(
                **self.redis_config
            )
            # 测试连接
            self.redis_client.ping()
            logger.info(f"Connected to Redis: {self.redis_config['host']}:{self.redis_config['port']}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False

    def get_redis_info(self) -> str:
        """获取Redis信息"""
        try:
            info = self.redis_client.info()
            # 只返回关键信息
            key_info = {
                "version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }

            # 计算命中率
            hits = key_info["keyspace_hits"]
            misses = key_info["keyspace_misses"]
            total = hits + misses
            if total > 0:
                key_info["hit_rate"] = f"{(hits / total * 100):.2f}%"

            return json.dumps(key_info, indent=2)
        except Exception as e:
            error_msg = f"Failed to get Redis info: {str(e)}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})

    def get_key_info(self, key: str) -> str:
        """获取键信息"""
        try:
            key_type = self.redis_client.type(key).decode('utf-8')
            ttl = self.redis_client.ttl(key)
            size = self.redis_client.memory_usage(key)

            info = {
                "key": key,
                "type": key_type,
                "ttl": ttl,
                "memory_usage": size
            }

            # 根据类型获取具体信息
            if key_type == "string":
                info["length"] = self.redis_client.strlen(key)
            elif key_type == "hash":
                info["field_count"] = self.redis_client.hlen(key)
            elif key_type == "list":
                info["length"] = self.redis_client.llen(key)
            elif key_type == "set":
                info["length"] = self.redis_client.scard(key)
            elif key_type == "zset":
                info["length"] = self.redis_client.zcard(key)

            return json.dumps(info, indent=2)
        except Exception as e:
            error_msg = f"Failed to get key info: {str(e)}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})

    def search_keys(self, pattern: str = "*", limit: int = 100) -> str:
        """搜索键"""
        try:
            keys = self.redis_client.keys(pattern)
            if limit:
                keys = keys[:limit]

            # 获取每个键的基本信息
            key_list = []
            for key in keys:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                key_list.append(key_str)

            return json.dumps({
                "pattern": pattern,
                "keys": key_list,
                "count": len(key_list)
            }, indent=2)
        except Exception as e:
            error_msg = f"Failed to search keys: {str(e)}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})

# 初始化服务器
redis_server = RedisMCPServer()

@redis_server.server.list_tools()
async def list_tools() -> List[Tool]:
    """列出可用工具"""
    return [
        Tool(
            name="redis_get",
            description="Get value from Redis by key",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Redis key"
                    }
                },
                "required": ["key"]
            }
        ),
        Tool(
            name="redis_set",
            description="Set value in Redis",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Redis key"},
                    "value": {"type": "string", "description": "Redis value"},
                    "ttl": {
                        "type": "integer",
                        "description": "Time to live in seconds (optional)"
                    }
                },
                "required": ["key", "value"]
            }
        ),
        Tool(
            name="redis_delete",
            description="Delete key from Redis",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Redis key to delete"}
                },
                "required": ["key"]
            }
        ),
        Tool(
            name="redis_info",
            description="Get Redis server information",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="redis_key_info",
            description="Get detailed information about a specific key",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Redis key"}
                },
                "required": ["key"]
            }
        ),
        Tool(
            name="redis_search",
            description="Search Redis keys by pattern",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Search pattern (e.g., 'prediction:*')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of keys to return",
                        "default": 100
                    }
                },
                "required": ["pattern"]
            }
        ),
        Tool(
            name="redis_flushall",
            description="Clear all keys in current database (use with caution!)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="check_connection",
            description="Test Redis connection",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@redis_server.server.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """执行工具调用"""
    try:
        if name == "redis_get":
            value = redis_server.redis_client.get(arguments["key"])
            if value:
                value = value.decode('utf-8') if isinstance(value, bytes) else value
            result = json.dumps({
                "key": arguments["key"],
                "value": value,
                "exists": True
            }, indent=2)

        elif name == "redis_set":
            key = arguments["key"]
            value = arguments["value"]
            ttl = arguments.get("ttl")

            if ttl:
                result = redis_server.redis_client.setex(key, ttl, value)
            else:
                result = redis_server.redis_client.set(key, value)

            response = json.dumps({
                "key": key,
                "value": value,
                "success": bool(result),
                "ttl": ttl
            }, indent=2)

        elif name == "redis_delete":
            result = redis_server.redis_client.delete(arguments["key"])
            response = json.dumps({
                "key": arguments["key"],
                "deleted": result,
                "success": bool(result)
            }, indent=2)

        elif name == "redis_info":
            response = redis_server.get_redis_info()

        elif name == "redis_key_info":
            response = redis_server.get_key_info(arguments["key"])

        elif name == "redis_search":
            pattern = arguments["pattern"]
            limit = arguments.get("limit", 100)
            response = redis_server.search_keys(pattern, limit)

        elif name == "redis_flushall":
            result = redis_server.redis_client.flushdb()
            response = json.dumps({
                "success": bool(result),
                "message": "All keys cleared from current database"
            })

        elif name == "check_connection":
            if redis_server.connect():
                response = json.dumps({
                    "status": "connected",
                    "config": redis_server.redis_config
                }, indent=2)
            else:
                response = json.dumps({
                    "status": "failed",
                    "config": redis_server.redis_config
                }, indent=2)

        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(type="text", text=response)]

    except Exception as e:
        error_msg = f"Tool execution failed: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]

@redis_server.server.list_resources()
async def list_resources() -> List[Resource]:
    """列出可用资源"""
    return [
        Resource(
            uri="redis://info",
            name="Redis Server Info",
            description="Redis server information and statistics",
            mimeType="application/json"
        ),
        Resource(
            uri="redis://cache/predictions",
            name="Prediction Cache",
            description="Cached prediction results",
            mimeType="application/json"
        ),
        Resource(
            uri="redis://cache/features",
            name="Feature Cache",
            description="Cached feature data",
            mimeType="application/json"
        )
    ]

@redis_server.server.read_resource()
async def read_resource(uri: str) -> str:
    """读取资源"""
    try:
        if uri == "redis://info":
            return redis_server.get_redis_info()
        elif uri == "redis://cache/predictions":
            # 搜索预测相关的键
            return redis_server.search_keys("prediction:*", 50)
        elif uri == "redis://cache/features":
            # 搜索特征相关的键
            return redis_server.search_keys("feature:*", 50)
        else:
            raise ValueError(f"Unknown resource: {uri}")
    except Exception as e:
        return f"Failed to read resource {uri}: {str(e)}"

async def main():
    """启动MCP服务器"""
    logger.info("Starting Redis MCP Server...")

    # 尝试连接Redis
    if redis_server.connect():
        logger.info("Redis connection successful")
    else:
        logger.error("Failed to connect to Redis, but server will start anyway")

    # 启动服务器
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await redis_server.server.run(
            read_stream,
            write_stream,
            redis_server.server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())