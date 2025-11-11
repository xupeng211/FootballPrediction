#!/usr/bin/env python3
"""
快速GitHub Issues清理工具
立即关闭已完成的Issues，为Phase 11.8同步腾出空间
"""

import subprocess
import sys

def close_specific_issues():
    """关闭特定的已完成Issues"""

    # 需要关闭的已完成Issues列表（基于分析报告）
    completed_issues = [
        985,  # 🎯 Phase 11.3: SQLAlchemy导入错误修复 - 第三阶段超额完成
        984,  # Phase 9.0 阶段2: 高价值任务执行 - 任务2.1 API文档完善
        983,  # Phase 9.0 阶段1: GitHub Issues清理与收尾
        982,  # Phase 8.0 Task 1: GitHub Issues清理与架构统一
        981,  # Phase 7.0: API模块覆盖率扩展 - 8%到15%
        980,  # Phase 6.0: Utils模块覆盖率提升 - 24%到40%
        979,  # 🔧 Phase 11.2: F821未定义名称错误修复 - 第二阶段完成
        978,  # Phase 9.0 成果总结与下一阶段规划
        977,  # Phase 9.0 阶段2: 高价值任务执行 - 任务2.1 API文档完善
        976,  # Phase 9.0 阶段1: GitHub Issues清理与收尾
        975,  # Phase 8.0 Task 1: GitHub Issues清理与架构统一
        974,  # Phase 7.0: API模块覆盖率扩展 - 8%到15%
        973,  # Phase 6.0: Utils模块覆盖率提升 - 24%到40%
        972,  # 🔧 Phase 11.1: 代码质量系统性改进 - 第一阶段完成
        971,  # Phase 9.0 成果总结与下一阶段规划
        970,  # Phase 9.0 阶段2: 高价值任务执行 - 任务2.1 API文档完善
        969,  # Phase 9.0 阶段1: GitHub Issues清理与收尾
        968,  # Phase 8.0 Task 1: GitHub Issues清理与架构统一
        967,  # Phase 7.0: API模块覆盖率扩展 - 8%到15%
        966,  # Phase 6.0: Utils模块覆盖率提升 - 24%到40%
        965,  # 🎯 Phase 10.0: 基于活跃Issues的智能推进完成
        964,  # 🎯 Phase 9.0: 基于GitHub Issues的渐进式推进路线
    ]

    success_count = 0
    failed_count = 0

    print(f"🔧 开始关闭 {len(completed_issues)} 个已完成的Issues...")

    for issue_number in completed_issues:
        try:
            result = subprocess.run([
                'gh', 'issue', 'close',
                str(issue_number),
                '--repo', 'xupeng211/FootballPrediction',
                '--comment', '✅ 自动关闭 - 任务已完成，为新的工作记录腾出空间。感谢贡献！'
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                print(f"✅ 关闭Issue #{issue_number} 成功")
                success_count += 1
            else:
                print(f"❌ 关闭Issue #{issue_number} 失败: {result.stderr}")
                failed_count += 1

        except subprocess.TimeoutExpired:
            print(f"⏰ 关闭Issue #{issue_number} 超时")
            failed_count += 1
        except Exception as e:
            print(f"❌ 关闭Issue #{issue_number} 出错: {e}")
            failed_count += 1

    return success_count, failed_count

def check_current_status():
    """检查当前Issues状态"""
    try:
        result = subprocess.run([
            'gh', 'issue', 'list',
            '--repo', 'xupeng211/FootballPrediction',
            '--state', 'open',
            '--limit', '5'
        ], capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            print(f"📊 当前开放Issues (前5个):")
            for line in lines:
                if line.strip():
                    print(f"   {line}")
            return len(lines)
        else:
            print("❌ 无法获取当前Issues状态")
            return 0

    except Exception as e:
        print(f"❌ 检查状态失败: {e}")
        return 0

def main():
    """主函数"""
    print("🚀 快速GitHub Issues清理工具")
    print("=" * 50)
    print("目标: 为Phase 11.8历史性成就同步腾出空间")

    # 检查当前状态
    print("\n📊 检查当前状态...")
    current_count = check_current_status()

    if current_count == 0:
        print("❌ 无法获取当前Issues数量")
        return

    print(f"   当前开放Issues数: {current_count}")

    if current_count < 25:
        print("✅ Issues数量在合理范围内，但仍建议清理已完成的Issues")
    else:
        print(f"⚠️  Issues数量达到上限 ({current_count}/25)")

    # 执行清理
    print(f"\n🧹 执行快速清理...")
    success_count, failed_count = close_specific_issues()

    # 显示结果
    print(f"\n📈 清理结果:")
    print(f"   成功关闭: {success_count}")
    print(f"   关闭失败: {failed_count}")
    print(f"   总计处理: {success_count + failed_count}")

    # 检查清理后状态
    print(f"\n🔍 检查清理后状态...")
    new_count = check_current_status()

    print(f"\n🎯 下一步:")
    if new_count < 25:
        print("✅ 清理成功！现在可以同步工作记录")
        print("💡 立即执行: python3 scripts/record_work.py start-work 'Phase 11.8: 语法错误完全消除 - 历史性成就' 'Phase 11.8完成了语法错误的完全消除，从503个减少到0个，实现了100%的语法健康度' development --priority high")
        print("🚀 然后执行: make claude-sync")
    else:
        print("⚠️  仍有较多Issues，可能需要手动清理一些")
        print("💡 建议手动关闭一些已完成的Issues")

if __name__ == "__main__":
    main()