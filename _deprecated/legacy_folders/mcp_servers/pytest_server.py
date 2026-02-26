#!/usr/bin/env python3
"""
pytest MCP Server - 测试执行服务器
====================================
提供 pytest 运行、日志获取、覆盖率报告功能
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

# 创建 MCP 服务器实例
server = Server("pytest-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用工具"""
    return [
        Tool(
            name="run_tests",
            description="运行 pytest 测试套件",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "测试路径 (如 tests/ 或 tests/test_foo.py)",
                        "default": "tests/"
                    },
                    "verbose": {
                        "type": "boolean",
                        "description": "详细输出",
                        "default": True
                    },
                    "coverage": {
                        "type": "boolean",
                        "description": "生成覆盖率报告",
                        "default": False
                    },
                    "markers": {
                        "type": "string",
                        "description": "pytest markers (如 -m 'not slow')",
                        "default": ""
                    },
                    "extra_args": {
                        "type": "string",
                        "description": "额外参数",
                        "default": ""
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_test_failures",
            description="获取最近一次测试失败的详细日志",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_coverage_report",
            description="生成并获取覆盖率报告",
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "enum": ["term", "html", "json"],
                        "description": "报告格式",
                        "default": "term"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="run_continuous_bugfix",
            description="运行持续修复脚本 (continuous_bugfix.py)",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_iterations": {
                        "type": "integer",
                        "description": "最大迭代次数",
                        "default": 5
                    },
                    "test_path": {
                        "type": "string",
                        "description": "测试路径",
                        "default": "tests/"
                    }
                },
                "required": []
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """执行工具调用"""

    if name == "run_tests":
        return await _run_tests(arguments)
    elif name == "get_test_failures":
        return await _get_test_failures()
    elif name == "get_coverage_report":
        return await _get_coverage_report(arguments)
    elif name == "run_continuous_bugfix":
        return await _run_continuous_bugfix(arguments)
    else:
        return [TextContent(type="text", text=f"未知工具: {name}")]


async def _run_tests(args: dict) -> list[TextContent]:
    """运行 pytest 测试"""
    path = args.get("path", "tests/")
    verbose = args.get("verbose", True)
    coverage = args.get("coverage", False)
    markers = args.get("markers", "")
    extra_args = args.get("extra_args", "")

    cmd = ["pytest", path]

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend(["--cov=src", "--cov-report=term-missing"])

    if markers:
        cmd.extend(["-m", markers])

    if extra_args:
        cmd.extend(extra_args.split())

    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300
        )

        output = f"命令: {' '.join(cmd)}\n"
        output += f"返回码: {result.returncode}\n\n"
        output += "=== STDOUT ===\n"
        output += result.stdout
        if result.stderr:
            output += "\n=== STDERR ===\n"
            output += result.stderr

        return [TextContent(type="text", text=output)]

    except subprocess.TimeoutExpired:
        return [TextContent(type="text", text="测试超时 (300s)")]
    except Exception as e:
        return [TextContent(type="text", text=f"执行失败: {e}")]


async def _get_test_failures() -> list[TextContent]:
    """获取测试失败日志"""
    # 运行测试并捕获失败
    cmd = ["pytest", "tests/", "-v", "--tb=long", "-x"]

    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300
        )

        output = "=== 测试失败日志 ===\n\n"
        output += result.stdout
        if result.stderr:
            output += "\n=== STDERR ===\n"
            output += result.stderr

        return [TextContent(type="text", text=output)]

    except Exception as e:
        return [TextContent(type="text", text=f"获取失败日志出错: {e}")]


async def _get_coverage_report(args: dict) -> list[TextContent]:
    """获取覆盖率报告"""
    format_type = args.get("format", "term")

    cmd = ["pytest", "tests/", "--cov=src"]

    if format_type == "term":
        cmd.append("--cov-report=term-missing")
    elif format_type == "html":
        cmd.append("--cov-report=html")
    elif format_type == "json":
        cmd.append("--cov-report=json")

    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300
        )

        output = result.stdout
        if format_type == "html":
            output += f"\nHTML 报告已生成: {PROJECT_ROOT}/htmlcov/index.html"
        elif format_type == "json":
            output += f"\nJSON 报告已生成: {PROJECT_ROOT}/coverage.json"

        return [TextContent(type="text", text=output)]

    except Exception as e:
        return [TextContent(type="text", text=f"生成覆盖率报告失败: {e}")]


async def _run_continuous_bugfix(args: dict) -> list[TextContent]:
    """运行持续修复脚本"""
    max_iterations = args.get("max_iterations", 5)
    test_path = args.get("test_path", "tests/")

    # 检查 continuous_bugfix.py 是否存在
    bugfix_script = PROJECT_ROOT / "scripts" / "ops" / "continuous_bugfix.py"
    if not bugfix_script.exists():
        return [TextContent(
            type="text",
            text=f"continuous_bugfix.py 不存在: {bugfix_script}\n请先创建该脚本"
        )]

    cmd = [
        "python", str(bugfix_script),
        "--max-iterations", str(max_iterations),
        "--test-path", test_path
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=600
        )

        output = f"命令: {' '.join(cmd)}\n\n"
        output += result.stdout
        if result.stderr:
            output += "\n=== STDERR ===\n"
            output += result.stderr

        return [TextContent(type="text", text=output)]

    except subprocess.TimeoutExpired:
        return [TextContent(type="text", text="持续修复超时 (600s)")]
    except Exception as e:
        return [TextContent(type="text", text=f"执行失败: {e}")]


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
