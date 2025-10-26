#!/usr/bin/env python3
"""
智能阶段3修复器 - 专注于关键源码文件
跳过问题脚本，只处理 src/ 目录下的重要文件
"""

import subprocess
import os
from pathlib import Path

def fix_src_files_only():
    """只修复src目录下的文件"""
    print("🎯 智能阶段3修复器 - 专注源码质量")
    print("=" * 50)

    # 1. 先自动修复可修复的错误
    print("第1步: 自动修复可修复的错误")
    fixable_codes = ["F541", "E401", "F402", "F841"]

    for code in fixable_codes:
        print(f"🔧 修复 {code} 错误...")
        try:
            # 只对src目录修复
            result = subprocess.run(
                ["ruff", "check", "src/", f"--select={code}", "--fix", "--quiet"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                print(f"  ✅ {code} 修复成功")
            else:
                print(f"  ⚠️ {code} 部分修复")
        except Exception as e:
            print(f"  ❌ {code} 修复失败: {e}")

    # 2. 修复src目录下的bare-except错误
    print("第2步: 修复bare-except错误")
    try:
        result = subprocess.run(
            ["ruff", "check", "src/", "--select=E722", "--fix", "--quiet"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print("  ✅ E722 修复成功")
        else:
            print("  ⚠️ E722 部分修复")
    except Exception as e:
        print(f"  ❌ E722 修复失败: {e}")

    # 3. 检查修复效果
    print("第3步: 检查修复效果")
    try:
        result = subprocess.run(
            ["ruff", "check", "src/", "--statistics"],
            capture_output=True,
            text=True,
            timeout=30
        )

        print("src/ 目录修复后的状态:")
        print(result.stdout)

        # 提取剩余错误数
        lines = result.stdout.split('\n')
        for line in lines:
            if 'Found' in line and 'errors' in line:
                print(f"📊 src目录剩余错误: {line}")
                break

    except Exception as e:
        print(f"❌ 检查失败: {e}")

def run_basic_tests():
    """运行基础测试确保没有破坏功能"""
    print("\n🧪 第4步: 运行基础测试验证")
    try:
        result = subprocess.run(
            ["python", "test_basic_pytest.py"],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print("✅ 基础测试通过")
        else:
            print("⚠️ 基础测试遇到问题:")
            print(result.stdout)
            print(result.stderr)

    except Exception as e:
        print(f"❌ 测试运行失败: {e}")

def generate_coverage_report():
    """生成覆盖率报告"""
    print("\n📊 第5步: 生成覆盖率报告")
    try:
        result = subprocess.run(
            ["pytest", "test_basic_pytest.py", "--cov=src", "--cov-report=term-missing", "--quiet"],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print("✅ 覆盖率报告生成成功")
            # 提取覆盖率信息
            lines = result.stdout.split('\n')
            for line in lines:
                if 'TOTAL' in line and '%' in line:
                    print(f"📈 当前覆盖率: {line.strip()}")
                    break
            print("详细覆盖率信息:")
            print(result.stdout)
        else:
            print("⚠️ 覆盖率报告生成遇到问题")
            print(result.stderr)

    except Exception as e:
        print(f"❌ 覆盖率报告生成失败: {e}")

def main():
    """主函数"""
    print("🚀 Issue #88 阶段3: 智能源码质量修复")
    print("=" * 60)

    # 执行修复流程
    fix_src_files_only()
    run_basic_tests()
    generate_coverage_report()

    print("\n🎉 阶段3智能修复完成!")
    print("📋 完成内容:")
    print("  ✅ 修复了 src/ 目录下的可自动修复错误")
    print("  ✅ 运行了基础功能测试验证")
    print("  ✅ 生成了当前覆盖率报告")
    print("🎯 建议: 基于当前结果决定是否继续阶段4")

if __name__ == "__main__":
    main()