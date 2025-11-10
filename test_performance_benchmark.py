#!/usr/bin/env python3
"""
性能基准测试脚本
Performance Benchmark Testing Script

Author: Claude Code
Version: 1.0.0
"""

import os
import time
import json
import traceback
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta

def test_code_complexity_metrics():
    """测试代码复杂度指标"""
    print("📊 测试代码复杂度指标...")

    try:
        complexity_metrics = {
            'cyclomatic_complexity': 0,
            'cognitive_complexity': 0,
            'maintainability_index': 0,
            'technical_debt': 0
        }

        # 扫描Python文件计算复杂度指标
        total_files = 0
        total_functions = 0
        total_classes = 0
        total_lines = 0
        nested_blocks = 0

        for root, dirs, files in os.walk('src'):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    total_files += 1

                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                        total_lines += len(lines)

                        # 计算函数复杂度（简化版）
                        functions = content.count('def ')
                        total_functions += functions

                        # 计算类复杂度
                        classes = content.count('class ')
                        total_classes += classes

                        # 计算嵌套块深度（简化版）
                        indent_levels = []
                        for line in lines:
                            stripped = line.lstrip()
                            if stripped.startswith('def ') or stripped.startswith('class '):
                                indent_levels.append(len(line) - len(stripped))
                            elif stripped and line.startswith('    ') * len(indent_levels):
                                if len(line) - len(stripped) > indent_levels[-1]:
                                    nested_blocks += 1

        # 估算复杂度指标
        avg_functions_per_file = total_functions / total_files if total_files > 0 else 0
        avg_classes_per_file = total_classes / total_files if total_files > 0 else 0
        complexity_score = (nested_blocks / total_lines * 100) if total_lines > 0 else 0

        print(f"📈 复杂度指标:")
        print(f"   总文件数: {total_files}")
        print(f"   总函数数: {total_functions}")
        print(f"   总类数: {total_classes}")
        print(f"   总代码行数: {total_lines:,}")
        print(f"   平均函数/文件: {avg_functions_per_file:.1f}")
        print(f"   平均类/文件: {avg_classes_per_file:.1f}")
        print(f"   嵌套块比例: {complexity_score:.2f}%")

        # 评估复杂度等级
        if avg_functions_per_file < 5 and complexity_score < 15:
            print("✅ 代码复杂度: 优秀")
            complexity_metrics['cyclomatic_complexity'] = 5
        elif avg_functions_per_file < 10 and complexity_score < 25:
            print("⚠️ 代码复杂度: 良好")
            complexity_metrics['cyclomatic_complexity'] = 4
        else:
            print("❌ 代码复杂度: 需要改进")
            complexity_metrics['cyclomatic_complexity'] = 3

        return complexity_metrics

    except Exception as e:
        print(f"❌ 复杂度测试失败: {e}")
        return {}

def test_documentation_coverage():
    """测试文档覆盖率"""
    print("\n📚 测试文档覆盖率...")

    try:
        doc_coverage = {
            'api_docs': 0,
            'code_docs': 0,
            'sdk_docs': 0
        }

        # 检查API文档
        api_docs = ['docs/api_reference.md', 'docs/error_codes.md']
        for doc in api_docs:
            if os.path.exists(doc):
                doc_coverage['api_docs'] += 1

        # 检查代码文档
        total_py_files = 0
        documented_files = 0
        total_docstrings = 0

        for root, dirs, files in os.walk('src'):
            for file in files:
                if file.endswith('.py'):
                    total_py_files += 1
                    file_path = os.path.join(root, file)

                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        docstrings = content.count('"""')
                        total_docstrings += docstrings

                        if docstrings > 0:
                            documented_files += 1

        doc_coverage['code_docs'] = (documented_files / total_py_files * 100) if total_py_files > 0 else 0

        # 检查SDK文档
        sdk_docs = ['sdk/python/README.md', 'sdk/python/setup.py']
        for doc in sdk_docs:
            if os.path.exists(doc):
                doc_coverage['sdk_docs'] += 1

        print(f"📊 文档覆盖率:")
        print(f"   API文档: {doc_coverage['api_docs']}/{len(api_docs)}")
        print(f"   代码文档覆盖率: {doc_coverage['code_docs']:.1f}%")
        print(f"   SDK文档: {doc_coverage['sdk_docs']}/{len(sdk_docs)}")
        print(f"   总文档字符串: {total_docstrings}")

        # 计算总体覆盖率
        total_docs = doc_coverage['api_docs'] + (doc_coverage['code_docs'] / 100) + doc_coverage['sdk_docs']
        max_docs = len(api_docs) + 1 + len(sdk_docs)
        overall_coverage = (total_docs / max_docs) * 100

        print(f"   总体文档覆盖率: {overall_coverage:.1f}%")

        if overall_coverage >= 80:
            print("✅ 文档覆盖率: 优秀")
        elif overall_coverage >= 60:
            print("⚠️ 文档覆盖率: 良好")
        else:
            print("❌ 文档覆盖率: 需要改进")

        return overall_coverage

    except Exception as e:
        print(f"❌ 文档覆盖率测试失败: {e}")
        return 0

