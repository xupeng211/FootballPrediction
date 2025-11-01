#!/usr/bin/env python3
"""
测试可执行性检查脚本
Test Executability Check Script

用于CI/CD流水线验证测试文件的基本语法和执行能力
"""

import subprocess
import sys
import os
from pathlib import Path


def check_test_syntax(test_files):
    """检查测试文件的语法正确性"""
    syntax_errors = []
    syntax_correct = []

    for file_path in test_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                compile(f.read(), file_path, "exec")
            syntax_correct.append(file_path)
        except SyntaxError as e:
            syntax_errors.append((file_path, f"语法错误: {e}"))
        except Exception as e:
            syntax_errors.append((file_path, f"其他错误: {e}"))

    return syntax_correct, syntax_errors


def run_test_collection(test_files):
    """运行测试收集，检查pytest能否正常收集"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"] + test_files,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            return True, "测试收集成功"
        else:
            return False, f"测试收集失败: {result.stderr}"

    except subprocess.TimeoutExpired:
        return False, "测试收集超时"
    except Exception as e:
        return False, f"测试收集异常: {e}"


def main():
    """主函数"""
    print("🧪 开始测试可执行性检查...")

    # 检查关键的已修复测试文件
    key_test_files = [
        "tests/unit/test_final_coverage_push.py",
        "tests/unit/test_observers.py",
        "tests/unit/test_checks.py",
        "tests/unit/api/test_comprehensive.py",
        "tests/unit/utils/test_config_loader_comprehensive.py",
        "tests/unit/utils/test_low_coverage_boost.py",
        "tests/unit/utils/test_final_coverage.py",
        "tests/unit/api/test_events_simple.py",
        "tests/unit/api/test_decorators_simple.py",
        "tests/unit/api/test_core_modules.py",
    ]

    # 1. 语法检查
    print("\n📝 1. 语法检查...")
    syntax_correct, syntax_errors = check_test_syntax(key_test_files)

    print(f"✅ 语法正确: {len(syntax_correct)}个文件")
    if syntax_errors:
        print(f"❌ 语法错误: {len(syntax_errors)}个文件")
        for file_path, error in syntax_errors:
            print(f"   - {file_path}: {error}")

    # 2. 测试收集检查
    print("\n🔍 2. 测试收集检查...")
    can_collect, collect_message = run_test_collection(syntax_correct)

    if can_collect:
        print(f"✅ {collect_message}")
        return_code = 0
    else:
        print(f"❌ {collect_message}")
        return_code = 1

    # 3. 总结
    print("\n📊 总结:")
    total_files = len(key_test_files)
    success_rate = (len(syntax_correct) / total_files) * 100
    print(f"- 总文件数: {total_files}")
    print(f"- 语法正确率: {success_rate:.1f}%")
    print(f"- 可收集测试: {'是' if can_collect else '否'}")

    print(f"\n🎯 状态: {'✅ 通过' if return_code == 0 else '❌ 失败'}")
    return return_code


if __name__ == "__main__":
    sys.exit(main())
