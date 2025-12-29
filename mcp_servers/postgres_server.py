#!/usr/bin/env python3
"""
PostgreSQL MCP Server for Football Prediction System
为Claude提供PostgreSQL数据库访问能力
"""

import asyncio
import json
import logging
import os
from typing import Any

import asyncpg
from mcp.server import Server
from mcp.types import Resource, TextContent, Tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PostgresMCPServer:
    def __init__(self):
        self.server = Server("postgres-mcp")
        self.pool = None
        self.db_config = self.get_db_config()

    @staticmethod
    def get_db_config() -> dict[str, Any]:
        """从环境变量获取数据库配置"""
        return {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", 5432)),
            "database": os.getenv("DB_NAME", "football_prediction_dev"),
            "user": os.getenv("DB_USER", "football_user"),
            "password": os.getenv("DB_PASSWORD", "football_pass"),
        }

    async def connect(self):
        """连接到PostgreSQL数据库"""
        try:
            dsn = (
                f"postgresql://{self.db_config['user']}:{self.db_config['password']}@"
                f"{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
            )
            self.pool = await asyncpg.create_pool(dsn, min_size=1, max_size=10, command_timeout=60)
            logger.info(f"Connected to PostgreSQL: {self.db_config['host']}:{self.db_config['port']}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return False

    async def execute_query(self, query: str, params: list = None) -> str:
        """执行SQL查询"""
        try:
            async with self.pool.acquire() as conn:
                if params:
                    result = await conn.fetch(query, *params)
                else:
                    result = await conn.fetch(query)

                # 格式化结果
                if result:
                    columns = [desc.name for desc in result[0]._asdict().keys()]
                    rows = [dict(row) for row in result]
                    return json.dumps({"columns": columns, "rows": rows, "count": len(rows)}, indent=2)
                else:
                    return json.dumps({"message": "Query executed successfully", "count": 0})
        except Exception as e:
            error_msg = f"Query failed: {str(e)}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})

    async def get_table_info(self, table_name: str) -> str:
        """获取表结构信息"""
        query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = $1
        ORDER BY ordinal_position;
        """
        return await self.execute_query(query, [table_name])

    async def get_schema_info(self) -> str:
        """获取数据库schema信息"""
        query = """
        SELECT table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
        """
        return await self.execute_query(query)


# 初始化服务器
postgres_server = PostgresMCPServer()


# Set up the server
@postgres_server.server.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用工具"""
    return [
        Tool(
            name="execute_sql",
            description="Execute SQL query on PostgreSQL database",
            inputSchema={
                "type": "object",
                "properties": {"query": {"type": "string", "description": "SQL query to execute"}},
                "required": ["query"],
            },
        ),
        Tool(
            name="get_table_info",
            description="Get table structure information",
            inputSchema={
                "type": "object",
                "properties": {"table_name": {"type": "string", "description": "Name of the table"}},
                "required": ["table_name"],
            },
        ),
        Tool(
            name="get_schema_info",
            description="Get database schema information",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="check_connection",
            description="Test database connection",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@postgres_server.server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """执行工具调用"""
    try:
        if name == "execute_sql":
            result = await postgres_server.execute_query(arguments["query"])
            return [TextContent(type="text", text=result)]

        elif name == "get_table_info":
            result = await postgres_server.get_table_info(arguments["table_name"])
            return [TextContent(type="text", text=result)]

        elif name == "get_schema_info":
            result = await postgres_server.get_schema_info()
            return [TextContent(type="text", text=result)]

        elif name == "check_connection":
            if await postgres_server.connect():
                result = json.dumps({"status": "connected", "config": postgres_server.db_config}, indent=2)
            else:
                result = json.dumps({"status": "failed", "config": postgres_server.db_config}, indent=2)
            return [TextContent(type="text", text=result)]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        error_msg = f"Tool execution failed: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]


@postgres_server.server.list_resources()
async def list_resources() -> list[Resource]:
    """列出可用资源"""
    resources = [
        Resource(
            uri="postgres://schema",
            name="Database Schema",
            description="Database schema information",
            mimeType="application/json",
        ),
        Resource(
            uri="postgres://tables/matches",
            name="Matches Table",
            description="Football matches table",
            mimeType="application/json",
        ),
        Resource(
            uri="postgres://tables/predictions",
            name="Predictions Table",
            description="Prediction results table",
            mimeType="application/json",
        ),
    ]
    return resources


@postgres_server.server.read_resource()
async def read_resource(uri: str) -> str:
    """读取资源"""
    if uri == "postgres://schema":
        return await postgres_server.get_schema_info()
    elif uri == "postgres://tables/matches":
        return await postgres_server.get_table_info("matches")
    elif uri == "postgres://tables/predictions":
        return await postgres_server.get_table_info("predictions")
    else:
        raise ValueError(f"Unknown resource: {uri}")


async def main():
    """启动MCP服务器"""
    logger.info("Starting PostgreSQL MCP Server...")

    # 尝试连接数据库
    if await postgres_server.connect():
        logger.info("Database connection successful")
    else:
        logger.error("Failed to connect to database, but server will start anyway")

    # 启动服务器
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await postgres_server.server.run(
            read_stream, write_stream, postgres_server.server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
