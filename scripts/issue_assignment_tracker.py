#!/usr/bin/env python3
"""
Issue分配和跟踪管理脚本
自动分配Issues给合适的团队成员并跟踪处理进度

Author: Claude Code
Version: 1.0
Purpose: Automated issue assignment and progress tracking
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import requests


class IssueAssignmentTracker:
    """Issue分配和跟踪器"""

    def __init__(self, repo: str, github_token: str = None):
        self.repo = repo
        self.github_token = github_token
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Issue-Assignment-Tracker/1.0"
        }

        if github_token:
            self.headers["Authorization"] = f"token {github_token}"

        # 团队成员专长领域配置
        self.team_expertise = {
            "backend": ["api", "database", "services", "cache", "ml"],
            "frontend": ["ui", "ux", "documentation", "templates"],
            "devops": ["docker", "ci/cd", "deployment", "infrastructure"],
            "testing": ["tests", "quality", "coverage", "performance"],
            "architecture": ["design", "patterns", "ddd", "cqrs"]
        }

        # 团队成员配置
        self.team_members = {
            "backend-developer": {
                "expertise": ["backend"],
                "max_assignments": 5,
                "current_assignments": 0
            },
            "frontend-developer": {
                "expertise": ["frontend"],
                "max_assignments": 4,
                "current_assignments": 0
            },
            "devops-engineer": {
                "expertise": ["devops"],
                "max_assignments": 3,
                "current_assignments": 0
            },
            "qa-engineer": {
                "expertise": ["testing"],
                "max_assignments": 6,
                "current_assignments": 0
            },
            "architect": {
                "expertise": ["architecture"],
                "max_assignments": 3,
                "current_assignments": 0
            }
        }

    def get_unassigned_issues(self) -> list:
        """获取未分配的Issues"""
        url = f"https://api.github.com/repos/{self.repo}/issues"
        params = {
            "state": "open",
            "labels": "status/pending",
            "assignee": "none",
            "per_page": 100
        }

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException:
            return []

    def get_team_member_assignments(self, member: str) -> int:
        """获取团队成员当前的分配数量"""
        url = f"https://api.github.com/repos/{self.repo}/issues"
        params = {
            "state": "open",
            "assignee": member,
            "per_page": 100
        }

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return len(response.json())

        except requests.exceptions.RequestException:
            return 0

    def analyze_issue_content(self, issue: dict) -> dict:
        """分析Issue内容，确定分类和优先级"""
        title = issue.get("title", "").lower()
        body = issue.get("body", "").lower()
        content = f"{title} {body}"
        [label["name"].lower() for label in issue.get("labels", [])]

        analysis = {
            "expertise_areas": [],
            "complexity": "medium",
            "urgency": "normal",
            "estimated_hours": 4
        }

        # 分析专长领域
        for area, keywords in self.team_expertise.items():
            if any(keyword in content for keyword in keywords):
                analysis["expertise_areas"].append(area)

        # 分析复杂度
        complexity_indicators = {
            "high": ["refactor", "architecture", "performance", "security", "migration"],
            "low": ["documentation", "typo", "minor", "simple", "quick"]
        }

        for level, indicators in complexity_indicators.items():
            if any(indicator in content for indicator in indicators):
                analysis["complexity"] = level
                break

        # 分析紧急程度
        urgency_indicators = {
            "high": ["critical", "urgent", "blocker", "production"],
            "normal": ["enhancement", "feature", "improvement"],
            "low": ["nice-to-have", "wishlist", "low-priority"]
        }

        for urgency, indicators in urgency_indicators.items():
            if any(indicator in content for indicator in indicators):
                analysis["urgency"] = urgency
                break

        # 估算工作时间
        complexity_hours = {
            "low": 2,
            "medium": 4,
            "high": 8
        }

        urgency_multiplier = {
            "low": 0.8,
            "normal": 1.0,
            "high": 1.2
        }

        analysis["estimated_hours"] = int(
            complexity_hours[analysis["complexity"]] * urgency_multiplier[analysis["urgency"]]
        )

        return analysis

    def find_best_assignee(self, issue_analysis: dict) -> str:
        """找到最合适的分配人选"""
        required_expertise = issue_analysis["expertise_areas"]

        if not required_expertise:
            return None  # 无法确定专长领域

        # 筛选具有相关专长的团队成员
        candidates = []
        for member, info in self.team_members.items():
            if any(exp in required_expertise for exp in info["expertise"]):
                # 更新当前分配数量
                current_assignments = self.get_team_member_assignments(member)
                info["current_assignments"] = current_assignments

                # 检查是否还有容量
                if current_assignments < info["max_assignments"]:
                    candidates.append((member, info))

        if not candidates:
            return None  # 没有合适的人选

        # 根据工作负载和专长匹配度评分
        best_candidate = None
        best_score = -1

        for candidate, info in candidates:
            # 计算负载分数 (负载越低分数越高)
            load_score = 1.0 - (info["current_assignments"] / info["max_assignments"])

            # 计算专长匹配分数
            expertise_match = len(set(info["expertise"]) & set(required_expertise))
            expertise_score = expertise_match / len(required_expertise)

            # 综合评分
            total_score = (load_score * 0.6) + (expertise_score * 0.4)

            if total_score > best_score:
                best_score = total_score
                best_candidate = candidate

        return best_candidate

    def assign_issue(self, issue_number: int, assignee: str) -> bool:
        """分配Issue给指定用户"""
        url = f"https://api.github.com/repos/{self.repo}/issues/{issue_number}/assignees"
        data = {"assignees": [assignee]}

        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            return True

        except requests.exceptions.RequestException:
            return False

    def update_issue_status(self, issue_number: int, status: str) -> bool:
        """更新Issue状态标签"""
        url = f"https://api.github.com/repos/{self.repo}/issues/{issue_number}/labels"

        # 移除旧状态标签，添加新状态标签
        old_status_labels = ["status/pending", "status/in-progress", "status/blocked", "status/on-hold"]
        new_labels = [f"status/{status}"]

        # 先获取现有标签
        try:
            get_url = f"https://api.github.com/repos/{self.repo}/issues/{issue_number}/labels"
            response = requests.get(get_url, headers=self.headers)
            response.raise_for_status()

            existing_labels = [label["name"] for label in response.json()]

            # 保留非状态标签
            for label in existing_labels:
                if not any(label.startswith(old_status) for old_status in old_status_labels):
                    new_labels.append(label)

            # 更新标签
            data = {"labels": new_labels}
            response = requests.put(url, headers=self.headers, json=data)
            response.raise_for_status()
            return True

        except requests.exceptions.RequestException:
            return False

    def generate_assignment_report(self, assignments: list) -> str:
        """生成分配报告"""
        report_lines = [
            "# Issue自动分配报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**仓库**: {self.repo}",
            f"**分配数量**: {len(assignments)}",
            "",
            "## 📋 分配详情",
            ""
        ]

        for assignment in assignments:
            report_lines.extend([
                f"### 🎯 Issue #{assignment['issue_number']}: {assignment['issue_title']}",
                "",
                f"- **分配给**: {assignment['assignee']}",
                f"- **专长领域**: {', '.join(assignment['analysis']['expertise_areas'])}",
                f"- **复杂度**: {assignment['analysis']['complexity']}",
                f"- **紧急程度**: {assignment['analysis']['urgency']}",
                f"- **预估工时**: {assignment['analysis']['estimated_hours']}小时",
                f"- **分配原因**: {assignment['reason']}",
                ""
            ])

        report_lines.extend([
            "## 📊 团队工作负载",
            ""
        ])

        # 统计团队工作负载
        for member, info in self.team_members.items():
            current_assignments = self.get_team_member_assignments(member)
            capacity_usage = (current_assignments / info["max_assignments"]) * 100

            report_lines.append(
                f"- **{member}**: {current_assignments}/{info['max_assignments']} ({capacity_usage:.1f}%)"
            )

        report_lines.extend([
            "",
            "## 💡 建议",
            "",
            "1. 📋 **定期检查**: 建议每日检查新Issues并进行分配",
            "2. ⚖️ **负载均衡**: 关注团队成员工作负载，避免过载",
            "3. 🎯 **专长匹配**: 根据Issue内容选择最合适的专长领域",
            "4. 📈 **进度跟踪**: 定期回顾分配效果和完成情况",
            "",
            "---",
            f"*报告生成时间: {datetime.now().isoformat()}*",
            "*工具: Issue Assignment Tracker v1.0*"
        ])

        return "\n".join(report_lines)

    def run_auto_assignment(self, dry_run: bool = True) -> list:
        """运行自动分配"""

        unassigned_issues = self.get_unassigned_issues()
        if not unassigned_issues:
            return []

        assignments = []

        for issue in unassigned_issues:

            # 分析Issue内容
            analysis = self.analyze_issue_content(issue)

            # 找到最合适的分配人选
            best_assignee = self.find_best_assignee(analysis)

            if best_assignee:
                assignment = {
                    "issue_number": issue["number"],
                    "issue_title": issue["title"],
                    "assignee": best_assignee,
                    "analysis": analysis,
                    "reason": f"专长匹配: {', '.join(analysis['expertise_areas'])}"
                }

                assignments.append(assignment)

                if not dry_run:
                    # 实际执行分配
                    if self.assign_issue(issue["number"], best_assignee):
                        self.update_issue_status(issue["number"], "in-progress")
                else:
                    pass
            else:
                pass

        return assignments

    def save_assignment_report(self, assignments: list, output_file: str = None):
        """保存分配报告"""
        if not assignments:
            return

        report_content = self.generate_assignment_report(assignments)

        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report_content, encoding='utf-8')
        else:
            # 使用默认文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_file = f"reports/issue_assignment_report_{timestamp}.md"
            output_path = Path(default_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report_content, encoding='utf-8')


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Issue分配和跟踪管理")
    parser.add_argument("--repo", required=True, help="GitHub仓库 (格式: owner/repo)")
    parser.add_argument("--token", help="GitHub访问令牌")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式，不实际分配")
    parser.add_argument("--output", help="输出报告文件路径")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    # 获取GitHub令牌
    github_token = args.token or os.environ.get("GITHUB_TOKEN")

    if not github_token:
        pass

    # 创建跟踪器
    tracker = IssueAssignmentTracker(args.repo, github_token)

    # 执行自动分配
    assignments = tracker.run_auto_assignment(args.dry_run)

    # 保存报告
    tracker.save_assignment_report(assignments, args.output)

    if args.verbose:
        if assignments:
            for _assignment in assignments:
                pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
