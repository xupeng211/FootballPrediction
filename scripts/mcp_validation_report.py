#!/usr/bin/env python3
"""
MCP配置验证报告
为用户提供清晰的MCP配置状态和修复建议
"""

import os
import json
import subprocess
import asyncio
from pathlib import Path

def print_header(title):
    """打印标题"""
    print(f"\n{'=' * 60}")
    print(f"🎯 {title}")
    print('=' * 60)

def print_success(message):
    print(f"✅ {message}")

def print_warning(message):
    print(f"⚠️  {message}")

def print_error(message):
    print(f"❌ {message}")

def check_mcp_config():
    """检查MCP配置文件"""
    print_header("MCP配置文件检查")

    config_file = Path(".claude/mcp-config.json")

    if not config_file.exists():
        print_error("MCP配置文件不存在")
        return False

    try:
        with open(config_file, 'r') as f:
            config = json.load(f)

        servers = config.get('mcpServers', {})
        print_success(f"MCP配置文件存在，包含 {len(servers)} 个服务器")

        expected_servers = ['postgres', 'redis', 'filesystem', 'system_monitor', 'git']

        for server_name in expected_servers:
            if server_name in servers:
                server_config = servers[server_name]
                command = server_config.get('command', '')
                args = server_config.get('args', [])

                if server_name in ['postgres', 'redis', 'filesystem']:
                    if args and args[0].endswith('.py') and Path(args[0]).exists():
                        print_success(f"  {server_name}: 配置正确")
                    else:
                        print_warning(f"  {server_name}: Python文件不存在")
                else:
                    print_success(f"  {server_name}: 配置正确")
            else:
                print_error(f"  {server_name}: 未配置")

        return True

    except Exception as e:
        print_error(f"读取MCP配置文件失败: {e}")
        return False

def check_docker_services():
    """检查Docker服务状态"""
    print_header("Docker服务检查")

    try:
        # 检查Docker容器状态
        result = subprocess.run(
            ['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}'],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')

            # 查找关键服务
            db_running = any('db' in line and 'Up' in line for line in lines)
            redis_running = any('redis' in line and 'Up' in line for line in lines)

            if db_running:
                print_success("PostgreSQL容器运行中")
            else:
                print_error("PostgreSQL容器未运行")

            if redis_running:
                print_success("Redis容器运行中")
            else:
                print_error("Redis容器未运行")

            return db_running and redis_running
        else:
            print_error("无法获取Docker状态")
            return False

    except Exception as e:
        print_error(f"检查Docker服务失败: {e}")
        return False

def check_port_connectivity():
    """检查端口连接性"""
    print_header("端口连接性检查")

    import socket

    ports_to_check = [
        ('PostgreSQL', 'localhost', 5432),
        ('Redis', 'localhost', 6379)
    ]

    all_connected = True

    for service_name, host, port in ports_to_check:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                print_success(f"{service_name} ({host}:{port}) - 连接成功")
            else:
                print_error(f"{service_name} ({host}:{port}) - 连接失败")
                all_connected = False

        except Exception as e:
            print_error(f"{service_name} ({host}:{port}) - 检查失败: {e}")
            all_connected = False

    return all_connected

def check_mcp_servers():
    """检查MCP服务器文件"""
    print_header("MCP服务器文件检查")

    server_files = [
        'mcp_servers/postgres_server.py',
        'mcp_servers/redis_server.py',
        'mcp_servers/filesystem_server.py',
        'mcp_servers/system_monitor_server.py'
    ]

    all_exist = True

    for server_file in server_files:
        if Path(server_file).exists():
            print_success(f"{server_file} - 存在")
        else:
            print_error(f"{server_file} - 不存在")
            all_exist = False

    return all_exist

def check_environment_variables():
    """检查环境变量"""
    print_header("环境变量检查")

    required_vars = [
        'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
        'REDIS_HOST', 'REDIS_PORT', 'REDIS_DB'
    ]

    all_set = True

    for var in required_vars:
        value = os.getenv(var)
        if value:
            print_success(f"{var} - 已设置")
        else:
            print_warning(f"{var} - 未设置")
            all_set = False

    return all_set

def generate_report():
    """生成完整的MCP验证报告"""
    print("🚀 Football Prediction System - MCP配置验证报告")
    print("生成时间:", subprocess.run(['date'], capture_output=True, text=True).stdout.strip())

    # 执行各项检查
    results = {
        'MCP配置': check_mcp_config(),
        'Docker服务': check_docker_services(),
        '端口连接': check_port_connectivity(),
        '服务器文件': check_mcp_servers(),
        '环境变量': check_environment_variables()
    }

    # 总结
    print_header("验证总结")

    passed_checks = sum(results.values())
    total_checks = len(results)

    for category, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{category}: {status}")

    print(f"\n📊 总体结果: {passed_checks}/{total_checks} 项检查通过")

    # 修复建议
    print_header("修复建议")

    if not results['Docker服务']:
        print("🔧 启动Docker服务:")
        print("   docker-compose up -d")
        print()

    if not results['端口连接']:
        print("🔧 检查端口映射:")
        print("   docker-compose down")
        print("   docker-compose up -d")
        print()

    if not results['环境变量']:
        print("🔧 设置环境变量:")
        print("   export DB_HOST=localhost")
        print("   export DB_PORT=5432")
        print("   export DB_NAME=football_prediction_dev")
        print("   export DB_USER=football_user")
        print("   export DB_PASSWORD=football_pass")
        print("   export REDIS_HOST=localhost")
        print("   export REDIS_PORT=6379")
        print("   export REDIS_DB=0")
        print()

    if passed_checks == total_checks:
        print("🎉 所有检查通过！你的MCP配置是正确的。")
        print("\n📋 下一步:")
        print("1. 重启Claude Code以加载更新的MCP配置")
        print("2. 使用 /mcp 命令检查MCP服务器连接状态")
        print("3. 开始使用MCP工具进行开发")
    else:
        print("⚠️  请按照上述建议修复配置问题后重新运行验证。")

if __name__ == "__main__":
    generate_report()