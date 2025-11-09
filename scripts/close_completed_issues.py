#!/usr/bin/env python3
"""
关闭已标记为完成的GitHub Issues
根据Issue #827的分析结果关闭9个已完成但仍开放的Issues
"""

import json
import subprocess
from typing import List, Dict

class CompletedIssuesCleaner:
    def __init__(self, repo: str):
        self.repo = repo
        self.issues_to_close = []
        self.closed_count = 0

    def identify_completed_issues(self) -> List[Dict]:
        """识别应关闭的已完成Issues"""
        # 基于之前分析的结果，这些Issue应该关闭
        completed_issues = [
            {"number": 826, "title": "✅ Phase 9.0: 代码质量和系统稳定化完成", "reason": "已标记为完成"},
            {"number": 825, "title": "✅ Phase 8.0: 代码质量优化和GitHub Issues清理完成", "reason": "已标记为完成"},
            {"number": 824, "title": "Phase 8.1: API文档完善启动", "reason": "Phase 8.0已完成，此Issue过时"},
            {"number": 822, "title": "Phase 4B.4: 验证30%覆盖率目标达成", "reason": "有重复更新的Issue"},
            {"number": 821, "title": "Phase 4B: 测试覆盖率扩展 - 25%→30%+目标", "reason": "有重复更新的Issue"},
            {"number": 820, "title": "✅ Phase 7.0: 架构文档更新完成 - 系统设计和技术决策记录", "reason": "已标记为完成"}
        ]

        # 验证这些Issue确实存在且是开放状态
        valid_issues = []
        for issue in completed_issues:
            if self._is_issue_open(issue["number"]):
                valid_issues.append(issue)
                print(f"📋 找到需要关闭的Issue: #{issue['number']} - {issue['title']}")
            else:
                print(f"⚠️ Issue #{issue['number']} 已经关闭或不存在")

        self.issues_to_close = valid_issues
        return valid_issues

    def _is_issue_open(self, issue_number: int) -> bool:
        """检查Issue是否处于开放状态"""
        try:
            result = subprocess.run([
                "gh", "issue", "view", str(issue_number),
                f"--repo={self.repo}",
                "--json", "state", "title"
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                issue_data = json.loads(result.stdout)
                return issue_data.get("state") == "OPEN"
            return False

        except Exception as e:
            print(f"检查Issue #{issue_number}状态时出错: {e}")
            return False

    def close_issue_with_comment(self, issue_number: int, reason: str) -> bool:
        """关闭Issue并添加评论"""
        try:
            # 添加关闭评论
            comment = f"""🔧 自动化清理操作

此Issue正在被自动关闭，原因：{reason}

相关信息：
- 此操作是Phase 11.0渐进式稳定化的一部分
- 详情请参见: #827
- 关闭时间: {subprocess.run(['date'], capture_output=True, text=True).stdout.strip()}

如需重新开放，请评论说明原因。"""

            # 添加评论
            subprocess.run([
                "gh", "issue", "comment", str(issue_number),
                f"--repo={self.repo}",
                "--body", comment
            ], capture_output=True, text=True, timeout=10)

            # 关闭Issue
            subprocess.run([
                "gh", "issue", "close", str(issue_number),
                f"--repo={self.repo}"
            ], capture_output=True, text=True, timeout=10)

            print(f"✅ 已关闭Issue #{issue_number}")
            self.closed_count += 1
            return True

        except Exception as e:
            print(f"❌ 关闭Issue #{issue_number}失败: {e}")
            return False

    def batch_close_completed_issues(self) -> Dict[str, int]:
        """批量关闭已完成的Issues"""
        print("🧹 开始清理已标记为完成的Issues")
        print("=" * 50)

        # 识别需要关闭的Issues
        issues = self.identify_completed_issues()

        if not issues:
            print("📊 没有找到需要关闭的已完成Issues")
            return {"total": 0, "closed": 0, "failed": 0}

        print(f"\n📋 找到 {len(issues)} 个需要关闭的Issues")

        # 批量关闭
        closed_count = 0
        failed_count = 0

        for issue in issues:
            print(f"\n🔄 处理Issue #{issue['number']}: {issue['title']}")
            success = self.close_issue_with_comment(issue['number'], issue['reason'])
            if success:
                closed_count += 1
            else:
                failed_count += 1

        result = {
            "total": len(issues),
            "closed": closed_count,
            "failed": failed_count
        }

        print(f"\n📊 清理结果:")
        print(f"  总数: {result['total']}")
        print(f"  ✅ 成功关闭: {result['closed']}")
        print(f"  ❌ 失败: {result['failed']}")

        return result

def main():
    """主函数"""
    print("🧹 GitHub Issues清理工具 - 已完成Issues清理")
    print("=" * 60)

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

    # 创建清理器并执行清理
    cleaner = CompletedIssuesCleaner(repo)
    result = cleaner.batch_close_completed_issues()

    print(f"\n🎉 清理完成!")
    if result['closed'] > 0:
        print(f"✅ 成功清理了 {result['closed']} 个已完成Issues")
    print(f"📋 建议下一步: 继续语法错误修复到200个以下")

if __name__ == "__main__":
    main()