#!/usr/bin/env python3
"""
长文件分析工具 - Issue #87
识别和分析项目中需要拆分的长文件
"""

import os
import ast
from typing import Dict, List, Tuple, Any
from pathlib import Path
import subprocess

class LongFileAnalyzer:
    """长文件分析器"""

    def __init__(self, max_lines: int = 100):
        self.max_lines = max_lines
        self.long_files = []

    def find_long_files(self, directory: str = "src/") -> List[Dict]:
        """查找长文件"""
        print(f"🔍 搜索长文件 (>{self.max_lines} 行)...")
        print("=" * 60)

        # 使用find命令快速获取文件行数
        result = subprocess.run([
            'find', directory, '-name', '*.py', '-exec', 'wc', '-l', '{}', '+'
        ], capture_output=True, text=True, cwd='.')

        # 解析结果
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if line.strip():
                try:
                    parts = line.strip().split()
                    line_count = int(parts[0])
                    file_path = parts[1]

                    if line_count > self.max_lines:
                        file_info = self.analyze_file_structure(file_path, line_count)
                        self.long_files.append(file_info)
                except (ValueError, IndexError) as e:
                    print(f"解析错误: {line} - {e}")

        # 按行数排序
        self.long_files.sort(key=lambda x: x['line_count'], reverse=True)
        return self.long_files

    def analyze_file_structure(self, file_path: str, line_count: int) -> Dict:
        """分析文件结构"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            classes = []
            functions = []
            imports = []
            complexity_score = 0

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # 计算类复杂度
                    class_methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                    class_complexity = len(class_methods) + self._calculate_node_complexity(node)

                    classes.append({
                        'name': node.name,
                        'line_start': node.lineno,
                        'line_end': self._get_end_line(node, content),
                        'methods': len(class_methods),
                        'complexity': class_complexity
                    })
                    complexity_score += class_complexity

                elif isinstance(node, ast.FunctionDef):
                    if not any(cls['line_start'] <= node.lineno <= cls['line_end'] for cls in classes):
                        # 不在类中的函数
                        func_complexity = self._calculate_node_complexity(node)
                        functions.append({
                            'name': node.name,
                            'line_start': node.lineno,
                            'line_end': self._get_end_line(node, content),
                            'complexity': func_complexity
                        })
                        complexity_score += func_complexity

                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports.append({
                        'type': 'import' if isinstance(node, ast.Import) else 'from_import',
                        'line': node.lineno
                    })

            # 计算拆分建议
            split_suggestions = self._generate_split_suggestions(
                file_path, classes, functions, line_count, complexity_score
            )

            return {
                'path': file_path,
                'line_count': line_count,
                'classes': classes,
                'functions': functions,
                'imports': imports,
                'complexity_score': complexity_score,
                'split_suggestions': split_suggestions,
                'priority': self._calculate_priority(line_count, complexity_score)
            }

        except Exception as e:
            return {
                'path': file_path,
                'line_count': line_count,
                'error': str(e),
                'priority': 'high'
            }

    def _calculate_node_complexity(self, node) -> int:
        """计算AST节点的复杂度"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def _get_end_line(self, node, content: str) -> int:
        """获取节点结束行号"""
        lines = content.split('\n')
        if hasattr(node, 'end_lineno') and node.end_lineno:
            return node.end_lineno

        # 回退计算：查找节点的最后一条语句
        max_line = node.lineno
        for child in ast.walk(node):
            if hasattr(child, 'lineno') and child.lineno > max_line:
                max_line = child.lineno

        return max_line

    def _generate_split_suggestions(self, file_path: str, classes: List[Dict],
                                   functions: List[Dict], line_count: int, complexity: int) -> List[str]:
        """生成拆分建议"""
        suggestions = []

        if line_count > 500:
            suggestions.append("文件过长(>500行)，建议立即拆分")

        if len(classes) > 5:
            suggestions.append(f"类过多({len(classes)}个)，建议按功能拆分到多个模块")

        if len(functions) > 10:
            suggestions.append(f"独立函数过多({len(functions)}个)，建议按职责分组")

        if complexity > 100:
            suggestions.append(f"复杂度过高({complexity})，建议拆分复杂类和函数")

        # 具体建议
        if classes:
            largest_class = max(classes, key=lambda x: x['complexity'])
            if largest_class['complexity'] > 30:
                suggestions.append(f"类'{largest_class['name']}'过于复杂，建议拆分为多个类")

        if functions:
            complex_functions = [f for f in functions if f['complexity'] > 10]
            if complex_functions:
                suggestions.append(f"存在{len(complex_functions)}个复杂函数，建议拆分或重构")

        # 基于文件路径的建议
        if 'monitoring' in file_path and line_count > 200:
            suggestions.append("监控模块建议按监控类型拆分（异常检测、性能监控、指标收集等）")

        if 'strategies' in file_path and line_count > 200:
            suggestions.append("策略模块建议按策略类型拆分（历史策略、ML策略、统计策略等）")

        if 'decorators' in file_path and line_count > 200:
            suggestions.append("装饰器模块建议按功能拆分（缓存装饰器、验证装饰器、监控装饰器等）")

        return suggestions

    def _calculate_priority(self, line_count: int, complexity: int) -> str:
        """计算拆分优先级"""
        if line_count > 600 or complexity > 150:
            return "critical"
        elif line_count > 400 or complexity > 100:
            return "high"
        elif line_count > 200 or complexity > 50:
            return "medium"
        else:
            return "low"

    def generate_report(self) -> str:
        """生成分析报告"""
        if not self.long_files:
            return "没有发现需要拆分的长文件。"

        report = f"""
📊 长文件分析报告 - Issue #87
=============================

发现 {len(self.long_files)} 个需要关注的长文件 (> {self.max_lines} 行)

优先级分布:
"""

        # 统计优先级
        priorities = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for file_info in self.long_files:
            priority = file_info.get('priority', 'low')
            priorities[priority] = priorities.get(priority, 0) + 1

        for priority, count in priorities.items():
            if count > 0:
                report += f"- {priority.capitalize()}: {count} 个文件\n"

        report += "\n详细分析:\n"
        report += "-" * 50 + "\n"

        # 详细信息
        for i, file_info in enumerate(self.long_files, 1):
            report += f"\n{i}. {file_info['path']}\n"
            report += f"   行数: {file_info['line_count']}\n"
            report += f"   优先级: {file_info.get('priority', 'unknown').upper()}\n"

            if 'error' in file_info:
                report += f"   错误: {file_info['error']}\n"
                continue

            report += f"   类数: {len(file_info.get('classes', []))}\n"
            report += f"   函数数: {len(file_info.get('functions', []))}\n"
            report += f"   复杂度: {file_info.get('complexity_score', 0)}\n"

            suggestions = file_info.get('split_suggestions', [])
            if suggestions:
                report += "   拆分建议:\n"
                for suggestion in suggestions:
                    report += f"     - {suggestion}\n"

        return report

    def create_split_plan(self) -> Dict:
        """创建拆分计划"""
        split_plan = {
            'critical_files': [],
            'high_priority_files': [],
            'medium_priority_files': [],
            'low_priority_files': []
        }

        for file_info in self.long_files:
            priority = file_info.get('priority', 'low')
            file_plan = {
                'path': file_info['path'],
                'line_count': file_info['line_count'],
                'suggestions': file_info.get('split_suggestions', []),
                'classes': file_info.get('classes', []),
                'functions': file_info.get('functions', [])
            }

            if priority == 'critical':
                split_plan['critical_files'].append(file_plan)
            elif priority == 'high':
                split_plan['high_priority_files'].append(file_plan)
            elif priority == 'medium':
                split_plan['medium_priority_files'].append(file_plan)
            else:
                split_plan['low_priority_files'].append(file_plan)

        return split_plan

