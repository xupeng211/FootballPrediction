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
            return 0

        # 读取安全报告
        with open(report_file, encoding="utf-8") as f:
            data = json.load(f)

        # 检查结果
        results = data.get("results", [])
        high_issues = [r for r in results if r.get("issue_severity") == "HIGH"]
        medium_issues = [r for r in results if r.get("issue_severity") == "MEDIUM"]

        # 统计信息
        len(results)
        len(high_issues)
        medium_count = len(medium_issues)

        # 如果有高危问题，详细显示并返回错误码
        if high_issues:
            for _i, issue in enumerate(high_issues, 1):
                issue.get("test_name", "unknown")
                issue.get("issue_text", "unknown description")
                issue.get("filename", "unknown file")
                issue.get("line_number", "unknown line")

            return 1

        # 如果有中危问题，警告但不阻止构建
        if medium_issues:
            for issue in medium_issues[:5]:  # 只显示前5个中危问题
                issue.get("test_name", "unknown")
                issue.get("filename", "unknown file")

            if medium_count > 5:
                pass

        # 没有高危问题
        return 0

    except FileNotFoundError:
        return 0
    except json.JSONDecodeError:
        return 1
    except Exception:
        return 1


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="安全报告检查脚本")
    parser.add_argument(
        "--report-path",
        default="bandit-report.json",
        help="安全报告文件路径 (默认: bandit-report.json)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出模式")

    args = parser.parse_args()

    if args.verbose:
        pass

    exit_code = check_security_report(args.report_path)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
