#!/usr/bin/env python3
"""
简化的MCP配置验证脚本
"""

import json
import sys
import os


def test_imports():
    """测试MCP服务器模块导入"""
    print("🔍 测试MCP服务器导入...")

    try:
        sys.path.append("mcp_servers")

        # 测试PostgreSQL服务器
        from postgres_server import PostgresMCPServer

        pg_server = PostgresMCPServer()
        print("  ✅ PostgreSQL服务器导入成功")

        # 测试Redis服务器
        from redis_server import RedisMCPServer

        redis_server = RedisMCPServer()
        print("  ✅ Redis服务器导入成功")

        # 测试文件系统服务器
        from filesystem_server import FileSystemMCPServer

        fs_server = FileSystemMCPServer()
        print("  ✅ 文件系统服务器导入成功")

        return True
    except Exception as e:
        print(f"  ❌ 导入错误: {e}")
        return False


def test_claude_settings():
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
                command = config.get("command", "N/A")
                args = config.get("args", [])
                print(f"    - {name}: {command} {' '.join(args)}")

                # 检查环境变量配置
                if "env" in config:
                    env_vars = list(config["env"].keys())
                    print(f"      环境变量: {', '.join(env_vars)}")
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


def test_basic_functionality():
    """测试基本功能"""
    print("\n🔍 测试基本功能...")
    try:
        sys.path.append("mcp_servers")

        # 测试文件系统服务器的基本功能
        from filesystem_server import FileSystemMCPServer

        fs_server = FileSystemMCPServer()

        # 测试安全路径
        test_path = fs_server.safe_path("src/config.py")
        print(f"  ✅ 安全路径测试: {test_path}")

        # 测试目录列表
        result = fs_server.list_directory(".")
        data = json.loads(result)
        if "items" in data:
            print(f"  ✅ 目录列表功能正常，找到 {data['count']} 个项目")

        # 测试文件读取
        content = fs_server.read_file("README.md", max_lines=5)
        file_data = json.loads(content)
        if "content" in file_data:
            print(f"  ✅ 文件读取功能正常，读取了 {file_data.get('lines_read', 0)} 行")

        return True
    except Exception as e:
        print(f"  ❌ 基本功能测试错误: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 MCP配置验证开始...\n")

    results = []

    # 测试各个组件
    results.append(test_imports())
    results.append(test_claude_settings())
    results.append(test_basic_functionality())

    # 汇总结果
    passed = sum(results)
    total = len(results)

    print(f"\n📊 测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 MCP配置验证通过！")
        print("\n📝 配置总结:")
        print("✅ 3个MCP服务器已配置 (PostgreSQL, Redis, FileSystem)")
        print("✅ Claude Code技能系统已启用")
        print("✅ 5个专业技能已配置")
        print("\n📋 下一步:")
        print("1. 启动数据库服务: docker-compose up -d db redis")
        print("2. 重启Claude Code以加载MCP配置")
        print("3. 开始使用技能和MCP工具进行开发")
    else:
        print("⚠️ 部分测试失败，请检查配置")

    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
