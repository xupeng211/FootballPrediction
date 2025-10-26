#!/usr/bin/env python3
"""
GitHub Issue 重复检查和验证工具
用于防止创建重复Issue和验证标题格式
"""

import re
import sys
import subprocess
from typing import List, Dict, Any

class IssueValidator:
    def __init__(self):
        self.gh_cli = "gh"

    def run_gh_command(self, args: List[str]) -> List[Dict[str, Any]]:
        """运行GitHub CLI命令"""
        try:
            result = subprocess.run(
                [self.gh_cli] + args,
                capture_output=True,
                text=True,
                check=True
            )

            if result.returncode != 0:
                return []

            # 解析输出为结构化数据
            lines = result.stdout.strip().split('\n')
            issues = []

            for line in lines:
                if line.strip():
                    # 解析 Issue 行格式
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        issue = {
                            'number': parts[0].strip(),
                            'title': parts[1].strip(),
                            'state': parts[2].strip(),
                            'author': parts[3].strip() if len(parts) > 3 else 'unknown'
                        }
                        issues.append(issue)

            return issues
        except Exception as e:
            print(f"❌ 运行gh命令失败: {e}")
            return []

    def check_duplicates(self, search_term: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """检查重复Issue"""
        issues = self.run_gh_command(['issue', 'list', '--search', search_term, '--limit', str(max_results)])
        return issues

    def validate_title(self, title: str) -> Dict[str, Any]:
        """验证Issue标题格式"""
        issues = []

        # 检查标准Phase X.Y格式
        phase_pattern = r'^Phase\s+[0-9]+\.[0-9]+:\s*.+$'

        try:
            phase_match = bool(re.match(phase_pattern, title))
        except re.error:
            phase_match = False

        issues.append({
            'check': 'format',
            'valid': phase_match,
            'message': 'Issue标题格式检查'
        })

        # 检查长度
        if len(title) > 100:
            issues.append({
                'check': 'length',
                'valid': False,
                'message': 'Issue标题过长 (建议100字符以内)'
            })

        # 检查特殊字符
        special_chars_pattern = r'[<>{}[\]|\\|&]'
        if re.search(special_chars_pattern, title):
            issues.append({
                'check': 'special_chars',
                'valid': False,
                'message': 'Issue标题包含特殊字符 (<>{}[]\\&)'
            })

        # 检查引用 (不应该有 #82)
        if '#' in title and re.search(r'#\d+', title):
            issues.append({
                'check': 'reference',
                'valid': False,
                'message': 'Issue标题包含其他Issue引用 (如 #82)'
            })

        # 检查末尾格式
        if title.endswith(' ') or title.endswith('\t') or title.endswith('\n'):
            issues.append({
                'check': 'format',
                'valid': False,
                'message': 'Issue标题末尾格式不正确'
            })

        return issues

    def suggest_phase_number(self, search_term: str) -> str:
        """建议下一个Phase编号"""
        issues = self.run_gh_command(['issue', 'list', '--search', search_term])

        phase_numbers = []
        for issue in issues:
            title = issue['title']
            # 提取Phase编号
            match = re.search(r'Phase\s+([0-9]+)\.[0-9]+', title)
            if match:
                phase_numbers.append(int(match.group(1)))

        if not phase_numbers:
            return "4A.1"

        # 找到最大编号并加1
        max_phase = max(phase_numbers)
        next_phase = max_phase + 1
        next_week = 1

        return f"{max_phase}.{next_week}"

    def full_validation(self, title: str, search_term: str) -> Dict[str, Any]:
        """完整验证"""
        print("🔍 开始验证Issue...")
        print(f"   标题: {title}")
        print(f"   搜索: {search_term}")

        # 检查重复
        duplicates = self.check_duplicates(search_term)
        if len(duplicates) > 1:
            print(f"❌ 发现 {len(duplicates)} 个重复Issue:")
            for dup in duplicates[:3]:  # 只显示前3个
                print(f"   - #{dup['number']}: {dup['title']}")

            return {
                'valid': False,
                'issues': duplicates,
                'message': '发现重复Issue，建议先关闭重复或使用不同标题'
            }

        # 验证标题
        validation_issues = self.validate_title(title)
        invalid_issues = [issue for issue in validation_issues if not issue['valid']]

        if invalid_issues:
            print("❌ Issue标题验证失败:")
            for issue in invalid_issues:
                print(f"   - {issue['check']}: {issue['message']}")

            return {
                'valid': False,
                'validation_issues': validation_issues,
                'message': 'Issue标题不符合规范'
            }

        # 建议Phase编号
        suggested_phase = self.suggest_phase_number(search_term)
        print(f"💡 建议Phase编号: {suggested_phase}")

        print("✅ 验证通过")
        return {
            'valid': True,
            'title': title,
            'suggested_phase': suggested_phase
        }


def main():
    if len(sys.argv) < 3:
        print("GitHub Issue 重复检查和验证工具")
        print("\n使用方法:")
        print("  python check_issue_duplicates.py <command> <title>")
        print("  python check_issue.py full \"Phase 4A.2: 服务层深度测试\"")
        print("  python check_issue.py suggest \"Phase 4A\"")
        print("\n命令说明:")
        print("  full - 完整验证(检查重复+标题格式)")
        print("  suggest - 建议Phase编号")
        sys.exit(1)

    command = sys.argv[1]
    title = sys.argv[2]

    if command == "full":
        search_term = title.split(':')[0] if ':' in title else title
        validator = IssueValidator()
        result = validator.full_validation(title, search_term)

        if not result['valid']:
            sys.exit(1)

        print(f"\n✅ Issue验证通过，可以创建: {result['title']}")
        print(f"💡 建议Phase编号: {result['suggested_phase']}")

    elif command == "suggest":
        validator = IssueValidator()
        suggested = validator.suggest_phase_number(title)
        print(f"\n💡 搜索 '{title}' 的建议Phase编号: {suggested}")

    else:
        print(f"❌ 未知命令: {command}")


if __name__ == "__main__":
    main()