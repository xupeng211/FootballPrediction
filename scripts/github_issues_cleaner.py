#!/usr/bin/env python3
"""GitHub Issues定期清理工具"""

import json
import subprocess
from datetime import datetime, timedelta


class GitHubIssuesCleaner:
    def __init__(self, repo_path=None):
        self.repo_path = repo_path or "xupeng211/FootballPrediction"
        self.cleanup_actions = []

    def get_open_issues(self) -> list[dict]:
        """获取所有开放Issues"""
        try:
            result = subprocess.run(
                ['gh', 'issue', 'list', '--repo', self.repo_path,
                 '--state', 'open', '--limit', '100', '--json', 'number,title,labels,createdAt,state,author'],
                capture_output=True, text=True
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return []
        except Exception:
            return []

    def detect_duplicate_issues(self, issues: list[dict]) -> list[tuple[dict, dict]]:
        """检测重复Issues"""
        duplicates = []

        for i, issue1 in enumerate(issues):
            for issue2 in issues[i+1:]:
                # 简单的重复检测逻辑
                similarity = self.calculate_similarity(issue1['title'], issue2['title'])
                if similarity > 0.8:  # 80%相似度阈值
                    duplicates.append((issue1, issue2))

        return duplicates

    def calculate_similarity(self, str1: str, str2: str) -> float:
        """计算字符串相似度"""
        # 简单的相似度计算
        words1 = set(str1.lower().split())
        words2 = set(str2.lower().split())

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0

    def detect_stale_issues(self, issues: list[dict], days_threshold=30) -> list[dict]:
        """检测过期Issues"""
        stale_issues = []
        cutoff_date = datetime.now() - timedelta(days=days_threshold)

        for issue in issues:
            created_at = datetime.fromisoformat(issue['createdAt'].replace('Z', '+00:00')).replace(tzinfo=None)
            if created_at < cutoff_date:
                # 检查是否有最近的活动
                if not self.has_recent_activity(issue['number']):
                    stale_issues.append(issue)

        return stale_issues

    def has_recent_activity(self, issue_number: int, days_threshold=7) -> bool:
        """检查Issue是否有最近活动"""
        try:
            result = subprocess.run(
                ['gh', 'issue', 'view', str(issue_number), '--repo', self.repo_path,
                 '--json', 'comments', '--jq', '.comments | map(select(.createdAt > now - 30d)) | length'],
                capture_output=True, text=True
            )

            if result.returncode == 0:
                recent_comments = int(result.stdout.strip())
                return recent_comments > 0
        except Exception:
            pass

        return False

    def detect_completed_issues(self, issues: list[dict]) -> list[dict]:
        """检测已完成但未关闭的Issues"""
        completed_keywords = [
            '完成', 'finished', 'completed', 'done', '✅',
            '解决', 'resolved', 'fixed', '修复', '成功'
        ]

        completed_issues = []

        for issue in issues:
            # 检查标题中是否包含完成关键词
            title_lower = issue['title'].lower()
            if any(keyword in title_lower for keyword in completed_keywords):
                # 进一步验证是否真的完成
                if self.verify_issue_completion(issue):
                    completed_issues.append(issue)

        return completed_issues

    def verify_issue_completion(self, issue: dict) -> bool:
        """验证Issue是否真的完成"""
        # 检查标签
        labels = [label['name'] for label in issue['labels']]
        if 'status/completed' in labels:
            return True

        # 检查是否有完成相关的评论
        try:
            result = subprocess.run(
                ['gh', 'issue', 'view', str(issue['number']), '--repo', self.repo_path,
                 '--json', 'comments', '--jq', '.comments[-1].body'],
                capture_output=True, text=True
            )

            if result.returncode == 0:
                last_comment = result.stdout.strip().lower()
                completion_indicators = ['完成', 'finished', 'completed', 'done', '✅']
                return any(indicator in last_comment for indicator in completion_indicators)
        except Exception:
            pass

        return False

    def generate_cleanup_plan(self, issues: list[dict]) -> dict:
        """生成清理计划"""
        duplicates = self.detect_duplicate_issues(issues)
        stale_issues = self.detect_stale_issues(issues)
        completed_issues = self.detect_completed_issues(issues)

        plan = {
            'duplicates': duplicates,
            'stale_issues': stale_issues,
            'completed_issues': completed_issues,
            'total_actions': len(duplicates) + len(stale_issues) + len(completed_issues)
        }

        return plan

    def execute_cleanup_action(self, action_type: str, issue: dict, reason: str = "") -> bool:
        """执行清理操作"""
        try:
            if action_type == 'close_completed':
                comment = f"🤖 自动关闭: 此Issue已完成但未关闭。\n{reason}"
                subprocess.run([
                    'gh', 'issue', 'close', str(issue['number']),
                    '--repo', self.repo_path, '--comment', comment
                ], check=True)

            elif action_type == 'mark_stale':
                subprocess.run([
                    'gh', 'issue', 'edit', str(issue['number']),
                    '--repo', self.repo_path, '--add-label', 'stale'
                ], check=True)

            elif action_type == 'request_merge_duplicate':
                # 对于重复Issues，添加评论请求合并
                comment = f"🤖 检测到可能重复的Issue，请考虑是否需要合并或关闭其中一个。\n{reason}"
                subprocess.run([
                    'gh', 'issue', 'comment', str(issue['number']),
                    '--repo', self.repo_path, '--body', comment
                ], check=True)

            return True
        except subprocess.CalledProcessError:
            return False

    def run_cleanup(self, dry_run=True) -> dict:
        """执行清理流程"""
        issues = self.get_open_issues()


        plan = self.generate_cleanup_plan(issues)


        if dry_run:
            return plan

        # 执行清理操作
        executed = 0
        failed = 0

        # 关闭已完成的Issues
        for issue in plan['completed_issues']:
            if self.execute_cleanup_action('close_completed', issue):
                executed += 1
            else:
                failed += 1

        # 标记过期Issues
        for issue in plan['stale_issues']:
            if self.execute_cleanup_action('mark_stale', issue):
                executed += 1
            else:
                failed += 1

        # 处理重复Issues
        for issue1, issue2 in plan['duplicates']:
            reason = f"可能与Issue #{issue2['number']}重复: {issue2['title']}"
            if self.execute_cleanup_action('request_merge_duplicate', issue1, reason):
                executed += 1
            else:
                failed += 1

        result = {
            'plan': plan,
            'executed': executed,
            'failed': failed,
            'total_issues': len(issues)
        }


        return result

if __name__ == '__main__':
    import sys

    dry_run = '--dry-run' in sys.argv
    cleaner = GitHubIssuesCleaner()
    result = cleaner.run_cleanup(dry_run=dry_run)

    # 保存报告
    report = {
        'timestamp': datetime.now().isoformat(),
        'dry_run': dry_run,
        'result': result
    }

    with open('github_issues_cleanup_report.json', 'w') as f:
        json.dump(report, f, indent=2)


    if not dry_run:
        pass
