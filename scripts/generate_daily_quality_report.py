#!/usr/bin/env python3
"""
Daily Quality Report Generator
每日质量报告生成器
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any

class DailyQualityReportGenerator:
    def __init__(self):
        self.report_date = datetime.now().strftime('%Y-%m-%d')
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.repo = os.getenv('GITHUB_REPOSITORY', 'xupeng211/FootballPrediction')

    def get_commit_stats(self) -> Dict[str, Any]:
        """获取提交统计"""
        try:
            # 获取过去24小时的提交
            since = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')

            cmd = [
                'git', 'log',
                f'--since={since}',
                '--pretty=format:%H|%an|%s',
                '--numstat'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            commits = []
            lines_added = 0
            lines_deleted = 0
            authors = set()

            # 解析git log输出
            current_commit = None
            for line in result.stdout.split('\n'):
                if '|' in line and len(line.split('|')) == 3:
                    parts = line.split('|')
                    current_commit = {
                        'hash': parts[0],
                        'author': parts[1],
                        'message': parts[2],
                        'files_changed': 0,
                        'lines_added': 0,
                        'lines_deleted': 0
                    }
                    commits.append(current_commit)
                    authors.add(parts[1])
                elif current_commit and '\t' in line:
                    # 这是文件变更统计
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
                'authors': list(authors),
                'commits': commits
            }

        except subprocess.CalledProcessError as e:
            print(f"❌ Error getting commit stats: {e}")
            return {'total_commits': 0, 'lines_added': 0, 'lines_deleted': 0, 'authors': [], 'commits': []}

    def get_test_stats(self) -> Dict[str, Any]:
        """获取测试统计"""
        try:
            # 运行pytest收集测试
            cmd = [
                'pytest',
                '--collect-only',
                '-q',
                'tests/'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"⚠️  pytest collection failed: {result.stderr}")
                return {'total_tests': 0, 'categories': {}}

            # 解析pytest输出
            lines = result.stdout.strip().split('\n')
            total_tests = 0
            categories = {}

            for line in lines:
                if 'test session starts' in line:
                    continue
                if 'collected' in line:
                    # 提取测试数量
                    import re
                    match = re.search(r'(\d+) items? collected', line)
                    if match:
                        total_tests = int(match.group(1))
                elif '::' in line:
                    # 分析测试类别
                    if 'test_' in line:
                        if 'unit' in line:
                            categories['unit'] = categories.get('unit', 0) + 1
                        elif 'integration' in line:
                            categories['integration'] = categories.get('integration', 0) + 1
                        elif 'api' in line:
                            categories['api'] = categories.get('api', 0) + 1
                        else:
                            categories['other'] = categories.get('other', 0) + 1

            return {
                'total_tests': total_tests,
                'categories': categories
            }

        except Exception as e:
            print(f"❌ Error getting test stats: {e}")
            return {'total_tests': 0, 'categories': {}}

    def get_code_quality_stats(self) -> Dict[str, Any]:
        """获取代码质量统计"""
        stats = {}

        # Ruff统计
        try:
            cmd = ['ruff', 'check', 'src/', '--output-format=json']
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.stdout:
                issues = json.loads(result.stdout)
                stats['ruff_issues'] = len(issues)

                # 按错误类型分类
                error_codes = {}
                for issue in issues:
                    code = issue.get('code', 'UNKNOWN')
                    error_codes[code] = error_codes.get(code, 0) + 1

                stats['ruff_error_codes'] = dict(sorted(error_codes.items(), key=lambda x: x[1], reverse=True)[:10])
            else:
                stats['ruff_issues'] = 0
                stats['ruff_error_codes'] = {}

        except Exception as e:
            print(f"❌ Error running ruff: {e}")
            stats['ruff_issues'] = -1
            stats['ruff_error_codes'] = {}

        # Bandit安全扫描
        try:
            cmd = ['bandit', '-r', 'src/', '-f', 'json']
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.stdout:
                bandit_data = json.loads(result.stdout)
                stats['bandit_issues'] = len(bandit_data.get('results', []))

                # 按严重性分类
                severity_counts = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0}
                for issue in bandit_data.get('results', []):
                    severity = issue.get('issue_severity', 'LOW')
                    severity_counts[severity] = severity_counts.get(severity, 0) + 1

                stats['bandit_severity'] = severity_counts
            else:
                stats['bandit_issues'] = 0
                stats['bandit_severity'] = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0}

        except Exception as e:
            print(f"❌ Error running bandit: {e}")
            stats['bandit_issues'] = -1
            stats['bandit_severity'] = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0}

        return stats

    def get_coverage_stats(self) -> Dict[str, Any]:
        """获取测试覆盖率统计"""
        try:
            # 尝试读取现有的覆盖率报告
            coverage_files = ['htmlcov/index.html', 'coverage.xml', '.coverage']

            for cov_file in coverage_files:
                if os.path.exists(cov_file):
                    if cov_file == 'htmlcov/index.html':
                        # 从HTML报告中提取覆盖率
                        with open(cov_file, 'r') as f:
                            content = f.read()
                            import re
                            match = re.search(r'(\d+\.?\d*)%', content)
                            if match:
                                return {
                                    'coverage_percentage': float(match.group(1)),
                                    'source': 'htmlcov/index.html'
                                }
                    elif cov_file == 'coverage.xml':
                        # 从XML报告中提取覆盖率
                        import xml.etree.ElementTree as ET
                        tree = ET.parse(cov_file)
                        root = tree.getroot()
                        coverage_elem = root.find('.//coverage')
                        if coverage_elem is not None:
                            line_rate = float(coverage_elem.get('line-rate', '0'))
                            return {
                                'coverage_percentage': line_rate * 100,
                                'source': 'coverage.xml'
                            }

            # 如果没有找到覆盖率报告，尝试运行覆盖率测试
            cmd = [
                'pytest',
                '--cov=src',
                '--cov-report=term-missing',
                '--cov-report=json',
                'tests/',
                '--maxfail=5',
                '--timeout=300'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode == 0:
                # 从输出中提取覆盖率
                import re
                match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+\.?\d*)%', result.stdout)
                if match:
                    return {
                        'coverage_percentage': float(match.group(1)),
                        'source': 'pytest_run'
                    }

        except Exception as e:
            print(f"❌ Error getting coverage stats: {e}")

        return {
            'coverage_percentage': 0,
            'source': 'unavailable'
        }

    def generate_report(self) -> str:
        """生成质量报告"""
        print("📊 Generating daily quality report...")

        # 收集所有统计数据
        commit_stats = self.get_commit_stats()
        test_stats = self.get_test_stats()
        quality_stats = self.get_code_quality_stats()
        coverage_stats = self.get_coverage_stats()

        # 生成报告内容
        report = f"""# 📊 Daily Quality Report