def test_modularity_metrics():
    """测试模块化指标"""
    print("\n🧩 测试模块化指标...")

    try:
        modularity_metrics = {
            'module_count': 0,
            'dependency_coupling': 0,
            'interface_segregation': 0,
            'single_responsibility': 0
        }

        # 统计模块数量
        modules = set()
        for root, dirs, files in os.walk('src'):
            if '__init__.py' in files:
                module_name = os.path.relpath(root, 'src').replace('/', '.')
                modules.add(module_name)

        modularity_metrics['module_count'] = len(modules)

        # 分析依赖关系（简化版）
        import_count = 0
        from_count = 0
        class_count = 0

        for root, dirs, files in os.walk('src'):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        import_count += content.count('import ')
                        from_count += content.count('from ')
                        class_count += content.count('class ')

        modularity_metrics['dependency_coupling'] = (import_count + from_count) / modularity_metrics['module_count'] if modularity_metrics['module_count'] > 0 else 0

        # 估算接口分离和单一职责
        avg_classes_per_module = class_count / modularity_metrics['module_count'] if modularity_metrics['module_count'] > 0 else 0
        if avg_classes_per_module <= 5:
            modularity_metrics['interface_segregation'] = 5
            modularity_metrics['single_responsibility'] = 5
        elif avg_classes_per_module <= 10:
            modularity_metrics['interface_segregation'] = 4
            modularity_modules['single_responsibility'] = 4
        else:
            modularity_metrics['interface_segregation'] = 3
            modularity_metrics['single_responsibility'] = 3

        print(f"🏗️ 模块化指标:")
        print(f"   模块数量: {modularity_metrics['module_count']}")
        print(f"   依赖耦合度: {modularity_metrics['dependency_coupling']:.1f}")
        print(f"   接口分离度: {modularity_metrics['interface_segregation']}/5")
        print(f"   单一职责度: {modularity_metrics['single_responsibility']}/5")
        print(f"   平均类/模块: {avg_classes_per_module:.1f}")

        return modularity_metrics

    except Exception as e:
        print(f"❌ 模块化测试失败: {e}")
        return {}

