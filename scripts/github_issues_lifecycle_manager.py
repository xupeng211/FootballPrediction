#!/usr/bin/env python3
"""
GitHub Issues生命周期自动化管理工具
提供Issues自动化清理、标签管理、最佳实践检查等功能
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

class GitHubIssuesLifecycleManager:
    """GitHub Issues生命周期管理器"""

    def __init__(self, repo: str = "xupeng211/FootballPrediction"):
        self.repo = repo
        self.issues_cache = {}
        self.stats_cache = {}

    def run_gh_command(self, args: List[str]) -> Tuple[bool, str]:
        """运行GitHub CLI命令"""
        try:
            cmd = ['gh'] + args
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0, result.stdout
        except subprocess.TimeoutExpired:
            return False, "Command timeout"
        except Exception as e:
            return False, str(e)

    def get_all_issues(self, state: str = "all", limit: int = 100) -> List[Dict]:
        """获取所有Issues"""
        if f"{state}_{limit}" in self.issues_cache:
            return self.issues_cache[f"{state}_{limit}"]

        success, output = self.run_gh_command([
            'issue', 'list', '--repo', self.repo, '--state', state,
            '--limit', str(limit), '--json', 'number,title,state,labels,created_at,closed_at,author'
        ])

        if success:
            issues = json.loads(output)
            self.issues_cache[f"{state}_{limit}"] = issues
            return issues
        else:
            print(f"❌ 获取Issues失败: {output}")
            return []

    def get_issues_by_label(self, label: str, state: str = "open") -> List[Dict]:
        """根据标签获取Issues"""
        issues = self.get_all_issues(state)
        return [issue for issue in issues
                if any(lbl['name'] == label for lbl in issue.get('labels', []))]

    def analyze_issue_health(self) -> Dict:
        """分析Issue健康状况"""
        all_issues = self.get_all_issues()
        open_issues = [i for i in all_issues if i['state'] == 'OPEN']
        closed_issues = [i for i in all_issues if i['state'] == 'CLOSED']

        # 统计标签使用情况
        label_counts = {}
        priority_counts = {}
        type_counts = {}

        resolved_but_open = 0
        stale_issues = 0
        old_open_issues = 0

        cutoff_date = datetime.now() - timedelta(days=30)

        for issue in all_issues:
            # 统计标签
            for label in issue.get('labels', []):
                name = label['name']
                label_counts[name] = label_counts.get(name, 0) + 1

                # 优先级统计
                if name.startswith('priority-'):
                    priority_counts[name] = priority_counts.get(name, 0) + 1

                # 类型统计
                if name in ['bug', 'enhancement', 'feature', 'documentation', 'testing']:
                    type_counts[name] = type_counts.get(name, 0) + 1

            # 问题分析
            if issue['state'] == 'OPEN':
                if 'resolved' in [lbl['name'] for lbl in issue.get('labels', [])]:
                    resolved_but_open += 1

                # 创建时间分析
                created_date = datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00'))
                if created_date < cutoff_date:
                    old_open_issues += 1

                # 检查是否长时间未活动
                if created_date < datetime.now() - timedelta(days=90):
                    stale_issues += 1

        total_issues = len(all_issues)
        close_rate = (len(closed_issues) / total_issues * 100) if total_issues > 0 else 0

        return {
            'total_issues': total_issues,
            'open_issues': len(open_issues),
            'closed_issues': len(closed_issues),
            'close_rate': close_rate,
            'resolved_but_open': resolved_but_open,
            'old_open_issues': old_open_issues,
            'stale_issues': stale_issues,
            'label_counts': label_counts,
            'priority_counts': priority_counts,
            'type_counts': type_counts,
            'health_score': self._calculate_health_score(close_rate, resolved_but_open, old_open_issues)
        }

    def _calculate_health_score(self, close_rate: float, resolved_open: int, old_open: int) -> int:
        """计算Issue健康评分 (0-100)"""
        score = 100

        # 关闭率评分 (40%权重)
        score += (close_rate - 50) * 0.4

        # resolved但开放的Issues (30%权重)
        if resolved_open > 20:
            score -= resolved_open
        elif resolved_open > 10:
            score -= resolved_open * 0.5
        elif resolved_open > 5:
            score -= resolved_open * 0.2

        # 老的开放Issues (30%权重)
        if old_open > 20:
            score -= old_open * 0.5
        elif old_open > 10:
            score -= old_open * 0.3
        elif old_open > 5:
            score -= old_open * 0.1

        return max(0, min(100, int(score)))

    def auto_cleanup_resolved_issues(self, dry_run: bool = True, limit: int = 10) -> Dict:
        """自动清理已解决的Issues"""
        resolved_issues = self.get_issues_by_label('resolved', 'open')

        results = {
            'total_found': len(resolved_issues),
            'processed': 0,
            'success': 0,
            'failed': 0,
            'errors': []
        }

        print(f"🔍 找到 {len(resolved_issues)} 个标记为resolved但仍开放的Issues")

        # 按创建时间排序，优先处理旧的
        resolved_issues.sort(key=lambda x: x['created_at'])

        for issue in resolved_issues[:limit]:
            issue_number = issue['number']
            issue_title = issue['title']

            if dry_run:
                print(f"🔍 [DRY RUN] Issue #{issue_number}: {issue_title}")
                results['processed'] += 1
                continue

            # 添加关闭评论
            comment = f"""🎯 **Issue自动关闭**

