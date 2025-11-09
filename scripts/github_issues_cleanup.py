#!/usr/bin/env python3
"""
GitHub Issues 清理工具
清理重复和过时的Issues，优化项目管理
"""

import json
import subprocess
from typing import Dict, List, Any

class GitHubIssuesCleaner:
    def __init__(self, repo: str):
        self.repo = repo
        self.issues = []
        self.cleaned_count = 0

    def load_issues(self) -> List[Dict[str, Any]]:
        """加载所有Issues"""
        try:
            result = subprocess.run([
                "gh", "issue", "list",
                f"--repo={self.repo}",
                "--limit=50",
                "--state=all",
                "--json", "number,title,state,labels,body,createdAt,updatedAt"
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                self.issues = json.loads(result.stdout)
                print(f"📋 加载了 {len(self.issues)} 个Issues")
                return self.issues
            else:
                print(f"❌ 加载Issues失败: {result.stderr}")
                return []

        except Exception as e:
            print(f"❌ 加载Issues时出错: {e}")
            return []

    def find_duplicate_issues(self) -> Dict[str, List[Dict[str, Any]]]:
        """查找重复的Issues"""
        duplicates = {}

        for issue in self.issues:
            title = issue['title'].lower()

            # 查找相似标题的Issues
            for key in duplicates:
                # 简单的相似性检查
                if self._are_titles_similar(title, key):
                    duplicates[key].append(issue)
                    break
            else:
                # 如果没有找到相似的，创建新组
                duplicates[title] = [issue]

        # 只保留有重复的组
        return {k: v for k, v in duplicates.items() if len(v) > 1}

    def _are_titles_similar(self, title1: str, title2: str) -> bool:
        """检查两个标题是否相似"""
        # 提取关键词进行比较
        keywords1 = set(title1.split())
        keywords2 = set(title2.split())

        # 如果关键词重叠度高，认为是相似
        if not keywords1 or not keywords2:
            return False

        intersection = keywords1.intersection(keywords2)
        union = keywords1.union(keywords2)

        similarity = len(intersection) / len(union)
        return similarity > 0.6  # 60%相似度阈值

    def find_stale_issues(self, days: int = 30) -> List[Dict[str, Any]]:
        """查找过时的Issues"""
        from datetime import datetime, timedelta, timezone

        stale_issues = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        for issue in self.issues:
            # 处理不同的时间格式
            updated_str = issue['updatedAt']
            if updated_str.endswith('Z'):
                updated_at = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
            else:
                updated_at = datetime.fromisoformat(updated_str)

            if updated_at < cutoff_date and issue['state'] == 'OPEN':
                stale_issues.append(issue)

        return stale_issues

    def find_completed_issues_to_close(self) -> List[Dict[str, Any]]:
        """查找应该关闭的已完成Issues"""
        completed_to_close = []

        for issue in self.issues:
            if issue['state'] == 'OPEN':
                title = issue['title']

                # 检查是否标记为已完成
                if any(label['name'] == 'status/completed' for label in issue['labels']):
                    completed_to_close.append(issue)

                # 检查标题是否表明已完成
                if title.startswith('✅ ') or '完成' in title or 'completed' in title.lower():
                    completed_to_close.append(issue)

        return completed_to_close

    def generate_cleanup_report(self) -> Dict[str, Any]:
        """生成清理报告"""
        duplicates = self.find_duplicate_issues()
        stale_issues = self.find_stale_issues(30)
        completed_to_close = self.find_completed_issues_to_close()

        report = {
            "total_issues": len(self.issues),
            "duplicate_groups": len(duplicates),
            "total_duplicates": sum(len(group) for group in duplicates.values()),
            "stale_issues": len(stale_issues),
            "completed_to_close": len(completed_to_close),
            "duplicate_details": duplicates,
            "stale_details": stale_issues,
            "completed_details": completed_to_close
        }

        return report

    def print_cleanup_report(self):
        """打印清理报告"""
        report = self.generate_cleanup_report()

        print("📊 GitHub Issues 清理报告")
        print("=" * 50)
        print(f"📋 总Issues数: {report['total_issues']}")
        print(f"🔄 重复Issues组: {report['duplicate_groups']}")
        print(f"📊 重复Issues总数: {report['total_duplicates']}")
        print(f"⏰ 过时Issues数 (30天): {report['stale_issues']}")
        print(f"✅ 应关闭的已完成Issues: {report['completed_to_close']}")

        print(f"\n🔄 重复Issues组详情:")
        for title, issues in report['duplicate_details'].items():
            print(f"  - {title}: {len(issues)} 个重复")
            for issue in issues:
                print(f"    #{issue['number']} ({issue['state']})")

        if report['completed_to_close'] > 0:
            print(f"\n✅ 应关闭的已完成Issues:")
            for issue in report['completed_details']:
                print(f"  - #{issue['number']}: {issue['title']}")

    def create_cleanup_suggestions(self) -> List[str]:
        """创建清理建议"""
        suggestions = []
        report = self.generate_cleanup_report()

        # 关于重复Issues的建议
        if report['duplicate_groups'] > 0:
            suggestions.append(f"🔄 合并 {report['duplicate_groups']} 组重复Issues，保留最新的")

        # 关于已完成Issues的建议
        if report['completed_to_close'] > 0:
            suggestions.append(f"✅ 关闭 {report['completed_to_close']} 个已标记为完成的Issues")

        # 关于过时Issues的建议
        if report['stale_issues'] > 0:
            suggestions.append(f"⏰ 审查 {report['stale_issues']} 个30天未更新的过时Issues")

        return suggestions

def main():
    """主函数"""
    print("🧹 GitHub Issues 清理工具")
    print("=" * 50)

    # 获取仓库信息
    try:
        result = subprocess.run([
            "gh", "repo", "view", "--json", "name,owner"
        ], capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            repo_info = json.loads(result.stdout)
            repo = f"{repo_info['owner']['login']}/{repo_info['name']}"
            print(f"📂 仓库: {repo}")
        else:
            print("❌ 无法获取仓库信息")
            return
    except Exception as e:
        print(f"❌ 获取仓库信息失败: {e}")
        return

    # 创建清理器
    cleaner = GitHubIssuesCleaner(repo)

    # 加载Issues
    issues = cleaner.load_issues()
    if not issues:
        return

    # 生成并打印报告
    cleaner.print_cleanup_report()

    # 打印清理建议
    suggestions = cleaner.create_cleanup_suggestions()
    if suggestions:
        print(f"\n💡 清理建议:")
        for suggestion in suggestions:
            print(f"  {suggestion}")

    print(f"\n🎯 下一步操作建议:")
    print(f"  1. 手动审查重复Issues，合并或关闭重复项")
    print(f"  2. 关闭已标记为完成的Issues")
    print(f"  3. 审查过时Issues，更新或关闭")
    print(f"  4. 创建新的Issue跟踪当前状态")

if __name__ == "__main__":
    main()