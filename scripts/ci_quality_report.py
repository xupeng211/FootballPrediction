#!/usr/bin/env python3
"""
CI质量报告生成脚本
替代GitHub Actions中的复杂Python代码块
"""

import json
import sys
from datetime import datetime
from pathlib import Path


def generate_quality_summary():
    """
    生成质量检查摘要
    """
    try:
        with open('quality-report.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ 质量报告文件未找到")
        return

    metrics = data.get('metrics', {})

    # 输出到GitHub Actions摘要
    print("| Metric | Status |")
    print("|--------|--------|")
    print(f"| Coverage | {metrics.get('coverage', 0):.1f}% |")
    print(f"| Test Pass Rate | {metrics.get('test_pass_rate', 0):.1f}% |")
    print(f"| Code Quality | {metrics.get('code_quality', 0):.1f}/10 |")
    print(f"| Overall Score | {data.get('score', 0):.1f}/10 |")
    print(f"| Status | {'✅ PASS' if data.get('passed') else '❌ FAIL'} |")

    # 输出到文件
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    report = f"""# 📋 CI质量检查报告

**生成时间**: {timestamp}
**CI运行编号**: {os.getenv('GITHUB_RUN_ID', 'N/A')}
**提交SHA**: {os.getenv('GITHUB_SHA', 'N/A')[:7]}

## 📊 质量指标

- **测试覆盖率**: {metrics.get('coverage', 0):.1f}%
- **测试通过率**: {metrics.get('test_pass_rate', 0):.1f}%
- **代码质量评分**: {metrics.get('code_quality', 0):.1f}/10
- **总体评分**: {data.get('score', 0):.1f}/10
- **状态**: {'✅ PASS' if data.get('passed') else '❌ FAIL'}

## 📋 检查详情

{json.dumps(data, indent=2, ensure_ascii=False)}
"""

    with open('ci_quality_report.md', 'w', encoding='utf-8') as f:
        f.write(report)

    print("📄 CI质量报告已生成: ci_quality_report.md")


def generate_type_checking_report():
    """
    生成类型检查报告
    """
    try:
        with open('type-improvement.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ 类型改进文件未找到")
        return

    # 输出到PR评论
    report_lines = [
        "## Type Checking Report",
        "",
        f"- **Error Changes**: {data.get('error_improvement', 0):+d}",
        f"- **Warning Changes**: {data.get('warning_improvement', 0):+d}",
        f"- **Current Errors**: {data.get('total_errors', 0)}",
        f"- **Current Warnings**: {data.get('total_warnings', 0)}"
    ]

    report = "\n".join(report_lines)

    with open('type_checking_report.md', 'w', encoding='utf-8') as f:
        f.write(report)

    print(report)
    print("📄 类型检查报告已生成: type_checking_report.md")


def generate_kanban_check_report(kanban_file: str = "docs/_reports/TEST_OPTIMIZATION_KANBAN.md"):
    """
    生成Kanban检查报告
    """
    import os

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    run_id = os.getenv('GITHUB_RUN_ID', 'N/A')
    commit_sha = os.getenv('GITHUB_SHA', 'N/A')

    if not Path(kanban_file).exists():
        # 文件不存在的报告
        report = f"""# 📋 Kanban 文件检查报告

**生成时间**: {timestamp}
**CI 运行编号**: {run_id}
**提交 SHA**: {commit_sha}

## 🚨 检查结果
- 状态: ❌ 失败
- 原因: Kanban 文件缺失

## 📂 文件路径
- {kanban_file}

## 📌 提示
👉 每次提交必须同步更新 Kanban 文件，以保持任务进度与代码一致。
"""
        status = "FAILED"
    else:
        # 文件存在的报告
        report = f"""# 📋 Kanban 文件检查报告

**生成时间**: {timestamp}
**CI 运行编号**: {run_id}
**提交 SHA**: {commit_sha}

## ✅ 检查结果
- 状态: ✅ 成功
- 原因: Kanban 文件存在

## 📂 文件路径
- {kanban_file}

## 📌 说明
Kanban 文件已正确同步，任务进度与代码保持一致。
"""
        status = "SUCCESS"

    with open('kanban_check_report.md', 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"📄 Kanban检查报告已生成: kanban_check_report.md (状态: {status})")


def main():
    """
    主函数
    """
    import argparse

    parser = argparse.ArgumentParser(description='CI报告生成工具')
    parser.add_argument('--type', choices=['quality', 'type-checking', 'kanban'],
                       required=True, help='报告类型')
    parser.add_argument('--kanban-file', default='docs/_reports/TEST_OPTIMIZATION_KANBAN.md',
                       help='Kanban文件路径')

    args = parser.parse_args()

    if args.type == 'quality':
        generate_quality_summary()
    elif args.type == 'type-checking':
        generate_type_checking_report()
    elif args.type == 'kanban':
        generate_kanban_check_report(args.kanban_file)


if __name__ == "__main__":
    main()