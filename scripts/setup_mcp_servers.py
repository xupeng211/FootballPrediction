#!/usr/bin/env python3
"""
Setup MCP Servers for Football Prediction System
安装和配置MCP服务器以增强AI编程能力
"""

import subprocess
import os
import sys
from pathlib import Path

def install_npm_packages():
    """安装必要的npm包"""
    packages = [
        "@modelcontextprotocol/server-filesystem",
        "@modelcontextprotocol/server-git"
    ]

    print("📦 Installing NPM packages...")
    for package in packages:
        try:
            subprocess.run(["npm", "install", "-g", package], check=True)
            print(f"✅ Installed {package}")
        except subprocess.CalledProcessError:
            print(f"⚠️  Failed to install {package}")

def setup_postgres_mcp():
    """设置PostgreSQL MCP服务器"""
    print("\n🐘 Setting up PostgreSQL MCP Server...")

    server_code = '''
import asyncio
import asyncpg
import sys
from mcp.server import Server
from mcp.types import Resource, Tool, TextContent
import os

class PostgresMCPServer:
    def __init__(self):
        self.server = Server("postgres-mcp")
        self.pool = None

    async def connect(self):
        """连接到PostgreSQL"""
        db_url = os.getenv("DATABASE_URL") or (
            f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@"
            f"{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
        )
        self.pool = await asyncpg.create_pool(db_url)

    async def query_database(self, query: str) -> str:
        """执行查询"""
        async with self.pool.acquire() as conn:
            result = await conn.fetch(query)
            return "\\n".join([str(row) for row in result])

# 注册工具
server = PostgresMCPServer().server

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="query_postgres",
            description="Execute PostgreSQL queries",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL query to execute"}
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "query_postgres":
        pg_server = PostgresMCPServer()
        await pg_server.connect()
        result = await pg_server.query_database(arguments["query"])
        return [TextContent(type="text", text=result)]
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
'''

    with open("postgres_mcp_server.py", "w") as f:
        f.write(server_code)

    print("✅ Created postgres_mcp_server.py")

def setup_redis_mcp():
    """设置Redis MCP服务器"""
    print("\n🔴 Setting up Redis MCP Server...")

    server_code = '''
import asyncio
import redis
import json
from mcp.server import Server
from mcp.types import Tool, TextContent
import os

class RedisMCPServer:
    def __init__(self):
        self.server = Server("redis-mcp")
        self.redis_client = None

    def connect(self):
        """连接到Redis"""
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", 6379))
        db = int(os.getenv("REDIS_DB", 0))
        password = os.getenv("REDIS_PASSWORD")

        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password if password else None,
            decode_responses=True
        )

    def get_info(self) -> str:
        """获取Redis信息"""
        info = self.redis_client.info()
        return json.dumps(info, indent=2)

# 注册服务器
server = RedisMCPServer().server

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="redis_get",
            description="Get value from Redis",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Redis key"}
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
                    "value": {"type": "string", "description": "Redis value"}
                },
                "required": ["key", "value"]
            }
        ),
        Tool(
            name="redis_info",
            description="Get Redis server information",
            inputSchema={"type": "object", "properties": {}}
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    redis_server = RedisMCPServer()
    redis_server.connect()

    if name == "redis_get":
        value = redis_server.redis_client.get(arguments["key"])
        return [TextContent(type="text", text=value or "")]
    elif name == "redis_set":
        redis_server.redis_client.set(arguments["key"], arguments["value"])
        return [TextContent(type="text", text=f"Set {arguments['key']}")]
    elif name == "redis_info":
        info = redis_server.get_info()
        return [TextContent(type="text", text=info)]
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
'''

    with open("redis_mcp_server.py", "w") as f:
        f.write(server_code)

    print("✅ Created redis_mcp_server.py")

def create_claude_config():
    """创建Claude配置文件"""
    print("\n⚙️  Creating Claude configuration...")

    config_content = '''
{
  "skills": {
    "enabled": true,
    "autoLoad": true
  },
  "mcpServers": {
    "postgres": {
      "command": "python",
      "args": ["-m", "postgres_mcp_server"]
    },
    "redis": {
      "command": "python",
      "args": ["-m", "redis_mcp_server"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "."]
    },
    "git": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-git", "."]
    }
  }
}
'''

    with open(".claude/settings.json", "w") as f:
        f.write(config_content)

    print("✅ Created .claude/settings.json")

def main():
    print("🚀 Setting up MCP Servers for Football Prediction System")
    print("=" * 60)

    # 安装npm包
    install_npm_packages()

    # 设置PostgreSQL MCP
    setup_postgres_mcp()

    # 设置Redis MCP
    setup_redis_mcp()

    # 创建配置文件
    create_claude_config()

    print("\n✅ MCP Servers setup complete!")
    print("\n📋 Next steps:")
    print("1. Export environment variables:")
    print("   export DATABASE_URL=postgresql://user:pass@localhost:5432/football_prediction")
    print("   export REDIS_HOST=localhost")
    print("   export REDIS_PORT=6379")
    print("\n2. Restart Claude Code to load MCP servers")
    print("3. Test with: '查询数据库中最新的10场比赛'")
    print("4. Test with: '检查Redis缓存状态'")

if __name__ == "__main__":
    main()