#!/usr/bin/env python3
"""
GitHub Issues自动化清理工具
GitHub Issues Automated Cleaner

定期检查GitHub Issues状态，自动识别需要清理的Issues
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


class GitHubIssueCleaner:
    """GitHub Issue清理器"""

    def __init__(self, repo: str, dry_run: bool = True):
        """
        初始化清理器

        Args:
            repo: 仓库名称，格式为 "owner/repo"
            dry_run: 是否为试运行模式
        """
        self.repo = repo
        self.dry_run = dry_run
        self.now = datetime.now()

    def run_command(self, command: str) -> dict[str, Any]:
        """运行shell命令并返回结果"""
        import subprocess
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                check=True
            )
            return {
                "success": True,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip()
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "stdout": e.stdout.strip() if e.stdout else "",
                "stderr": e.stderr.strip() if e.stderr else str(e)
            }

    def get_issues(self, state: str = "open") -> list[dict[str, Any]]:
        """获取Issues列表"""
        command = f"gh issue list --repo {self.repo} --state {state} --limit 100 --json number,title,labels,state,createdAt,updatedAt,author,assignees"
        result = self.run_command(command)

        if not result["success"]:
            return []

        try:
            return json.loads(result["stdout"])
        except json.JSONDecodeError:
            return []

    def parse_date(self, date_str: str) -> datetime:
        """解析ISO日期字符串"""
        try:
            # 处理Z时区标记
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            dt = datetime.fromisoformat(date_str)
            # 转换为无时区的datetime以便比较
            return dt.replace(tzinfo=None)
        except (ValueError, AttributeError):
            return self.now

    def is_stale(self, issue: dict[str, Any], days: int = 30) -> bool:
        """检查Issue是否过期"""
        updated_at = self.parse_date(issue["updatedAt"])
        return (self.now - updated_at) > timedelta(days=days)

    def is_inactive(self, issue: dict[str, Any], days: int = 60) -> bool:
        """检查Issue是否长期无活动"""
        return self.is_stale(issue, days)

    def has_label(self, issue: dict[str, Any], label: str) -> bool:
        """检查Issue是否有指定标签"""
        return any(label_info["name"] == label for label_info in issue.get("labels", []))

    def extract_status_from_labels(self, issue: dict[str, Any]) -> str | None:
        """从标签中提取状态信息"""
        status_labels = ["status/completed", "status/resolved", "status/in-progress", "status/cancelled"]
        for label in issue.get("labels", []):
            if label["name"] in status_labels:
                return label["name"].replace("status/", "")
        return None

    def categorize_issues(self, issues: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """对Issues进行分类"""
        categories = {
            "completed_but_open": [],
            "stale_issues": [],
            "inactive_issues": [],
            "unassigned_high_priority": [],
            "missing_priority_labels": [],
            "duplicate_candidates": [],
            "healthy_issues": []
        }

        for issue in issues:
            # 检查已完成但未关闭的Issues
            status = self.extract_status_from_labels(issue)
            if status in ["completed", "resolved"] and issue["state"] == "open":
                categories["completed_but_open"].append(issue)
                continue

            # 检查过期Issues（30天未更新）
            if self.is_stale(issue, 30):
                categories["stale_issues"].append(issue)
                continue

            # 检查长期无活动Issues（60天未更新）
            if self.is_inactive(issue, 60):
                categories["inactive_issues"].append(issue)
                continue

            # 检查高优先级但未分配的Issues
            has_priority = any(label["name"].startswith("priority/") for label in issue.get("labels", []))
            has_high_priority = self.has_label(issue, "priority/high") or self.has_label(issue, "priority/critical")
            if has_high_priority and not issue.get("assignees"):
                categories["unassigned_high_priority"].append(issue)
                continue

            # 检查缺少优先级标签的Issues
            if not has_priority and issue["state"] == "open":
                categories["missing_priority_labels"].append(issue)
                continue

            # 健康的Issues
            categories["healthy_issues"].append(issue)

        return categories

    def generate_cleanup_report(self, categories: dict[str, list[dict[str, Any]]]) -> str:
        """生成清理报告"""
        report = []
        report.append("# GitHub Issues清理报告")
        report.append(f"生成时间: {self.now.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"仓库: {self.repo}")
        report.append(f"模式: {'试运行' if self.dry_run else '执行模式'}")
        report.append("")

        total_issues = sum(len(issues) for issues in categories.values())
        report.append("## 📊 总体统计")
        report.append(f"- 总Issues数: {total_issues}")
        report.append("")

        # 各分类统计
        for category, issues in categories.items():
            if issues:
                category_name = {
                    "completed_but_open": "✅ 已完成但未关闭",
                    "stale_issues": "⚠️  过期Issues (30天+未更新)",
                    "inactive_issues": "🕐 长期无活动 (60天+未更新)",
                    "unassigned_high_priority": "🔥 高优先级未分配",
                    "missing_priority_labels": "📋 缺少优先级标签",
                    "duplicate_candidates": "🔄 重复候选",
                    "healthy_issues": "💚 健康Issues"
                }.get(category, category)

                report.append(f"## {category_name}: {len(issues)}个")

                for issue in issues[:10]:  # 只显示前10个
                    updated_at = self.parse_date(issue["updatedAt"])
                    days_ago = (self.now - updated_at).days

                    labels = ", ".join([label["name"] for label in issue.get("labels", [])[:3]])
                    if len(issue.get("labels", [])) > 3:
                        labels += f" (+{len(issue.get('labels', [])) - 3})"

                    report.append(f"- **#{issue['number']}**: {issue['title']}")
                    report.append(f"  - 状态: {issue['state']} | {days_ago}天前更新")
                    report.append(f"  - 标签: {labels}")
                    if issue.get("assignees"):
                        assignees = ", ".join([assignee["login"] for assignee in issue["assignees"]])
                        report.append(f"  - 负责人: {assignees}")
                    report.append("")

                if len(issues) > 10:
                    report.append(f"- ... 还有 {len(issues) - 10} 个Issues")
                    report.append("")

        # 清理建议
        report.append("## 🎯 清理建议")

        if categories["completed_but_open"]:
            report.append("1. **关闭已完成的Issues**: 这些Issues标记为已完成但仍开放")

        if categories["stale_issues"]:
            report.append("2. **更新过期Issues**: 联系维护者更新状态或关闭")

        if categories["inactive_issues"]:
            report.append("3. **清理长期无活动Issues**: 考虑关闭或重新评估")

        if categories["unassigned_high_priority"]:
            report.append("4. **分配高优先级Issues**: 为高优先级Issues指定负责人")

        if categories["missing_priority_labels"]:
            report.append("5. **添加优先级标签**: 为开放Issues添加优先级标记")

        return "\n".join(report)

    def close_completed_issues(self, issues: list[dict[str, Any]]) -> int:
        """关闭已完成的Issues"""
        closed_count = 0

        for issue in issues:
            if self.dry_run:
                closed_count += 1
            else:
                command = f"gh issue close {issue['number']} --repo {self.repo} --comment 'Issue已完成，自动关闭'"
                result = self.run_command(command)
                if result["success"]:
                    closed_count += 1
                else:
                    pass

        return closed_count

    def add_missing_priority_labels(self, issues: list[dict[str, Any]]) -> int:
        """为缺少优先级标签的Issues添加默认标签"""
        labeled_count = 0

        for issue in issues:
            if self.dry_run:
                labeled_count += 1
            else:
                command = f"gh issue edit {issue['number']} --repo {self.repo} --add-label 'priority/medium'"
                result = self.run_command(command)
                if result["success"]:
                    labeled_count += 1
                else:
                    pass

        return labeled_count

    def run_cleanup(self) -> dict[str, int]:
        """执行清理操作"""

        # 获取所有开放Issues
        issues = self.get_issues("open")
        if not issues:
            return {}


        # 分类Issues
        categories = self.categorize_issues(issues)

        # 生成报告
        report = self.generate_cleanup_report(categories)

        # 保存报告
        report_path = Path("reports/github_issues_cleanup_report.md")
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)


        # 执行清理操作
        results = {}

        if not self.dry_run:

            if categories["completed_but_open"]:
                results["closed_completed"] = self.close_completed_issues(categories["completed_but_open"])

            if categories["missing_priority_labels"]:
                results["added_priority_labels"] = self.add_missing_priority_labels(categories["missing_priority_labels"])

        else:
            pass

        return results


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="GitHub Issues自动化清理工具")
    parser.add_argument("--repo", default="xupeng211/FootballPrediction", help="仓库名称 (默认: xupeng211/FootballPrediction)")
    parser.add_argument("--execute", action="store_true", help="执行实际清理操作 (默认为试运行)")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式 (默认)")

    args = parser.parse_args()

    # 确定运行模式
    dry_run = not args.execute

    # 创建清理器
    cleaner = GitHubIssueCleaner(args.repo, dry_run=dry_run)

    # 执行清理
    results = cleaner.run_cleanup()

    # 输出结果统计
    if results:
        for operation, _count in results.items():
            {
                "closed_completed": "关闭已完成Issues",
                "added_priority_labels": "添加优先级标签"
            }.get(operation, operation)


if __name__ == "__main__":
    main()
