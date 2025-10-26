#!/usr/bin/env python3
"""
Issue #83-C 覆盖率瓶颈分析工具
分析当前覆盖率瓶颈，识别低覆盖率模块，制定深度测试策略
"""

import os
import ast
from pathlib import Path
from typing import Dict, List, Tuple, Any
import subprocess
import re


class CoverageBottleneckAnalyzer:
    """覆盖率瓶颈分析器"""

    def __init__(self):
        self.src_path = Path("src")
        self.test_path = Path("tests")
        self.coverage_data = {}

    def analyze_source_files(self) -> Dict[str, Dict]:
        """分析源代码文件，提取函数和类信息"""
        print("🔍 分析源代码文件...")

        source_info = {}

        # 遍历src目录
        for src_file in self.src_path.rglob("*.py"):
            if src_file.name == "__init__.py":
                continue

            try:
                with open(src_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 解析AST
                tree = ast.parse(content)

                # 统计信息
                functions = []
                classes = []
                imports = []

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        functions.append({
                            'name': node.name,
                            'lineno': node.lineno,
                            'args': len(node.args.args)
                        })
                    elif isinstance(node, ast.ClassDef):
                        classes.append({
                            'name': node.name,
                            'lineno': node.lineno,
                            'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                        })
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        for alias in node.names:
                            imports.append(f"{module}.{alias.name}")

                # 计算代码行数
                lines = content.split('\n')
                code_lines = len([line for line in lines if line.strip() and not line.strip().startswith('#')])

                # 生成相对路径作为模块名
                module_name = str(src_file.relative_to(self.src_path)).replace('/', '.').replace('.py', '')

                source_info[module_name] = {
                    'file_path': str(src_file),
                    'functions': functions,
                    'classes': classes,
                    'imports': imports,
                    'code_lines': code_lines,
                    'total_lines': len(lines)
                }

            except Exception as e:
                print(f"   ⚠️ 分析文件失败 {src_file}: {e}")

        print(f"✅ 分析完成: {len(source_info)} 个源文件")
        return source_info

    def analyze_existing_tests(self) -> Dict[str, List[str]]:
        """分析现有测试文件"""
        print("🔍 分析现有测试文件...")

        test_coverage = {}

        # 遍历tests目录
        for test_file in self.test_path.rglob("*.py"):
            if not test_file.name.startswith(("test_", "test")):
                continue

            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 提取导入的模块
                imports = []
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        for alias in node.names:
                            if alias.name == "*":
                                # 对于import *，尝试从文件路径推断
                                rel_path = test_file.relative_to(self.test_path)
                                # 简化：假设测试文件对应的源模块
                                parts = str(rel_path).split('/')
                                if len(parts) >= 2:
                                    inferred_module = f"{parts[1]}.{parts[0].replace('test_', '').replace('_test', '')}"
                                    imports.append(inferred_module)
                            else:
                                imports.append(f"{module}.{alias.name}")

                # 统计测试函数和类
                test_functions = []
                test_classes = []

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                        test_functions.append(node.name)
                    elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                        test_classes.append(node.name)

                # 生成对应的源模块
                test_path_parts = test_file.relative_to(self.test_path).parts
                if len(test_path_parts) >= 2:
                    # 例如: tests/unit/core/di_test.py -> core.di
                    source_module = f"{test_path_parts[1]}.{test_path_parts[2].replace('test_', '').replace('_test', '')}"

                    if source_module not in test_coverage:
                        test_coverage[source_module] = []

                    test_coverage[source_module].append({
                        'test_file': str(test_file),
                        'test_functions': test_functions,
                        'test_classes': test_classes,
                        'imports': imports
                    })

            except Exception as e:
                print(f"   ⚠️ 分析测试文件失败 {test_file}: {e}")

        print(f"✅ 分析完成: {len(test_coverage)} 个模块有测试覆盖")
        return test_coverage

    def identify_low_coverage_modules(self, source_info: Dict, test_coverage: Dict) -> List[Dict]:
        """识别低覆盖率模块"""
        print("🔍 识别低覆盖率模块...")

        low_coverage_modules = []

        for module_name, module_info in source_info.items():
            has_tests = module_name in test_coverage
            test_count = 0

            if has_tests:
                for test_info in test_coverage[module_name]:
                    test_count += len(test_info['test_functions'])
                    test_count += len(test_info['test_classes'])

            # 计算测试密度
            code_complexity = len(module_info['functions']) + len(module_info['classes'])
            test_density = test_count / max(code_complexity, 1)

            # 评估覆盖率等级
            if not has_tests:
                coverage_level = "无测试"
                priority = "HIGH"
            elif test_density < 0.5:
                coverage_level = "低覆盖"
                priority = "HIGH"
            elif test_density < 1.0:
                coverage_level = "中覆盖"
                priority = "MEDIUM"
            else:
                coverage_level = "高覆盖"
                priority = "LOW"

            # 特别关注业务逻辑模块
            business_modules = [
                'domain', 'services', 'api', 'database', 'cqrs'
            ]
            is_business = any(bm in module_name for bm in business_modules)

            if is_business and priority in ["HIGH", "MEDIUM"]:
                low_coverage_modules.append({
                    'module': module_name,
                    'file_path': module_info['file_path'],
                    'functions_count': len(module_info['functions']),
                    'classes_count': len(module_info['classes']),
                    'code_lines': module_info['code_lines'],
                    'has_tests': has_tests,
                    'test_count': test_count,
                    'test_density': test_density,
                    'coverage_level': coverage_level,
                    'priority': priority,
                    'is_business': is_business,
                    'imports': module_info['imports']
                })

        # 按优先级和代码行数排序
        priority_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        low_coverage_modules.sort(key=lambda x: (priority_order[x['priority']], -x['code_lines']))

        print(f"✅ 识别完成: {len(low_coverage_modules)} 个低覆盖率模块")
        return low_coverage_modules

    def generate_deep_test_strategy(self, low_coverage_modules: List[Dict]) -> Dict[str, Any]:
        """生成深度测试策略"""
        print("🎯 生成深度测试策略...")

        strategy = {
            'high_priority_modules': [],
            'medium_priority_modules': [],
            'test_categories': {},
            'recommended_approaches': [],
            'implementation_plan': []
        }

        for module_info in low_coverage_modules:
            module_name = module_info['module']

            if module_info['priority'] == 'HIGH':
                strategy['high_priority_modules'].append(module_info)
            elif module_info['priority'] == 'MEDIUM':
                strategy['medium_priority_modules'].append(module_info)

            # 确定测试类别
            category = module_name.split('.')[0]
            if category not in strategy['test_categories']:
                strategy['test_categories'][category] = []
            strategy['test_categories'][category].append(module_info)

        # 生成推荐方法
        strategy['recommended_approaches'] = [
            "数据驱动测试 - 使用真实数据场景",
            "业务流程测试 - 测试完整的业务流程",
            "边界条件测试 - 测试边界和异常情况",
            "集成测试 - 测试模块间的交互",
            "性能测试 - 测试关键路径性能"
        ]

        # 生成实施计划
        strategy['implementation_plan'] = [
            {
                'phase': 'Phase 1: 数据驱动测试',
                'modules': strategy['high_priority_modules'][:5],
                'focus': '使用真实数据场景提升覆盖率'
            },
            {
                'phase': 'Phase 2: 业务流程测试',
                'modules': strategy['high_priority_modules'][5:] + strategy['medium_priority_modules'][:3],
                'focus': '测试完整的业务流程'
            },
            {
                'phase': 'Phase 3: 集成和性能测试',
                'modules': strategy['medium_priority_modules'][3:],
                'focus': '端到端测试和性能测试'
            }
        ]

        print("✅ 策略生成完成:")
        print(f"   高优先级模块: {len(strategy['high_priority_modules'])}")
        print(f"   中优先级模块: {len(strategy['medium_priority_modules'])}")
        print(f"   测试类别: {len(strategy['test_categories'])}")

        return strategy

    def run_coverage_analysis(self) -> Dict[str, Any]:
        """运行完整的覆盖率分析"""
        print("🚀 Issue #83-C 覆盖率瓶颈分析")
        print("=" * 60)

        # 1. 分析源代码文件
        source_info = self.analyze_source_files()

        # 2. 分析现有测试文件
        test_coverage = self.analyze_existing_tests()

        # 3. 识别低覆盖率模块
        low_coverage_modules = self.identify_low_coverage_modules(source_info, test_coverage)

        # 4. 生成深度测试策略
        strategy = self.generate_deep_test_strategy(low_coverage_modules)

        print("=" * 60)
        print("📊 分析总结:")
        print(f"   源代码文件: {len(source_info)}")
        print(f"   有测试的模块: {len(test_coverage)}")
        print(f"   低覆盖率模块: {len(low_coverage_modules)}")
        print(f"   高优先级模块: {len(strategy['high_priority_modules'])}")

        return {
            'source_info': source_info,
            'test_coverage': test_coverage,
            'low_coverage_modules': low_coverage_modules,
            'strategy': strategy
        }

    def save_analysis_report(self, analysis_result: Dict[str, Any], output_file: str = "coverage_analysis_report.json"):
        """保存分析报告"""
        import json

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)

        print(f"📋 分析报告已保存: {output_file}")

    def print_top_modules(self, low_coverage_modules: List[Dict], limit: int = 10):
        """打印最重要的低覆盖率模块"""
        print(f"\n🎯 优先处理的前{limit}个模块:")
        print("-" * 80)

        for i, module in enumerate(low_coverage_modules[:limit]):
            print(f"{i+1:2d}. {module['module']}")
            print(f"     文件: {module['file_path']}")
            print(f"     代码行数: {module['code_lines']} | 函数: {module['functions_count']} | 类: {module['classes_count']}")
            print(f"     测试数量: {module['test_count']} | 覆盖级别: {module['coverage_level']}")
            print(f"     优先级: {module['priority']} | 业务模块: {'是' if module['is_business'] else '否'}")
            print()


def main():
    """主函数"""
    analyzer = CoverageBottleneckAnalyzer()

    # 运行分析
    analysis_result = analyzer.run_coverage_analysis()

    # 打印重点模块
    analyzer.print_top_modules(analysis_result['low_coverage_modules'])

    # 保存分析报告
    analyzer.save_analysis_report(analysis_result)

    return analysis_result


if __name__ == "__main__":
    result = main()