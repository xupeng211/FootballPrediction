#!/usr/bin/env python3
"""
Issue标签一致性检查脚本
检查GitHub Issues的标签使用是否符合规范

Author: Claude Code
Version: 1.0
Purpose: Validate label consistency and generate reports
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import requests


class LabelConsistencyChecker:
    """标签一致性检查器"""

    def __init__(self, repo: str, github_token: str = None):
        self.repo = repo
        self.github_token = github_token
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Label-Checker/1.0"
        }

        if github_token:
            self.headers["Authorization"] = f"token {github_token}"

    def get_issues(self) -> list:
        """获取所有开放和关闭的Issues"""
        all_issues = []

        # 获取开放Issues
        open_issues = self._fetch_issues("open")
        all_issues.extend(open_issues)

        # 获取最近关闭的Issues (最近30天)
        closed_issues = self._fetch_issues("closed", per_page=100)
        all_issues.extend(closed_issues)

        return all_issues

    def _fetch_issues(self, state: str, per_page: int = 100) -> list:
        """获取Issues数据"""
        issues = []
        page = 1

        while True:
            url = f"https://api.github.com/repos/{self.repo}/issues"
            params = {
                "state": state,
                "per_page": per_page,
                "page": page
            }

            try:
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()

                page_issues = response.json()
                if not page_issues:
                    break

                issues.extend(page_issues)
                page += 1

                # 避免API限制
                if len(page_issues) < per_page:
                    break

            except requests.exceptions.RequestException:
                break

        return issues

    def get_repo_labels(self) -> dict:
        """获取仓库的所有标签"""
        url = f"https://api.github.com/repos/{self.repo}/labels"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            labels = {}
            for label in response.json():
                labels[label["name"]] = {
                    "color": label["color"],
                    "description": label.get("description", "")
                }

            return labels

        except requests.exceptions.RequestException:
            return {}

    def analyze_label_consistency(self) -> dict:
        """分析标签一致性"""

        issues = self.get_issues()
        repo_labels = self.get_repo_labels()

        analysis = {
            "total_issues": len(issues),
            "issues_with_labels": 0,
            "issues_without_labels": 0,
            "label_usage_stats": {},
            "label_inconsistencies": [],
            "missing_required_labels": [],
            "deprecated_labels": [],
            "label_format_issues": []
        }

        # 标准标签分类
        standard_labels = {
            "status": ["status/pending", "status/in-progress", "status/completed", "status/blocked", "status/on-hold"],
            "priority": ["priority/critical", "priority/high", "priority/medium", "priority/low"],
            "type": ["enhancement", "bug", "documentation", "testing", "performance", "refactoring", "infrastructure", "claude-code", "automated"],
            "special": ["phase-x.y", "good-first-issue", "help-wanted", "question"]
        }

        for issue in issues:
            issue_labels = [label["name"] for label in issue.get("labels", [])]

            if issue_labels:
                analysis["issues_with_labels"] += 1

                # 统计标签使用频率
                for label in issue_labels:
                    if label in analysis["label_usage_stats"]:
                        analysis["label_usage_stats"][label] += 1
                    else:
                        analysis["label_usage_stats"][label] = 1

                # 检查标签组合一致性
                self._check_label_combinations(issue, issue_labels, standard_labels, analysis)

            else:
                analysis["issues_without_labels"] += 1
                analysis["missing_required_labels"].append({
                    "issue_number": issue["number"],
                    "issue_title": issue["title"],
                    "reason": "No labels assigned"
                })

        # 分析仓库标签规范
        self._analyze_repo_label_standards(repo_labels, analysis)

        return analysis

    def _check_label_combinations(self, issue, issue_labels, standard_labels, analysis):
        """检查标签组合的一致性"""
        issue_number = issue["number"]
        issue_title = issue["title"]

        # 检查是否缺少状态标签
        has_status_label = any(label.startswith("status/") for label in issue_labels)
        if not has_status_label and issue["state"] == "open":
            analysis["missing_required_labels"].append({
                "issue_number": issue_number,
                "issue_title": issue_title,
                "reason": "Missing status label for open issue"
            })

        # 检查是否缺少优先级标签
        has_priority_label = any(label.startswith("priority/") for label in issue_labels)
        if not has_priority_label:
            analysis["missing_required_labels"].append({
                "issue_number": issue_number,
                "issue_title": issue_title,
                "reason": "Missing priority label"
            })

        # 检查标签格式问题
        for label in issue_labels:
            if "/" in label:
                category, name = label.split("/", 1)
                if category not in standard_labels:
                    analysis["label_format_issues"].append({
                        "issue_number": issue_number,
                        "issue_title": issue_title,
                        "label": label,
                        "issue": f"Unknown label category: {category}"
                    })

    def _analyze_repo_label_standards(self, repo_labels, analysis):
        """分析仓库标签标准"""
        # 检查标签颜色一致性
        color_patterns = {
            "status": "0075ca",  # 蓝色
            "priority": "d73a4a",  # 红色
            "type": "a2eeef",     # 浅绿色
            "special": "7057ff"   # 紫色
        }

        for label_name, label_info in repo_labels.items():
            for category, expected_color in color_patterns.items():
                if label_name.startswith(category):
                    if label_info["color"] != expected_color:
                        analysis["label_inconsistencies"].append({
                            "label": label_name,
                            "issue": f"Color mismatch for {category} label",
                            "current_color": label_info["color"],
                            "expected_color": expected_color
                        })

    def generate_report(self, analysis: dict, output_file: str = None) -> str:
        """生成一致性检查报告"""
        report_lines = [
            "# Issue标签一致性检查报告",
            "",
            f"**检查时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**仓库**: {self.repo}",
            f"**总Issues数**: {analysis['total_issues']}",
            "",
            "## 📊 基础统计",
            "",
            f"- **有标签的Issues**: {analysis['issues_with_labels']}",
            f"- **无标签的Issues**: {analysis['issues_without_labels']}",
            f"- **标签覆盖率**: {analysis['issues_with_labels'] / analysis['total_issues'] * 100:.1f}%",
            "",
            "## 🏷️ 标签使用统计",
            ""
        ]

        # 标签使用统计
        sorted_labels = sorted(analysis["label_usage_stats"].items(), key=lambda x: x[1], reverse=True)
        for label, count in sorted_labels:
            report_lines.append(f"- **{label}**: {count}次使用")

        # 缺失必要标签的Issues
        if analysis["missing_required_labels"]:
            report_lines.extend([
                "",
                "## ⚠️ 缺失必要标签的Issues",
                ""
            ])
            for item in analysis["missing_required_labels"][:10]:  # 只显示前10个
                report_lines.append(
                    f"- **#{item['issue_number']} {item['issue_title']}**: {item['reason']}"
                )

        # 标签不一致问题
        if analysis["label_inconsistencies"]:
            report_lines.extend([
                "",
                "## 🔄 标签不一致问题",
                ""
            ])
            for item in analysis["label_inconsistencies"]:
                report_lines.append(
                    f"- **{item['label']}**: {item['issue']}"
                )

        # 标签格式问题
        if analysis["label_format_issues"]:
            report_lines.extend([
                "",
                "## 📝 标签格式问题",
                ""
            ])
            for item in analysis["label_format_issues"][:10]:  # 只显示前10个
                report_lines.append(
                    f"- **#{item['issue_number']} {item['issue_title']}**: 标签'{item['label']}' - {item['issue']}"
                )

        report_lines.extend([
            "",
            "## 💡 改进建议",
            "",
            "1. 🏷️ **统一标签使用**: 为所有Issue添加标准化的状态和优先级标签",
            "2. 📊 **标签分类**: 确保标签按照预定义的分类使用",
            "3. 🎨 **颜色规范**: 统一同类标签的颜色方案",
            "4. 🔄 **定期检查**: 建立定期标签检查和维护机制",
            "5. 📚 **文档更新**: 更新标签使用指南和最佳实践",
            "",
            "---",
            f"*报告生成时间: {datetime.now().isoformat()}*",
            "*工具: Label Consistency Checker v1.0*"
        ])

        report_content = "\n".join(report_lines)

        # 保存报告
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report_content, encoding='utf-8')

        return report_content


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="检查GitHub Issues标签一致性")
    parser.add_argument("--repo", required=True, help="GitHub仓库 (格式: owner/repo)")
    parser.add_argument("--token", help="GitHub访问令牌")
    parser.add_argument("--output", help="输出报告文件路径")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    # 获取GitHub令牌
    github_token = args.token or os.environ.get("GITHUB_TOKEN")

    if not github_token:
        pass

    # 创建检查器
    checker = LabelConsistencyChecker(args.repo, github_token)

    # 执行分析
    analysis = checker.analyze_label_consistency()

    # 生成报告
    checker.generate_report(analysis, args.output)

    if args.verbose:
        pass

    return 0


if __name__ == "__main__":
    import os
    sys.exit(main())