**Date**: {self.report_date}
**Repository**: {self.repo}
**Generated by**: Automated Quality System

## 📈 Summary

| Metric | Value | Status |
|--------|-------|--------|
| Commits (24h) | {commit_stats['total_commits']} | {'🟢 Active' if commit_stats['total_commits'] > 0 else '🔴 No Activity'} |
| Lines Added | {commit_stats['lines_added']:,} | {'🟢 Growing' if commit_stats['lines_added'] > 0 else '🟡 Stable'} |
| Test Cases | {test_stats['total_tests']:,} | {'🟢 Healthy' if test_stats['total_tests'] > 100 else '🟡 Needs More'} |
| Code Coverage | {coverage_stats['coverage_percentage']:.1f}% | {'🟢 Good' if coverage_stats['coverage_percentage'] >= 25 else '🟡 Improve'} |
| Ruff Issues | {quality_stats['ruff_issues']} | {'🟢 Clean' if quality_stats['ruff_issues'] < 10 else '🟡 Review Needed'} |
| Security Issues | {quality_stats['bandit_issues']} | {'🟢 Secure' if quality_stats['bandit_issues'] < 5 else '🟡 Review Needed'} |

## 🔄 Commit Activity

### Recent Commits
"""

        # 添加最近的提交
        for i, commit in enumerate(commit_stats['commits'][:5]):
            report += f"""
{i+1}. **{commit['hash'][:8]}** - {commit['author']}
   - {commit['message']}
   - Files: {commit['files_changed']}, Lines: +{commit['lines_added']}/-{commit['lines_deleted']}
"""

        if len(commit_stats['commits']) > 5:
            report += f"\n*... and {len(commit_stats['commits']) - 5} more commits*\n"

        report += f"""
### Contributors
{', '.join(commit_stats['authors']) if commit_stats['authors'] else 'No commits today'}

