#!/usr/bin/env python3
"""
代码质量检查脚本
防止类似问题再次发生
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """运行命令并返回结果"""
    print(f"🔧 {description}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✅ {description} - 通过")
        return True
    else:
        print(f"❌ {description} - 失败")
        print(f"错误信息: {result.stderr}")
        return False

def main():
    """主检查函数"""
    print("🚀 开始代码质量检查...")

    checks = [
        (["python", "-m", "pytest", "tests/unit/utils/test_dict_utils_fixed.py", "-v"], "dict_utils 功能测试"),
        (["python", "-m", "pytest", "tests/unit/api/test_health.py", "-v"], "健康检查API测试"),
        (["ruff", "check", "src/utils/dict_utils.py"], "dict_utils 代码质量检查"),
        (["ruff", "check", "src/api/monitoring.py"], "monitoring 代码质量检查"),
    ]

    passed = 0
    total = len(checks)

    for cmd, description in checks:
        if run_command(cmd, description):
            passed += 1
        print("-" * 50)

    print(f"\n📊 检查结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有质量检查通过！")
        return 0
    else:
        print("⚠️  存在质量问题需要修复")
        return 1

if __name__ == "__main__":
    sys.exit(main())
