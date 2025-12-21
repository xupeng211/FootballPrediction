#!/usr/bin/env python3
"""
Pytest MCP Server for Football Prediction System
为Claude提供安全的测试运行能力，严格限制为只读模式
"""

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from mcp.server import Server
from mcp.types import Resource, Tool, TextContent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PytestMCPServer:
    def __init__(self):
        self.server = Server("pytest-mcp")
        self.root_path = Path("/home/user/projects/FootballPrediction")
        self.venv_path = self.root_path / "venv"

        # 严格的安全限制
        self.allowed_pytest_args = [
            "--version",
            "--collect-only",
            "--tb=short",
            "-v",
            "--maxfail=5",
            "-x",
            "-k",
            "--co",
            "--help"
        ]

        self.forbidden_patterns = [
            "--disable-warnings",
            "-W ignore",
            "--runxfail",
            "--lf",
            "--ff",
            "--cleanup-on-failure"
        ]

    def safe_path(self, path: str) -> Path:
        """确保路径在项目根目录内"""
        path_obj = Path(path).resolve()
        try:
            path_obj.relative_to(self.root_path)
            return path_obj
        except ValueError:
            raise ValueError(f"Path {path} is outside project root")

    def validate_pytest_args(self, args: List[str]) -> bool:
        """验证pytest参数安全性"""
        for arg in args:
            # 检查禁止的参数
            if any(forbidden in arg for forbidden in self.forbidden_patterns):
                logger.warning(f"Blocked pytest argument: {arg}")
                return False

            # 检查允许的参数
            if not any(arg.startswith(allowed) for allowed in self.allowed_pytest_args):
                if arg not in ["-v", "-x", "-q", "--tb=short"]:
                    logger.warning(f"Unauthorized pytest argument: {arg}")
                    return False
        return True

    def run_pytest(self, test_path: Optional[str] = None, args: List[str] = None) -> Dict[str, Any]:
        """安全地运行pytest"""
        try:
            # 设置工作目录
            cwd = self.root_path

            # 构建pytest命令
            cmd = [str(self.venv_path / "bin" / "python"), "-m", "pytest"]

            # 添加测试路径
            if test_path:
                safe_test_path = self.safe_path(test_path)
                if safe_test_path.is_file() or safe_test_path.is_dir():
                    cmd.append(str(safe_test_path.relative_to(self.root_path)))
                else:
                    return {
                        "success": False,
                        "error": f"Test path not found: {test_path}",
                        "output": ""
                    }

            # 验证并添加参数
            if args:
                if not self.validate_pytest_args(args):
                    return {
                        "success": False,
                        "error": "Unauthorized pytest arguments detected",
                        "output": ""
                    }
                cmd.extend(args)

            # 安全环境变量
            env = {
                "PATH": f"{self.venv_path}/bin:{os.environ.get('PATH', '')}",
                "VIRTUAL_ENV": str(self.venv_path),
                "PYTHONPATH": str(self.root_path),
                "PYTEST_CURRENT_TEST": "",
                # 禁用插件和警告
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                "PYTEST_PLUGINS": ""
            }

            # 运行pytest（只读模式，超时限制）
            result = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
                check=False  # 不抛出异常，手动处理返回码
            )

            return {
                "success": result.returncode == 0 or result.returncode == 1,  # 1=测试失败但运行成功
                "returncode": result.returncode,
                "output": result.stdout,
                "error": result.stderr,
                "command": " ".join(cmd)
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Pytest execution timeout (300s limit exceeded)",
                "output": ""
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Pytest execution failed: {str(e)}",
                "output": ""
            }

    def list_tests(self, test_path: Optional[str] = None) -> Dict[str, Any]:
        """列出可用的测试"""
        try:
            cmd = [str(self.venv_path / "bin" / "python"), "-m", "pytest", "--collect-only", "-q"]

            if test_path:
                safe_test_path = self.safe_path(test_path)
                if safe_test_path.is_file() or safe_test_path.is_dir():
                    cmd.append(str(safe_test_path.relative_to(self.root_path)))

            env = {
                "PATH": f"{self.venv_path}/bin:{os.environ.get('PATH', '')}",
                "VIRTUAL_ENV": str(self.venv_path),
                "PYTHONPATH": str(self.root_path)
            }

            result = subprocess.run(
                cmd,
                cwd=self.root_path,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
                check=False
            )

            return {
                "success": result.returncode == 0,
                "tests": result.stdout.strip().split('\n') if result.stdout else [],
                "error": result.stderr
            }

        except Exception as e:
            return {
                "success": False,
                "tests": [],
                "error": str(e)
            }

async def main():
    server_instance = PytestMCPServer()

    @server_instance.server.list_tools()
    async def list_tools() -> List[Tool]:
        return [
            Tool(
                name="run_pytest",
                description="Run pytest with safety restrictions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "test_path": {
                            "type": "string",
                            "description": "Path to test file or directory (relative to project root)"
                        },
                        "args": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Pytest arguments (only safe arguments allowed)"
                        }
                    }
                }
            ),
            Tool(
                name="list_tests",
                description="List available tests in collection mode",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "test_path": {
                            "type": "string",
                            "description": "Path to test file or directory (optional)"
                        }
                    }
                }
            )
        ]

    @server_instance.server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        if name == "run_pytest":
            test_path = arguments.get("test_path")
            args = arguments.get("args", [])

            result = server_instance.run_pytest(test_path, args)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "list_tests":
            test_path = arguments.get("test_path")
            result = server_instance.list_tests(test_path)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        else:
            raise ValueError(f"Unknown tool: {name}")

    await server_instance.server.run()

if __name__ == "__main__":
    asyncio.run(main())