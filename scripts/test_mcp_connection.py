#!/usr/bin/env python3
"""
MCP连接测试脚本
验证PostgreSQL和Redis连接
"""

import os
import asyncio
import psycopg2
import redis
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

print("🔍 MCP连接测试开始...")
print("=" * 50)

# 1. 测试PostgreSQL连接
print("\n📊 PostgreSQL连接测试:")
try:
    # 从容器内部测试
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="football_prediction_dev",
        user="football_user",
        password="football_pass",
    )

    with conn.cursor() as cur:
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"✅ PostgreSQL连接成功!")
        print(f"   版本: {version[0]}")

        cur.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
        )
        table_count = cur.fetchone()[0]
        print(f"   数据表数量: {table_count}")

    conn.close()

except Exception as e:
    print(f"❌ PostgreSQL连接失败: {e}")

# 2. 测试Redis连接
print("\n📊 Redis连接测试:")
try:
    r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

    # 测试连接
    r.ping()
    print("✅ Redis连接成功!")

    # 测试基本操作
    r.set("test_key", "test_value")
    value = r.get("test_key")
    print(f"   基本操作测试: {value}")

    # 获取信息
    info = r.info()
    print(f"   Redis版本: {info.get('redis_version', 'unknown')}")

except Exception as e:
    print(f"❌ Redis连接失败: {e}")

# 3. 环境变量检查
print("\n🌍 环境变量检查:")
env_vars = [
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "REDIS_HOST",
    "REDIS_PORT",
    "REDIS_DB",
]

for var in env_vars:
    value = os.environ.get(var, "未设置")
    status = "✅" if value != "未设置" else "⚠️"
    print(f"   {status} {var}: {value}")

print("\n🎯 MCP配置建议:")
print("1. 确保Docker服务运行: docker-compose up -d")
print("2. 设置正确的环境变量")
print("3. 检查防火墙设置")
print("4. 验证端口映射: docker-compose port")

print("\n📋 测试完成!")
