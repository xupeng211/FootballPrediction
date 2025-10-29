#!/usr/bin/env python3
"""
高级质量度量分析器
Advanced Quality Metrics Analyzer

提供代码复杂度、技术债务、性能监控等高级质量度量指标
"""

import ast
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psutil

from src.core.logging_system import get_logger
from src.core.config import get_config

logger = get_logger(__name__)


class CodeComplexityAnalyzer:
    """代码复杂度分析器"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    def analyze_file_complexity(self, file_path: Path) -> Dict[str, Any]:
        """分析单个文件的复杂度"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            complexity_metrics = {
                'file_path': str(file_path),
                'lines_of_code': len(content.splitlines()),
                'cyclomatic_complexity': self._calculate_cyclomatic_complexity(tree),
                'cognitive_complexity': self._calculate_cognitive_complexity(tree),
                'maintainability_index': self._calculate_maintainability_index(content, tree),
                'nesting_depth': self._calculate_max_nesting_depth(tree),
                'function_count': len([node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]),
                'class_count': len([node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)])
            }

            return complexity_metrics

        except Exception as e:
            self.logger.error(f"分析文件复杂度失败 {file_path}: {e}")
            return {}

    def _calculate_cyclomatic_complexity(self, tree: ast.AST) -> int:
        """计算圈复杂度"""
        complexity = 1  # 基础复杂度

        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, ast.With, ast.AsyncWith):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
            elif isinstance(node, ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp):
                complexity += 1

        return complexity

    def _calculate_cognitive_complexity(self, tree: ast.AST) -> int:
        """计算认知复杂度（简化版）"""
        complexity = 0
        nesting_level = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1 + nesting_level
                nesting_level += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1 + nesting_level
            elif isinstance(node, (ast.Try, ast.With, ast.AsyncWith)):
                complexity += 1

        return complexity

    def _calculate_maintainability_index(self, content: str, tree: ast.AST) -> float:
        """计算可维护性指数（简化版）"""
        lines_of_code = len(content.splitlines())
        cyclomatic_complexity = self._calculate_cyclomatic_complexity(tree)
        volume = lines_of_code * 0.5  # 简化的体积计算

        if volume == 0:
            return 100.0

        # 简化的可维护性指数计算
        maintainability = max(0, 171 - 5.2 * (cyclomatic_complexity ** 0.23) - 0.23 * (volume ** 0.5))
        return round(maintainability, 2)

    def _calculate_max_nesting_depth(self, tree: ast.AST) -> int:
        """计算最大嵌套深度"""
        max_depth = 0

        def calculate_depth(node, current_depth=0):
            nonlocal max_depth
            max_depth = max(max_depth, current_depth)

            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.With, ast.AsyncWith, ast.Try)):
                for child in ast.iter_child_nodes(node):
                    calculate_depth(child, current_depth + 1)
            else:
                for child in ast.iter_child_nodes(node):
                    calculate_depth(child, current_depth)

        calculate_depth(tree)
        return max_depth

    def analyze_directory_complexity(self, directory: Path) -> Dict[str, Any]:
        """分析目录的复杂度"""
        python_files = list(directory.rglob("*.py"))

        if not python_files:
            return {}

        total_metrics = {
            'total_files': len(python_files),
            'file_metrics': [],
            'summary': {
                'total_lines': 0,
                'avg_cyclomatic_complexity': 0,
                'avg_cognitive_complexity': 0,
                'avg_maintainability_index': 0,
                'max_nesting_depth': 0,
                'total_functions': 0,
                'total_classes': 0
            }
        }

        cyclomatic_complexities = []
        cognitive_complexities = []
        maintainability_indices = []

        for file_path in python_files:
            if '__pycache__' in str(file_path):
                continue

            metrics = self.analyze_file_complexity(file_path)
            if metrics:
                total_metrics['file_metrics'].append(metrics)

                # 累加统计数据
                total_metrics['summary']['total_lines'] += metrics['lines_of_code']
                total_metrics['summary']['total_functions'] += metrics['function_count']
                total_metrics['summary']['total_classes'] += metrics['class_count']
                total_metrics['summary']['max_nesting_depth'] = max(
                    total_metrics['summary']['max_nesting_depth'],
                    metrics['nesting_depth']
                )

                cyclomatic_complexities.append(metrics['cyclomatic_complexity'])
                cognitive_complexities.append(metrics['cognitive_complexity'])
                maintainability_indices.append(metrics['maintainability_index'])

        # 计算平均值
        if cyclomatic_complexities:
            total_metrics['summary']['avg_cyclomatic_complexity'] = sum(cyclomatic_complexities) / len(cyclomatic_complexities)
            total_metrics['summary']['avg_cognitive_complexity'] = sum(cognitive_complexities) / len(cognitive_complexities)
            total_metrics['summary']['avg_maintainability_index'] = sum(maintainability_indices) / len(maintainability_indices)

        return total_metrics


