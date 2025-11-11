#!/usr/bin/env python3
"""
⚡ 快速代码审查工具
用于开发者提交前的快速自检
"""

import subprocess
import sys
import time
from pathlib import Path


def run_command(command: str, timeout: int = 60) -> dict[str, str]:
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(__file__).parent.parent
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "Command timed out"
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e)
        }

def quick_checks():
    """运行快速检查"""
    checks = [
        ("🔍 代码规范", "ruff check src/ tests/ --output-format=concise"),
        ("🎨 代码格式", "ruff format --check src/ tests/"),
        ("🧪 单元测试", "pytest tests/unit/ -x --tb=short"),
        ("🔒 安全检查", "bandit -r src/ -f json -q"),
    ]


    all_passed = True

    for _name, command in checks:
        start_time = time.time()

        result = run_command(command)
        time.time() - start_time

        if result["success"]:
            pass
        else:
            if result["stderr"]:
                # 只显示关键的错误信息
                error_lines = result["stderr"].strip().split('\n')[:3]
                for line in error_lines:
                    if line.strip():
                        pass
            all_passed = False


    if all_passed:
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(quick_checks())
