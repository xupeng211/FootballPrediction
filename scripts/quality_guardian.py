#!/usr/bin/env python3
"""
质量守护工具 - 简化版本
"""

import subprocess
import sys

def main():
    """主函数"""
    print("🛡️ 质量守护工具")
    print("=" * 30)

    # 检查代码质量
    tools = [
        ("Ruff代码检查", ["ruff", "check", "src/", "tests/"]),
        ("Ruff代码格式化", ["ruff", "format", "src/", "tests/", "--check"]),
        ("MyPy类型检查", ["mypy", "src/", "--ignore-missing-imports"]),
        ("Bandit安全检查", ["bandit", "-r", "src/"])
    ]

    all_passed = True

    for tool_name, command in tools:
        print(f"🔍 运行{tool_name}...")
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print(f"✅ {tool_name}通过")
            else:
                print(f"⚠️ {tool_name}发现问题")
                if result.stdout:
                    print(result.stdout[:200])
                all_passed = False
        except Exception as e:
            print(f"❌ {tool_name}执行失败: {e}")
            all_passed = False

    if all_passed:
        print("🎉 所有质量检查通过！")
        return 0
    else:
        print("⚠️ 部分质量检查未通过")
        return 1

if __name__ == '__main__':
    sys.exit(main())