#!/usr/bin/env python3
"""
🤖 Auto Test Generator
自动化测试生成器 - Phase G核心组件

基于智能分析的测试缺口，自动生成高质量的测试代码
支持边界条件、异常处理、性能测试等多种测试类型
"""

import ast
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from jinja2 import Template

@dataclass
class TestGenerationConfig:
    """测试生成配置"""
    output_dir: str = "tests/generated"
    template_dir: str = "scripts/templates"
    include_performance_tests: bool = True
    include_boundary_tests: bool = True
    include_exception_tests: bool = True
    max_test_cases_per_function: int = 10

class AutoTestGenerator:
    """自动化测试生成器"""

    def __init__(self, config: Optional[TestGenerationConfig] = None):
        self.config = config or TestGenerationConfig()
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_tests_from_analysis(self, analysis_report: Dict) -> Dict:
        """基于分析报告生成测试"""
        print("🚀 开始自动化测试生成...")

        generation_results = {
            'generated_files': [],
            'generated_test_cases': 0,
            'generation_errors': [],
            'by_module': {}
        }

        # 按模块组织测试生成
        gaps_by_module = analysis_report.get('gaps_by_module', {})

        for module_name, gaps in gaps_by_module.items():
            if not gaps:
                continue

            print(f"📝 为模块 {module_name} 生成测试...")

            module_result = self._generate_module_tests(module_name, gaps)
            generation_results['by_module'][module_name] = module_result
            generation_results['generated_files'].extend(module_result['files'])
            generation_results['generated_test_cases'] += module_result['test_cases']

        # 生成测试索引文件
        self._generate_test_index(generation_results)

        print("✅ 测试生成完成:")
        print(f"   生成文件: {len(generation_results['generated_files'])}")
        print(f"   生成测试用例: {generation_results['generated_test_cases']}")
        print(f"   输出目录: {self.output_dir}")

        return generation_results

    def _generate_module_tests(self, module_name: str, gaps: List[Dict]) -> Dict:
        """为单个模块生成测试"""
        module_result = {
            'files': [],
            'test_cases': 0,
            'errors': []
        }

        # 按优先级排序
        gaps.sort(key=lambda x: (x.get('priority', 1), x.get('complexity', 1)), reverse=True)

        # 生成测试文件内容
        test_content = self._generate_test_file_content(module_name, gaps)

        # 确定文件名
        safe_module_name = module_name.replace('/', '_').replace('\\', '_')
        test_file_name = f"test_{safe_module_name}_generated.py"
        test_file_path = self.output_dir / test_file_name

        try:
            # 写入测试文件
            with open(test_file_path, 'w', encoding='utf-8') as f:
                f.write(test_content)

            module_result['files'].append(str(test_file_path))
            module_result['test_cases'] = len([gap for gap in gaps])

            print(f"   ✅ 生成 {test_file_name} ({len(gaps)} 个测试)")

        except Exception as e:
            error_msg = f"生成测试文件失败 {test_file_name}: {e}"
            module_result['errors'].append(error_msg)
            print(f"   ❌ {error_msg}")

        return module_result

    def _generate_test_file_content(self, module_name: str, gaps: List[Dict]) -> str:
        """生成测试文件内容"""

        # 文件头部
        header = self._generate_file_header(module_name)

        # 导入语句
        imports = self._generate_imports(gaps)

        # 测试类定义
        test_classes = self._generate_test_classes(gaps)

        # 组合完整内容
        content = f"{header}\n\n{imports}\n\n{test_classes}"

        return content

    def _generate_file_header(self, module_name: str) -> str:
        """生成文件头部注释"""
        return f'''"""
🤖 自动生成的测试文件
模块: {module_name}
生成时间: {self._get_current_time()}
生成器: AutoTest Generator (Phase G)

⚠️  这是自动生成的测试文件，请根据需要调整和完善
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any, Optional
import tempfile
import os'''

    def _generate_imports(self, gaps: List[Dict]) -> str:
        """生成导入语句"""
        imports = []

        # 收集所有需要导入的模块
        modules_to_import = set()
        for gap in gaps:
            file_path = gap.get('file_path', '')
            if file_path and file_path.startswith('src/'):
                # 转换文件路径为Python模块路径
                module_path = file_path.replace('.py', '').replace('/', '.')
                modules_to_import.add(module_path)

        # 生成导入语句
        if modules_to_import:
            imports.extend(["try:" for _ in modules_to_import])
            for module in sorted(modules_to_import):
                imports.append(f"    from {module} import *")
            imports.extend(["except ImportError:" for _ in modules_to_import])
            imports.extend(["    pass" for _ in modules_to_import])

        return '\n'.join(imports)

    def _generate_test_classes(self, gaps: List[Dict]) -> str:
        """生成测试类"""
        test_classes = []

        # 按功能域分组
        gaps_by_domain = self._group_gaps_by_domain(gaps)

        for domain, domain_gaps in gaps_by_domain.items():
            class_name = f"Test{domain.title().replace('_', '')}Generated"
            test_class = self._generate_test_class(class_name, domain_gaps)
            test_classes.append(test_class)

        return '\n\n'.join(test_classes)

    def _group_gaps_by_domain(self, gaps: List[Dict]) -> Dict[str, List[Dict]]:
        """按功能域分组测试缺口"""
        domains = {}

        for gap in gaps:
            function_name = gap.get('function_name', '')

            # 根据函数名确定功能域
            if any(keyword in function_name.lower() for keyword in ['predict', 'forecast', 'estimate']):
                domain = 'prediction'
            elif any(keyword in function_name.lower() for keyword in ['parse', 'load', 'save', 'export', 'import']):
                domain = 'data_processing'
            elif any(keyword in function_name.lower() for keyword in ['validate', 'check', 'verify', 'ensure']):
                domain = 'validation'
            elif any(keyword in function_name.lower() for keyword in ['calculate', 'compute', 'process']):
                domain = 'calculation'
            elif any(keyword in function_name.lower() for keyword in ['get', 'fetch', 'retrieve', 'find']):
                domain = 'retrieval'
            else:
                domain = 'general'

            if domain not in domains:
                domains[domain] = []
            domains[domain].append(gap)

        return domains

    def _generate_test_class(self, class_name: str, gaps: List[Dict]) -> str:
        """生成单个测试类"""
        class_header = f"""@pytest.mark.generated
@pytest.mark.unit
class {class_name}:
    \"\"\"
    🤖 自动生成的测试类

    功能域: {gaps[0].get('file_path', 'unknown') if gaps else 'unknown'}
    测试数量: {len(gaps)}
    \"\"\"
"""

        methods = []
        for gap in gaps:
            function_name = gap.get('function_name', 'unknown_function')
            test_methods = self._generate_test_methods(function_name, gap)
            methods.extend(test_methods)

        return f"{class_header}\n\n" + "\n\n".join(methods)

    def _generate_test_methods(self, function_name: str, gap: Dict) -> List[str]:
        """为单个函数生成测试方法"""
        methods = []
        suggested_tests = gap.get('suggested_tests', [])

        for i, test_suggestion in enumerate(suggested_tests):
            test_type = test_suggestion.get('type', 'basic')
            test_cases = test_suggestion.get('test_cases', [])

            if test_type == 'basic_functionality':
                methods.append(self._generate_basic_test_method(function_name, test_cases, i))
            elif test_type == 'boundary_conditions':
                methods.append(self._generate_boundary_test_method(function_name, test_cases, i))
            elif test_type == 'exception_handling':
                methods.append(self._generate_exception_test_method(function_name, test_cases, i))
            elif test_type == 'performance':
                methods.append(self._generate_performance_test_method(function_name, test_cases, i))

        return methods

    def _generate_basic_test_method(self, function_name: str, test_cases: List[Dict], index: int) -> str:
        """生成基础功能测试方法"""
        method_name = f"test_{function_name}_basic_functionality_{index}"

        method_template = f'''    def {method_name}(self):
        """🤖 自动生成的基础功能测试

        测试目标: {function_name}
        测试类型: 基础功能验证
        """
        # 准备测试数据
        test_inputs = self._prepare_test_inputs_for_{function_name}()
        expected_output = self._get_expected_output_for_{function_name}()

        try:
            # 执行测试
            result = {function_name}(**test_inputs)

            # 基本断言
            assert result is not None, f"{{function_name}} 不应返回 None"
            print(f"✅ {{function_name}} 基础功能测试通过: {{result}}")

        except ImportError:
            pytest.skip(f"{{function_name}} 模块不可用")
        except Exception as e:
            pytest.fail(f"{{function_name}} 基础功能测试失败: {{e}}")

    def _prepare_test_inputs_for_{function_name}(self) -> Dict[str, Any]:
        """为 {function_name} 准备测试输入数据"""
        return {{
            # TODO: 根据实际函数签名调整测试数据
            'param1': 'test_value_1',
            'param2': 'test_value_2',
            'param3': True,
        }}

    def _get_expected_output_for_{function_name}(self) -> Any:
        """获取 {function_name} 的期望输出"""
        # TODO: 根据实际函数逻辑调整期望值
        return "expected_result"'''

        return method_template

    def _generate_boundary_test_method(self, function_name: str, test_cases: List[Dict], index: int) -> str:
        """生成边界条件测试方法"""
        method_name = f"test_{function_name}_boundary_conditions_{index}"

        method_template = f'''    def {method_name}(self):
        """🤖 自动生成的边界条件测试

        测试目标: {function_name}
        测试类型: 边界条件验证
        """
        boundary_test_cases = [
            # 空值测试
            {{'input': None, 'expected': 'appropriate_handling'}},
            # 极小值测试
            {{'input': 0, 'expected': 'appropriate_handling'}},
            # 极大值测试
            {{'input': 999999, 'expected': 'appropriate_handling'}},
            # 空字符串测试
            {{'input': '', 'expected': 'appropriate_handling'}},
            # 负值测试
            {{'input': -1, 'expected': 'appropriate_handling'}},
        ]

        for i, test_case in enumerate(boundary_test_cases):
            with pytest.subTest(test_case=i, input=test_case['input']):
                try:
                    result = {function_name}(test_case['input'])

                    # 根据期望结果进行断言
                    if test_case['expected'] == 'appropriate_handling':
                        assert result is not None, "边界条件处理不当: 输入 {{test_case['input']}}"

                    print("✅ 边界条件测试通过: 输入 {{test_case['input']}} -> 结果 {{result}}")

                except Exception as e:
                    if test_case['expected'] == 'appropriate_exception':
                        print("✅ 期望的异常: {{e}}")
                    else:
                        pytest.fail("边界条件测试失败: 输入 {{test_case['input']}}, 异常 {{e}}")'''

        return method_template

    def _generate_exception_test_method(self, function_name: str, test_cases: List[Dict], index: int) -> str:
        """生成异常处理测试方法"""
        method_name = f"test_{function_name}_exception_handling_{index}"

        method_template = f'''    def {method_name}(self):
        """🤖 自动生成的异常处理测试

        测试目标: {function_name}
        测试类型: 异常处理验证
        """
        exception_test_cases = [
            # 无效类型输入
            {{'input': {{'type': 'invalid_type', 'value': [{{}}]}}, 'expected_exception': (TypeError, ValueError)}},
            # 缺少必需参数
            {{'input': {{}}, 'expected_exception': (TypeError, ValueError)}},
            # 格式错误输入
            {{'input': 'invalid_format_string', 'expected_exception': ValueError}},
            # 权限不足
            {{'input': {{'user_id': None, 'action': 'admin_only'}}, 'expected_exception': PermissionError}},
        ]

        for i, test_case in enumerate(exception_test_cases):
            with pytest.subTest(test_case=i, description=test_case.get('description', 'exception test')):
                expected_exceptions = test_case['expected_exception']

                # 检查是否抛出期望的异常
                with pytest.raises(expected_exceptions):
                    try:
                        {function_name}(test_case['input'])
                    except ImportError:
                        pytest.skip(f"{{function_name}} 模块不可用")

                print(f"✅ 异常处理测试通过: {{test_case.get('description', 'exception test')}}")'''

        return method_template

    def _generate_performance_test_method(self, function_name: str, test_cases: List[Dict], index: int) -> str:
        """生成性能测试方法"""
        method_name = f"test_{function_name}_performance_{index}"

        method_template = f'''    def {method_name}(self):
        """🤖 自动生成的性能测试

        测试目标: {function_name}
        测试类型: 性能基准验证
        """
        import time
        import psutil
        import os

        # 准备性能测试数据
        performance_inputs = self._prepare_performance_inputs_for_{function_name}()

        try:
            # 执行时间测试
            start_time = time.time()
            result = {function_name}(**performance_inputs)
            execution_time = time.time() - start_time

            # 性能断言
            assert execution_time < 1.0, f"执行时间过长: {{execution_time:.3f}}秒"

            # 内存使用测试
            process = psutil.Process(os.getpid())
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB

            # 基本结果验证
            assert result is not None, "性能测试中函数返回了None"

            print(f"✅ 性能测试通过:")
            print(f"   执行时间: {{execution_time:.3f}}秒")
            print(f"   内存使用: {{memory_usage:.2f}}MB")
            print(f"   测试结果: {{result}}")

        except ImportError:
            pytest.skip(f"{{function_name}} 模块不可用，跳过性能测试")
        except Exception as e:
            pytest.fail(f"性能测试失败: {{e}}")

    def _prepare_performance_inputs_for_{function_name}(self) -> Dict[str, Any]:
        """为 {function_name} 准备性能测试数据"""
        return {{
            # 使用相对较大的数据集进行性能测试
            'large_dataset': list(range(1000)),
            'complex_config': {{
                'option1': True,
                'option2': False,
                'nested': {{
                    'level1': {{'level2': [1, 2, 3, 4, 5]}}
                }}
            }}
        }}'''

        return method_template

    def _generate_test_index(self, generation_results: Dict):
        """生成测试索引文件"""
        index_content = f'''"""
🤖 自动生成测试索引
生成时间: {self._get_current_time()}

本文件包含所有自动生成的测试文件的索引信息
"""

AUTO_GENERATED_TESTS_INDEX = {{
    "generation_summary": {{
        "total_files": {len(generation_results['generated_files'])},
        "total_test_cases": {generation_results['generated_test_cases']},
        "generation_time": "{self._get_current_time()}"
    }},
    "generated_files": {generation_results['generated_files']},
    "by_module": {{
'''

        # 添加模块信息
        for module_name, module_result in generation_results['by_module'].items():
            index_content += f'''
        "{module_name}": {{
            "files": {module_result['files']},
            "test_cases": {module_result['test_cases']},
            "errors": {module_result['errors']}
        }},'''

        index_content += '''
    }
}

# 使用示例:
# from test_index import AUTO_GENERATED_TESTS_INDEX
# print(f"生成了 {AUTO_GENERATED_TESTS_INDEX['generation_summary']['total_files']} 个测试文件")
'''

        index_file_path = self.output_dir / "__init__.py"
        with open(index_file_path, 'w', encoding='utf-8') as f:
            f.write(index_content)

        print(f"📋 生成测试索引: {index_file_path}")

    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main():
    """主函数 - 执行自动化测试生成"""
    print("🚀 启动自动化测试生成器...")

    # 检查是否有分析报告
    analysis_report_file = "test_gap_analysis_report.json"
    if not os.path.exists(analysis_report_file):
        print(f"❌ 未找到分析报告文件: {analysis_report_file}")
        print("请先运行智能测试缺口分析器生成分析报告")
        return

    # 读取分析报告
    try:
        with open(analysis_report_file, 'r', encoding='utf-8') as f:
            analysis_report = json.load(f)
    except Exception as e:
        print(f"❌ 读取分析报告失败: {e}")
        return

    # 创建生成器配置
    config = TestGenerationConfig(
        output_dir="tests/generated",
        include_performance_tests=True,
        include_boundary_tests=True,
        include_exception_tests=True
    )

    # 执行测试生成
    generator = AutoTestGenerator(config)
    results = generator.generate_tests_from_analysis(analysis_report)

    # 保存生成结果
    results_file = "test_generation_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n📊 生成结果:")
    print(f"   总文件数: {len(results['generated_files'])}")
    print(f"   总测试用例: {results['generated_test_cases']}")
    print(f"   错误数量: {len(results.get('generation_errors', []))}")
    print(f"   详细结果: {results_file}")

    return results

if __name__ == "__main__":
    main()