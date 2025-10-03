import os
#!/usr/bin/env python3
"""MLflow 安全审计和修复脚本

此脚本用于审计项目中的 MLflow 使用情况，并提供安全修复建议。
"""

import ast
import re
import sys
from pathlib import Path
from typing import List, Dict
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format = os.getenv("MLFLOW_AUDIT_FORMAT_17")
)
logger = logging.getLogger(__name__)


class MLflowSecurityAuditor:
    """MLflow 安全审计器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.issues = []
        self.secure_patterns = {
            'direct_load_model': r'mlflow\.sklearn\.load_model\(',
            'direct_log_model': r'mlflow\.sklearn\.log_model\(',
            'unrestricted_set_tracking_uri': r'mlflow\.set_tracking_uri\(',
            'pickle_usage': r'pickle\.load\(|pickle\.loads\(',
        }

    def audit_file(self, file_path: Path) -> List[Dict]:
        """审计单个文件

        Args:
            file_path: 文件路径

        Returns:
            发现的问题列表
        """
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析 AST
            try:
                tree = ast.parse(content)
            except SyntaxError:
                logger.warning(f"无法解析文件: {file_path}")
                return issues

            # 检查导入
            imports = self._check_imports(tree, file_path)

            # 检查函数调用
            calls = self._check_function_calls(tree, file_path)

            # 检查字符串模式
            pattern_issues = self._check_patterns(content, file_path)

            issues.extend(imports)
            issues.extend(calls)
            issues.extend(pattern_issues)

        except Exception as e:
            logger.error(f"审计文件失败 {file_path}: {e}")

        return issues

    def _check_imports(self, tree: ast.AST, file_path: Path) -> List[Dict]:
        """检查导入语句"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == 'mlflow':
                        issues.append({
                            'type': 'unsafe_import',
                            'file': str(file_path),
                            'line': node.lineno,
                            'description': '直接导入 mlflow，建议使用安全封装',
                            'severity': 'medium',
                            'code': f"import {alias.name}"
                        })

            elif isinstance(node, ast.ImportFrom):
                if node.module and 'mlflow' in node.module:
                    if not any(alias.name.startswith('secure') for alias in node.names):
                        issues.append({
                            'type': 'unsafe_import',
                            'file': str(file_path),
                            'line': node.lineno,
                            'description': f'导入 mlflow.{node.module}，建议使用安全封装',
                            'severity': 'medium',
                            'code': f"from {node.module} import ..."
                        })

        return issues

    def _check_function_calls(self, tree: ast.AST, file_path: Path) -> List[Dict]:
        """检查函数调用"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # 检查 mlflow.sklearn.load_model
                if self._is_mlflow_call(node, 'load_model'):
                    issues.append({
                        'type': 'unsafe_model_load',
                        'file': str(file_path),
                        'line': node.lineno,
                        'description': '直接使用 mlflow.sklearn.load_model，存在反序列化风险',
                        'severity': 'high',
                        'code': 'mlflow.sklearn.load_model()'
                    })

                # 检查 mlflow.sklearn.log_model
                elif self._is_mlflow_call(node, 'log_model'):
                    issues.append({
                        'type': 'unsafe_model_log',
                        'file': str(file_path),
                        'line': node.lineno,
                        'description': '直接使用 mlflow.sklearn.log_model，可能记录敏感信息',
                        'severity': 'medium',
                        'code': 'mlflow.sklearn.log_model()'
                    })

        return issues

    def _check_patterns(self, content: str, file_path: Path) -> List[Dict]:
        """检查字符串模式"""
        issues = []
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            for pattern_name, pattern in self.secure_patterns.items():
                if re.search(pattern, line):
                    severity = 'high' if 'load_model' in pattern else 'medium'
                    issues.append({
                        'type': f'unsafe_pattern_{pattern_name}',
                        'file': str(file_path),
                        'line': i,
                        'description': f'检测到不安全的模式: {pattern_name}',
                        'severity': severity,
                        'code': line.strip()
                    })

        return issues

    def _is_mlflow_call(self, node: ast.Call, function_name: str) -> bool:
        """检查是否是 mlflow 函数调用"""
        if isinstance(node.func, ast.Attribute):
            if (node.func.attr == function_name and
                isinstance(node.func.value, ast.Attribute) and
                node.func.value.attr == 'sklearn' and
                isinstance(node.func.value.value, ast.Name) and
                node.func.value.value.id == 'mlflow'):
                return True
        return False

    def audit_project(self) -> Dict:
        """审计整个项目"""
        logger.info(f"开始审计项目: {self.project_root}")

        all_issues = []
        python_files = list(self.project_root.rglob('*.py'))

        # 排除某些目录
        exclude_dirs = {'.git', '__pycache__', '.venv', 'venv', 'node_modules'}
        python_files = [
            f for f in python_files
            if not any(exclude in f.parts for exclude in exclude_dirs)
        ]

        logger.info(f"找到 {len(python_files)} 个 Python 文件")

        for file_path in python_files:
            file_issues = self.audit_file(file_path)
            all_issues.extend(file_issues)

        # 统计
        stats = {
            'total_files': len(python_files),
            'files_with_issues': len(set(issue['file'] for issue in all_issues)),
            'total_issues': len(all_issues),
            'high_severity': len([i for i in all_issues if i['severity'] == 'high']),
            'medium_severity': len([i for i in all_issues if i['severity'] == 'medium']),
            'low_severity': len([i for i in all_issues if i['severity'] == 'low']),
            'issues_by_type': {}
        }

        for issue in all_issues:
            issue_type = issue['type']
            if issue_type not in stats['issues_by_type']:
                stats['issues_by_type'][issue_type] = 0
            stats['issues_by_type'][issue_type] += 1

        return {
            'stats': stats,
            'issues': all_issues
        }

    def generate_report(self, audit_result: Dict) -> str:
        """生成审计报告"""
        report = []
        report.append("=" * 60)
        report.append("MLflow 安全审计报告")
        report.append("=" * 60)
        report.append(f"项目路径: {self.project_root}")
        report.append(f"审计时间: {sys.version}")
        report.append("")

        # 统计信息
        stats = audit_result['stats']
        report.append("📊 统计信息")
        report.append("-" * 30)
        report.append(f"总文件数: {stats['total_files']}")
        report.append(f"有问题的文件数: {stats['files_with_issues']}")
        report.append(f"总问题数: {stats['total_issues']}")
        report.append(f"高危问题: {stats['high_severity']}")
        report.append(f"中危问题: {stats['medium_severity']}")
        report.append(f"低危问题: {stats['low_severity']}")
        report.append("")

        # 问题类型分布
        report.append("📋 问题类型分布")
        report.append("-" * 30)
        for issue_type, count in stats['issues_by_type'].items():
            report.append(f"{issue_type}: {count}")
        report.append("")

        # 详细问题列表
        if audit_result['issues']:
            report.append("🔍 详细问题列表")
            report.append("-" * 30)

            # 按严重程度分组
            high_issues = [i for i in audit_result['issues'] if i['severity'] == 'high']
            medium_issues = [i for i in audit_result['issues'] if i['severity'] == 'medium']
            low_issues = [i for i in audit_result['issues'] if i['severity'] == 'low']

            if high_issues:
                report.append("\n🚨 高危问题:")
                for issue in high_issues:
                    report.append(f"  文件: {issue['file']}:{issue['line']}")
                    report.append(f"  描述: {issue['description']}")
                    report.append(f"  代码: {issue['code']}")
                    report.append("")

            if medium_issues:
                report.append("\n⚠️ 中危问题:")
                for issue in medium_issues:
                    report.append(f"  文件: {issue['file']}:{issue['line']}")
                    report.append(f"  描述: {issue['description']}")
                    report.append(f"  代码: {issue['code']}")
                    report.append("")

            if low_issues:
                report.append("\n💡 低危问题:")
                for issue in low_issues:
                    report.append(f"  文件: {issue['file']}:{issue['line']}")
                    report.append(f"  描述: {issue['description']}")
                    report.append(f"  代码: {issue['code']}")
                    report.append("")
        else:
            report.append("✅ 未发现安全问题")

        # 修复建议
        report.append("\n🔧 修复建议")
        report.append("-" * 30)
        report.append("1. 使用 src/utils/mlflow_security.py 中的安全封装")
        report.append("2. 在加载模型前验证模型签名")
        report.append("3. 在沙箱环境中执行模型操作")
        report.append("4. 限制模型记录的信息，避免泄露敏感数据")
        report.append("5. 启用 MLflow 访问控制和审计日志")

        return "\n".join(report)

    def fix_issues(self, audit_result: Dict, dry_run: bool = True):
        """修复发现的问题

        Args:
            audit_result: 审计结果
            dry_run: 是否只是模拟运行
        """
        logger.info("开始修复安全问题...")

        # 按文件分组问题
        issues_by_file = {}
        for issue in audit_result['issues']:
            file_path = issue['file']
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append(issue)

        for file_path, file_issues in issues_by_file.items():
            logger.info(f"修复文件: {file_path}")

            if dry_run:
                logger.info("  [DRY RUN] 将会进行的修复:")
                for issue in file_issues:
                    logger.info(f"    - 行 {issue['line']}: {issue['description']}")
            else:
                # 实际修复逻辑
                self._fix_file(file_path, file_issues)

    def _fix_file(self, file_path: str, issues: List[Dict]):
        """修复单个文件"""
        # 这里可以实现自动修复逻辑
        # 由于修复可能很复杂，建议手动修复
        logger.warning(f"请手动修复文件: {file_path}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description = os.getenv("MLFLOW_AUDIT_DESCRIPTION_324"))
    parser.add_argument(
        '--project-root',
        default='.',
        help = os.getenv("MLFLOW_AUDIT_HELP_327")
    )
    parser.add_argument(
        '--output',
        help = os.getenv("MLFLOW_AUDIT_HELP_330")
    )
    parser.add_argument(
        '--fix',
        action = os.getenv("MLFLOW_AUDIT_ACTION_332"),
        help = os.getenv("MLFLOW_AUDIT_HELP_334")
    )
    parser.add_argument(
        '--dry-run',
        action = os.getenv("MLFLOW_AUDIT_ACTION_332"),
        default=True,
        help = os.getenv("MLFLOW_AUDIT_HELP_337")
    )

    args = parser.parse_args()

    # 创建审计器
    auditor = MLflowSecurityAuditor(args.project_root)

    # 执行审计
    result = auditor.audit_project()

    # 生成报告
    report = auditor.generate_report(result)

    # 输出报告
    print(report)

    # 保存报告到文件
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"报告已保存到: {args.output}")

    # 修复问题
    if args.fix:
        auditor.fix_issues(result, dry_run=args.dry_run)

    # 返回适当的退出码
    if result['stats']['high_severity'] > 0:
        sys.exit(1)
    elif result['stats']['medium_severity'] > 0:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()