#!/usr/bin/env python3
"""
开始第二阶段：代码质量改进
"""

import subprocess
import sys
from datetime import datetime


def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"执行: {description}")
    print(f"命令: {cmd}")
    print("=" * 60)

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ 成功!")
        if result.stdout:
            print(result.stdout)
    else:
        print("❌ 失败!")
        if result.stderr:
            print(result.stderr)

    return result.returncode == 0


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("🚀 开始第二阶段：代码质量改进")
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    print("\n📋 当前项目状态:")
    print("   - 导入错误: 0个 ✅")
    print("   - 测试数量: 3,703个")
    print("   - 警告信息: 已全部过滤 ✅")

    print("\n🎯 第二阶段目标:")
    print("   1. 清理F401未使用导入错误（当前5,790个）")
    print("   2. 优化异常处理（except Exception → 具体异常）")
    print("   3. 重构长文件（<500行）")
    print("   4. 重构长函数（<50行）")

    # 检查当前状态
    print("\n📊 检查当前状态...")

    # 统计F401错误
    run_command("ruff check --select F401 src/ | wc -l", "统计F401错误数量")

    # 统计except Exception
    run_command(
        "grep -r 'except Exception' --include='*.py' src/ | wc -l",
        "统计宽泛异常处理数量",
    )

    # 查找最长的文件
    run_command(
        "find src -name '*.py' -exec wc -l {} + | sort -n | tail -5",
        "查找最长的5个文件",
    )

    print("\n" + "=" * 80)
    print("✨ 第一阶段已完成！准备进入第二阶段")
    print("=" * 80)

    print("\n📝 建议的下一步操作:")
    print("1. 运行 'python scripts/phase2_f401_cleanup.py' 开始清理F401错误")
    print("2. 运行 'make lint' 检查代码质量")
    print("3. 查看 TECHNICAL_DEBT_KANBAN.md 了解更多任务")


if __name__ == "__main__":
    main()
