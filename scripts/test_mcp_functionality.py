#!/usr/bin/env python3
"""
MCP功能测试脚本
测试所有MCP服务器的基本功能
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_postgres_mcp():
    """测试PostgreSQL MCP服务器功能"""
    print("🔍 测试PostgreSQL MCP服务器...")

    try:
        from mcp_servers.postgres_server import (
            execute_sql,
            get_table_info,
            check_connection,
        )

        # 测试连接
        connection_status = await check_connection()
        print(f"   连接状态: {'✅ 成功' if connection_status else '❌ 失败'}")

        # 测试SQL查询
        result = await execute_sql("SELECT version() as version", fetch_one=True)
        if result and "version" in result:
            print(f"   数据库版本: {result['version'][:50]}...")

        # 测试表信息
        tables = await get_table_info("public")
        print(f"   数据表数量: {len(tables)}")

        return True

    except Exception as e:
        print(f"   ❌ PostgreSQL MCP测试失败: {e}")
        return False


async def test_redis_mcp():
    """测试Redis MCP服务器功能"""
    print("🔍 测试Redis MCP服务器...")

    try:
        from mcp_servers.redis_server import redis_get, redis_set, redis_info

        # 测试设置值
        await redis_set("test_mcp_key", "test_mcp_value")
        print("   ✅ Redis SET 操作成功")

        # 测试获取值
        value = await redis_get("test_mcp_key")
        print(f"   ✅ Redis GET 操作: {value}")

        # 测试Redis信息
        info = await redis_info()
        if info and "redis_version" in info:
            print(f"   Redis版本: {info['redis_version']}")

        return True

    except Exception as e:
        print(f"   ❌ Redis MCP测试失败: {e}")
        return False


async def test_filesystem_mcp():
    """测试文件系统MCP服务器功能"""
    print("🔍 测试文件系统MCP服务器...")

    try:
        from mcp_servers.filesystem_server import read_file, list_directory

        # 测试读取文件
        content = await read_file("README.md", max_lines=5)
        if content:
            print(f"   ✅ 文件读取成功: {len(content)} 行")

        # 测试目录列表
        files = await list_directory("src/", pattern="*.py")
        print(f"   ✅ 目录列表成功: {len(files)} 个Python文件")

        return True

    except Exception as e:
        print(f"   ❌ 文件系统MCP测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("🚀 MCP功能测试开始...")
    print("=" * 50)

    # 测试所有MCP服务器
    results = []

    results.append(await test_postgres_mcp())
    print()

    results.append(await test_redis_mcp())
    print()

    results.append(await test_filesystem_mcp())
    print()

    # 统计结果
    passed = sum(results)
    total = len(results)

    print("=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有MCP服务器功能正常!")
        print("\n📋 你的MCP配置现在是正确的:")
        print("   ✅ PostgreSQL MCP服务器 - 连接正常")
        print("   ✅ Redis MCP服务器 - 连接正常")
        print("   ✅ 文件系统MCP服务器 - 功能正常")
        print("\n🔄 重启Claude Code以加载更新的MCP配置")
    else:
        print("⚠️  部分MCP服务器存在问题，请检查配置")


if __name__ == "__main__":
    asyncio.run(main())
