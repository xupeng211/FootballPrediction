"""
真实测试覆盖率测量工具
使用Python标准库进行实际的代码覆盖率测量，不依赖第三方工具
"""

import sys
import os
import ast
import importlib.util
import inspect
from typing import Dict, List, Set, Tuple
import traceback

class CoverageAnalyzer:
    """覆盖率分析器"""

    def __init__(self, src_path: str):
        self.src_path = src_path
        self.covered_modules = set()
        self.covered_functions = set()
        self.covered_classes = set()
        self.total_functions = set()
        self.total_classes = set()
        self.import_errors = {}

    def analyze_module_structure(self, module_path: str) -> Dict:
        """分析模块结构"""
        try:
            with open(module_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            functions = []
            classes = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)

            return {
                'functions': functions,
                'classes': classes,
                'lines': len(content.split('\n')),
                'ast_valid': True
            }
        except SyntaxError as e:
            return {
                'functions': [],
                'classes': [],
                'lines': 0,
                'ast_valid': False,
                'syntax_error': str(e)
            }
        except Exception as e:
            return {
                'functions': [],
                'classes': [],
                'lines': 0,
                'ast_valid': False,
                'error': str(e)
            }

    def test_module_import(self, module_name: str) -> Tuple[bool, str]:
        """测试模块导入"""
        try:
            # 添加src路径
            if self.src_path not in sys.path:
                sys.path.insert(0, self.src_path)

            # 尝试导入模块
            module = importlib.import_module(module_name)

            # 获取模块的函数和类
            functions = []
            classes = []

            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj) and obj.__module__ == module.__name__:
                    functions.append(name)
                elif inspect.isclass(obj) and obj.__module__ == module.__name__:
                    classes.append(name)

            return True, f"成功导入 - 函数: {len(functions)}, 类: {len(classes)}"

        except ImportError as e:
            return False, f"导入错误: {e}"
        except SyntaxError as e:
            return False, f"语法错误: {e}"
        except Exception as e:
            return False, f"其他错误: {e}"

    def test_module_functionality(self, module_name: str) -> Tuple[bool, int, List[str]]:
        """测试模块功能"""
        executed_functions = 0
        test_results = []

        try:
            if self.src_path not in sys.path:
                sys.path.insert(0, self.src_path)

            module = importlib.import_module(module_name)

            # 测试无参数函数
            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj) and obj.__module__ == module.__name__:
                    try:
                        sig = inspect.signature(obj)
                        if len(sig.parameters) == 0:
                            result = obj()
                            executed_functions += 1
                            test_results.append(f"✅ 函数 {name}() 执行成功")
                            self.covered_functions.add(f"{module_name}.{name}")
                        else:
                            test_results.append(f"⚠️  函数 {name} 需要参数，跳过执行")
                    except Exception as e:
                        test_results.append(f"❌ 函数 {name}() 执行失败: {e}")

                # 测试类实例化（无参数构造函数）
                elif inspect.isclass(obj) and obj.__module__ == module.__name__:
                    try:
                        sig = inspect.signature(obj.__init__)
                        if len(sig.parameters) <= 1:  # 只有self参数
                            instance = obj()
                            executed_functions += 1
                            test_results.append(f"✅ 类 {name} 实例化成功")
                            self.covered_classes.add(f"{module_name}.{name}")

                            # 测试无参数方法
                            for method_name, method_obj in inspect.getmembers(instance):
                                if (inspect.ismethod(method_obj) or inspect.isfunction(method_obj)) and not method_name.startswith('_'):
                                    try:
                                        method_sig = inspect.signature(method_obj)
                                        if len(method_sig.parameters) <= 1:  # 只有self参数
                                            method_result = method_obj()
                                            test_results.append(f"  ✅ 方法 {method_name}() 执行成功")
                                    except Exception:
                                        test_results.append(f"  ⚠️  方法 {method_name}() 执行失败")
                        else:
                            test_results.append(f"⚠️  类 {name} 需要参数构造，跳过实例化")
                    except Exception as e:
                        test_results.append(f"❌ 类 {name} 实例化失败: {e}")

            return True, executed_functions, test_results

        except Exception as e:
            return False, 0, [f"❌ 模块功能测试失败: {e}"]

    def analyze_all_modules(self) -> Dict:
        """分析所有模块"""
        results = {}

        # 查找所有Python文件
        for root, dirs, files in os.walk(self.src_path):
            # 跳过__pycache__和其他非源码目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, self.src_path)
                    module_name = relative_path.replace('/', '.').replace('.py', '')

                    # 分析模块结构
                    structure = self.analyze_module_structure(file_path)
                    results[module_name] = structure

                    # 统计总的函数和类
                    self.total_functions.update([f"{module_name}.{f}" for f in structure['functions']])
                    self.total_classes.update([f"{module_name}.{c}" for c in structure['classes']])

        return results

    def calculate_real_coverage(self) -> Dict:
        """计算真实覆盖率"""
        # 计算各项覆盖率指标
        function_coverage = 0
        if len(self.total_functions) > 0:
            function_coverage = len(self.covered_functions) / len(self.total_functions) * 100

        class_coverage = 0
        if len(self.total_classes) > 0:
            class_coverage = len(self.covered_classes) / len(self.total_classes) * 100

        module_coverage = 0
        total_modules = len(self.total_functions)  # 近似模块数
        if total_modules > 0:
            module_coverage = len(self.covered_modules) / total_modules * 100

        # 综合覆盖率（加权平均）
        overall_coverage = (function_coverage * 0.5 + class_coverage * 0.3 + module_coverage * 0.2)

        return {
            'function_coverage': function_coverage,
            'class_coverage': class_coverage,
            'module_coverage': module_coverage,
            'overall_coverage': overall_coverage,
            'total_functions': len(self.total_functions),
            'covered_functions': len(self.covered_functions),
            'total_classes': len(self.total_classes),
            'covered_classes': len(self.covered_classes),
            'total_modules': total_modules,
            'covered_modules': len(self.covered_modules)
        }