此Issue已标记为'resolved'，系统自动关闭。

✅ **完成状态**: 已完成
🤖 **关闭原因**: 标记为resolved的Issue应该及时关闭
📋 **清理时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔧 **管理工具**: GitHub Issues Lifecycle Manager

---
*由自动化管理工具处理*"""

            # 添加评论
            success, _ = self.run_gh_command([
                'issue', 'comment', str(issue_number), '--repo', self.repo,
                '--body', comment
            ])

            results['processed'] += 1

            if success:
                # 关闭Issue
                success_close, _ = self.run_gh_command([
                    'issue', 'close', str(issue_number), '--repo', self.repo
                ])

                if success_close:
                    print(f"✅ Issue #{issue_number}: 已成功关闭")
                    results['success'] += 1
                else:
                    print(f"❌ Issue #{issue_number}: 关闭失败")
                    results['failed'] += 1
                    results['errors'].append(f"#{issue_number}: 关闭失败")
            else:
                print(f"❌ Issue #{issue_number}: 添加评论失败")
                results['failed'] += 1
                results['errors'].append(f"#{issue_number}: 添加评论失败")

        return results

    def improve_label_consistency(self, dry_run: bool = True) -> Dict:
        """改善标签一致性"""
        all_issues = self.get_all_issues()

        # 标签标准化映射
        label_standardization = {
            # 优先级标签
            'high': 'priority-high',
            'medium': 'priority-medium',
            'low': 'priority-low',
            'critical': 'priority-critical',
            'urgent': 'priority-critical',

            # 类型标签
            'bugfix': 'bug',
            'feature-request': 'enhancement',
            'enhancement-request': 'enhancement',
            'doc': 'documentation',
            'docs': 'documentation',
            'test': 'testing',
            'tests': 'testing',

            # 状态标签
            'resolved': 'resolved',
            'wontfix': 'wont-fix',
            'duplicate': 'duplicate',
            'invalid': 'invalid',
        }

        results = {
            'total_checked': len(all_issues),
            'issues_modified': 0,
            'labels_added': 0,
            'labels_removed': 0,
            'errors': []
        }

        for issue in all_issues:
            if issue['state'] != 'OPEN':
                continue

            issue_number = issue['number']
            current_labels = [lbl['name'] for lbl in issue.get('labels', [])]

            labels_to_add = []
            labels_to_remove = []

            # 检查标签标准化
            for label in current_labels:
                if label in label_standardization:
                    standardized = label_standardization[label]
                    if standardized not in current_labels:
                        labels_to_add.append(standardized)
                    if label != standardized:
                        labels_to_remove.append(label)

            if labels_to_add or labels_to_remove:
                if dry_run:
                    print(f"🔍 [DRY RUN] Issue #{issue_number}: 添加{labels_to_add}, 移除{labels_to_remove}")
                    results['issues_modified'] += 1
                    results['labels_added'] += len(labels_to_add)
                    results['labels_removed'] += len(labels_to_remove)
                else:
                    # 实际执行标签修改
                    # 添加新标签
                    for label in labels_to_add:
                        success, _ = self.run_gh_command([
                            'issue', 'edit', str(issue_number), '--repo', self.repo,
                            '--add-label', label
                        ])
                        if success:
                            results['labels_added'] += 1

                    # 移除旧标签
                    for label in labels_to_remove:
                        success, _ = self.run_gh_command([
                            'issue', 'edit', str(issue_number), '--repo', self.repo,
                            '--remove-label', label
                        ])
                        if success:
                            results['labels_removed'] += 1

                    if labels_to_add or labels_to_remove:
                        results['issues_modified'] += 1

        return results

    def generate_best_practices_report(self) -> str:
        """生成最佳实践报告"""
        health = self.analyze_issue_health()

        report = f"""
# 📊 GitHub Issues最佳实践报告

## 🎯 健康状况总览
- **总Issues数量**: {health['total_issues']}
- **开放Issues**: {health['open_issues']}
- **关闭Issues**: {health['closed_issues']}
- **关闭率**: {health['close_rate']:.1f}%
- **健康评分**: {health['health_score']}/100

## ⚠️ 需要关注的问题
- **标记为resolved但仍开放**: {health['resolved_but_open']}个
- **超过30天未关闭**: {health['old_open_issues']}个
- **超过90天未活动**: {health['stale_issues']}个