def main():
    """主函数"""
    print("🚀 Issue #87: 长文件分析")
    print("=" * 50)

    analyzer = LongFileAnalyzer(max_lines=100)

    # 分析长文件
    long_files = analyzer.find_long_files()

    if long_files:
        # 生成报告
        report = analyzer.generate_report()
        print(report)

        # 创建拆分计划
        split_plan = analyzer.create_split_plan()

        # 保存报告和计划
        with open('LONG_FILES_ANALYSIS_REPORT.md', 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n📄 报告已保存到: LONG_FILES_ANALYSIS_REPORT.md")

        # 显示优先级统计
        total_files = len(long_files)
        critical_files = len(split_plan['critical_files'])
        high_files = len(split_plan['high_priority_files'])

        print(f"\n🎯 拆分优先级:")
        print(f"   紧急拆分: {critical_files} 个文件")
        print(f"   高优先级: {high_files} 个文件")
        print(f"   总计: {total_files} 个文件需要处理")

        if critical_files > 0:
            print(f"\n⚠️ 建议优先处理紧急文件:")
            for file_plan in split_plan['critical_files']:
                print(f"   - {file_plan['path']} ({file_plan['line_count']} 行)")

    else:
        print("✅ 没有发现需要拆分的长文件！")

if __name__ == "__main__":
    main()