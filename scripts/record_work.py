#!/usr/bin/env python3
"""
Claude Code 作业记录工具（非交互式）
Claude Code Work Recording Tool (Non-Interactive)

提供命令行参数方式记录作业，避免交互式输入问题

Author: Claude AI Assistant
Date: 2025-11-06
Version: 1.0.0
"""

import argparse
import json
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "scripts"))

from claude_work_sync import ClaudeWorkSynchronizer


def start_work(title, description, work_type, priority="medium"):
    """开始新作业记录"""
    synchronizer = ClaudeWorkSynchronizer()

    work_item = synchronizer.create_work_item_from_current_work(
        title=title,
        description=description,
        work_type=work_type,
        priority=priority
    )

    print("✅ 作业记录已创建")
    print(f"   ID: {work_item.id}")
    print(f"   标题: {work_item.title}")
    print(f"   类型: {work_item.work_type}")
    print(f"   优先级: {work_item.priority}")
    print(f"   状态: {work_item.status}")

    return work_item.id


def complete_work(work_id, deliverables=None, test_results_json=None):
    """完成作业记录"""
    synchronizer = ClaudeWorkSynchronizer()

    # 解析交付成果
    deliverables_list = []
    if deliverables:
        deliverables_list = [d.strip() for d in deliverables.split(',')]

    # 解析测试结果
    test_results = {}
    if test_results_json:
        try:
            test_results = json.loads(test_results_json)
        except json.JSONDecodeError:
            print("⚠️ 测试结果JSON格式无效，将忽略")

    success = synchronizer.complete_work_item(
        work_id=work_id,
        completion_percentage=100,
        deliverables=deliverables_list,
        test_results=test_results
    )

    if success:
        print(f"✅ 作业 {work_id} 已完成")
        if deliverables_list:
            print(f"   交付成果: {len(deliverables_list)}项")
        if test_results:
            print("   测试结果: 已记录")
    else:
        print(f"❌ 完成作业 {work_id} 失败")

    return success


def list_work():
    """列出所有作业记录"""
    synchronizer = ClaudeWorkSynchronizer()
    work_items = synchronizer.load_work_log()

    if not work_items:
        print("📝 没有找到作业记录")
        return

    print(f"📋 找到 {len(work_items)} 个作业项目:")
    print("-" * 60)

    for i, item in enumerate(work_items, 1):
        status_emoji = {
            "pending": "⏳",
            "in_progress": "🔄",
            "completed": "✅",
            "review": "👀"
        }

        print(f"{i:2d}. {status_emoji.get(item.status, '❓')} {item.id}")
        print(f"    标题: {item.title}")
        print(f"    类型: {item.work_type} | 优先级: {item.priority}")
        print(f"    状态: {item.status} ({item.completion_percentage}%)")
        if item.time_spent_minutes > 0:
            hours = item.time_spent_minutes // 60
            minutes = item.time_spent_minutes % 60
            if hours > 0:
                print(f"    工作时长: {hours}小时{minutes}分钟")
            else:
                print(f"    工作时长: {minutes}分钟")
        print()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Claude Code 作业记录工具（非交互式）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 开始新作业
  python record_work.py start-work "实现用户认证" "添加JWT认证系统" feature high

  # 完成作业
  python record_work.py complete-work claude_20251106_143022 "JWT中间件,登录API,测试用例"

  # 查看所有作业
  python record_work.py list-work
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # start-work 命令
    start_parser = subparsers.add_parser('start-work', help='开始新作业记录')
    start_parser.add_argument('title', help='作业标题')
    start_parser.add_argument('description', help='作业描述')
    start_parser.add_argument('work_type',
                             choices=['development', 'testing', 'documentation', 'bugfix', 'feature'],
                             help='作业类型')
    start_parser.add_argument('--priority', '-p',
                             choices=['low', 'medium', 'high', 'critical'],
                             default='medium',
                             help='优先级 (默认: medium)')

    # complete-work 命令
    complete_parser = subparsers.add_parser('complete-work', help='完成作业记录')
    complete_parser.add_argument('work_id', help='作业ID')
    complete_parser.add_argument('--deliverables', '-d', help='交付成果，用逗号分隔')
    complete_parser.add_argument('--test-results', '-t', help='测试结果，JSON格式')

    # list-work 命令
    list_parser = subparsers.add_parser('list-work', help='列出所有作业记录')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == 'start-work':
            work_id = start_work(
                title=args.title,
                description=args.description,
                work_type=args.work_type,
                priority=args.priority
            )
            print("\n💡 下一步使用以下命令完成这个作业:")
            print(f"   python record_work.py complete-work {work_id} --deliverables \"交付成果1,交付成果2\"")

        elif args.command == 'complete-work':
            complete_work(
                work_id=args.work_id,
                deliverables=args.deliverables,
                test_results_json=args.test_results
            )
            print("\n💡 下一步同步到GitHub:")
            print("   make claude-sync")

        elif args.command == 'list-work':
            list_work()

    except KeyboardInterrupt:
        print("\n⚠️ 操作被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 操作失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
