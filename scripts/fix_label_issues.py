#!/usr/bin/env python3
"""
GitHub Issues标签修复脚本
自动修复标签使用不一致的问题

Author: Claude Code
Version: 1.0
Purpose: Fix inconsistent label usage automatically
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests


class LabelIssueFixer:
    """标签问题修复器"""

    def __init__(self, repo: str, github_token: str = None):
        self.repo = repo
        self.github_token = github_token
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Label-Issue-Fixer/1.0"
        }

        if github_token:
            self.headers["Authorization"] = f"token {github_token}"

        # 标签修复规则
        self.label_fixes = {
            # 状态标签修复
            "status": {
                "patterns": [
                    (r"todo", "status/pending"),
                    (r"todo\s*doing", "status/in-progress"),
                    (r"in\s*progress", "status/in-progress"),
                    (r"doing", "status/in-progress"),
                    (r"done", "status/completed"),
                    (r"complete", "status/completed"),
                    (r"finished", "status/completed"),
                    (r"blocked", "status/blocked"),
                    (r"hold", "status/on-hold"),
                ]
            },
            # 优先级标签修复
            "priority": {
                "patterns": [
                    (r"critical", "priority/critical"),
                    (r"urgent", "priority/critical"),
                    (r"high", "priority/high"),
                    (r"medium", "priority/medium"),
                    (r"low", "priority/low"),
                ]
            },
            # 类型标签修复
            "type": {
                "patterns": [
                    (r"bug", "bug"),
                    (r"feature", "enhancement"),
                    (r"enhancement", "enhancement"),
                    (r"doc", "documentation"),
                    (r"documentation", "documentation"),
                    (r"test", "testing"),
                    (r"testing", "testing"),
                    (r"perf", "performance"),
                    (r"performance", "performance"),
                    (r"refactor", "refactoring"),
                    (r"refactoring", "refactoring"),
                    (r"infra", "infrastructure"),
                    (r"infrastructure", "infrastructure"),
                ]
            }
        }

        # 标签颜色规范
        self.label_colors = {
            "status/": "0075ca",      # 蓝色
            "priority/": "d73a4a",   # 红色
            "enhancement": "a2eeef", # 浅绿色
            "bug": "d73a4a",         # 红色
            "documentation": "0075ca", # 蓝色
            "testing": "fef2c0",     # 黄色
            "performance": "1d76db", # 深蓝色
            "refactoring": "fbca04", # 橙色
            "infrastructure": "ededed", # 灰色
            "claude-code": "7057ff", # 紫色
            "automated": "006b75",   # 青色
        }

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
                    "description": label.get("description", ""),
                    "url": label["url"]
                }

            return labels

        except requests.exceptions.RequestException as e:
            print(f"获取标签失败: {e}")
            return {}

    def create_label(self, name: str, color: str, description: str = "") -> bool:
        """创建新标签"""
        url = f"https://api.github.com/repos/{self.repo}/labels"
        data = {
            "name": name,
            "color": color,
            "description": description
        }

        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            print(f"✅ 创建标签: {name}")
            return True

        except requests.exceptions.RequestException as e:
            print(f"❌ 创建标签 {name} 失败: {e}")
            return False

    def update_label(self, name: str, color: str, description: str = "") -> bool:
        """更新现有标签"""
        url = f"https://api.github.com/repos/{self.repo}/labels/{name}"
        data = {
            "color": color,
            "description": description
        }

        try:
            response = requests.patch(url, headers=self.headers, json=data)
            response.raise_for_status()
            print(f"✅ 更新标签: {name}")
            return True

        except requests.exceptions.RequestException as e:
            print(f"❌ 更新标签 {name} 失败: {e}")
            return False

    def fix_label_colors(self) -> dict:
        """修复标签颜色"""
        print("🎨 开始修复标签颜色...")

        repo_labels = self.get_repo_labels()
        fixes_applied = []

        for label_name, label_info in repo_labels.items():
            expected_color = None

            # 查找匹配的颜色规范
            for prefix, color in self.label_colors.items():
                if label_name.startswith(prefix):
                    expected_color = color
                    break

            if expected_color and label_info["color"] != expected_color:
                print(f"🔧 修复标签颜色: {label_name} ({label_info['color']} → {expected_color})")

                if self.update_label(label_name, expected_color, label_info["description"]):
                    fixes_applied.append({
                        "label": label_name,
                        "action": "color_fix",
                        "old_color": label_info["color"],
                        "new_color": expected_color
                    })

        return fixes_applied

    def get_issues_with_label_issues(self) -> list:
        """获取有标签问题的Issues"""
        url = f"https://api.github.com/repos/{self.repo}/issues"
        params = {
            "state": "all",
            "per_page": 100
        }

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()

            issues = response.json()
            problematic_issues = []

            for issue in issues:
                if "pull_request" in issue:
                    continue  # 跳过PR

                labels = [label["name"] for label in issue.get("labels", [])]
                issues_with_problems = self._analyze_label_problems(labels)

                if issues_with_problems:
                    problematic_issues.append({
                        "issue_number": issue["number"],
                        "title": issue["title"],
                        "current_labels": labels,
                        "problems": issues_with_problems,
                        "url": issue["html_url"]
                    })

            return problematic_issues

        except requests.exceptions.RequestException as e:
            print(f"获取Issues失败: {e}")
            return []

    def _analyze_label_problems(self, labels: list) -> list:
        """分析标签问题"""
        problems = []

        # 检查是否有状态标签
        has_status_label = any(label.startswith("status/") for label in labels)
        if not has_status_label and labels:  # 如果有标签但没有状态标签
            problems.append({
                "type": "missing_status",
                "description": "缺少状态标签"
            })

        # 检查是否有优先级标签
        has_priority_label = any(label.startswith("priority/") for label in labels)
        if not has_priority_label and labels:  # 如果有标签但没有优先级标签
            problems.append({
                "type": "missing_priority",
                "description": "缺少优先级标签"
            })

        # 检查标签格式问题
        for label in labels:
            if "/" in label:
                prefix, name = label.split("/", 1)
                if prefix not in ["status", "priority"]:
                    problems.append({
                        "type": "invalid_format",
                        "description": f"标签格式不正确: {label}"
                    })

        # 检查重复或相似标签
        normalized_labels = [label.lower().replace(" ", "").replace("-", "") for label in labels]
        if len(set(normalized_labels)) != len(normalized_labels):
            problems.append({
                "type": "duplicate_labels",
                "description": "存在重复或相似的标签"
            })

        return problems

    def fix_issue_labels(self, issue_number: int, current_labels: list, problems: list) -> bool:
        """修复Issue的标签"""
        url = f"https://api.github.com/repos/{self.repo}/issues/{issue_number}/labels"

        # 保留有效的标签
        fixed_labels = []

        # 处理当前标签
        for label in current_labels:
            should_keep = True

            # 检查格式问题
            if "/" in label:
                prefix, name = label.split("/", 1)
                if prefix not in ["status", "priority"]:
                    should_keep = False
                    # 尝试转换格式
                    converted_label = self._convert_label_format(label)
                    if converted_label:
                        fixed_labels.append(converted_label)
                        print(f"  🔧 转换标签: {label} → {converted_label}")

            if should_keep:
                fixed_labels.append(label)

        # 添加缺失的必要标签
        for problem in problems:
            if problem["type"] == "missing_status":
                fixed_labels.append("status/pending")
                print(f"  ➕ 添加状态标签: status/pending")
            elif problem["type"] == "missing_priority":
                fixed_labels.append("priority/medium")
                print(f"  ➕ 添加优先级标签: priority/medium")

        # 去重
        fixed_labels = list(set(fixed_labels))

        try:
            response = requests.put(url, headers=self.headers, json={"labels": fixed_labels})
            response.raise_for_status()
            print(f"✅ Issue #{issue_number} 标签已修复")
            return True

        except requests.exceptions.RequestException as e:
            print(f"❌ 修复Issue #{issue_number} 标签失败: {e}")
            return False

    def _convert_label_format(self, label: str) -> str:
        """转换标签格式"""
        label_lower = label.lower()

        # 状态标签转换
        status_mapping = {
            "todo": "status/pending",
            "inprogress": "status/in-progress",
            "doing": "status/in-progress",
            "done": "status/completed",
            "completed": "status/completed",
            "blocked": "status/blocked",
            "onhold": "status/on-hold",
        }

        for old, new in status_mapping.items():
            if old in label_lower:
                return new

        # 优先级标签转换
        priority_mapping = {
            "critical": "priority/critical",
            "urgent": "priority/critical",
            "high": "priority/high",
            "medium": "priority/medium",
            "low": "priority/low",
        }

        for old, new in priority_mapping.items():
            if old in label_lower:
                return new

        return None

    def run_label_fixes(self, execute: bool = False) -> dict:
        """运行标签修复"""
        print("🔍 开始分析标签问题...")

        # 修复标签颜色
        color_fixes = self.fix_label_colors()

        # 获取有标签问题的Issues
        problematic_issues = self.get_issues_with_label_issues()

        print(f"📋 发现 {len(problematic_issues)} 个有标签问题的Issues")

        issue_fixes = []

        for issue in problematic_issues:
            print(f"\n🔧 处理Issue #{issue['issue_number']}: {issue['title']}")
            print(f"  当前标签: {', '.join(issue['current_labels'])}")
            print(f"  问题: {', '.join([p['description'] for p in issue['problems']])}")

            if execute:
                if self.fix_issue_labels(issue["issue_number"], issue["current_labels"], issue["problems"]):
                    issue_fixes.append({
                        "issue_number": issue["issue_number"],
                        "title": issue["title"],
                        "problems_fixed": issue["problems"],
                        "url": issue["url"]
                    })
            else:
                print("  🔍 试运行模式 - 跳过实际修复")

        return {
            "color_fixes": color_fixes,
            "issue_fixes": issue_fixes,
            "total_issues_processed": len(problematic_issues)
        }

    def generate_fix_report(self, fix_results: dict) -> str:
        """生成修复报告"""
        report_lines = [
            "# GitHub Issues标签修复报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**仓库**: {self.repo}",
            "",
            "## 📊 修复统计",
            "",
            f"- **标签颜色修复**: {len(fix_results['color_fixes'])} 个",
            f"- **Issue标签修复**: {len(fix_results['issue_fixes'])} 个",
            f"- **处理Issues总数**: {fix_results['total_issues_processed']}",
            "",
        ]

        if fix_results["color_fixes"]:
            report_lines.extend([
                "## 🎨 标签颜色修复",
                ""
            ])
            for fix in fix_results["color_fixes"]:
                report_lines.append(
                    f"- **{fix['label']}**: {fix['old_color']} → {fix['new_color']}"
                )
            report_lines.append("")

        if fix_results["issue_fixes"]:
            report_lines.extend([
                "## 🔧 Issue标签修复",
                ""
            ])
            for fix in fix_results["issue_fixes"]:
                report_lines.extend([
                    f"### #{fix['issue_number']} {fix['title']}",
                    f"- **修复的问题**: {', '.join([p['description'] for p in fix['problems_fixed']])}",
                    f"- **链接**: {fix['url']}",
                    ""
                ])

        report_lines.extend([
            "## 📋 修复规则",
            "",
            "### 标签颜色规范",
            "- `status/*`: 蓝色 (#0075ca)",
            "- `priority/*`: 红色 (#d73a4a)",
            "- `enhancement`: 浅绿色 (#a2eeef)",
            "- `bug`: 红色 (#d73a4a)",
            "- `documentation`: 蓝色 (#0075ca)",
            "- `testing`: 黄色 (#fef2c0)",
            "- `performance`: 深蓝色 (#1d76db)",
            "- `refactoring`: 橙色 (#fbca04)",
            "- `infrastructure`: 灰色 (#ededed)",
            "- `claude-code`: 紫色 (#7057ff)",
            "- `automated`: 青色 (#006b75)",
            "",
            "### 标签格式规范",
            "- 状态标签: `status/pending`, `status/in-progress`, `status/completed`, `status/blocked`, `status/on-hold`",
            "- 优先级标签: `priority/critical`, `priority/high`, `priority/medium`, `priority/low`",
            "- 类型标签: `enhancement`, `bug`, `documentation`, `testing`, `performance`, `refactoring`, `infrastructure`",
            "",
            "## 💡 建议",
            "",
            "1. 🏷️ **定期检查**: 建立定期标签检查机制",
            "2. 📚 **文档更新**: 更新标签使用指南",
            "3. 🎨 **颜色一致**: 确保同类标签使用统一颜色",
            "4. 🔄 **自动化**: 考虑自动化标签管理流程",
            "",
            "---",
            f"*报告生成时间: {datetime.now().isoformat()}*",
            f"*工具: Label Issue Fixer v1.0*"
        ])

        return "\n".join(report_lines)

    def save_fix_report(self, fix_results: dict, output_file: str = None):
        """保存修复报告"""
        report_content = self.generate_fix_report(fix_results)

        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report_content, encoding='utf-8')
            print(f"📄 修复报告已保存到: {output_path}")
        else:
            # 使用默认文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_file = f"reports/label_fix_report_{timestamp}.md"
            output_path = Path(default_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report_content, encoding='utf-8')
            print(f"📄 修复报告已保存到: {output_path}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="修复GitHub Issues标签问题")
    parser.add_argument("--repo", required=True, help="GitHub仓库 (格式: owner/repo)")
    parser.add_argument("--token", help="GitHub访问令牌")
    parser.add_argument("--execute", action="store_true", help="实际执行修复操作")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式 (默认)")
    parser.add_argument("--output", help="输出报告文件路径")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    # 获取GitHub令牌
    github_token = args.token or os.environ.get("GITHUB_TOKEN")

    if not github_token:
        print("⚠️ 警告: 未提供GitHub令牌，API调用可能受限")

    # 确定执行模式
    execute = args.execute and not args.dry_run

    if execute:
        print("🔧 执行模式 - 将实际修复标签问题")
    else:
        print("🔍 试运行模式 - 仅生成报告")

    # 创建修复器
    fixer = LabelIssueFixer(args.repo, github_token)

    # 执行修复
    fix_results = fixer.run_label_fixes(execute)

    # 生成报告
    fixer.save_fix_report(fix_results, args.output)

    if args.verbose:
        print(f"\n📊 修复完成!")
        print(f"🎨 标签颜色修复: {len(fix_results['color_fixes'])}")
        print(f"🔧 Issue标签修复: {len(fix_results['issue_fixes'])}")
        print(f"📋 处理Issues: {fix_results['total_issues_processed']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())