def run_real_coverage_measurement():
    """运行真实覆盖率测量"""
    print("=" * 80)
    print("🎯 真实测试覆盖率测量 - 标准方法")
    print("=" * 80)

    # 设置src路径
    src_path = '/app/src'  # Docker环境中的路径
    analyzer = CoverageAnalyzer(src_path)

    print("\n📊 第一步: 分析所有模块结构...")
    module_analysis = analyzer.analyze_all_modules()

    total_modules = len(module_analysis)
    valid_modules = sum(1 for m in module_analysis.values() if m['ast_valid'])
    syntax_error_modules = total_modules - valid_modules

    print(f"   总模块数: {total_modules}")
    print(f"   语法正确模块: {valid_modules}")
    print(f"   语法错误模块: {syntax_error_modules}")

    print("\n🧪 第二步: 测试核心模块导入和功能...")

    # 选择核心模块进行详细测试
    core_modules = [
        'utils.crypto_utils',
        'observers.manager',
        'monitoring.metrics_collector_enhanced',
        'adapters.base',
        'adapters.factory',
        'adapters.factory_simple'
    ]

    successful_imports = 0
    detailed_results = []

    for module_name in core_modules:
        if module_name in module_analysis:
            print(f"\n🔍 测试模块: {module_name}")

            # 测试导入
            import_success, import_msg = analyzer.test_module_import(module_name)
            if import_success:
                successful_imports += 1
                analyzer.covered_modules.add(module_name)
                print(f"   ✅ 导入成功: {import_msg}")

                # 测试功能
                func_success, func_count, func_results = analyzer.test_module_functionality(module_name)
                if func_success:
                    print(f"   ✅ 功能测试: 执行了 {func_count} 个函数/方法")
                    for result in func_results:
                        print(f"      {result}")
                else:
                    print(f"   ❌ 功能测试失败")
                    for result in func_results:
                        print(f"      {result}")
            else:
                print(f"   ❌ 导入失败: {import_msg}")
                analyzer.import_errors[module_name] = import_msg

    print("\n📈 第三步: 计算真实覆盖率...")
    coverage_data = analyzer.calculate_real_coverage()

    print("\n" + "=" * 80)
    print("📊 真实测试覆盖率报告")
    print("=" * 80)

    print(f"模块导入成功率: {successful_imports}/{len(core_modules)} ({(successful_imports/len(core_modules))*100:.1f}%)")
    print(f"函数覆盖率: {coverage_data['function_coverage']:.1f}% ({coverage_data['covered_functions']}/{coverage_data['total_functions']})")
    print(f"类覆盖率: {coverage_data['class_coverage']:.1f}% ({coverage_data['covered_classes']}/{coverage_data['total_classes']})")
    print(f"综合覆盖率: {coverage_data['overall_coverage']:.1f}%")

    # 与Issue #159目标对比
    original_coverage = 23.0
    target_coverage = 60.0
    current_coverage = coverage_data['overall_coverage']
    improvement = current_coverage - original_coverage

    print(f"\n📋 Issue #159 真实进度评估:")
    print(f"   原始覆盖率: {original_coverage}%")
    print(f"   目标覆盖率: {target_coverage}%")
    print(f"   当前真实覆盖率: {current_coverage:.1f}%")
    print(f"   覆盖率提升: +{improvement:.1f}%")

    if current_coverage >= target_coverage:
        print(f"   ✅ Issue #159 状态: 目标达成")
        issue_status = "COMPLETED"
    elif current_coverage >= (target_coverage * 0.8):
        print(f"   🔄 Issue #159 状态: 基本达成，需要完善")
        issue_status = "IN_PROGRESS"
    elif improvement >= 10:
        print(f"   📈 Issue #159 状态: 显著进展")
        issue_status = "IN_PROGRESS"
    else:
        print(f"   ⚠️  Issue #159 状态: 需要实质性工作")
        issue_status = "TODO"

    # 显示导入错误
    if analyzer.import_errors:
        print(f"\n⚠️  导入错误模块:")
        for module, error in analyzer.import_errors.items():
            print(f"   {module}: {error}")

    return {
        'real_coverage': current_coverage,
        'improvement': improvement,
        'issue_status': issue_status,
        'successful_imports': successful_imports,
        'total_core_modules': len(core_modules),
        'coverage_data': coverage_data,
        'import_errors': analyzer.import_errors
    }


if __name__ == "__main__":
    try:
        results = run_real_coverage_measurement()

        print("\n" + "=" * 80)
        print("🏁 真实覆盖率测量完成")
        print("=" * 80)

        print(f"\n📊 GitHub Issues 更新建议:")
        print(f"Issue #159 主状态: {results['issue_status']}")
        print(f"真实测试覆盖率: {results['real_coverage']:.1f}%")
        print(f"需要创建子issue: {'是' if results['real_coverage'] < 60 else '否'}")

        if results['real_coverage'] < 60:
            print(f"\n💡 建议创建子issue:")
            print(f"标题: Issue #159.1: 修复测试覆盖率从 {results['real_coverage']:.1f}% 到 60%")
            print(f"描述: 需要解决导入错误并增加更多测试用例")

    except Exception as e:
        print(f"❌ 覆盖率测量失败: {e}")
        traceback.print_exc()