class TechnicalDebtAnalyzer:
    """技术债务分析器"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    def analyze_technical_debt(self, directory: Path) -> Dict[str, Any]:
        """分析技术债务"""
        debt_metrics = {
            'code_smells': self._detect_code_smells(directory),
            'duplicate_code': self._detect_duplicate_code(directory),
            'long_methods': self._detect_long_methods(directory),
            'large_classes': self._detect_large_classes(directory),
            'dead_code': self._detect_dead_code(directory),
            'security_issues': self._detect_security_issues(directory)
        }

        # 计算技术债务分数
        debt_score = self._calculate_debt_score(debt_metrics)
        debt_metrics['debt_score'] = debt_score

        return debt_metrics

    def _detect_code_smells(self, directory: Path) -> List[Dict[str, Any]]:
        """检测代码异味"""
        smells = []
        python_files = list(directory.rglob("*.py"))

        for file_path in python_files:
            if '__pycache__' in str(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                # 检测长行
                for i, line in enumerate(lines, 1):
                    if len(line.strip()) > 88:  # PEP 8 行长度限制
                        smells.append({
                            'type': 'long_line',
                            'file': str(file_path),
                            'line': i,
                            'message': f'行长度超过88字符: {len(line.strip())}字符',
                            'severity': 'medium'
                        })

                # 检测未使用的导入
                content = ''.join(lines)
                tree = ast.parse(content)
                imports = set()
                used_names = set()

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(alias.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.add(node.module.split('.')[0])
                    elif isinstance(node, ast.Name):
                        used_names.add(node.id)

                unused_imports = imports - used_names
                for import_name in unused_imports:
                    smells.append({
                        'type': 'unused_import',
                        'file': str(file_path),
                        'line': 1,
                        'message': f'未使用的导入: {import_name}',
                        'severity': 'low'
                    })

            except Exception as e:
                self.logger.error(f"检测代码异味失败 {file_path}: {e}")

        return smells

    def _detect_duplicate_code(self, directory: Path) -> List[Dict[str, Any]]:
        """检测重复代码（简化版）"""
        duplicates = []
        code_blocks = {}

        python_files = list(directory.rglob("*.py"))
        for file_path in python_files:
            if '__pycache__' in str(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 简单的代码块相似度检测
                lines = content.split('\n')
                for i in range(0, len(lines) - 4):
                    block = '\n'.join(lines[i:i+5])
                    block_hash = hash(block)

                    if block_hash in code_blocks:
                        duplicates.append({
                            'type': 'duplicate_block',
                            'files': [code_blocks[block_hash], str(file_path)],
                            'line_start': i + 1,
                            'message': '发现重复代码块',
                            'severity': 'medium'
                        })
                    else:
                        code_blocks[block_hash] = str(file_path)

            except Exception as e:
                self.logger.error(f"检测重复代码失败 {file_path}: {e}")

        return duplicates

    def _detect_long_methods(self, directory: Path) -> List[Dict[str, Any]]:
        """检测长方法"""
        long_methods = []

        python_files = list(directory.rglob("*.py"))
        for file_path in python_files:
            if '__pycache__' in str(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                tree = ast.parse(''.join(lines))
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        start_line = node.lineno
                        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
                        method_length = end_line - start_line + 1

                        if method_length > 50:  # 长方法阈值
                            long_methods.append({
                                'type': 'long_method',
                                'file': str(file_path),
                                'line': start_line,
                                'method_name': node.name,
                                'length': method_length,
                                'message': f'方法过长: {method_length}行',
                                'severity': 'medium'
                            })

            except Exception as e:
                self.logger.error(f"检测长方法失败 {file_path}: {e}")

        return long_methods

    def _detect_large_classes(self, directory: Path) -> List[Dict[str, Any]]:
        """检测大类"""
        large_classes = []

        python_files = list(directory.rglob("*.py"))
        for file_path in python_files:
            if '__pycache__' in str(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                tree = ast.parse(''.join(lines))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        start_line = node.lineno
                        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
                        class_length = end_line - start_line + 1

                        method_count = len([n for n in node.body if isinstance(n, ast.FunctionDef)])

                        if class_length > 200 or method_count > 20:  # 大类阈值
                            large_classes.append({
                                'type': 'large_class',
                                'file': str(file_path),
                                'line': start_line,
                                'class_name': node.name,
                                'length': class_length,
                                'method_count': method_count,
                                'message': f'类过大: {class_length}行, {method_count}个方法',
                                'severity': 'high'
                            })

            except Exception as e:
                self.logger.error(f"检测大类失败 {file_path}: {e}")

        return large_classes

    def _detect_dead_code(self, directory: Path) -> List[Dict[str, Any]]:
        """检测死代码"""
        dead_code = []

        python_files = list(directory.rglob("*.py"))
        for file_path in python_files:
            if '__pycache__' in str(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                defined_functions = set()
                called_functions = set()

                # 收集定义的函数
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        defined_functions.add(node.name)

                # 收集调用的函数
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            called_functions.add(node.func.id)

                # 找出未调用的函数（排除特殊方法）
                unused_functions = defined_functions - called_functions
                for func_name in unused_functions:
                    if not func_name.startswith('_') and not func_name.startswith('test_'):
                        dead_code.append({
                            'type': 'dead_function',
                            'file': str(file_path),
                            'message': f'未使用的函数: {func_name}',
                            'severity': 'low'
                        })

            except Exception as e:
                self.logger.error(f"检测死代码失败 {file_path}: {e}")

        return dead_code

    def _detect_security_issues(self, directory: Path) -> List[Dict[str, Any]]:
        """检测安全问题"""
        security_issues = []

        python_files = list(directory.rglob("*.py"))
        for file_path in python_files:
            if '__pycache__' in str(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for i, line in enumerate(lines, 1):
                    line_content = line.strip().lower()

                    # 检测潜在的安全问题
                    security_patterns = {
                        'eval(': '使用了危险的eval()函数',
                        'exec(': '使用了危险的exec()函数',
                        'subprocess.call': '使用了subprocess.call',
                        'os.system': '使用了os.system',
                        'pickle.loads': '使用了不安全的pickle.loads',
                        'input()': '使用了input()（可能存在注入风险）'
                    }

                    for pattern, message in security_patterns.items():
                        if pattern in line_content:
                            security_issues.append({
                                'type': 'security_issue',
                                'file': str(file_path),
                                'line': i,
                                'message': message,
                                'severity': 'high'
                            })

            except Exception as e:
                self.logger.error(f"检测安全问题失败 {file_path}: {e}")

        return security_issues

    def _calculate_debt_score(self, debt_metrics: Dict[str, Any]) -> float:
        """计算技术债务分数"""
        total_issues = 0
        weighted_sum = 0

        severity_weights = {
            'low': 1,
            'medium': 5,
            'high': 10
        }

        for category, issues in debt_metrics.items():
            if isinstance(issues, list):
                for issue in issues:
                    severity = issue.get('severity', 'medium')
                    weight = severity_weights.get(severity, 5)
                    total_issues += 1
                    weighted_sum += weight

        if total_issues == 0:
            return 100.0  # 无技术债务

        # 债务分数：100 - (加权平均 * 10)
        avg_weight = weighted_sum / total_issues
        debt_score = max(0, 100 - (avg_weight * 2))

        return round(debt_score, 2)


class PerformanceMetricsCollector:
    """性能指标收集器"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    def collect_system_metrics(self) -> Dict[str, Any]:
        """收集系统性能指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)

            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_info = {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent,
                'used': memory.used,
                'free': memory.free
            }

            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            disk_info = {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': (disk.used / disk.total) * 100
            }

            # 网络IO
            network = psutil.net_io_counters()
            network_info = {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            }

            # 进程信息
            process_count = len(psutil.pids())

            return {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': cpu_percent,
                'memory': memory_info,
                'disk': disk_info,
                'network': network_info,
                'process_count': process_count
            }

        except Exception as e:
            self.logger.error(f"收集系统指标失败: {e}")
            return {}

    def collect_application_metrics(self) -> Dict[str, Any]:
        """收集应用程序性能指标"""
        try:
            current_process = psutil.Process()

            process_info = {
                'pid': current_process.pid,
                'memory_info': current_process.memory_info()._asdict(),
                'memory_percent': current_process.memory_percent(),
                'cpu_percent': current_process.cpu_percent(),
                'num_threads': current_process.num_threads(),
                'create_time': current_process.create_time(),
                'status': current_process.status()
            }

            return {
                'timestamp': datetime.now().isoformat(),
                'process': process_info
            }

        except Exception as e:
            self.logger.error(f"收集应用指标失败: {e}")
            return {}


class AdvancedMetricsAnalyzer:
    """高级度量分析器主类"""

    def __init__(self):
        self.complexity_analyzer = CodeComplexityAnalyzer()
        self.debt_analyzer = TechnicalDebtAnalyzer()
        self.performance_collector = PerformanceMetricsCollector()
        self.logger = get_logger(self.__class__.__name__)

    def run_full_analysis(self, project_root: Path) -> Dict[str, Any]:
        """运行完整的高级度量分析"""
        self.logger.info("开始高级度量分析...")

        # 只分析src目录
        src_directory = project_root / "src"
        if not src_directory.exists():
            self.logger.warning(f"src目录不存在: {src_directory}")
            return {}

        analysis_results = {
            'timestamp': datetime.now().isoformat(),
            'project_root': str(project_root),
            'complexity_metrics': self.complexity_analyzer.analyze_directory_complexity(src_directory),
            'technical_debt': self.debt_analyzer.analyze_technical_debt(src_directory),
            'performance_metrics': {
                'system': self.performance_collector.collect_system_metrics(),
                'application': self.performance_collector.collect_application_metrics()
            }
        }

        # 计算综合分数
        overall_score = self._calculate_overall_score(analysis_results)
        analysis_results['overall_advanced_score'] = overall_score

        self.logger.info("高级度量分析完成")
        return analysis_results

    def _calculate_overall_score(self, results: Dict[str, Any]) -> float:
        """计算综合高级度量分数"""
        scores = []

        # 复杂度分数 (可维护性指数)
        complexity = results.get('complexity_metrics', {}).get('summary', {})
        maintainability_index = complexity.get('avg_maintainability_index', 50)
        scores.append(maintainability_index)

        # 技术债务分数
        debt_score = results.get('technical_debt', {}).get('debt_score', 50)
        scores.append(debt_score)

        # 性能分数 (基于系统资源使用)
        system_metrics = results.get('performance_metrics', {}).get('system', {})
        cpu_usage = system_metrics.get('cpu_percent', 50)
        memory_usage = system_metrics.get('memory', {}).get('percent', 50)
        performance_score = max(0, 100 - ((cpu_usage + memory_usage) / 2))
        scores.append(performance_score)

        # 计算加权平均
        if scores:
            return round(sum(scores) / len(scores), 2)
        return 50.0


def main():
    """主函数，用于测试"""
    analyzer = AdvancedMetricsAnalyzer()
    project_root = Path(__file__).parent.parent.parent

    results = analyzer.run_full_analysis(project_root)

    print("🔍 高级度量分析结果:")
    print(f"📊 综合分数: {results.get('overall_advanced_score', 0):.2f}")

    complexity = results.get('complexity_metrics', {}).get('summary', {})
    print(f"🧮 平均圈复杂度: {complexity.get('avg_cyclomatic_complexity', 0):.1f}")
    print(f"🧠 平均认知复杂度: {complexity.get('avg_cognitive_complexity', 0):.1f}")
    print(f"🛠️ 平均可维护性指数: {complexity.get('avg_maintainability_index', 0):.1f}")

    debt = results.get('technical_debt', {})
    print(f"⚠️ 技术债务分数: {debt.get('debt_score', 0):.1f}")

    system = results.get('performance_metrics', {}).get('system', {})
    print(f"💻 CPU使用率: {system.get('cpu_percent', 0):.1f}%")
    print(f"🧠 内存使用率: {system.get('memory', {}).get('percent', 0):.1f}%")


if __name__ == "__main__":
    main()