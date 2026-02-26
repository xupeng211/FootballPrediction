#!/usr/bin/env python3
"""
Docker MCP Server - 容器管理服务器
====================================
提供 Docker 和 Docker Compose 管理功能
限制: 仅允许访问当前项目的 docker-compose
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# MCP SDK
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("请安装 MCP SDK: pip install mcp", file=sys.stderr)
    sys.exit(1)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"

# 允许的服务列表 (基于项目 docker-compose.yml)
ALLOWED_SERVICES = [
    "db", "redis", "pipeline_worker", "predictor_api",
    "dashboard", "pgadmin", "redis-commander", "db_backup",
    "odds_scraper", "production_cron"
]

# 创建 MCP 服务器实例
server = Server("docker-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用工具"""
    return [
        Tool(
            name="docker_ps",
            description="列出当前项目相关容器状态",
            inputSchema={
                "type": "object",
                "properties": {
                    "all": {
                        "type": "boolean",
                        "description": "显示所有容器 (包括停止的)",
                        "default": False
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="docker_logs",
            description="获取容器日志",
            inputSchema={
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": f"服务名称: {', '.join(ALLOWED_SERVICES)}",
                        "enum": ALLOWED_SERVICES
                    },
                    "tail": {
                        "type": "integer",
                        "description": "显示最后 N 行",
                        "default": 100
                    },
                    "follow": {
                        "type": "boolean",
                        "description": "实时跟踪 (仅返回初始日志)",
                        "default": False
                    }
                },
                "required": ["service"]
            }
        ),
        Tool(
            name="docker_exec",
            description="在容器内执行命令",
            inputSchema={
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": f"服务名称: {', '.join(ALLOWED_SERVICES)}",
                        "enum": ALLOWED_SERVICES
                    },
                    "command": {
                        "type": "string",
                        "description": "要执行的命令"
                    }
                },
                "required": ["service", "command"]
            }
        ),
        Tool(
            name="compose_up",
            description="启动服务",
            inputSchema={
                "type": "object",
                "properties": {
                    "services": {
                        "type": "array",
                        "items": {"type": "string", "enum": ALLOWED_SERVICES},
                        "description": "要启动的服务列表 (空=启动核心服务)"
                    },
                    "profile": {
                        "type": "string",
                        "description": "配置文件: pipeline, api, dev, all",
                        "enum": ["pipeline", "api", "dev", "all", ""]
                    },
                    "detach": {
                        "type": "boolean",
                        "description": "后台运行",
                        "default": True
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="compose_down",
            description="停止服务",
            inputSchema={
                "type": "object",
                "properties": {
                    "services": {
                        "type": "array",
                        "items": {"type": "string", "enum": ALLOWED_SERVICES},
                        "description": "要停止的服务列表 (空=停止所有)"
                    },
                    "volumes": {
                        "type": "boolean",
                        "description": "同时删除卷 (危险)",
                        "default": False
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="compose_restart",
            description="重启服务",
            inputSchema={
                "type": "object",
                "properties": {
                    "services": {
                        "type": "array",
                        "items": {"type": "string", "enum": ALLOWED_SERVICES},
                        "description": "要重启的服务列表 (空=重启所有)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_service_health",
            description="获取服务健康状态",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """执行工具调用"""

    if name == "docker_ps":
        return await _docker_ps(arguments)
    elif name == "docker_logs":
        return await _docker_logs(arguments)
    elif name == "docker_exec":
        return await _docker_exec(arguments)
    elif name == "compose_up":
        return await _compose_up(arguments)
    elif name == "compose_down":
        return await _compose_down(arguments)
    elif name == "compose_restart":
        return await _compose_restart(arguments)
    elif name == "get_service_health":
        return await _get_service_health()
    else:
        return [TextContent(type="text", text=f"未知工具: {name}")]


def _run_compose_cmd(cmd: list, timeout: int = 60) -> tuple[int, str, str]:
    """运行 docker-compose 命令"""
    full_cmd = ["docker-compose", "-f", str(COMPOSE_FILE)] + cmd
    result = subprocess.run(
        full_cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr


async def _docker_ps(args: dict) -> list[TextContent]:
    """列出容器状态"""
    show_all = args.get("all", False)

    cmd = ["ps"]
    if show_all:
        cmd.append("-a")

    try:
        returncode, stdout, stderr = _run_compose_cmd(cmd)

        output = "=== 项目容器状态 ===\n\n"
        output += stdout
        if stderr:
            output += f"\n错误: {stderr}"

        return [TextContent(type="text", text=output)]

    except subprocess.TimeoutExpired:
        return [TextContent(type="text", text="命令超时")]
    except Exception as e:
        return [TextContent(type="text", text=f"执行失败: {e}")]


async def _docker_logs(args: dict) -> list[TextContent]:
    """获取容器日志"""
    service = args.get("service")
    tail = args.get("tail", 100)

    if service not in ALLOWED_SERVICES:
        return [TextContent(type="text", text=f"服务 '{service}' 不在允许列表中")]

    cmd = ["logs", f"--tail={tail}", service]

    try:
        returncode, stdout, stderr = _run_compose_cmd(cmd, timeout=30)

        output = f"=== {service} 日志 (最后 {tail} 行) ===\n\n"
        output += stdout
        if stderr:
            output += f"\n=== STDERR ===\n{stderr}"

        return [TextContent(type="text", text=output)]

    except subprocess.TimeoutExpired:
        return [TextContent(type="text", text="获取日志超时")]
    except Exception as e:
        return [TextContent(type="text", text=f"获取日志失败: {e}")]


async def _docker_exec(args: dict) -> list[TextContent]:
    """在容器内执行命令"""
    service = args.get("service")
    command = args.get("command")

    if service not in ALLOWED_SERVICES:
        return [TextContent(type="text", text=f"服务 '{service}' 不在允许列表中")]

    # 安全检查: 禁止危险命令
    dangerous_cmds = ["rm -rf", "mkfs", "dd if=", "> /dev/", "chmod 777"]
    for dangerous in dangerous_cmds:
        if dangerous in command:
            return [TextContent(
                type="text",
                text=f"禁止执行危险命令: 包含 '{dangerous}'"
            )]

    cmd = ["exec", "-T", service] + command.split()

    try:
        returncode, stdout, stderr = _run_compose_cmd(cmd, timeout=120)

        output = f"=== 在 {service} 中执行: {command} ===\n"
        output += f"返回码: {returncode}\n\n"
        output += stdout
        if stderr:
            output += f"\n=== STDERR ===\n{stderr}"

        return [TextContent(type="text", text=output)]

    except subprocess.TimeoutExpired:
        return [TextContent(type="text", text="命令执行超时")]
    except Exception as e:
        return [TextContent(type="text", text=f"执行失败: {e}")]


async def _compose_up(args: dict) -> list[TextContent]:
    """启动服务"""
    services = args.get("services", [])
    profile = args.get("profile", "")
    detach = args.get("detach", True)

    # 验证服务名称
    for svc in services:
        if svc not in ALLOWED_SERVICES:
            return [TextContent(type="text", text=f"服务 '{svc}' 不在允许列表中")]

    cmd = ["up"]
    if detach:
        cmd.append("-d")

    if profile:
        cmd.extend(["--profile", profile])

    cmd.extend(services)

    try:
        returncode, stdout, stderr = _run_compose_cmd(cmd, timeout=120)

        output = "=== 启动服务 ===\n\n"
        output += stdout
        if stderr:
            output += f"\n{stderr}"

        if returncode == 0:
            output += "\n✓ 服务启动成功"
        else:
            output += f"\n✗ 服务启动失败 (返回码: {returncode})"

        return [TextContent(type="text", text=output)]

    except subprocess.TimeoutExpired:
        return [TextContent(type="text", text="启动超时")]
    except Exception as e:
        return [TextContent(type="text", text=f"启动失败: {e}")]


async def _compose_down(args: dict) -> list[TextContent]:
    """停止服务"""
    services = args.get("services", [])
    volumes = args.get("volumes", False)

    # 验证服务名称
    for svc in services:
        if svc not in ALLOWED_SERVICES:
            return [TextContent(type="text", text=f"服务 '{svc}' 不在允许列表中")]

    cmd = ["down"]
    if volumes:
        cmd.append("-v")

    if services:
        cmd = ["stop"] + services

    try:
        returncode, stdout, stderr = _run_compose_cmd(cmd, timeout=60)

        output = "=== 停止服务 ===\n\n"
        output += stdout
        if stderr:
            output += f"\n{stderr}"

        if returncode == 0:
            output += "\n✓ 服务已停止"
        else:
            output += f"\n✗ 停止失败 (返回码: {returncode})"

        return [TextContent(type="text", text=output)]

    except subprocess.TimeoutExpired:
        return [TextContent(type="text", text="停止超时")]
    except Exception as e:
        return [TextContent(type="text", text=f"停止失败: {e}")]


async def _compose_restart(args: dict) -> list[TextContent]:
    """重启服务"""
    services = args.get("services", [])

    # 验证服务名称
    for svc in services:
        if svc not in ALLOWED_SERVICES:
            return [TextContent(type="text", text=f"服务 '{svc}' 不在允许列表中")]

    cmd = ["restart"] + services if services else ["restart"]

    try:
        returncode, stdout, stderr = _run_compose_cmd(cmd, timeout=60)

        output = "=== 重启服务 ===\n\n"
        output += stdout
        if stderr:
            output += f"\n{stderr}"

        if returncode == 0:
            output += "\n✓ 服务已重启"
        else:
            output += f"\n✗ 重启失败 (返回码: {returncode})"

        return [TextContent(type="text", text=output)]

    except subprocess.TimeoutExpired:
        return [TextContent(type="text", text="重启超时")]
    except Exception as e:
        return [TextContent(type="text", text=f"重启失败: {e}")]


async def _get_service_health() -> list[TextContent]:
    """获取服务健康状态"""
    try:
        # 获取容器状态
        _, ps_output, _ = _run_compose_cmd(["ps"])

        # 检查数据库连接
        db_check = subprocess.run(
            ["docker-compose", "-f", str(COMPOSE_FILE), "exec", "-T", "db",
             "pg_isready", "-U", "football_user"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=10
        )

        # 检查 Redis 连接
        redis_check = subprocess.run(
            ["docker-compose", "-f", str(COMPOSE_FILE), "exec", "-T", "redis",
             "redis-cli", "ping"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=10
        )

        output = "=== 服务健康检查 ===\n\n"
        output += "容器状态:\n"
        output += ps_output
        output += "\n\n数据库 (PostgreSQL):\n"
        output += "✓ 可用\n" if db_check.returncode == 0 else "✗ 不可用\n"
        output += "\nRedis:\n"
        output += "✓ 可用 (PONG)\n" if "PONG" in redis_check.stdout else "✗ 不可用\n"

        return [TextContent(type="text", text=output)]

    except Exception as e:
        return [TextContent(type="text", text=f"健康检查失败: {e}")]


async def main():
    """启动 MCP 服务器"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