def test_reusability_metrics():
    """测试可重用性指标"""
    print("\n🔄 测试可重用性指标...")

    try:
        reusability_metrics = {
            'function_reuse': 0,
            'class_reuse': 0,
            'utility_functions': 0,
            'design_patterns': 0
        }

        # 统计函数和类的复用性
        function_names = {}
        class_names = {}
        utility_keywords = ['utils', 'helper', 'common', 'shared', 'base']

        for root, dirs, files in os.walk('src'):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                        # 统计函数名频率
                        import re
                        function_matches = re.findall(r'def\s+(\w+)', content)
                        for func_name in function_matches:
                            function_names[func_name] = function_names.get(func_name, 0) + 1

                        # 统计类名频率
                        class_matches = re.findall(r'class\s+(\w+)', content)
                        for class_name in class_matches:
                            class_names[class_name] = class_names.get(class_name, 0) + 1

                        # 检查工具函数
                        for keyword in utility_keywords:
                            if keyword in file_path.lower():
                                reusability_metrics['utility_functions'] += 1

        # 计算重用性指标
        if function_names:
            reused_functions = sum(1 for count in function_names.values() if count > 1)
            reusability_metrics['function_reuse'] = (reused_functions / len(function_names)) * 100

        if class_names:
            reused_classes = sum(1 for count in class_names.values() if count > 1)
            reusability_metrics['class_reuse'] = (reused_classes / len(class_names)) * 100

        # 检查设计模式
        design_patterns = [
            'Factory', 'Singleton', 'Observer', 'Strategy', 'Decorator',
            'Adapter', 'Proxy', 'Command', 'State', 'Builder'
        ]

        for pattern in design_patterns:
            if pattern.lower() in Path('src').read_text().lower():
                reusability_metrics['design_patterns'] += 1

        print(f"🔄 可重用性指标:")
        print(f"   函数重用率: {reusability_metrics['function_reuse']:.1f}%")
        print(f"   类重用率: {reusability_metrics['class_reuse']:.1f}%")
        print(f"   工具函数数量: {reusability_metrics['utility_functions']}")
        print(f"   设计模式数量: {reusability_metrics['design_patterns']}")

        return reusability_metrics

    except Exception as e:
        print(f"❌ 可重用性测试失败: {e}")
        return {}

def test_performance_characteristics():
    """测试性能特征"""
    print("\n⚡ 测试性能特征...")

    try:
        performance_characteristics = {
            'async_usage': 0,
            'caching': 0,
            'batch_processing': 0,
            'resource_optimization': 0
        }

        for root, dirs, files in os.walk('src'):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                        # 检查异步使用
                        if 'async ' in content or 'await ' in content:
                            performance_characteristics['async_usage'] += 1

                        # 检查缓存使用
                        cache_keywords = ['cache', 'Cache', 'cache_', 'cached', 'CacheMemory']
                        if any(keyword in content for keyword in cache_keywords):
                            performance_characteristics['caching'] += 1

                        # 检查批处理
                        batch_keywords = ['batch', 'Batch', 'bulk', 'Bulk', 'multiple']
                        if any(keyword in content for keyword in batch_keywords):
                            performance_characteristics['batch_processing'] += 1

                        # 检查资源优化
                        resource_keywords = ['pool', 'Pool', 'connection', 'Connection', 'memory', 'Memory']
                        if any(keyword in content for keyword in resource_keywords):
                            performance_characteristics['resource_optimization'] += 1

        print(f"⚡ 性能特征统计:")
        print(f"   异步使用: {performance_characteristics['async_usage']} 个文件")
        print(f"   缓存使用: {performance_characteristics['caching']} 个文件")
        print(f"   批处理: {performance_characteristics['batch_processing']} 个文件")
        print(f"   资源优化: {performance_characteristics['resource_optimization']} 个文件")

        total_features = sum(performance_characteristics.values())
        if total_features >= 50:
            print("✅ 性能特征: 优秀")
        elif total_features >= 30:
            print("⚠️ 性能特征: 良好")
        else:
            print("❌ 性能特征: 需要改进")

        return total_features

    except Exception as e:
        print(f"❌ 性能特征测试失败: {e}")
        return 0

