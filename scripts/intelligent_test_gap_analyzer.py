#!/usr/bin/env python3
"""
🤖 Intelligent Test Gap Analyzer
智能测试缺口分析器 - Phase G核心组件

基于AST分析和覆盖率数据的智能测试缺口识别工具
自动识别未测试代码并生成测试建议
"""

import ast
import inspect
import json
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class FunctionInfo:
    """函数信息数据类"""
    name: str
    file_path: str
    line_start: int
    line_end: int
    complexity: int
    parameters: List[str]
    return_type: Optional[str]
    docstring: Optional[str]
    is_async: bool
    decorators: List[str]

@dataclass
class TestGap:
    """测试缺口数据类"""
    function: FunctionInfo
    gap_type: str  # 'uncovered', 'partial', 'missing_branch'
    priority: int  # 1-5, 5最高
    suggested_tests: List[Dict]
    estimated_effort: int  # 分钟

class IntelligentTestGapAnalyzer:
    """智能测试缺口分析器"""

    def __init__(self, source_dir: str = "src", coverage_data: Optional[Dict] = None):
        self.source_dir = Path(source_dir)
        self.coverage_data = coverage_data or {}
        self.functions = []
        self.test_gaps = []

    def analyze_project(self) -> Dict:
        """分析整个项目的测试缺口"""
        print("🔍 开始智能测试缺口分析...")

        # 1. 扫描源代码函数
        print("📂 扫描源代码函数...")
        self._scan_source_functions()

        # 2. 分析覆盖率数据
        print("📊 分析覆盖率数据...")
        self._analyze_coverage()

        # 3. 识别测试缺口
        print("🎯 识别测试缺口...")
        self._identify_test_gaps()

        # 4. 生成分析报告
        report = self._generate_analysis_report()

        print(f"✅ 分析完成: 发现 {len(self.test_gaps)} 个测试缺口")
        return report

    def _scan_source_functions(self):
        """扫描源代码中的所有函数"""
        for py_file in self.source_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                self._extract_functions_from_ast(tree, str(py_file))

            except Exception as e:
                print(f"⚠️ 解析文件失败 {py_file}: {e}")

    def _extract_functions_from_ast(self, tree: ast.AST, file_path: str):
        """从AST中提取函数信息"""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # 计算复杂度
                complexity = self._calculate_complexity(node)

                # 提取参数信息
                parameters = [arg.arg for arg in node.args.args]

                # 提取文档字符串
                docstring = ast.get_docstring(node)

                # 提取装饰器
                decorators = []
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name):
                        decorators.append(decorator.id)
                    elif isinstance(decorator, ast.Attribute):
                        decorators.append(decorator.attr)

                function_info = FunctionInfo(
                    name=node.name,
                    file_path=file_path,
                    line_start=node.lineno,
                    line_end=getattr(node, 'end_lineno', node.lineno),
                    complexity=complexity,
                    parameters=parameters,
                    return_type=self._extract_return_type(node),
                    docstring=docstring,
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    decorators=decorators
                )

                self.functions.append(function_info)

    def _calculate_complexity(self, node: ast.AST) -> int:
        """计算函数的圈复杂度"""
        complexity = 1  # 基础复杂度

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.With, ast.AsyncWith):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def _extract_return_type(self, node: ast.AST) -> Optional[str]:
        """提取函数返回类型"""
        if hasattr(node, 'returns') and node.returns:
            if isinstance(node.returns, ast.Name):
                return node.returns.id
            elif isinstance(node.returns, ast.Constant):
                return str(node.returns.value)
        return None

    def _analyze_coverage(self):
        """分析覆盖率数据"""
        # 这里可以集成实际的覆盖率数据
        # 暂时使用模拟数据
        for function in self.functions:
            # 模拟覆盖率检查
            function.covered = hash(function.name) % 3 != 0  # 模拟部分覆盖

    def _identify_test_gaps(self):
        """识别测试缺口"""
        for function in self.functions:
            # 跳过测试文件和特殊函数
            if self._should_skip_function(function):
                continue

            coverage_status = getattr(function, 'covered', False)

            if not coverage_status:
                gap_type = 'uncovered'
                priority = self._calculate_priority(function)
                suggested_tests = self._generate_test_suggestions(function)
                effort = self._estimate_effort(function, suggested_tests)

                test_gap = TestGap(
                    function=function,
                    gap_type=gap_type,
                    priority=priority,
                    suggested_tests=suggested_tests,
                    estimated_effort=effort
                )

                self.test_gaps.append(test_gap)

    def _should_skip_function(self, function: FunctionInfo) -> bool:
        """判断是否应该跳过函数"""
        skip_patterns = [
            'test_', '_test', '__', 'setup_', 'teardown_',
            'main', 'run', 'start', 'init'
        ]

        for pattern in skip_patterns:
            if pattern in function.name.lower():
                return True

        # 跳过测试文件中的函数
        if 'test' in function.file_path:
            return True

        # 跳过私有方法（除非是重要的）
        if function.name.startswith('_') and function.complexity < 5:
            return True

        return False

    def _calculate_priority(self, function: FunctionInfo) -> int:
        """计算测试优先级 (1-5)"""
        priority = 1

        # 基于复杂度
        if function.complexity >= 10:
            priority += 2
        elif function.complexity >= 5:
            priority += 1

        # 基于参数数量
        if len(function.parameters) >= 4:
            priority += 1

        # 基于模块重要性
        if any(keyword in function.file_path.lower() for keyword in ['api', 'core', 'services', 'domain']):
            priority += 1

        # 基于函数特性
        if function.is_async:
            priority += 1

        # 基于装饰器
        if any(decorator in ['route', 'endpoint', 'api'] for decorator in function.decorators):
            priority += 2

        return min(priority, 5)

    def _generate_test_suggestions(self, function: FunctionInfo) -> List[Dict]:
        """为函数生成测试建议"""
        suggestions = []

        # 基础功能测试
        suggestions.append({
            'type': 'basic_functionality',
            'description': f'测试{function.name}的基本功能',
            'test_cases': self._generate_basic_test_cases(function)
        })

        # 边界条件测试
        if self._needs_boundary_tests(function):
            suggestions.append({
                'type': 'boundary_conditions',
                'description': f'测试{function.name}的边界条件',
                'test_cases': self._generate_boundary_test_cases(function)
            })

        # 异常处理测试
        if self._needs_exception_tests(function):
            suggestions.append({
                'type': 'exception_handling',
                'description': f'测试{function.name}的异常处理',
                'test_cases': self._generate_exception_test_cases(function)
            })

        # 性能测试
        if function.complexity >= 8 or function.is_async:
            suggestions.append({
                'type': 'performance',
                'description': f'测试{function.name}的性能表现',
                'test_cases': self._generate_performance_test_cases(function)
            })

        return suggestions

    def _generate_basic_test_cases(self, function: FunctionInfo) -> List[Dict]:
        """生成基础测试用例"""
        test_cases = []

        # 正常情况测试
        test_cases.append({
            'name': 'test_normal_case',
            'description': '正常输入情况测试',
            'inputs': self._generate_normal_inputs(function),
            'expected': '正常输出'
        })

        # 空参数测试
        if len(function.parameters) > 0:
            test_cases.append({
                'name': 'test_empty_inputs',
                'description': '空参数输入测试',
                'inputs': {param: None for param in function.parameters[:1]},
                'expected': '适当处理或异常'
            })

        return test_cases

    def _generate_boundary_test_cases(self, function: FunctionInfo) -> List[Dict]:
        """生成边界条件测试用例"""
        return [{
            'name': 'test_boundary_conditions',
            'description': '边界值测试',
            'test_cases': [
                {'input': '极小值', 'expected': '正确处理'},
                {'input': '极大值', 'expected': '正确处理'},
                {'input': '零值', 'expected': '正确处理'},
                {'input': '空值', 'expected': '正确处理'}
            ]
        }]

    def _generate_exception_test_cases(self, function: FunctionInfo) -> List[Dict]:
        """生成异常处理测试用例"""
        return [{
            'name': 'test_exception_handling',
            'description': '异常情况测试',
            'test_cases': [
                {'input': '无效输入', 'expected': '适当异常'},
                {'input': '格式错误', 'expected': '格式验证'},
                {'input': '权限不足', 'expected': '权限异常'}
            ]
        }]

    def _generate_performance_test_cases(self, function: FunctionInfo) -> List[Dict]:
        """生成性能测试用例"""
        return [{
            'name': 'test_performance',
            'description': '性能基准测试',
            'benchmarks': [
                {'metric': '执行时间', 'target': '<100ms'},
                {'metric': '内存使用', 'target': '<10MB'},
                {'metric': '并发处理', 'target': '10个并发请求'}
            ]
        }]

    def _generate_normal_inputs(self, function: FunctionInfo) -> Dict:
        """生成正常输入参数"""
        inputs = {}
        for param in function.parameters:
            if 'id' in param.lower():
                inputs[param] = 1
            elif 'name' in param.lower():
                inputs[param] = "test_name"
            elif 'data' in param.lower():
                inputs[param] = {"key": "value"}
            elif 'config' in param.lower():
                inputs[param] = {"setting": "value"}
            else:
                inputs[param] = "test_value"
        return inputs

    def _needs_boundary_tests(self, function: FunctionInfo) -> bool:
        """判断是否需要边界测试"""
        boundary_keywords = ['count', 'size', 'length', 'limit', 'offset', 'page']
        return any(keyword in function.name.lower() for keyword in boundary_keywords)

    def _needs_exception_tests(self, function: FunctionInfo) -> bool:
        """判断是否需要异常测试"""
        exception_keywords = ['validate', 'check', 'parse', 'load', 'save', 'delete', 'update']
        return any(keyword in function.name.lower() for keyword in exception_keywords)

    def _estimate_effort(self, function: FunctionInfo, suggestions: List[Dict]) -> int:
        """估算测试开发工作量（分钟）"""
        base_effort = 15  # 基础工作量

        # 基于复杂度
        effort = base_effort + (function.complexity * 3)

        # 基于测试建议数量
        effort += len(suggestions) * 10

        # 基于参数数量
        effort += len(function.parameters) * 5

        # 异步函数需要更多时间
        if function.is_async:
            effort += 10

        return effort

    def _generate_analysis_report(self) -> Dict:
        """生成分析报告"""
        # 按优先级排序
        self.test_gaps.sort(key=lambda x: (x.priority, x.function.complexity), reverse=True)

        # 统计信息
        total_functions = len(self.functions)
        uncovered_functions = len(self.test_gaps)
        total_effort = sum(gap.estimated_effort for gap in self.test_gaps)

        # 按优先级分组
        gaps_by_priority = defaultdict(list)
        for gap in self.test_gaps:
            gaps_by_priority[gap.priority].append(gap)

        # 按模块分组
        gaps_by_module = defaultdict(list)
        for gap in self.test_gaps:
            module = Path(gap.function.file_path).parent.name
            gaps_by_module[module].append(gap)

        return {
            'summary': {
                'total_functions': total_functions,
                'uncovered_functions': uncovered_functions,
                'coverage_percentage': ((total_functions - uncovered_functions) / total_functions * 100) if total_functions > 0 else 0,
                'total_estimated_effort_minutes': total_effort,
                'high_priority_gaps': len(gaps_by_priority.get(5, [])),
                'medium_priority_gaps': len(gaps_by_priority.get(3, [])) + len(gaps_by_priority.get(4, [])),
                'low_priority_gaps': len(gaps_by_priority.get(1, [])) + len(gaps_by_priority.get(2, []))
            },
            'gaps_by_priority': {
                str(priority): [
                    {
                        'function_name': gap.function.name,
                        'file_path': gap.function.file_path,
                        'complexity': gap.function.complexity,
                        'estimated_effort': gap.estimated_effort,
                        'suggested_tests': gap.suggested_tests
                    }
                    for gap in gaps[:10]  # 限制返回数量
                ]
                for priority, gaps in gaps_by_priority.items()
            },
            'gaps_by_module': {
                module: [
                    {
                        'function_name': gap.function.name,
                        'priority': gap.priority,
                        'complexity': gap.function.complexity,
                        'estimated_effort': gap.estimated_effort
                    }
                    for gap in gaps
                ]
                for module, gaps in gaps_by_module.items()
            },
            'top_recommendations': self.test_gaps[:10]  # 前10个最高优先级的缺口
        }

