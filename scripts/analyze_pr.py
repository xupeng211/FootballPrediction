#!/usr/bin/env python3
"""
PR Analysis Script
Pull Request分析和审查脚本
"""

import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Any, Optional

class PRAnalyzer:
    def __init__(self, pr_number: int, repo: str, token: str):
        self.pr_number = pr_number
        self.repo = repo
        self.token = token
        self.base_url = "https://api.github.com"

    def get_pr_details(self) -> Dict[str, Any]:
        """获取PR详情"""
        import requests

        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

        url = f"{self.base_url}/repos/{self.repo}/pulls/{self.pr_number}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.json()

    def get_pr_files(self) -> List[Dict[str, Any]]:
        """获取PR文件列表"""
        import requests

        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

        url = f"{self.base_url}/repos/{self.repo}/pulls/{self.pr_number}/files"
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.json()

    def analyze_code_complexity(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析代码复杂度"""
        complexity_score = 0
        risk_level = "Low"
        suggestions = []

        file_types = {}
        total_lines_added = 0
        total_lines_deleted = 0

        for file in files:
            filename = file['filename']
            additions = file.get('additions', 0)
            deletions = file.get('deletions', 0)
            changes = file.get('changes', 0)

            # 统计文件类型
            ext = os.path.splitext(filename)[1].lower()
            file_types[ext] = file_types.get(ext, 0) + 1

            total_lines_added += additions
            total_lines_deleted += deletions

            # 分析单个文件的复杂度
            if ext in ['.py']:
                # Python文件特殊处理
                if additions > 100:
                    complexity_score += 2
                    suggestions.append(f"Large Python file changed: {filename} ({additions} lines added)")
                elif additions > 50:
                    complexity_score += 1

                # 检查是否涉及复杂逻辑
                if filename.endswith('.py'):
                    try:
                        # 尝试分析Python文件的复杂性指标
                        self._analyze_python_file(filename, complexity_score, suggestions)
                        pass

            # 检查配置文件变更
            if ext in ['.yml', '.yaml', '.json']:
                if changes > 50:
                    complexity_score += 1
                    suggestions.append(f"Large configuration change: {filename}")

            # 检查文档变更
            if ext in ['.md', '.rst']:
                if additions > 200:
                    suggestions.append(f"Large documentation update: {filename}")

        # 计算风险级别
        if total_lines_added > 500:
            risk_level = "High"
        elif total_lines_added > 200:
            risk_level = "Medium"

        # 特殊文件类型风险
        high_risk_files = ['.sql', 'migrations/', 'requirements.txt', 'Dockerfile']
        for file in files:
            if any(risk_file in file['filename'] for risk_file in high_risk_files):
                if risk_level == "Low":
                    risk_level = "Medium"
                complexity_score += 1

        return {
            "score": min(10, complexity_score),
            "risk": risk_level,
            "suggestions": suggestions,
            "file_types": file_types,
            "lines_added": total_lines_added,
            "lines_deleted": total_lines_deleted
        }

    def _analyze_python_file(self, filename: str, current_score: int, suggestions: List[str]):
        """分析Python文件的复杂度"""
        try:
            # 尝试分析文件内容
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查复杂的代码模式
            patterns = {
                r'class\s+\w+.*\n.*def\s+__init__': "Complex class definition",
                r'def\s+\w+.*\(.*\*.*\).*:': "Function with variable arguments",
                r'@.*\n.*def\s+\w+': "Decorated function",
                r'async\s+def\s+\w+': "Async function",
                r'try:\s*\n.*except.*:\s*\n.*finally:': "Complex exception handling",
                r'for.*in.*:\s*\n.*for.*in.*:': "Nested loops",
                r'if.*:\s*\n.*if.*:\s*\n.*if.*:': "Deeply nested conditions"
            }

            for pattern, description in patterns.items():
                matches = len(re.findall(pattern, content))
                if matches > 0:
                    suggestions.append(f"{description} in {filename} ({matches} occurrences)")

            # 检查代码长度
            lines = content.split('\n')
            if len(lines) > 200:
                suggestions.append(f"Very long file: {filename} ({len(lines)} lines)")

        except Exception as e:
            print(f"Warning: Could not analyze {filename}: {e}")

    def check_for_common_issues(self, files: List[Dict[str, Any]]) -> List[str]:
        """检查常见问题"""
        issues = []

        # 检查是否有测试文件
        has_tests = any('test_' in f['filename'] or '/tests/' in f['filename'] for f in files)
        if not has_tests:
            issues.append("No test files included in this PR")

        # 检查是否有文档更新
        has_docs = any(f['filename'].endswith('.md') for f in files)
        if not has_docs:
            issues.append("Consider updating documentation for new features")

        # 检查是否有配置文件变更
        has_config = any(f['filename'].endswith(('.yml', '.yaml', '.ini', '.toml')) for f in files)
        if has_config:
            issues.append("Configuration files changed - please verify changes")

        # 检查是否有数据库迁移
        has_migrations = any('migration' in f['filename'].lower() for f in files)
        if has_migrations:
            issues.append("Database migrations included - ensure backward compatibility")

        # 检查是否有依赖更新
        has_deps = any(f['filename'] in ['requirements.txt', 'pyproject.toml', 'Pipfile'] for f in files)
        if has_deps:
            issues.append("Dependencies updated - please test compatibility")

        return issues

    def generate_review_summary(self, pr_details: Dict[str, Any], files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成审查摘要"""
        complexity = self.analyze_code_complexity(files)
        issues = self.check_for_common_issues(files)

        return {
            "pr_number": self.pr_number,
            "title": pr_details.get('title', ''),
            "author": pr_details.get('user', {}).get('login', ''),
            "description": pr_details.get('body', '')[:200] + '...' if len(pr_details.get('body', '')) > 200 else pr_details.get('body', ''),
            "files_count": len(files),
            "additions": pr_details.get('additions', 0),
            "deletions": pr_details.get('deletions', 0),
            "changed_files": pr_details.get('changed_files', 0),
            "complexity": complexity,
            "issues": issues,
            "mergeable": pr_details.get('mergeable', False),
            "draft": pr_details.get('draft', False)
        }

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='Analyze Pull Request')
    parser.add_argument('--pr-number', type=int, required=True, help='PR number')
    parser.add_argument('--repo', type=str, required=True, help='Repository name')
    parser.add_argument('--token', type=str, required=True, help='GitHub token')

    args = parser.parse_args()

    try:
        analyzer = PRAnalyzer(args.pr_number, args.repo, args.token)

        print(f"🔍 Analyzing PR #{args.pr_number} in {args.repo}...")

        # 获取PR详情
        pr_details = analyzer.get_pr_details()
        print(f"📋 Title: {pr_details.get('title', '')}")
        print(f"👤 Author: {pr_details.get('user', {}).get('login', '')}")
        print(f"📊 Changed files: {pr_details.get('changed_files', 0)}")

        # 获取文件列表
        files = analyzer.get_pr_files()
        print(f"📁 Files analyzed: {len(files)}")

        # 生成审查摘要
        summary = analyzer.generate_review_summary(pr_details, files)

        # 保存分析结果
        with open('pr_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        print("✅ Analysis completed. Results saved to pr_analysis.json")

        # 输出关键信息
        print(f"\n📊 Complexity Score: {summary['complexity']['score']}/10")
        print(f"⚠️  Risk Level: {summary['complexity']['risk']}")
        print(f"📝 Issues Found: {len(summary['issues'])}")

        if summary['issues']:
            print("\n🔍 Issues to address:")
            for issue in summary['issues']:
                print(f"  • {issue}")

        if summary['complexity']['suggestions']:
            print("\n💡 Suggestions:")
            for suggestion in summary['complexity']['suggestions'][:5]:
                print(f"  • {suggestion}")

    except Exception as e:
        print(f"❌ Error analyzing PR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()