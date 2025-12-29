#!/usr/bin/env python3
"""
File System MCP Server for Football Prediction System
为Claude提供文件系统访问能力
"""

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path

from mcp.server import Server
from mcp.types import Resource, TextContent, Tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FileSystemMCPServer:
    def __init__(self):
        self.server = Server("filesystem-mcp")
        self.root_path = Path("/home/user/projects/FootballPrediction")
        self.git_available = self.check_git()

    def check_git(self) -> bool:
        """检查Git是否可用"""
        try:
            subprocess.run(["git", "--version"], check=True, capture_output=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def safe_path(self, path: str) -> Path:
        """确保路径在项目根目录内"""
        path_obj = Path(path).resolve()
        try:
            path_obj.relative_to(self.root_path)
            return path_obj
        except ValueError:
            raise ValueError(f"Path {path} is outside project root")

    def read_file(self, file_path: str, max_lines: int | None = None) -> str:
        """安全地读取文件内容"""
        try:
            path_obj = self.safe_path(file_path)
            if not path_obj.exists():
                return json.dumps({"error": f"File not found: {file_path}"}, indent=2)

            if not path_obj.is_file():
                return json.dumps({"error": f"Path is not a file: {file_path}"}, indent=2)

            with open(path_obj, encoding="utf-8") as f:
                if max_lines:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            break
                        lines.append(line)
                    content = "".join(lines)
                    return json.dumps(
                        {"file": file_path, "content": content, "lines_read": len(lines), "truncated": True}, indent=2
                    )
                else:
                    content = f.read()
                    return json.dumps({"file": file_path, "content": content, "size": len(content)}, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Failed to read file: {str(e)}"}, indent=2)

    def write_file(self, file_path: str, content: str, create_dirs: bool = False) -> str:
        """安全地写入文件内容"""
        try:
            path_obj = self.safe_path(file_path)

            if create_dirs:
                path_obj.parent.mkdir(parents=True, exist_ok=True)

            with open(path_obj, "w", encoding="utf-8") as f:
                f.write(content)

            return json.dumps(
                {"file": str(path_obj), "success": True, "bytes_written": len(content.encode("utf-8"))}, indent=2
            )
        except Exception as e:
            return json.dumps({"error": f"Failed to write file: {str(e)}"}, indent=2)

    def list_directory(self, dir_path: str = ".") -> str:
        """列出目录内容"""
        try:
            path_obj = self.safe_path(dir_path)
            if not path_obj.exists():
                return json.dumps({"error": f"Directory not found: {dir_path}"}, indent=2)

            if not path_obj.is_dir():
                return json.dumps({"error": f"Path is not a directory: {dir_path}"}, indent=2)

            items = []
            for item in path_obj.iterdir():
                try:
                    relative_path = item.relative_to(self.root_path)
                    stat = item.stat()
                    items.append(
                        {
                            "name": relative_path.as_posix(),
                            "type": "directory" if item.is_dir() else "file",
                            "size": stat.st_size if item.is_file() else 0,
                            "modified": stat.st_mtime,
                            "is_executable": os.access(item, os.X_OK) if item.is_file() else False,
                        }
                    )
                except Exception:
                    continue

            # 排序：目录优先，然后按名称
            items.sort(key=lambda x: (x["type"], x["name"].lower()))

            return json.dumps({"directory": dir_path, "items": items, "count": len(items)}, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Failed to list directory: {str(e)}"}, indent=2)

    def search_files(self, pattern: str, file_type: str = "name", max_results: int = 50) -> str:
        """搜索文件"""
        try:
            path_obj = self.root_path
            results = []

            if file_type == "name":
                files = list(path_obj.rglob(f"*{pattern}*"))
            elif file_type == "extension":
                files = list(path_obj.rglob(f"*.{pattern}"))
            else:
                files = list(path_obj.rglob(pattern))

            # 转换为相对路径
            for file_path in files:
                try:
                    relative_path = file_path.relative_to(self.root_path)
                    if file_path.is_file():
                        stat = file_path.stat()
                        results.append({"file": str(relative_path), "size": stat.st_size, "modified": stat.st_mtime})
                except Exception:
                    continue

            # 限制结果数量
            if max_results:
                results = results[:max_results]

            return json.dumps(
                {"pattern": pattern, "type": file_type, "files": results, "count": len(results)}, indent=2
            )
        except Exception as e:
            return json.dumps({"error": f"Failed to search files: {str(e)}"}, indent=2)

    def git_status(self) -> str:
        """获取Git状态"""
        if not self.git_available:
            return json.dumps({"error": "Git is not available"}, indent=2)

        try:
            # 获取状态
            result = subprocess.run(
                ["git", "status", "--porcelain"], capture_output=True, text=True, cwd=self.root_path
            )

            if result.returncode != 0:
                return json.dumps({"error": "Git status command failed"}, indent=2)

            lines = result.stdout.strip().split("\n")
            status_info = {"modified": [], "added": [], "deleted": [], "untracked": []}

            for line in lines:
                if line.startswith(" M "):
                    status_info["modified"].append(line[2:])
                elif line.startswith("A "):
                    status_info["added"].append(line[2:])
                elif line.startswith("D "):
                    status_info["deleted"].append(line[2:])
                elif line.startswith("?? "):
                    status_info["untracked"].append(line[2:])

            return json.dumps(status_info, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Failed to get git status: {str(e)}"}, indent=2)

    def git_diff(self, file_path: str | None = None) -> str:
        """获取Git差异"""
        if not self.git_available:
            return json.dumps({"error": "Git is not available"}, indent=2)

        try:
            cmd = ["git", "diff", "--color=never"]
            if file_path:
                cmd.append(file_path)

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.root_path)

            return json.dumps(
                {"command": " ".join(cmd), "output": result.stdout, "return_code": result.returncode}, indent=2
            )
        except Exception as e:
            return json.dumps({"error": f"Failed to get git diff: {str(e)}"}, indent=2)


# 初始化服务器
fs_server = FileSystemMCPServer()


@fs_server.server.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用工具"""
    return [
        Tool(
            name="read_file",
            description="Read file content from the project",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file to read"},
                    "max_lines": {"type": "integer", "description": "Maximum number of lines to read (optional)"},
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="write_file",
            description="Write content to a file in the project",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file to write"},
                    "content": {"type": "string", "description": "Content to write to the file"},
                    "create_dirs": {
                        "type": "boolean",
                        "description": "Create parent directories if needed",
                        "default": False,
                    },
                },
                "required": ["file_path", "content"],
            },
        ),
        Tool(
            name="list_directory",
            description="List files and directories",
            inputSchema={
                "type": "object",
                "properties": {
                    "dir_path": {
                        "type": "string",
                        "description": "Directory path (relative to project root)",
                        "default": ".",
                    }
                },
            },
        ),
        Tool(
            name="search_files",
            description="Search for files by name or extension",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern"},
                    "file_type": {
                        "type": "string",
                        "enum": ["name", "extension"],
                        "description": "Search by name or extension",
                        "default": "name",
                    },
                    "max_results": {"type": "integer", "description": "Maximum number of results", "default": 50},
                },
                "required": ["pattern"],
            },
        ),
        Tool(
            name="git_status", description="Get Git repository status", inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="git_diff",
            description="Get Git diff output",
            inputSchema={
                "type": "object",
                "properties": {"file_path": {"type": "string", "description": "Specific file to diff (optional)"}},
            },
        ),
        Tool(
            name="run_command",
            description="Run a shell command in the project directory",
            inputSchema={
                "type": "object",
                "properties": {"command": {"type": "string", "description": "Shell command to run"}},
                "required": ["command"],
            },
        ),
    ]


@fs_server.server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """执行工具调用"""
    try:
        if name == "read_file":
            max_lines = arguments.get("max_lines")
            result = fs_server.read_file(arguments["file_path"], max_lines)

        elif name == "write_file":
            create_dirs = arguments.get("create_dirs", False)
            result = fs_server.write_file(arguments["file_path"], arguments["content"], create_dirs)

        elif name == "list_directory":
            dir_path = arguments.get("dir_path", ".")
            result = fs_server.list_directory(dir_path)

        elif name == "search_files":
            pattern = arguments["pattern"]
            file_type = arguments.get("file_type", "name")
            max_results = arguments.get("max_results", 50)
            result = fs_server.search_files(pattern, file_type, max_results)

        elif name == "git_status":
            result = fs_server.git_status()

        elif name == "git_diff":
            file_path = arguments.get("file_path")
            result = fs_server.git_diff(file_path)

        elif name == "run_command":
            command = arguments["command"]
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=fs_server.root_path)
                response = json.dumps(
                    {
                        "command": command,
                        "return_code": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    },
                    indent=2,
                )
            except Exception as e:
                response = json.dumps({"command": command, "error": str(e)}, indent=2)

        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(type="text", text=result)]

    except Exception as e:
        error_msg = f"Tool execution failed: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]


@fs_server.server.list_resources()
async def list_resources() -> list[Resource]:
    """列出可用资源"""
    return [
        Resource(
            uri="file://src", name="Source Code", description="Source code directory", mimeType="application/json"
        ),
        Resource(
            uri="file://tests", name="Tests", description="Test files and directories", mimeType="application/json"
        ),
        Resource(uri="file://scripts", name="Scripts", description="Utility scripts", mimeType="application/json"),
        Resource(
            uri="file://config", name="Configuration", description="Configuration files", mimeType="application/json"
        ),
    ]


@fs_server.server.read_resource()
async def read_resource(uri: str) -> str:
    """读取资源"""
    try:
        if uri == "file://src":
            return fs_server.list_directory("src")
        elif uri == "file://tests":
            return fs_server.list_directory("tests")
        elif uri == "file://scripts":
            return fs_server.list_directory("scripts")
        elif uri == "file://config":
            return fs_server.list_directory("config")
        else:
            raise ValueError(f"Unknown resource: {uri}")
    except Exception as e:
        return f"Failed to read resource {uri}: {str(e)}"


async def main():
    """启动MCP服务器"""
    logger.info("Starting File System MCP Server...")
    logger.info(f"Root path: {fs_server.root_path}")

    # 启动服务器
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await fs_server.server.run(read_stream, write_stream, fs_server.server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
