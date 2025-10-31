#!/usr/bin/env python3
"""
Weekly Collaboration Report Generator
团队协作周报生成器
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

class WeeklyCollaborationReportGenerator:
    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.repo = os.getenv('GITHUB_REPOSITORY', 'xupeng211/FootballPrediction')
        self.base_url = "https://api.github.com"

    def get_week_data(self) -> Dict[str, Any]:
        """获取一周的数据"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        print(f"📊 Generating report for period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

        return {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'commits': self.get_commit_stats(start_date, end_date),
            'prs': self.get_pr_stats(start_date, end_date),
            'issues': self.get_issue_stats(start_date, end_date),
            'contributors': self.get_contributor_stats(start_date, end_date)
        }

    def get_commit_stats(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """获取提交统计"""
        try:
            since = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            until = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')

            cmd = [
                'git', 'log',
                f'--since={since}',
                f'--until={until}',
                '--pretty=format:%H|%an|%ad|%s',
                '--date=short',
                '--numstat'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            commits = []
            lines_added = 0
            lines_deleted = 0
            authors = set()
            commit_days = set()

            current_commit = None
            for line in result.stdout.split('\n'):
                if '|' in line and len(line.split('|')) == 4:
                    parts = line.split('|')
                    current_commit = {
                        'hash': parts[0],
                        'author': parts[1],
                        'date': parts[2],
                        'message': parts[3],
                        'files_changed': 0,
                        'lines_added': 0,
                        'lines_deleted': 0
                    }
                    commits.append(current_commit)
                    authors.add(parts[1])
                    commit_days.add(parts[2])
                elif current_commit and '\t' in line:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        added = int(parts[0]) if parts[0] != '-' else 0
                        deleted = int(parts[1]) if parts[1] != '-' else 0
                        current_commit['lines_added'] += added
                        current_commit['lines_deleted'] += deleted
                        current_commit['files_changed'] += 1
                        lines_added += added
                        lines_deleted += deleted

            return {
                'total_commits': len(commits),
                'lines_added': lines_added,
                'lines_deleted': lines_deleted,
                'unique_authors': len(authors),
                'active_days': len(commit_days),
                'commits_per_day': len(commits) / max(len(commit_days), 1),
                'authors': list(authors),
                'commits': commits
            }

        except subprocess.CalledProcessError as e:
            print(f"❌ Error getting commit stats: {e}")
            return {'total_commits': 0, 'lines_added': 0, 'lines_deleted': 0, 'unique_authors': 0, 'active_days': 0}

    def get_pr_stats(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """获取PR统计"""
        try:
            import requests

            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }

            # 获取已关闭的PR
            closed_url = f"{self.base_url}/repos/{self.repo}/pulls?state=closed&sort=updated&direction=desc&per_page=100"
            closed_response = requests.get(closed_url, headers=headers)
            closed_response.raise_for_status()

            # 获取开放的PR
            open_url = f"{self.base_url}/repos/{self.repo}/pulls?state=open&sort=updated&direction=desc&per_page=100"
            open_response = requests.get(open_url, headers=headers)
            open_response.raise_for_status()

            all_prs = closed_response.json() + open_response.json()

            closed_this_week = []
            opened_this_week = []
            merged_this_week = []
            open_prs = []

            for pr in all_prs:
                pr_date = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00')).date()
                closed_date = datetime.fromisoformat(pr['closed_at'].replace('Z', '+00:00')).date() if pr['closed_at'] else None

                # 检查是否在本周范围内
                if start_date.date() <= pr_date <= end_date.date():
                    opened_this_week.append(pr)
                    if not pr.get('merged_at'):
                        open_prs.append(pr)

                if closed_date and start_date.date() <= closed_date <= end_date.date():
                    closed_this_week.append(pr)
                    if pr.get('merged_at'):
                        merged_this_week.append(pr)

            return {
                'opened': len(opened_this_week),
                'closed': len(closed_this_week),
                'merged': len(merged_this_week),
                'open': len(open_prs),
                'merge_rate': (len(merged_this_week) / max(len(closed_this_week), 1)) * 100,
                'opened_this_week': opened_this_week,
                'closed_this_week': closed_this_week,
                'open_prs': open_prs
            }

        except Exception as e:
            print(f"❌ Error getting PR stats: {e}")
            return {'opened': 0, 'closed': 0, 'merged': 0, 'open': 0, 'merge_rate': 0}

    def get_issue_stats(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """获取Issue统计"""
        try:
            import requests

            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }

            # 获取Issues
            url = f"{self.base_url}/repos/{self.repo}/issues?state=all&sort=updated&direction=desc&per_page=100"
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            issues = response.json()
            opened_this_week = []
            closed_this_week = []

            for issue in issues:
                # 跳过PR（PR也是issues类型）
                if 'pull_request' in issue:
                    continue

                created_date = datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00')).date()
                closed_date = datetime.fromisoformat(issue['closed_at'].replace('Z', '+00:00')).date() if issue['closed_at'] else None

                if start_date.date() <= created_date <= end_date.date():
                    opened_this_week.append(issue)

                if closed_date and start_date.date() <= closed_date <= end_date.date():
                    closed_this_week.append(issue)

            return {
                'opened': len(opened_this_week),
                'closed': len(closed_this_week),
                'open': len([i for i in issues if i['state'] == 'open' and 'pull_request' not in i]),
                'opened_this_week': opened_this_week,
                'closed_this_week': closed_this_week
            }

        except Exception as e:
            print(f"❌ Error getting issue stats: {e}")
            return {'opened': 0, 'closed': 0, 'open': 0}

    def get_contributor_stats(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """获取贡献者统计"""
        commit_stats = self.get_commit_stats(start_date, end_date)
        pr_stats = self.get_pr_stats(start_date, end_date)

        contributors = {}

        # 从提交统计中收集贡献者
        for author in commit_stats['authors']:
            contributors[author] = {
                'name': author,
                'commits': 0,
                'lines_added': 0,
                'lines_deleted': 0,
                'prs_opened': 0,
                'prs_merged': 0
            }

        # 统计每个贡献者的提交
        for commit in commit_stats['commits']:
            author = commit['author']
            if author in contributors:
                contributors[author]['commits'] += 1
                contributors[author]['lines_added'] += commit['lines_added']
                contributors[author]['lines_deleted'] += commit['lines_deleted']

        # 统计PR活动
        for pr in pr_stats['opened_this_week']:
            author = pr['user']['login']
            if author in contributors:
                contributors[author]['prs_opened'] += 1
            else:
                contributors[author] = {
                    'name': author,
                    'commits': 0,
                    'lines_added': 0,
                    'lines_deleted': 0,
                    'prs_opened': 1,
                    'prs_merged': 0
                }

        for pr in pr_stats['closed_this_week']:
            if pr.get('merged_at'):
                author = pr['user']['login']
                if author in contributors:
                    contributors[author]['prs_merged'] += 1
                elif author in contributors:
                    contributors[author]['prs_merged'] = 1

        return {
            'total_contributors': len(contributors),
            'contributors': contributors
        }

    def generate_report(self, data: Dict[str, Any]) -> str:
        """生成周报"""
        report = f"""# 📊 Weekly Collaboration Report

**Period**: {data['start_date']} to {data['end_date']}
**Repository**: {self.repo}
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📈 Summary

| Metric | Value | Week Trend |
|--------|-------|------------|
| Total Commits | {data['commits']['total_commits']} | {'📈 Growing' if data['commits']['total_commits'] > 0 else '📊 Stable'} |
| Active Contributors | {data['commits']['unique_authors']} | {'👥 Active' if data['commits']['unique_authors'] >= 2 else '👤 Limited'} |
| PRs Opened | {data['prs']['opened']} | {'📈 Active' if data['prs']['opened'] >= 2 else '📊 Normal'} |
| PRs Merged | {data['prs']['merged']} | {'🎉 Excellent' if data['prs']['merged'] >= data['prs']['opened'] * 0.8 else '📊 Review Needed'} |
| Issues Closed | {data['issues']['closed']} | {'🎉 Excellent' if data['issues']['closed'] >= 2 else '📊 Normal'} |
| Open Issues | {data['issues']['open']} | {'⚠️ Attention' if data['issues']['open'] > 10 else '✅ Healthy'} |

## 🔄 Activity Analysis

### Commit Activity
"""

        # 添加每日活动统计
        if data['commits']['commits']:
            daily_activity = {}
            for commit in data['commits']['commits']:
                date = commit['date']
                daily_activity[date] = daily_activity.get(date, 0) + 1

            report += "#### Daily Commit Distribution\n"
            for date, count in sorted(daily_activity.items()):
                report += f"- **{date}**: {count} commits\n"

        report += f"""
- **Total Lines Added**: {data['commits']['lines_added']:,}
- **Total Lines Deleted**: {data['commits']['lines_deleted']:,}
- **Net Change**: {data['commits']['lines_added'] - data['commits']['lines_deleted']:,} lines
- **Active Days**: {data['commits']['active_days']} days
- **Commits per Day**: {data['commits']['commits_per_day']:.1f}

### Pull Request Activity
"""

        # 添加PR详情
        if data['prs']['opened_this_week']:
            report += "#### PRs Opened This Week\n"
            for pr in data['prs']['opened_this_week']:
                report += f"- **#{pr['number']}**: {pr['title'][:60]}{'...' if len(pr['title']) > 60 else ''} by @{pr['user']['login']}\n"

        if data['prs']['closed_this_week']:
            report += "\n#### PRs Closed This Week\n"
            for pr in data['prs']['closed_this_week'][:5]:  # 只显示前5个
                status = "✅ Merged" if pr.get('merged_at') else "📝 Closed"
                report += f"- **#{pr['number']}**: {status} by @{pr['user']['login']}\n"

        report += f"""
- **Merge Rate**: {data['prs']['merge_rate']:.1f}%
- **Currently Open**: {data['prs']['open']} PRs

### Issue Activity
"""

        # 添加Issue详情
        if data['issues']['opened_this_week']:
            report += "#### Issues Opened This Week\n"
            for issue in data['issues']['opened_this_week'][:5]:  # 只显示前5个
                report += f"- **#{issue['number']}**: {issue['title'][:60]}{'...' if len(issue['title']) > 60 else ''} by @{issue['user']['login']}\n"

        report += f"""
- **Total Open Issues**: {data['issues']['open']}

## 👥 Contributor Spotlight

### Top Contributors This Week
"""

        # 按提交数排序贡献者
        sorted_contributors = sorted(
            data['contributors']['contributors'].items(),
            key=lambda x: (x[1]['commits'], x[1]['lines_added']),
            reverse=True
        )

        for i, (name, stats) in enumerate(sorted_contributors[:10]):
            report += f"""
{i+1}. **@{name}**
   - Commits: {stats['commits']}
   - Lines: +{stats['lines_added']:,}/-{stats['lines_deleted']:,}
   - PRs: {stats['prs_opened']} opened, {stats['prs_merged']} merged
"""

        report += f"""
## 🎯 Highlights & Achievements

### Key Accomplishments
"""

        # 生成亮点
        highlights = []

        if data['prs']['merged'] > 0:
            highlights.append(f"🎉 Successfully merged {data['prs']['merged']} pull request{'s' if data['prs']['merged'] > 1 else ''}")

        if data['commits']['total_commits'] > 10:
            highlights.append(f"🚀 High development activity with {data['commits']['total_commits']} commits")

        if data['commits']['unique_authors'] >= 3:
            highlights.append(f"👥 Strong team collaboration with {data['commits']['unique_authors']} active contributors")

        if data['issues']['closed'] > 0:
            highlights.append(f"✅ Resolved {data['issues']['closed']} issue{'s' if data['issues']['closed'] > 1 else ''}")

        if not highlights:
            highlights.append("📊 Steady development progress this week")

        for highlight in highlights:
            report += f"- {highlight}\n"

        report += f"""
## 📊 Trend Analysis

### Week-over-Week Comparison
- **Note**: Trend data will accumulate over the coming weeks
- **Current Focus**: {'High activity' if data['commits']['total_commits'] > 5 else 'Steady progress'}

## 🎯 Upcoming Week

### Priorities for Next Week
"""

        # 基于当前状态生成下周建议
        suggestions = []

        if data['prs']['open'] > 5:
            suggestions.append("📋 Review and merge pending PRs")

        if data['issues']['open'] > 10:
            suggestions.append("🔍 Address open issues and bug reports")

        if data['commits']['unique_authors'] < 2:
            suggestions.append("👥 Encourage more team members to contribute")

        if data['prs']['merge_rate'] < 70:
            suggestions.append("🔄 Improve PR review process and merge rate")

        if not suggestions:
            suggestions = [
                "🚀 Continue current development momentum",
                "📈 Focus on quality and testing",
                "👥 Engage with community feedback"
            ]

        for suggestion in suggestions:
            report += f"- {suggestion}\n"

        report += f"""
## 📝 Notes

- This report is automatically generated every Monday morning
- All data is pulled from GitHub API
- For questions or suggestions, please create an issue

---

*Generated by Automated Collaboration System on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Repository: {self.repo}*
"""

        return report

    def save_report(self, content: str) -> str:
        """保存报告"""
        filename = f"weekly_collaboration_report_{datetime.now().strftime('%Y%m%d')}.md"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ Report saved to: {filename}")
        return filename

def main():
    """主函数"""
    generator = WeeklyCollaborationReportGenerator()

    try:
        print("📊 Generating weekly collaboration report...")

        # 收集数据
        data = generator.get_week_data()

        # 生成报告
        report_content = generator.generate_report(data)

        # 保存报告
        filename = generator.save_report(report_content)

        print("🎉 Weekly collaboration report generated successfully!")
        print(f"📄 Report file: {filename}")

        # 输出摘要
        print(f"\n📈 Weekly Summary:")
        print(f"   Commits: {data['commits']['total_commits']}")
        print(f"   Contributors: {data['commits']['unique_authors']}")
        print(f"   PRs Opened: {data['prs']['opened']}")
        print(f"   PRs Merged: {data['prs']['merged']}")
        print(f"   Issues Closed: {data['issues']['closed']}")

    except Exception as e:
        print(f"❌ Error generating report: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()