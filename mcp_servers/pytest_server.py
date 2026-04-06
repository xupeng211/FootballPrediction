import os
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("pytest")
PROJECT_ROOT = Path(__file__).resolve().parent.parent


@mcp.tool()
def run_pytest(test_path: str = "tests", markers: str = None):
    """运行 pytest 测试。test_path 是测试目录或文件路径，markers 是 pytest -m 过滤标记。"""
    command = [
        "docker-compose",
        "-f",
        "docker-compose.dev.yml",
        "exec",
        "-T",
        "dev",
        "python",
        "-m",
        "pytest",
        test_path,
        "-v",
    ]
    if markers:
        command.extend(["-m", markers])

    env = os.environ.copy()
    env.setdefault("PWD", str(PROJECT_ROOT))

    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
        "command": command,
        "cwd": str(PROJECT_ROOT),
    }


if __name__ == "__main__":
    mcp.run()