## 🏷️ 标签使用统计
### 优先级分布
"""

        for priority, count in sorted(health['priority_counts'].items()):
            report += f"- **{priority}**: {count}个\n"

        report += "\n### 类型分布\n"
        for issue_type, count in sorted(health['type_counts'].items()):
            report += f"- **{issue_type}**: {count}个\n"

        report += f"""
## 💡 改进建议

### 立即行动 (高优先级)
1. **清理resolved Issues**: {health['resolved_but_open']}个已解决但仍开放的Issues需要关闭
2. **处理过期Issues**: {health['old_open_issues']}个超过30天的开放Issues需要 review

### 中期改进
1. **标签标准化**: 确保所有Issues使用一致的标签规范
2. **里程碑管理**: 为重要任务设置里程碑
3. **定期维护**: 建立每周Issue清理流程

### 长期优化
1. **自动化流程**: 集成更多自动化管理工具
2. **团队协作**: 建立团队Issue管理最佳实践
3. **指标监控**: 建立Issue健康度监控仪表板

## 🎯 下一步行动
```bash
# 执行自动清理 (先dry run)
python3 scripts/github_issues_lifecycle_manager.py cleanup --dry-run

# 改善标签一致性
python3 scripts/github_issues_lifecycle_manager.py labels --dry-run

# 生成健康报告
python3 scripts/github_issues_lifecycle_manager.py health
```

---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*工具版本: GitHub Issues Lifecycle Manager v1.0.0*
"""

        return report

    def schedule_automated_cleanup(self) -> bool:
        """调度自动化清理任务"""
        print("🚀 调度自动化清理任务...")

        # 1. 清理resolved Issues (限制5个避免影响过大)
        cleanup_result = self.auto_cleanup_resolved_issues(dry_run=False, limit=5)

        # 2. 改善标签一致性
        labels_result = self.improve_label_consistency(dry_run=False)

        # 3. 生成报告
        report = self.generate_best_practices_report()

        # 保存报告
        report_file = f"reports/github_issues_health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        try:
            import os
            os.makedirs('reports', exist_ok=True)
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"📋 健康报告已保存: {report_file}")
        except Exception as e:
            print(f"❌ 保存报告失败: {e}")

        print("✅ 自动化清理任务完成")
        print(f"🧹 清理Issues: {cleanup_result['success']}/{cleanup_result['processed']}")
        print(f"🏷️ 标签优化: {labels_result['issues_modified']}个Issues")

        return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='GitHub Issues生命周期管理工具')
    parser.add_argument('command', choices=['health', 'cleanup', 'labels', 'schedule', 'report'],
                       help='执行的命令')
    parser.add_argument('--dry-run', action='store_true', help='仅显示将要执行的操作，不实际执行')
    parser.add_argument('--limit', type=int, default=10, help='处理的Issues数量限制')
    parser.add_argument('--repo', default='xupeng211/FootballPrediction', help='GitHub仓库')

    args = parser.parse_args()

    manager = GitHubIssuesLifecycleManager(args.repo)

    if args.command == 'health':
        print("📊 分析GitHub Issues健康状况...")
        health = manager.analyze_issue_health()

        print(f"""
📈 Issues健康状况报告
================
总数量: {health['total_issues']}
开放: {health['open_issues']}
关闭: {health['closed_issues']}
关闭率: {health['close_rate']:.1f}%
健康评分: {health['health_score']}/100

⚠️ 需要关注:
- resolved但仍开放: {health['resolved_but_open']}个
- 超过30天未关闭: {health['old_open_issues']}个
- 超过90天未活动: {health['stale_issues']}个
        """)

    elif args.command == 'cleanup':
        print("🧹 清理已解决的Issues...")
        result = manager.auto_cleanup_resolved_issues(dry_run=args.dry_run, limit=args.limit)

        print(f"""
清理结果:
- 发现: {result['total_found']}个
- 处理: {result['processed']}个
- 成功: {result['success']}个
- 失败: {result['failed']}个
        """)

        if result['errors']:
            print("错误详情:")
            for error in result['errors']:
                print(f"  - {error}")

    elif args.command == 'labels':
        print("🏷️ 改善标签一致性...")
        result = manager.improve_label_consistency(dry_run=args.dry_run)

        print(f"""
标签优化结果:
- 检查Issues: {result['total_checked']}个
- 修改Issues: {result['issues_modified']}个
- 添加标签: {result['labels_added']}个
- 移除标签: {result['labels_removed']}个
        """)

    elif args.command == 'schedule':
        print("⏰ 执行调度自动化清理...")
        manager.schedule_automated_cleanup()

    elif args.command == 'report':
        print("📋 生成最佳实践报告...")
        report = manager.generate_best_practices_report()

        try:
            import os
            os.makedirs('reports', exist_ok=True)
            report_file = f"reports/github_issues_best_practices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"✅ 报告已保存: {report_file}")
        except Exception as e:
            print(f"❌ 保存报告失败: {e}")
            print(report)

if __name__ == '__main__':
    main()