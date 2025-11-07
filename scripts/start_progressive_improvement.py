#!/usr/bin/env python3
"""
渐进式改进启动脚本
Progressive Improvement Starter Script

当Claude Code打开此项目时，可以运行此脚本快速开始改进工作。
"""

import os
import subprocess
from datetime import datetime


def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n🔧 {description}")
    print(f"执行: {cmd}")
    try:
        # 在虚拟环境中执行命令
        full_cmd = f".venv/bin/python3 -c \"import subprocess; result = subprocess.run('{cmd}', shell=True, capture_output=True, text=True); print(result.stdout); print(result.stderr if result.stderr else '')\""
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=60)
        if result.stdout:
            print(f"✅ 输出: {result.stdout[:500]}")
        if result.stderr:
            print(f"⚠️  错误: {result.stderr[:200]}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ 命令超时")
        return False
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return False

def check_strategy_file():
    """检查策略文件是否存在"""
    strategy_file = "CLAUDE_IMPROVEMENT_STRATEGY.md"
    if os.path.exists(strategy_file):
        print(f"✅ 发现策略文件: {strategy_file}")
        return True
    else:
        print(f"❌ 策略文件不存在: {strategy_file}")
        return False

def assess_current_status():
    """评估当前项目状态"""
    print(f"\n📊 项目状态评估 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # 检查语法错误
    print("\n1️⃣ 检查语法错误:")
    run_command(
        "source .venv/bin/activate && ruff check src/ --output-format=concise | grep 'invalid-syntax' | wc -l",
        "统计语法错误数量"
    )

    # 检查测试状态
    print("\n2️⃣ 检查测试状态:")
    run_command(
        "source .venv/bin/activate && pytest tests/unit/utils/ tests/unit/core/ --maxfail=5 -x --tb=no | grep -E '(PASSED|FAILED)' | wc -l",
        "统计测试通过数量"
    )

    # 验证核心功能
    print("\n3️⃣ 验证核心功能:")
    try:
        import sys
        sys.path.insert(0, 'src')

        import cache.decorators as cd
        import utils.date_utils as du
        import utils.validators as val

        print("✅ 核心功能验证:")
        print(f"  - DateUtils完整: {hasattr(du, 'DateUtils')}")
        print(f"  - 缓存函数: {hasattr(du, 'cached_format_datetime')}")
        print(f"  - 数据验证器: {hasattr(val, 'validate_data_types')}")
        print(f"  - 缓存装饰器: {hasattr(cd, 'CacheDecorator')}")
        print("✅ 验证完成!")
    except Exception as e:
        print(f"❌ 验证失败: {e}")

def suggest_next_steps():
    """建议下一步行动"""
    print("\n🎯 建议的下一步行动:")
    print("=" * 50)
    print("基于当前状态，建议按照以下顺序执行:")
    print()
    print("1️⃣ 语法错误修复阶段:")
    print("   source .venv/bin/activate && ruff check src/ --output-format=concise | head -10")
    print("   优先修复 domain/, ml/, collectors/ 模块的语法错误")
    print()
    print("2️⃣ 功能重建阶段:")
    print("   检查缺失的导入和函数")
    print("   重建被测试依赖的功能")
    print()
    print("3️⃣ 测试验证阶段:")
    print("   pytest tests/unit/utils/ tests/unit/core/ --maxfail=10 -x")
    print("   确保测试通过数量保持或增加")
    print()
    print("4️⃣ 成果提交阶段:")
    print("   git add -A")
    print("   git commit -m '渐进式改进成果'")
    print("   创建改进报告")

def show_improvement_history():
    """显示改进历史"""
    print("\n📈 改进历史回顾:")
    print("=" * 50)

    history = [
        ("第一轮", "25个测试", "基础语法修复"),
        ("第二轮", "7个测试", "功能重建"),
        ("第三轮", "14个测试", "模块扩展"),
        ("第四轮", "108个测试", "爆炸增长"),
        ("第五轮", "稳定保持", "成熟稳定")
    ]

    for i, (round_name, tests, focus) in enumerate(history, 1):
        print(f"{i}. {round_name}: {tests}通过 - {focus}")

def main():
    """主函数"""
    print("🚀 渐进式改进启动器")
    print("=" * 50)

    # 检查策略文件
    if not check_strategy_file():
        print("❌ 请先确保 CLAUDE_IMPROVEMENT_STRATEGY.md 文件存在")
        return

    # 显示改进历史
    show_improvement_history()

    # 评估当前状态
    assess_current_status()

    # 建议下一步行动
    suggest_next_steps()

    print("\n💡 提示:")
    print("=" * 50)
    print("1. 详细的改进策略请参考 CLAUDE_IMPROVEMENT_STRATEGY.md")
    print("2. 每个改进阶段都应该创建相应的改进报告")
    print("3. 保持渐进式方法，避免一次性大规模变更")
    print("4. 以测试通过作为成功标准")

    print("\n✅ 渐进式改进启动器完成!")
    print("现在您可以按照建议开始改进工作了。")

if __name__ == "__main__":
    main()