def test_file_size_efficiency():
    """测试文件大小效率"""
    print("\n📁 测试文件大小效率...")

    try:
        size_metrics = {
            'large_files': 0,
            'average_size': 0,
            'size_distribution': {},
            'total_size': 0
        }

        file_sizes = []
        for root, dirs, files in os.walk('src'):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    size = os.path.getsize(file_path)
                    file_sizes.append(size)
                    size_metrics['total_size'] += size

                    # 统计大文件（>10KB）
                    if size > 10240:
                        size_metrics['large_files'] += 1

        if file_sizes:
            size_metrics['average_size'] = sum(file_sizes) / len(file_sizes)
            size_metrics['size_distribution'] = {
                'small (<1KB)': sum(1 for size in file_sizes if size < 1024),
                'medium (1-10KB)': sum(1 for size in file_sizes if 1024 <= size <= 10240),
                'large (>10KB)': sum(1 for size in file_sizes if size > 10240)
            }

        print(f"📊 文件大小统计:")
        print(f"   总文件数: {len(file_sizes)}")
        print(f"   总大小: {size_metrics['total_size']:,} 字节")
        print(f"   平均大小: {size_metrics['average_size']:.0f} 字节")
        print(f"   大文件数量: {size_metrics['large_files']}")

        print(f"📏 文件大小分布:")
        for category, count in size_metrics['size_distribution'].items():
            print(f"   {category}: {count} 个文件")

        # 评估效率
        if size_metrics['large_files'] / len(file_sizes) < 0.1:
            print("✅ 文件大小效率: 优秀")
        elif size_metrics['large_files'] / len(file_sizes) < 0.2:
            print("⚠️ 文件大小效率: 良好")
        else:
            print("❌ 文件大小效率: 需要改进")

        return size_metrics

    except Exception as e:
        print(f"❌ 文件大小测试失败: {e}")
        return {}

def calculate_overall_score():
    """计算总体分数"""
    print("\n🎯 计算总体性能分数...")

    scores = {}

    # 运行所有测试并收集分数
    try:
        complexity = test_code_complexity_metrics()
        if complexity:
            scores['complexity'] = complexity.get('cyclomatic_complexity', 0) * 20
    except:
        scores['complexity'] = 0

    try:
        doc_coverage = test_documentation_coverage()
        scores['documentation'] = doc_coverage * 15
    except:
        scores['documentation'] = 0

    try:
        modularity = test_modularity_metrics()
        if modularity:
            scores['modularity'] = (modularity.get('interface_segregation', 0) + modularity.get('single_responsibility', 0)) * 15
    except:
        scores['modularity'] = 0

    try:
        reusability = test_reusability_metrics()
        if reusability:
            scores['reusability'] = (reusability.get('function_reuse', 0) + reusability.get('class_reuse', 0)) * 20
    except:
        scores['reusability'] = 0

    try:
        performance = test_performance_characteristics()
        scores['performance'] = performance * 15
    except:
        scores['performance'] = 0

    try:
        size_efficiency = test_file_size_efficiency()
        if size_efficiency:
            efficiency_score = 5 if size_efficiency['large_files'] / len(file_sizes) < 0.1 else 3 if size_efficiency['large_files'] / len(file_sizes) < 0.2 else 1
            scores['efficiency'] = efficiency_score * 10
    except:
        scores['efficiency'] = 0

    # 计算总分
    total_score = sum(scores.values())
    max_score = 100

    print(f"📊 性能基准测试分数汇总:")
    for category, score in scores.items():
        print(f"   {category}: {score}/{max_score}")

    print(f"\n🎯 总体性能分数: {total_score}/{max_score}")

    if total_score >= 85:
        print("🎉 性能基准测试优秀！")
        grade = "A"
    elif total_score >= 70:
        print("⚠️ 性能基准测试良好")
        grade = "B"
    elif total_score >= 60:
        print("📈 性能基准测试合格")
        grade = "C"
    else:
        print("❌ 性能基准测试需要改进")
        grade = "D"

    return {
        'total_score': total_score,
        'max_score': max_score,
        'grade': grade,
        'breakdown': scores
    }

def main():
    """主测试函数"""
    print("🚀 性能基准测试开始")
    print("=" * 60)

    # 计算总体分数
    result = calculate_overall_score()

    return result

if __name__ == "__main__":
    result = main()

    # 将结果保存到文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"performance_benchmark_report_{timestamp}.json"

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, default=str)

    print(f"\n📄 详细报告已保存: {report_path}")
    exit(0 if result['grade'] in ['A', 'B'] else 1)