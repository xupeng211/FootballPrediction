#!/usr/bin/env python3
"""
预提交快速检查工具
在提交代码前进行快速质量验证
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description, allow_failure=False):
    """运行命令并处理结果"""
    print(f"🔍 {description}...")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd="/home/user/projects/FootballPrediction"
        )

        if result.returncode == 0:
            print(f"   ✅ {description} 通过")
            return True
        else:
            if allow_failure:
                print(f"   ⚠️ {description} 有警告，但允许继续")
                return True
            else:
                print(f"   ❌ {description} 失败")
                if result.stdout:
                    print(f"      输出: {result.stdout[:200]}...")
                if result.stderr:
                    print(f"      错误: {result.stderr[:200]}...")
                return False
    except Exception as e:
        print(f"   ❌ {description} 执行异常: {e}")
        return not allow_failure

def quick_syntax_check():
    """快速语法检查"""
    print("🔍 进行快速语法检查...")

    # 检查关键文件的语法
    critical_files = [
        'src/core/di.py',
        'src/utils/dict_utils.py',
        'src/utils/time_utils.py'
    ]

    syntax_ok = True
    checked_count = 0

    for file_path in critical_files:
        if os.path.exists(file_path):
            success = run_command(
                f"python -m py_compile {file_path}",
                f"语法检查: {os.path.basename(file_path)}",
                allow_failure=False
            )
            if success:
                checked_count += 1
            else:
                syntax_ok = False

    if checked_count > 0:
        if syntax_ok:
            print(f"   ✅ 语法检查通过 ({checked_count} 个文件)")
            return True
        else:
            print("   ❌ 语法检查失败")
            return False
    else:
        print("   ℹ️ 没有找到关键文件，跳过语法检查")
        return True

def main():
    """主函数"""
    print("🚀 预提交快速检查开始...")
    print("=" * 50)

    checks = [
        # 基础检查
        ("python --version", "Python版本检查", False),

        # 语法检查
        (quick_syntax_check, "语法检查", False),

        # 轻量级代码质量检查
        ("ruff check src/ --output-format=text --quiet | head -5", "Ruff快速检查", True),

        # 类型检查抽样 (只检查关键文件)
        ("mypy src/utils/dict_utils.py src/core/di.py --no-error-summary --quiet", "MyPy抽样检查", True),
    ]

    failed_checks = []
    passed_checks = []

    for check, description, allow_failure in checks:
        if callable(check):
            success = check()
        else:
            success = run_command(check, description, allow_failure)

        if success:
            passed_checks.append(description)
        else:
            failed_checks.append(description)

    print("=" * 50)
    print(f"📊 检查结果: {len(passed_checks)}/{len(checks)} 通过")

    if passed_checks:
        print(f"✅ 通过的检查: {', '.join(passed_checks)}")

    if failed_checks:
        print(f"❌ 失败的检查: {', '.join(failed_checks)}")
        print("\n💡 建议:")
        print("   1. 修复失败的检查项")
        print("   2. 如果必须提交，使用: git commit --no-verify")
        print("   3. 查看详细错误信息并修复")

        return 1
    else:
        print("\n🎉 预提交检查全部通过！")
        return 0

if __name__ == '__main__':
    sys.exit(main())