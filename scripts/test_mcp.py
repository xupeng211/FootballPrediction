#!/usr/bin/env python3
"""
MCP服务器配置验证脚本
测试所有MCP服务器是否能正确初始化和提供工具
"""

import asyncio
import json
import sys
import os

# 添加mcp_servers到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_postgres_server():
    """测试PostgreSQL MCP服务器"""
    print("🔍 测试PostgreSQL MCP服务器...")
    try:
        from mcp_servers.postgres_server import PostgresMCPServer

        server = PostgresMCPServer()

        # 测试工具列表
        list_tools_func = server.server.list_tools()
        tools = await list_tools_func()
        print(f"  ✅ 工具数量: {len(tools)}")
        for tool in tools:
            print(f"    - {tool.name}: {tool.description}")

        # 测试连接（可能失败，这是正常的）
        connected = await server.connect()
        if connected:
            print("  ✅ 数据库连接成功")
        else:
            print("  ⚠️ 数据库连接失败（可能未启动数据库）")

        return True
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False


async def test_redis_server():
    """测试Redis MCP服务器"""
    print("\n🔍 测试Redis MCP服务器...")
    try:
        from mcp_servers.redis_server import RedisMCPServer

        server = RedisMCPServer()

        # 测试工具列表
        list_tools_func = server.server.list_tools()
        tools = await list_tools_func()
        print(f"  ✅ 工具数量: {len(tools)}")
        for tool in tools:
            print(f"    - {tool.name}: {tool.description}")

        # 测试连接（可能失败，这是正常的）
        connected = server.connect()
        if connected:
            print("  ✅ Redis连接成功")
        else:
            print("  ⚠️ Redis连接失败（可能未启动Redis）")

        return True
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False


async def test_filesystem_server():
    """测试文件系统MCP服务器"""
    print("\n🔍 测试文件系统MCP服务器...")
    try:
        from mcp_servers.filesystem_server import FileSystemMCPServer

        server = FileSystemMCPServer()

        # 测试工具列表
        list_tools_func = server.server.list_tools()
        tools = await list_tools_func()
        print(f"  ✅ 工具数量: {len(tools)}")
        for tool in tools:
            print(f"    - {tool.name}: {tool.description}")

        # 测试基本功能
        result = server.list_directory(".")
        data = json.loads(result)
        if "items" in data:
            print(f"  ✅ 文件系统访问正常，找到 {data['count']} 个项目")
        else:
            print("  ⚠️ 文件系统访问异常")

        return True
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False


async def test_claude_settings():
    """测试Claude配置文件"""
    print("\n🔍 测试Claude配置...")
    try:
        with open(".claude/settings.json", "r", encoding="utf-8") as f:
            settings = json.load(f)

        # 检查MCP服务器配置
        if "mcpServers" in settings:
            mcp_servers = settings["mcpServers"]
            print(f"  ✅ MCP服务器数量: {len(mcp_servers)}")
            for name, config in mcp_servers.items():
                print(f"    - {name}: {config.get('command', 'N/A')}")
        else:
            print("  ❌ 未找到MCP服务器配置")
            return False

        # 检查技能配置
        if "skills" in settings:
            skills = settings["skills"]
            enabled = skills.get("enabled", False)
            print(f"  ✅ 技能系统: {'启用' if enabled else '禁用'}")
            if enabled and "priority" in skills:
                print(f"    优先级技能: {', '.join(skills['priority'])}")

        return True
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False


async def main():
    """主测试函数"""
    print("🚀 MCP配置验证开始...\n")

    results = []

    # 测试各个MCP服务器
    results.append(await test_postgres_server())
    results.append(await test_redis_server())
    results.append(await test_filesystem_server())
    results.append(await test_claude_settings())

    # 汇总结果
    passed = sum(results)
    total = len(results)

    print(f"\n📊 测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有MCP配置验证通过！")
        print("\n📝 下一步:")
        print("1. 启动数据库和Redis服务")
        print("2. 重启Claude Code以加载MCP配置")
        print("3. 开始使用MCP工具")
    else:
        print("⚠️ 部分测试失败，请检查配置")

    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
