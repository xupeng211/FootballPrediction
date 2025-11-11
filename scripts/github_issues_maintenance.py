#!/usr/bin/env python3
"""
GitHub Issues 维护和清理工具
GitHub Issues Maintenance and Cleanup Tool

用于定期维护GitHub Issues，确保符合最佳实践。
Used for regular maintenance of GitHub Issues to ensure best practices.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta


class GitHubIssuesMaintenance:
    """GitHub Issues 维护工具类"""

    def __init__(self):
        self.issues: list[dict] = []
        self.stats = {
            "total_open": 0,
            "completed_not_closed": 0,
            "duplicates": 0,
            "no_status_label": 0,
            "no_priority_label": 0,
            "old_issues": 0
        }

    def run_command(self, command: str) -> str:
        """运行shell命令并返回结果"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""

    def fetch_open_issues(self) -> None:
        """获取所有开放的Issues"""
        output = self.run_command("gh issue list --state open --json number,title,labels,createdAt,state")

        if output:
            try:
                self.issues = json.loads(output)
                self.stats["total_open"] = len(self.issues)
            except json.JSONDecodeError:
                self.issues = []
        else:
            self.issues = []

    def analyze_issues(self) -> None:
        """分析Issues状态"""

        for issue in self.issues:
            labels = [label["name"] for label in issue.get("labels", [])]

            # 检查已完成但未关闭的Issues
            if "status/completed" in labels and issue["state"] == "OPEN":
                self.stats["completed_not_closed"] += 1

            # 检查缺少状态标签的Issues
            if not any(label.startswith("status/") for label in labels):
                self.stats["no_status_label"] += 1

            # 检查缺少优先级标签的Issues
            if not any(label.startswith("priority/") for label in labels):
                self.stats["no_priority_label"] += 1

            # 检查老旧Issues (超过30天)
            created_at = datetime.fromisoformat(issue["createdAt"].replace("Z", "+00:00")).replace(tzinfo=None)
            if datetime.now() - created_at > timedelta(days=30):
                self.stats["old_issues"] += 1

    def detect_duplicates(self) -> None:
        """检测重复的Issues"""

        title_counts = {}
        for issue in self.issues:
            title = issue["title"]
            # 简单的重复检测：相同标题的Issues
            if title in title_counts:
                title_counts[title] += 1
            else:
                title_counts[title] = 1

        duplicates = [title for title, count in title_counts.items() if count > 1]
        self.stats["duplicates"] = len(duplicates)

        if duplicates:
            for title in duplicates:
                pass

    def generate_report(self) -> str:
        """生成维护报告"""
        report = f"""
# 📊 GitHub Issues 维护报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📈 统计数据
- **开放Issues总数**: {self.stats['total_open']}
- **已完成但未关闭**: {self.stats['completed_not_closed']}
- **重复Issues**: {self.stats['duplicates']}
- **缺少状态标签**: {self.stats['no_status_label']}
- **缺少优先级标签**: {self.stats['no_priority_label']}
- **老旧Issues (>30天)**: {self.stats['old_issues']}

## 🎯 健康状态评估
"""

        # 健康状态评估
        health_score = 100
        issues = []

        if self.stats["total_open"] > 10:
            health_score -= 20
            issues.append("开放Issues数量过多 (>10)")

        if self.stats["completed_not_closed"] > 0:
            health_score -= 15
            issues.append(f"存在{self.stats['completed_not_closed']}个已完成但未关闭的Issues")

        if self.stats["duplicates"] > 0:
            health_score -= 20
            issues.append(f"存在{self.stats['duplicates']}组重复Issues")

        if self.stats["no_status_label"] > 0:
            health_score -= 10
            issues.append(f"存在{self.stats['no_status_label']}个缺少状态标签的Issues")

        if self.stats["no_priority_label"] > 0:
            health_score -= 5
            issues.append(f"存在{self.stats['no_priority_label']}个缺少优先级标签的Issues")

        if health_score >= 90:
            status = "🟢 优秀"
        elif health_score >= 70:
            status = "🟡 良好"
        else:
            status = "🔴 需要改进"

        report += f"**总体健康状态**: {status} ({health_score}/100分)\n\n"

        if issues:
            report += "## ⚠️ 发现的问题\n"
            for issue in issues:
                report += f"- {issue}\n"
        else:
            report += "## ✅ 未发现问题，GitHub Issues管理状态良好！\n"

        report += """
## 💡 建议的行动
1. **定期维护**: 建议每周运行一次此检查
2. **及时关闭**: 完成任务后立即关闭对应Issues
3. **标签规范**: 确保所有Issues都有状态和优先级标签
4. **避免重复**: 创建新Issue前检查是否已存在类似Issue

## 📋 当前活跃Issues
"""

        for issue in self.issues:
            labels = [label["name"] for label in issue.get("labels", [])]
            priority = next((l for l in labels if l.startswith("priority/")), "未设置")
            status = next((l for l in labels if l.startswith("status/")), "未设置")
            report += f"- **#{issue['number']}**: {issue['title']} (优先级: {priority}, 状态: {status})\n"

        return report

    def save_report(self, report: str) -> None:
        """保存报告到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reports/github_issues_maintenance_{timestamp}.md"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
        except Exception:
            pass

    def run_maintenance(self) -> None:
        """运行完整的维护流程"""

        self.fetch_open_issues()

        if not self.issues:
            return

        self.analyze_issues()
        self.detect_duplicates()

        report = self.generate_report()

        self.save_report(report)



def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        return

    maintenance = GitHubIssuesMaintenance()
    maintenance.run_maintenance()


if __name__ == "__main__":
    main()
