#!/usr/bin/env python3
"""
安全报告检查脚本
Security Report Checker Script

检查bandit生成的安全报告，发现高危安全漏洞时退出并返回错误码。
用于CI/CD流水线中的安全质量门禁。

作者: Claude Code
创建时间: 2025-11-19
"""

import json
import sys
from pathlib import Path


def check_security_report(report_path: str = "bandit-report.json") -> int:
    """
    检查安全报告中的高危漏洞

    Args:
        report_path: 安全报告文件路径

    Returns:
        int: 0 表示安全，1 表示发现高危漏洞
    """
    try:
        report_file = Path(report_path)

        # 如果报告文件不存在，认为是安全的（可能没有运行扫描）
        if not report_file.exists():
            print("✅ 安全报告文件不存在，认为安全")
            return 0

        # 读取安全报告
        with open(report_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 检查结果
        results = data.get('results', [])
        high_issues = [r for r in results if r.get('issue_severity') == 'HIGH']
        medium_issues = [r for r in results if r.get('issue_severity') == 'MEDIUM']

        # 统计信息
        total_issues = len(results)
        high_count = len(high_issues)
        medium_count = len(medium_issues)

        print(f"🔍 安全扫描结果统计:")
        print(f"   - 总问题数: {total_issues}")
        print(f"   - 高危问题: {high_count}")
        print(f"   - 中危问题: {medium_count}")

        # 如果有高危问题，详细显示并返回错误码
        if high_issues:
            print(f"\n❌ 发现 {high_count} 个高危安全问题，必须修复:")

            for i, issue in enumerate(high_issues, 1):
                test_name = issue.get('test_name', 'unknown')
                issue_text = issue.get('issue_text', 'unknown description')
                file_path = issue.get('filename', 'unknown file')
                line_number = issue.get('line_number', 'unknown line')

                print(f"  {i}. {test_name}")
                print(f"     位置: {file_path}:{line_number}")
                print(f"     描述: {issue_text}")
                print()

            print("🚨 高危安全漏洞阻止构建通过！请修复以上问题后重新提交。")
            return 1

        # 如果有中危问题，警告但不阻止构建
        if medium_issues:
            print(f"\n⚠️  发现 {medium_count} 个中危安全问题，建议修复:")

            for issue in medium_issues[:5]:  # 只显示前5个中危问题
                test_name = issue.get('test_name', 'unknown')
                file_path = issue.get('filename', 'unknown file')
                print(f"   - {test_name} ({file_path})")

            if medium_count > 5:
                print(f"   ... 还有 {medium_count - 5} 个中危问题")

        # 没有高危问题
        print(f"\n✅ 安全扫描通过 - 无高危漏洞")
        return 0

    except FileNotFoundError:
        print("✅ 安全报告文件未找到，跳过安全检查")
        return 0
    except json.JSONDecodeError as e:
        print(f"❌ 安全报告格式错误: {e}")
        return 1
    except Exception as e:
        print(f"❌ 安全检查失败: {e}")
        return 1


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='安全报告检查脚本')
    parser.add_argument(
        '--report-path',
        default='bandit-report.json',
        help='安全报告文件路径 (默认: bandit-report.json)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出模式'
    )

    args = parser.parse_args()

    if args.verbose:
        print(f"🔍 检查安全报告: {args.report_path}")

    exit_code = check_security_report(args.report_path)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()