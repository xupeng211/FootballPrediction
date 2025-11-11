#!/usr/bin/env python3
"""
Issue进度跟踪脚本
跟踪Issue的处理进度，识别停滞的Issues并提供优化建议

Author: Claude Code
Version: 1.0
Purpose: Monitor issue progress and identify bottlenecks
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests


class IssueProgressTracker:
    """Issue进度跟踪器"""

    def __init__(self, repo: str, github_token: str = None):
        self.repo = repo
        self.github_token = github_token
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Issue-Progress-Tracker/1.0"
        }

        if github_token:
            self.headers["Authorization"] = f"token {github_token}"

        # 进度阈值配置
        self.thresholds = {
            "stale_days": 7,        # 超过7天无更新视为停滞
            "overdue_days": 14,     # 超过14天视为逾期
            "critical_overdue": 21  # 超过21天视为严重逾期
        }

    def get_all_open_issues(self) -> list:
        """获取所有开放的Issues"""
        all_issues = []
        page = 1

        while True:
            url = f"https://api.github.com/repos/{self.repo}/issues"
            params = {
                "state": "open",
                "per_page": 100,
                "page": page,
                "sort": "updated",
                "direction": "desc"
            }

            try:
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()

                page_issues = response.json()
                if not page_issues:
                    break

                # 过滤掉PR (PRs在GitHub API中也是issues)
                issues = [issue for issue in page_issues if "pull_request" not in issue]
                all_issues.extend(issues)

                if len(page_issues) < 100:
                    break

                page += 1

            except requests.exceptions.RequestException:
                break

        return all_issues

    def get_issue_events(self, issue_number: int) -> list:
        """获取Issue的事件历史"""
        url = f"https://api.github.com/repos/{self.repo}/issues/{issue_number}/events"
        params = {"per_page": 100}

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException:
            return []

    def analyze_issue_progress(self, issue: dict) -> dict:
        """分析单个Issue的进度状态"""
        issue_number = issue["number"]
        created_at = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
        updated_at = datetime.fromisoformat(issue["updated_at"].replace("Z", "+00:00"))
        now = datetime.now()

        # 计算时间指标
        age_days = (now - created_at).days
        days_since_update = (now - updated_at).days

        # 获取标签
        labels = [label["name"] for label in issue.get("labels", [])]

        # 分析状态
        status = "normal"
        if days_since_update > self.thresholds["critical_overdue"]:
            status = "critical_overdue"
        elif days_since_update > self.thresholds["overdue_days"]:
            status = "overdue"
        elif days_since_update > self.thresholds["stale_days"]:
            status = "stale"

        # 分析分配情况
        assignee = issue.get("assignee")
        is_assigned = assignee is not None

        # 分析里程碑
        milestone = issue.get("milestone")
        has_milestone = milestone is not None

        # 分析评论活跃度
        comments_count = issue.get("comments", 0)
        recent_comments = self._count_recent_comments(issue_number)

        # 获取事件历史
        events = self.get_issue_events(issue_number)
        last_event_date = self._get_last_event_date(events)

        return {
            "issue_number": issue_number,
            "title": issue["title"],
            "status": status,
            "age_days": age_days,
            "days_since_update": days_since_update,
            "assignee": assignee.get("login") if assignee else None,
            "is_assigned": is_assigned,
            "labels": labels,
            "has_milestone": has_milestone,
            "comments_count": comments_count,
            "recent_comments": recent_comments,
            "created_at": created_at.isoformat(),
            "updated_at": updated_at.isoformat(),
            "last_event_date": last_event_date,
            "url": issue["html_url"]
        }

    def _count_recent_comments(self, issue_number: int, days: int = 7) -> int:
        """统计最近评论数量"""
        # 简化实现，可以通过API获取评论时间戳
        url = f"https://api.github.com/repos/{self.repo}/issues/{issue_number}/comments"
        params = {"per_page": 100, "sort": "created", "direction": "desc"}

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()

            comments = response.json()
            cutoff_date = datetime.now() - timedelta(days=days)

            recent_count = 0
            for comment in comments:
                created_at = datetime.fromisoformat(comment["created_at"].replace("Z", "+00:00"))
                if created_at >= cutoff_date:
                    recent_count += 1
                else:
                    break

            return recent_count

        except requests.exceptions.RequestException:
            return 0

    def _get_last_event_date(self, events: list) -> str:
        """获取最后一个事件的日期"""
        if not events:
            return None

        latest_event = max(events, key=lambda e: e["created_at"])
        return latest_event["created_at"]

    def categorize_issues(self, issues_analysis: list) -> dict:
        """将Issues按状态分类"""
        categories = {
            "normal": [],
            "stale": [],
            "overdue": [],
            "critical_overdue": [],
            "unassigned": [],
            "no_milestone": [],
            "inactive": []
        }

        for analysis in issues_analysis:
            # 按更新时间分类
            categories[analysis["status"]].append(analysis)

            # 按其他条件分类
            if not analysis["is_assigned"]:
                categories["unassigned"].append(analysis)

            if not analysis["has_milestone"]:
                categories["no_milestone"].append(analysis)

            if analysis["recent_comments"] == 0 and analysis["days_since_update"] > 3:
                categories["inactive"].append(analysis)

        return categories

    def generate_progress_report(self, issues_analysis: list, categories: dict) -> str:
        """生成进度报告"""
        total_issues = len(issues_analysis)

        report_lines = [
            "# Issue进度跟踪报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**仓库**: {self.repo}",
            f"**总Issues数**: {total_issues}",
            "",
            "## 📊 总体统计",
            "",
            f"- **正常进展**: {len(categories['normal'])} ({len(categories['normal'])/total_issues*100:.1f}%)",
            f"- **停滞Issues**: {len(categories['stale'])} ({len(categories['stale'])/total_issues*100:.1f}%)",
            f"- **逾期Issues**: {len(categories['overdue'])} ({len(categories['overdue'])/total_issues*100:.1f}%)",
            f"- **严重逾期**: {len(categories['critical_overdue'])} ({len(categories['critical_overdue'])/total_issues*100:.1f}%)",
            f"- **未分配**: {len(categories['unassigned'])} ({len(categories['unassigned'])/total_issues*100:.1f}%)",
            f"- **无里程碑**: {len(categories['no_milestone'])} ({len(categories['no_milestone'])/total_issues*100:.1f}%)",
            f"- **不活跃**: {len(categories['inactive'])} ({len(categories['inactive'])/total_issues*100:.1f}%)",
            ""
        ]

        # 需要关注的Issues
        if categories["critical_overdue"]:
            report_lines.extend([
                "## 🚨 严重逾期Issues (需要立即关注)",
                ""
            ])
            for issue in categories["critical_overdue"]:
                report_lines.append(
                    f"- **#{issue['issue_number']} {issue['title']}** "
                    f"(逾期{issue['days_since_update']}天) "
                    f"[查看详情]({issue['url']})"
                )
            report_lines.append("")

        if categories["overdue"]:
            report_lines.extend([
                "## ⚠️ 逾期Issues",
                ""
            ])
            for issue in categories["overdue"][:10]:  # 只显示前10个
                report_lines.append(
                    f"- **#{issue['issue_number']} {issue['title']}** "
                    f"(逾期{issue['days_since_update']}天) "
                    f"[查看详情]({issue['url']})"
                )
            report_lines.append("")

        if categories["stale"]:
            report_lines.extend([
                "## 🕐 停滞Issues",
                ""
            ])
            for issue in categories["stale"][:15]:  # 只显示前15个
                report_lines.append(
                    f"- **#{issue['issue_number']} {issue['title']}** "
                    f"(未更新{issue['days_since_update']}天) "
                    f"[查看详情]({issue['url']})"
                )
            report_lines.append("")

        if categories["unassigned"]:
            report_lines.extend([
                "## 👥 未分配Issues",
                ""
            ])
            for issue in categories["unassigned"][:10]:  # 只显示前10个
                report_lines.append(
                    f"- **#{issue['issue_number']} {issue['title']}** "
                    f"[查看详情]({issue['url']})"
                )
            report_lines.append("")

        # 分析和建议
        report_lines.extend([
            "## 📈 分析和建议",
            ""
        ])

        # 健康度评分
        health_score = (len(categories["normal"]) / total_issues) * 100
        report_lines.append(f"**整体健康度**: {health_score:.1f}/100")

        if health_score >= 80:
            report_lines.append("✅ Issue管理状况良好")
        elif health_score >= 60:
            report_lines.append("⚠️ Issue管理需要改进")
        else:
            report_lines.append("🚨 Issue管理存在严重问题")

        report_lines.extend([
            "",
            "### 💡 优化建议",
            ""
        ])

        if categories["critical_overdue"]:
            report_lines.append("1. 🚨 **立即处理严重逾期Issues**: 这些Issues已经严重逾期，需要立即评估和采取行动")

        if categories["overdue"]:
            report_lines.append("2. ⚠️ **优先处理逾期Issues**: 制定计划解决逾期Issues，避免进一步恶化")

        if categories["stale"]:
            report_lines.append("3. 🕐 **重新激活停滞Issues**: 联系相关负责人，更新进度或重新评估")

        if categories["unassigned"]:
            report_lines.append("4. 👥 **及时分配新Issues**: 建立自动分配机制，确保Issues有明确负责人")

        if categories["no_milestone"]:
            report_lines.append("5. 🎯 **设置里程碑**: 为重要Issues设置里程碑，提高目标管理效果")

        report_lines.extend([
            "",
            "### 📊 进度指标",
            "",
            "- **平均处理时间**: 计算中...",
            "- **Issue完成率**: 计算中...",
            "- **团队响应速度**: 计算中...",
            "",
            "---",
            f"*报告生成时间: {datetime.now().isoformat()}*",
            "*工具: Issue Progress Tracker v1.0*"
        ])

        return "\n".join(report_lines)

    def run_progress_analysis(self) -> tuple:
        """运行进度分析"""

        issues = self.get_all_open_issues()
        if not issues:
            return [], {}


        # 分析每个Issue
        issues_analysis = []
        for issue in issues:
            analysis = self.analyze_issue_progress(issue)
            issues_analysis.append(analysis)

        # 分类Issues
        categories = self.categorize_issues(issues_analysis)


        return issues_analysis, categories

    def save_progress_report(self, report_content: str, output_file: str = None):
        """保存进度报告"""
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report_content, encoding='utf-8')
        else:
            # 使用默认文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_file = f"reports/issue_progress_report_{timestamp}.md"
            output_path = Path(default_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report_content, encoding='utf-8')


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Issue进度跟踪分析")
    parser.add_argument("--repo", required=True, help="GitHub仓库 (格式: owner/repo)")
    parser.add_argument("--token", help="GitHub访问令牌")
    parser.add_argument("--output", help="输出报告文件路径")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    # 获取GitHub令牌
    github_token = args.token or os.environ.get("GITHUB_TOKEN")

    if not github_token:
        pass

    # 创建跟踪器
    tracker = IssueProgressTracker(args.repo, github_token)

    # 执行进度分析
    issues_analysis, categories = tracker.run_progress_analysis()

    # 生成报告
    if issues_analysis:
        report_content = tracker.generate_progress_report(issues_analysis, categories)
        tracker.save_progress_report(report_content, args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