## 🧪 Test Statistics

### Test Distribution
"""

        # 添加测试分布
        if test_stats['categories']:
            for category, count in test_stats['categories'].items():
                percentage = (count / test_stats['total_tests']) * 100 if test_stats['total_tests'] > 0 else 0
                report += f"- **{category.title()}**: {count} tests ({percentage:.1f}%)\n"
        else:
            report += "- No test categorization available\n"

        report += f"""
### Coverage Details
- **Current Coverage**: {coverage_stats['coverage_percentage']:.1f}%
- **Source**: {coverage_stats['source']}
- **Target**: 25% (minimum for production)
- **Status**: {'✅ On Track' if coverage_stats['coverage_percentage'] >= 25 else '⚠️ Needs Improvement'}

## 🔍 Code Quality

### Style Issues (Ruff)
- **Total Issues**: {quality_stats['ruff_issues']}
- **Status**: {'🟢 Clean Code' if quality_stats['ruff_issues'] < 10 else '🟡 Needs Review'}

"""

        # 添加Ruff错误详情
        if quality_stats['ruff_error_codes']:
            report += "#### Top Issues:\n"
            for code, count in list(quality_stats['ruff_error_codes'].items())[:5]:
                report += f"- `{code}`: {count} occurrences\n"

        report += f"""
### Security Issues (Bandit)
- **Total Issues**: {quality_stats['bandit_issues']}
- **Status**: {'🟢 Secure' if quality_stats['bandit_issues'] < 5 else '🟡 Review Needed'}

#### Severity Breakdown:
- **High**: {quality_stats['bandit_severity']['HIGH']} issues
- **Medium**: {quality_stats['bandit_severity']['MEDIUM']} issues
- **Low**: {quality_stats['bandit_severity']['LOW']} issues

## 🎯 Recommendations

"""

        # 生成建议
        recommendations = []

        if coverage_stats['coverage_percentage'] < 25:
            recommendations.append("📈 **Increase Test Coverage**: Add more unit tests to reach 25% coverage")

        if quality_stats['ruff_issues'] > 20:
            recommendations.append("🔧 **Code Style**: Run `ruff check --fix` to auto-fix style issues")

        if quality_stats['bandit_issues'] > 5:
            recommendations.append("🛡️ **Security**: Review and fix security vulnerabilities")

        if commit_stats['total_commits'] == 0:
            recommendations.append("🔄 **Development Activity**: Consider regular commits to maintain momentum")

        if not recommendations:
            recommendations.append("🎉 **Excellent**: All quality metrics are within acceptable ranges!")

        for rec in recommendations:
            report += f"- {rec}\n"

        report += f"""
## 📊 Trend Analysis

**7-Day Trend**: Data will be accumulated over the coming days
**Health Score**: {self.calculate_health_score(commit_stats, test_stats, quality_stats, coverage_stats)}/100

---

*Report generated automatically on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*For questions or issues, please check the repository issues or contact the development team*
"""

        return report

    def calculate_health_score(self, commit_stats, test_stats, quality_stats, coverage_stats) -> int:
        """计算健康评分 (0-100)"""
        score = 0

        # 提交活动 (20分)
        if commit_stats['total_commits'] > 0:
            score += min(20, commit_stats['total_commits'] * 4)

        # 测试数量 (20分)
        if test_stats['total_tests'] > 0:
            score += min(20, test_stats['total_tests'] // 10)

        # 代码覆盖率 (25分)
        score += min(25, coverage_stats['coverage_percentage'])

        # 代码质量 (25分)
        ruff_score = max(0, 25 - quality_stats['ruff_issues'])
        score += ruff_score

        # 安全性 (10分)
        if quality_stats['bandit_issues'] == 0:
            score += 10
        elif quality_stats['bandit_issues'] < 5:
            score += 5

        return min(100, score)

    def save_report(self, content: str) -> str:
        """保存报告到文件"""
        filename = f"daily_quality_report_{self.report_date.replace('-', '')}.md"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ Report saved to: {filename}")
        return filename

def main():
    """主函数"""
    generator = DailyQualityReportGenerator()

    try:
        report_content = generator.generate_report()
        filename = generator.save_report(report_content)

        print("🎉 Daily quality report generated successfully!")
        print(f"📄 Report file: {filename}")

    except Exception as e:
        print(f"❌ Error generating report: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()