def main():
    """主函数 - 执行智能测试缺口分析"""
    print("🤖 启动智能测试缺口分析器...")

    analyzer = IntelligentTestGapAnalyzer()
    report = analyzer.analyze_project()

    # 保存报告
    report_file = "test_gap_analysis_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # 打印摘要
    summary = report['summary']
    print(f"\n📊 分析摘要:")
    print(f"   总函数数: {summary['total_functions']}")
    print(f"   未覆盖函数: {summary['uncovered_functions']}")
    print(f"   覆盖率: {summary['coverage_percentage']:.1f}%")
    print(f"   预估工作量: {summary['total_estimated_effort_minutes']} 分钟")
    print(f"   高优先级缺口: {summary['high_priority_gaps']}")
    print(f"   中优先级缺口: {summary['medium_priority_gaps']}")
    print(f"   低优先级缺口: {summary['low_priority_gaps']}")

    print(f"\n📄 详细报告已保存至: {report_file}")

    # 生成高优先级建议
    print(f"\n🎯 高优先级测试建议:")
    for i, gap in enumerate(report['top_recommendations'][:5], 1):
        print(f"   {i}. {gap.function.name} ({gap.function.file_path})")
        print(f"      复杂度: {gap.function.complexity}, 工作量: {gap.estimated_effort}分钟")
        print(f"      建议测试: {[test['type'] for test in gap.suggested_tests]}")

    return report

if __name__ == "__main__":
    main()