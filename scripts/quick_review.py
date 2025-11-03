#!/usr/bin/env python3
"""
⚡ 快速代码审查工具
用于开发者提交前的快速自检
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List

def run_command(command: str, timeout: int = 60) -> Dict[str, str]:
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

    print("⚡ 开始快速代码审查...")
    print("=" * 50)

    all_passed = True

    for name, command in checks:
        print(f"\n{name} 检查中...")
        start_time = time.time()

        result = run_command(command)
        duration = time.time() - start_time

        if result["success"]:
            print(f"✅ {name} - 通过 ({duration:.2f}s)")
        else:
            print(f"❌ {name} - 失败 ({duration:.2f}s)")
            if result["stderr"]:
                # 只显示关键的错误信息
                error_lines = result["stderr"].strip().split('\n')[:3]
                for line in error_lines:
                    if line.strip():
                        print(f"   {line}")
            all_passed = False

    print("\n" + "=" * 50)

    if all_passed:
        print("🎉 所有检查通过！可以提交代码了。")
        return 0
    else:
        print("⚠️  存在问题，请修复后重试。")
        print("\n💡 快速修复建议:")
        print("   python3 scripts/smart_quality_fixer.py")
        print("   ruff check src/ tests/ --fix")
        print("   ruff format src/ tests/")
        return 1

if __name__ == "__main__":
    sys.exit(quick_checks())