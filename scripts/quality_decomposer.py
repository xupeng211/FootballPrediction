#!/usr/bin/env python3
"""代码质量系统性改进分解工具"""

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime


@dataclass
class QualityIssue:
    file_path: str
    line: int
    column: int
    error_type: str
    message: str
    severity: str
    tool: str

class QualityDecomposer:
    def __init__(self):
        self.issues: list[QualityIssue] = []
        self.categories: dict[str, list[QualityIssue]] = {}

    def run_quality_checks(self) -> dict[str, str]:
        """运行各种质量检查工具"""
        results = {}

        # Ruff检查
        try:
            ruff_result = subprocess.run(
                ['ruff', 'check', 'src/', '--output-format=json'],
                capture_output=True, text=True
            )
            results['ruff'] = ruff_result.stdout
        except Exception:
            results['ruff'] = "[]"

        # MyPy检查
        try:
            mypy_result = subprocess.run(
                ['mypy', 'src/', '--show-error-codes', '--no-error-summary'],
                capture_output=True, text=True
            )
            results['mypy'] = mypy_result.stdout
        except Exception:
            results['mypy'] = ""

        # Flake8检查
        try:
            flake8_result = subprocess.run(
                ['flake8', 'src/', '--format=json'],
                capture_output=True, text=True
            )
            results['flake8'] = flake8_result.stdout
        except Exception:
            results['flake8'] = ""

        return results

    def parse_ruff_issues(self, ruff_output: str) -> list[QualityIssue]:
        """解析Ruff输出"""
        issues = []
        try:
            data = json.loads(ruff_output)
            for item in data:
                issue = QualityIssue(
                    file_path=item.get('filename', ''),
                    line=item.get('location', {}).get('row', 0),
                    column=item.get('location', {}).get('column', 0),
                    error_type=item.get('code', ''),
                    message=item.get('message', ''),
                    severity='error' if item.get('fix') and item.get('fix', {}).get('availability') else 'warning',
                    tool='ruff'
                )
                issues.append(issue)
        except json.JSONDecodeError:
            pass
        return issues

    def parse_mypy_issues(self, mypy_output: str) -> list[QualityIssue]:
        """解析MyPy输出"""
        issues = []
        lines = mypy_output.split('\n')

        for line in lines:
            if ':' in line and 'error:' in line:
                try:
                    # 解析格式: filename:line: error: message
                    parts = line.split(':')
                    if len(parts) >= 4:
                        file_path = parts[0]
                        line_num = int(parts[1])
                        message = ':'.join(parts[3:]).strip()

                        issue = QualityIssue(
                            file_path=file_path,
                            line=line_num,
                            column=0,
                            error_type='mypy_error',
                            message=message,
                            severity='error',
                            tool='mypy'
                        )
                        issues.append(issue)
                except (ValueError, IndexError):
                    continue

        return issues

    def categorize_issues(self) -> dict[str, list[QualityIssue]]:
        """将问题分类"""
        categories = {
            'import_errors': [],
            'syntax_errors': [],
            'type_errors': [],
            'style_issues': [],
            'unused_imports': [],
            'naming_conventions': [],
            'documentation': [],
            'security': [],
            'other': []
        }

        for issue in self.issues:
            if 'import' in issue.message.lower() or 'module' in issue.message.lower():
                categories['import_errors'].append(issue)
            elif 'syntax' in issue.message.lower():
                categories['syntax_errors'].append(issue)
            elif 'type' in issue.error_type.lower() or 'annotation' in issue.message.lower():
                categories['type_errors'].append(issue)
            elif issue.error_type.startswith(('E', 'W', 'F')) and issue.tool == 'ruff':
                categories['style_issues'].append(issue)
            elif 'unused' in issue.message.lower():
                categories['unused_imports'].append(issue)
            elif 'naming' in issue.message.lower():
                categories['naming_conventions'].append(issue)
            elif 'docstring' in issue.message.lower() or 'missing' in issue.message.lower():
                categories['documentation'].append(issue)
            elif issue.error_type.startswith('S'):
                categories['security'].append(issue)
            else:
                categories['other'].append(issue)

        return categories

    def create_execution_plan(self, categories: dict[str, list[QualityIssue]]) -> list[dict]:
        """创建执行计划"""
        plan = []

        # 按优先级排序
        priority_order = [
            ('syntax_errors', 'critical', '修复语法错误'),
            ('import_errors', 'high', '修复导入错误'),
            ('type_errors', 'high', '修复类型错误'),
            ('security', 'high', '修复安全问题'),
            ('unused_imports', 'medium', '清理未使用的导入'),
            ('style_issues', 'medium', '修复代码风格问题'),
            ('naming_conventions', 'low', '统一命名规范'),
            ('documentation', 'low', '补充文档'),
            ('other', 'low', '其他问题')
        ]

        for category, priority, description in priority_order:
            issues = categories[category]
            if issues:
                # 按文件分组
                file_groups = {}
                for issue in issues:
                    file_path = issue.file_path
                    if file_path not in file_groups:
                        file_groups[file_path] = []
                    file_groups[file_path].append(issue)

                # 创建任务
                for i, (file_path, file_issues) in enumerate(file_groups.items()):
                    task = {
                        'task_id': f'{category}_{i+1}',
                        'category': category,
                        'priority': priority,
                        'description': f'{description} - {file_path}',
                        'file_path': file_path,
                        'issues_count': len(file_issues),
                        'estimated_time': max(15, len(file_issues) * 2),  # 至少15分钟
                        'issues': [
            {
                'file_path': issue.file_path,
                'line': issue.line,
                'column': issue.column,
                'error_type': issue.error_type,
                'message': issue.message,
                'severity': issue.severity,
                'tool': issue.tool
            }
            for issue in file_issues
        ]
                    }
                    plan.append(task)

        return plan

    def generate_plan_report(self, plan: list[dict]) -> str:
        """生成计划报告"""
        report = []
        report.append("# 📊 代码质量系统性改进计划\n")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append(f"**总任务数**: {len(plan)}\n")

        # 按优先级统计
        priority_stats = {}
        for task in plan:
            priority = task['priority']
            if priority not in priority_stats:
                priority_stats[priority] = {'count': 0, 'issues': 0}
            priority_stats[priority]['count'] += 1
            priority_stats[priority]['issues'] += task['issues_count']

        report.append("## 📈 优先级分布\n")
        for priority, stats in priority_stats.items():
            report.append(f"- **{priority}**: {stats['count']} 个任务，{stats['issues']} 个问题")

        report.append("\n## 📋 详细任务清单\n")

        for i, task in enumerate(plan, 1):
            report.append(f"### 任务 {i}: {task['description']}")
            report.append(f"- **优先级**: {task['priority']}")
            report.append(f"- **问题数量**: {task['issues_count']}")
            report.append(f"- **预估时间**: {task['estimated_time']} 分钟")
            report.append(f"- **任务ID**: `{task['task_id']}`\n")

        return '\n'.join(report)

    def decompose_and_plan(self) -> dict:
        """执行完整的分解和计划流程"""
        results = self.run_quality_checks()

        self.issues = self.parse_ruff_issues(results['ruff'])
        self.issues.extend(self.parse_mypy_issues(results['mypy']))


        self.categories = self.categorize_issues()

        plan = self.create_execution_plan(self.categories)

        report = self.generate_plan_report(plan)

        return {
            'total_issues': len(self.issues),
            'categories': {k: len(v) for k, v in self.categories.items()},
            'tasks_count': len(plan),
            'plan': plan,
            'report': report
        }

if __name__ == '__main__':
    decomposer = QualityDecomposer()
    result = decomposer.decompose_and_plan()

    for _category, _count in result['categories'].items():
        pass

    # 保存报告
    with open('docs/quality_improvement_plan.md', 'w', encoding='utf-8') as f:
        f.write(result['report'])

    # 保存详细计划
    with open('quality_plan.json', 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_issues': result['total_issues'],
                'tasks_count': result['tasks_count']
            },
            'plan': result['plan']
        }, f, indent=2, ensure_ascii=False)

