#!/usr/bin/env python3
"""
创建生产就绪优化GitHub Issues的脚本

使用方法:
python scripts/create_production_ready_issues.py

该脚本会自动创建所有生产就绪相关的GitHub Issues，
并分配相应的标签和优先级。
"""

import os
import subprocess
import json
from datetime import datetime
from typing import List, Dict, Any

class IssueCreator:
    """GitHub Issue 创建器"""

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self.issues = []

    def create_issues(self) -> List[Dict[str, Any]]:
        """创建所有生产就绪相关的Issues"""

        # Critical Issues (P0)
        self._add_critical_issues()

        # High Priority Issues (P1)
        self._add_high_priority_issues()

        # Medium Priority Issues (P2)
        self._add_medium_priority_issues()

        return self.issues

    def _add_critical_issues(self):
        """添加Critical级别Issues"""

        issue_1 = {
            "title": "🚨 [P0-Critical] 修复语法错误阻止部署",
            "body": self._load_issue_template("production_ready_fix_1.md"),
            "labels": ["critical", "production-ready", "syntax-error", "P0"],
            "assignees": [],
            "milestone": "Production Ready Phase 1"
        }
        self.issues.append(issue_1)

        issue_2 = {
            "title": "🚨 [P0-Critical] 测试覆盖率提升 - 23% → 60%+",
            "body": self._load_issue_template("production_ready_fix_2.md"),
            "labels": ["critical", "production-ready", "test-coverage", "P0"],
            "assignees": [],
            "milestone": "Production Ready Phase 1"
        }
        self.issues.append(issue_2)

    def _add_high_priority_issues(self):
        """添加High优先级Issues"""

        issue_3 = {
            "title": "⚠️ [P1-High] 安全配置强化 - 移除硬编码敏感信息",
            "body": self._load_issue_template("production_ready_fix_3.md"),
            "labels": ["high", "production-ready", "security", "P1"],
            "assignees": [],
            "milestone": "Production Ready Phase 1"
        }
        self.issues.append(issue_3)

        issue_4 = {
            "title": "⚠️ [P1-High] 依赖和环境兼容性修复 - 解决测试环境问题",
            "body": self._load_issue_template("production_ready_fix_4.md"),
            "labels": ["high", "production-ready", "dependencies", "environment", "P1"],
            "assignees": [],
            "milestone": "Production Ready Phase 1"
        }
        self.issues.append(issue_4)

    def _add_medium_priority_issues(self):
        """添加Medium优先级Issues"""

        issue_5 = {
            "title": "📋 [P2-Medium] 数据库迁移验证和性能优化",
            "body": self._load_issue_template("production_ready_fix_5.md"),
            "labels": ["medium", "production-ready", "database", "performance", "P2"],
            "assignees": [],
            "milestone": "Production Ready Phase 2"
        }
        self.issues.append(issue_5)

    def _load_issue_template(self, template_name: str) -> str:
        """加载Issue模板内容"""
        template_path = os.path.join(
            self.repo_path,
            ".github/ISSUE_TEMPLATE",
            template_name
        )

        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 清理模板front matter
            if content.startswith('---'):
                end_index = content.find('---', 3)
                if end_index != -1:
                    content = content[end_index + 3:].strip()

            return content
        except FileNotFoundError:
            return f"## Issue模板未找到: {template_name}\n\n请手动创建Issue内容。"

    def create_github_issues(self):
        """使用gh命令行工具创建GitHub Issues"""
        print("🚀 开始创建生产就绪优化GitHub Issues...")

        for i, issue in enumerate(self.issues, 1):
            print(f"\n📝 创建 Issue {i}/{len(self.issues)}: {issue['title']}")

            # 构建gh命令
            cmd = [
                "gh", "issue", "create",
                "--title", issue["title"],
                "--body", issue["body"],
                "--label", ",".join(issue["labels"])
            ]

            if issue["assignees"]:
                cmd.extend(["--assignee", ",".join(issue["assignees"])])

            if issue.get("milestone"):
                cmd.extend(["--milestone", issue["milestone"]])

            try:
                # 执行命令
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                issue_url = result.stdout.strip()
                print(f"✅ Issue创建成功: {issue_url}")

                # 记录创建的Issue URL
                issue["url"] = issue_url

            except subprocess.CalledProcessError as e:
                print(f"❌ Issue创建失败: {e}")
                print(f"错误输出: {e.stderr}")
                issue["url"] = None
            except FileNotFoundError:
                print("⚠️ GitHub CLI (gh) 未安装，请手动创建Issues")
                self._print_manual_creation_instructions()
                break

        self._print_summary()

    def _print_manual_creation_instructions(self):
        """打印手动创建Issue的说明"""
        print("\n" + "="*60)
        print("🔧 手动创建GitHub Issues说明")
        print("="*60)
        print("\n由于GitHub CLI (gh) 未安装，请手动创建以下Issues:\n")

        for i, issue in enumerate(self.issues, 1):
            print(f"Issue {i}: {issue['title']}")
            print(f"Labels: {', '.join(issue['labels'])}")
            print(f"Body: 见 .github/ISSUE_TEMPLATE/ 目录中的模板文件")
            print("-" * 40)

    def _print_summary(self):
        """打印创建总结"""
        print("\n" + "="*60)
        print("📊 GitHub Issues创建总结")
        print("="*60)

        created_count = sum(1 for issue in self.issues if issue.get("url"))
        total_count = len(self.issues)

        print(f"总Issues数: {total_count}")
        print(f"成功创建: {created_count}")
        print(f"创建失败: {total_count - created_count}")

        print("\n📅 优化时间线:")
        print("Phase 1 (24小时内): Critical Issues修复")
        print("Phase 2 (3天内): 生产就绪优化")
        print("Phase 3 (6天内): 企业级完善")

        print("\n📋 详细路线图: docs/PRODUCTION_READY_ROADMAP.md")
        print("🎯 开始优化: 从Issue #1 (修复语法错误) 开始")

def main():
    """主函数"""
    print("🚀 足球预测系统生产就绪优化")
    print("=" * 50)

    # 检查是否在正确的目录
    if not os.path.exists(".github"):
        print("❌ 错误: 请在项目根目录运行此脚本")
        return 1

    # 创建Issue创建器
    creator = IssueCreator()

    # 生成Issues
    issues = creator.create_issues()
    print(f"📝 准备创建 {len(issues)} 个生产就绪优化Issues")

    # 创建GitHub Issues
    creator.create_github_issues()

    return 0

if __name__ == "__main__":
    exit(main())