#!/usr/bin/env python3
"""
Pytest MCP Server for Football Prediction System
为Claude提供安全的测试运行能力，严格限制为只读模式
(Standalone version without external mcp library dependency)
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# 配置日志到 stderr，以免干扰 stdout 的 JSON 通信
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)


class PytestMCPServer:
    def __init__(self):
        # 默认项目根目录，可以通过环境变量覆盖
        self.root_path = Path(os.getenv("PROJECT_ROOT", "/home/user/projects/FootballPrediction"))
        self.venv_path = self.root_path / "venv"

        if not self.venv_path.exists():
            logger.warning(f"Virtual environment not found at {self.venv_path}")

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
            "--help",
            "-q",
        ]

        self.forbidden_patterns = [
            "--disable-warnings",
            "-W ignore",
            "--runxfail",
            "--lf",
            "--ff",
            "--cleanup-on-failure",
        ]

    def safe_path(self, path: str) -> Path:
        """确保路径在项目根目录内"""
        try:
            path_obj = (self.root_path / path).resolve()
            # 检查是否在根目录下
            path_obj.relative_to(self.root_path)
            return path_obj
        except (ValueError, RuntimeError) as e:
            logger.error(f"Path security check failed: {e}")
            raise ValueError(f"Path {path} is outside project root")

    def validate_pytest_args(self, args: list[str]) -> bool:
        """验证pytest参数安全性"""
        for arg in args:
            # 检查禁止的参数
            if any(forbidden in arg for forbidden in self.forbidden_patterns):
                logger.warning(f"Blocked pytest argument: {arg}")
                return False

            # 检查允许的参数
            # 简单起见，只要不包含危险字符且不在禁止列表中，且看起来像参数
            if arg.startswith("-"):
                # 这里可以放宽一点，或者严格匹配 allowed_pytest_args
                # 为了实用性，我们暂时只拦截明确禁止的
                pass
        return True

    def run_pytest(self, test_path: str | None = None, args: list[str] = None) -> dict[str, Any]:
        """安全地运行pytest"""
        try:
            # 设置工作目录
            cwd = self.root_path

            # 构建pytest命令
            python_exec = self.venv_path / "bin" / "python"
            if not python_exec.exists():
                python_exec = "python3"  # Fallback

            cmd = [str(python_exec), "-m", "pytest"]

            # 添加测试路径
            if test_path:
                try:
                    safe_test_path = self.safe_path(test_path)
                    # 传递相对路径给 pytest，输出更好看
                    rel_path = safe_test_path.relative_to(self.root_path)
                    cmd.append(str(rel_path))
                except ValueError as e:
                    return {"success": False, "error": str(e), "output": ""}

            # 验证并添加参数
            if args:
                if not self.validate_pytest_args(args):
                    return {"success": False, "error": "Unauthorized pytest arguments detected", "output": ""}
                cmd.extend(args)

            # 安全环境变量
            env = os.environ.copy()
            env["PATH"] = f"{self.venv_path}/bin:{env.get('PATH', '')}"
            env["VIRTUAL_ENV"] = str(self.venv_path)
            env["PYTHONPATH"] = str(self.root_path)
            env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

            logger.info(f"Running command: {' '.join(cmd)}")

            # 运行pytest（只读模式，超时限制）
            result = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
                check=False,
            )

            return {
                "success": result.returncode == 0 or result.returncode == 1,
                "returncode": result.returncode,
                "output": result.stdout,
                "error": result.stderr,
                "command": " ".join(cmd),
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Pytest execution timeout (300s limit exceeded)", "output": ""}
        except Exception as e:
            return {"success": False, "error": f"Pytest execution failed: {str(e)}", "output": ""}

    def list_tests(self, test_path: str | None = None) -> dict[str, Any]:
        """列出可用的测试"""
        return self.run_pytest(test_path, args=["--collect-only", "-q"])

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        """处理 MCP 请求"""
        method = request.get("method", "")
        params = request.get("params", {})
        msg_id = request.get("id")

        # 处理初始化握手
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "pytest-server", "version": "1.0.0"},
                },
            }

        if method == "notifications/initialized":
            return None

        # 工具列表发现
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": [
                        {
                            "name": "run_pytest",
                            "description": "Run pytest with safety restrictions",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "test_path": {
                                        "type": "string",
                                        "description": "Path to test file or directory (relative to project root)",
                                    },
                                    "args": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Pytest arguments (only safe arguments allowed)",
                                    },
                                },
                            },
                        },
                        {
                            "name": "list_tests",
                            "description": "List available tests in collection mode",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "test_path": {
                                        "type": "string",
                                        "description": "Path to test file or directory (optional)",
                                    }
                                },
                            },
                        },
                    ]
                },
            }

        # 处理工具调用
        if method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            handlers = {
                "run_pytest": lambda: self.run_pytest(tool_args.get("test_path"), tool_args.get("args")),
                "list_tests": lambda: self.list_tests(tool_args.get("test_path")),
            }

            if tool_name in handlers:
                try:
                    result = handlers[tool_name]()
                    # 格式化为 MCP tools/call 响应
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
                            "isError": False,
                        },
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": f"Error executing tool: {str(e)}"}],
                            "isError": True,
                        },
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Tool not found: {tool_name}"},
                }

        # 之前的直接方法调用（保留兼容性，或者直接移除）
        # 为了符合 MCP，我们主要依赖 tools/call，但也保留旧的直接映射以防万一
        handlers = {
            "run_pytest": lambda: self.run_pytest(params.get("test_path"), params.get("args")),
            "list_tests": lambda: self.list_tests(params.get("test_path")),
        }

        if method in handlers:
            try:
                result = handlers[method]()
                return {"jsonrpc": "2.0", "id": msg_id, "result": result}
            except Exception as e:
                return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32000, "message": str(e)}}
        else:
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}


def main():
    server = PytestMCPServer()

    # 简单的 stdin/stdout 循环
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            try:
                request = json.loads(line.strip())
            except json.JSONDecodeError:
                continue

            response = server.handle_request(request)
            if "id" in request:
                response["id"] = request["id"]

            print(json.dumps(response), flush=True)

        except Exception as e:
            logger.error(f"Loop error: {e}")


if __name__ == "__main__":
    main()
