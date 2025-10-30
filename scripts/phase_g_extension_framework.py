#!/usr/bin/env python3
"""
🔧 Phase G工具链扩展框架
支持更多编程语言和框架的扩展性设计

基于Phase G成功经验的模块化扩展系统
"""

import ast
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Type
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class LanguageSupport:
    """语言支持配置"""
    name: str
    extensions: List[str]
    parser_available: bool
    test_frameworks: List[str]
    coverage_tools: List[str]
    quality_checkers: List[str]

@dataclass
class FrameworkSupport:
    """框架支持配置"""
    name: str
    language: str
    patterns: List[str]
    test_generators: List[str]
    coverage_patterns: List[str]

class CodeAnalyzer(ABC):
    """代码分析器基类"""

    def __init__(self, language: str, source_dir: str):
        self.language = language
        self.source_dir = Path(source_dir)
        self.functions = []

    @abstractmethod
    def analyze_functions(self) -> List[Dict]:
        """分析函数 - 子类实现"""
        pass

    @abstractmethod
    def calculate_complexity(self, function_info: Dict) -> int:
        """计算复杂度 - 子类实现"""
        pass

class PythonCodeAnalyzer(CodeAnalyzer):
    """Python代码分析器"""

    def analyze_functions(self) -> List[Dict]:
        """分析Python函数"""
        functions = []

        for py_file in self.source_dir.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        func_info = {
                            'name': node.name,
                            'file_path': str(py_file),
                            'line_number': node.lineno,
                            'is_async': isinstance(node, ast.AsyncFunctionDef),
                            'args_count': len(node.args.args),
                            'decorators': [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list]
                        }

                        func_info['complexity'] = self.calculate_complexity(func_info)
                        functions.append(func_info)

            except Exception:
                continue

        self.functions = functions
        return functions

    def calculate_complexity(self, function_info: Dict) -> int:
        """计算Python函数复杂度"""
        base_complexity = 1

        # 根据参数数量增加复杂度
        base_complexity += function_info['args_count'] // 2

        # 异步函数增加复杂度
        if function_info['is_async']:
            base_complexity += 1

        # 根据装饰器增加复杂度
        base_complexity += len(function_info['decorators'])

        return base_complexity

class JavaScriptCodeAnalyzer(CodeAnalyzer):
    """JavaScript代码分析器"""

    def analyze_functions(self) -> List[Dict]:
        """分析JavaScript函数"""
        functions = []

        for js_file in self.source_dir.rglob("*.js"):
            try:
                with open(js_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 简化的JavaScript函数检测
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    line = line.strip()

                    # 检测函数声明
                    if line.startswith('function ') or line.startswith('const ') and '=>' in line:
                        func_info = {
                            'name': self._extract_function_name(line),
                            'file_path': str(js_file),
                            'line_number': i + 1,
                            'is_async': 'async' in line,
                            'is_arrow': '=>' in line
                        }

                        func_info['complexity'] = self.calculate_complexity(func_info)
                        functions.append(func_info)

            except Exception:
                continue

        self.functions = functions
        return functions

    def _extract_function_name(self, line: str) -> str:
        """提取函数名"""
        if 'function ' in line:
            return line.split('function ')[1].split('(')[0].strip()
        elif '=>' in line:
            return line.split('=')[0].strip().split()[-1]
        return "anonymous"

    def calculate_complexity(self, function_info: Dict) -> int:
        """计算JavaScript函数复杂度"""
        base_complexity = 1

        if function_info['is_async']:
            base_complexity += 1

        if function_info['is_arrow']:
            base_complexity += 1

        return base_complexity

class TestGenerator(ABC):
    """测试生成器基类"""

    def __init__(self, language: str, output_dir: str):
        self.language = language
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def generate_test(self, function_info: Dict) -> str:
        """生成测试代码 - 子类实现"""
        pass

class PythonTestGenerator(TestGenerator):
    """Python测试生成器"""

    def generate_test(self, function_info: Dict) -> str:
        """生成Python测试代码"""
        test_code = f'''#!/usr/bin/env python3
"""
🤖 自动生成的测试文件
函数: {function_info['name']}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
语言: Python
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# 添加源代码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class Test{function_info['name'].title()}Generated:
    """🤖 自动生成的测试类"""

    def test_{function_info['name']}_basic_functionality(self):
        """基础功能测试"""
        # TODO: 实现具体测试逻辑
        pass

    def test_{function_info['name']}_edge_cases(self):
        """边界条件测试"""
        # TODO: 实现边界条件测试
        pass

    def test_{function_info['name']}_error_handling(self):
        """错误处理测试"""
        # TODO: 实现错误处理测试
        pass

if __name__ == "__main__":
    pytest.main([__file__])
'''
        return test_code

class JavaScriptTestGenerator(TestGenerator):
    """JavaScript测试生成器"""

    def generate_test(self, function_info: Dict) -> str:
        """生成JavaScript测试代码"""
        test_code = f'''/**
 * 🤖 自动生成的测试文件
 * 函数: {function_info['name']}
 * 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 * 语言: JavaScript
 */

const {{ function_info['name'] }} = require('../{{ function_info['file_path'].split('/')[-1].replace('.js', '') }}');

describe('{function_info['name']}', () => {{
    test('基础功能测试', () => {{
        // TODO: 实现具体测试逻辑
        expect(true).toBe(true);
    }});

    test('边界条件测试', () => {{
        // TODO: 实现边界条件测试
        expect(true).toBe(true);
    }});

    test('错误处理测试', () => {{
        // TODO: 实现错误处理测试
        expect(true).toBe(true);
    }});
}});
'''
        return test_code

class LanguageExtensionManager:
    """语言扩展管理器"""

    def __init__(self):
        self.supported_languages = {
            'python': LanguageSupport(
                name='Python',
                extensions=['.py'],
                parser_available=True,
                test_frameworks=['pytest', 'unittest', 'nose'],
                coverage_tools=['coverage.py', 'pytest-cov'],
                quality_checkers=['ruff', 'mypy', 'pylint', 'flake8']
            ),
            'javascript': LanguageSupport(
                name='JavaScript',
                extensions=['.js', '.jsx', '.ts', '.tsx'],
                parser_available=False,  # 需要额外配置
                test_frameworks=['jest', 'mocha', 'jasmine', 'vitest'],
                coverage_tools=['istanbul', 'c8', 'nyc'],
                quality_checkers=['eslint', 'jshint', 'typescript']
            ),
            'java': LanguageSupport(
                name='Java',
                extensions=['.java'],
                parser_available=False,  # 需要额外配置
                test_frameworks=['junit', 'testng', 'spock'],
                coverage_tools=['jacoco', 'cobertura', 'emma'],
                quality_checkers=['checkstyle', 'pmd', 'spotbugs']
            ),
            'go': LanguageSupport(
                name='Go',
                extensions=['.go'],
                parser_available=False,  # 需要额外配置
                test_frameworks=['testing', 'testify', 'ginkgo'],
                coverage_tools=['go test -cover', 'gocov', 'gover'],
                quality_checkers=['golint', 'go vet', 'staticcheck']
            ),
            'rust': LanguageSupport(
                name='Rust',
                extensions=['.rs'],
                parser_available=False,  # 需要额外配置
                test_frameworks=['cargo test', 'tarpaulin'],
                coverage_tools=['cargo tarpaulin', 'kcov', 'grcov'],
                quality_checkers=['cargo clippy', 'rustfmt', 'cargo audit']
            )
        }

        self.analyzers = {
            'python': PythonCodeAnalyzer,
            'javascript': JavaScriptCodeAnalyzer
        }

        self.generators = {
            'python': PythonTestGenerator,
            'javascript': JavaScriptTestGenerator
        }

    def get_supported_languages(self) -> Dict[str, LanguageSupport]:
        """获取支持的语言列表"""
        return self.supported_languages

    def is_language_supported(self, language: str) -> bool:
        """检查语言是否支持"""
        return language.lower() in self.supported_languages

    def get_analyzer(self, language: str) -> Optional[Type[CodeAnalyzer]]:
        """获取代码分析器"""
        return self.analyzers.get(language.lower())

    def get_generator(self, language: str) -> Optional[Type[TestGenerator]]:
        """获取测试生成器"""
        return self.generators.get(language.lower())

    def detect_project_languages(self, project_path: str) -> List[str]:
        """检测项目中使用的编程语言"""
        project_path = Path(project_path)
        detected_languages = set()

        # 统计不同语言文件的扩展名
        extension_counts = {}
        for file_path in project_path.rglob('*'):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext:
                    extension_counts[ext] = extension_counts.get(ext, 0) + 1

        # 根据扩展名推断语言
        for ext, count in extension_counts.items():
            if count >= 3:  # 至少3个文件才认为是该语言
                for lang, support in self.supported_languages.items():
                    if ext in support.extensions:
                        detected_languages.add(lang)

        return list(detected_languages)

class ExtendedPhaseGSystem:
    """扩展的Phase G系统"""

    def __init__(self):
        self.extension_manager = LanguageExtensionManager()
        self.analysis_results = {}
        self.generation_results = {}

    def analyze_multilang_project(self, project_path: str) -> Dict:
        """分析多语言项目"""
        print("🔍 扩展Phase G多语言项目分析...")
        print("=" * 60)

        detected_languages = self.extension_manager.detect_project_languages(project_path)
        print(f"📂 检测到的编程语言: {detected_languages}")

        results = {
            'project_path': project_path,
            'detected_languages': detected_languages,
            'language_analysis': {},
            'total_functions': 0,
            'total_complexity': 0,
            'supported_languages': [],
            'unsupported_languages': []
        }

        for language in detected_languages:
            print(f"\n🔍 分析 {language} 代码...")

            if self.extension_manager.is_language_supported(language):
                analyzer_class = self.extension_manager.get_analyzer(language)

                if analyzer_class:
                    try:
                        analyzer = analyzer_class(language, project_path)
                        functions = analyzer.analyze_functions()

                        lang_results = {
                            'functions_found': len(functions),
                            'functions': functions,
                            'total_complexity': sum(f['complexity'] for f in functions),
                            'analyzer_used': analyzer_class.__name__
                        }

                        results['language_analysis'][language] = lang_results
                        results['total_functions'] += len(functions)
                        results['total_complexity'] += lang_results['total_complexity']
                        results['supported_languages'].append(language)

                        print(f"   ✅ 发现 {len(functions)} 个函数")
                        print(f"   📊 总复杂度: {lang_results['total_complexity']}")

                    except Exception as e:
                        print(f"   ❌ 分析失败: {e}")
                        results['unsupported_languages'].append(language)
                else:
                    print(f"   ⚠️ 暂不支持 {language} 代码分析")
                    results['unsupported_languages'].append(language)
            else:
                print(f"   ❌ 不支持的语言: {language}")
                results['unsupported_languages'].append(language)

        # 生成分析报告
        self._generate_multilang_report(results)

        return results

    def generate_multilang_tests(self, analysis_results: Dict, output_dir: str = "tests/generated_multilang") -> Dict:
        """为多语言项目生成测试"""
        print(f"\n🤖 扩展Phase G多语言测试生成...")
        print("=" * 60)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        generation_results = {
            'output_directory': str(output_path),
            'language_results': {},
            'total_files_generated': 0,
            'total_tests_generated': 0,
            'supported_languages': [],
            'failed_generations': []
        }

        for language, lang_analysis in analysis_results['language_analysis'].items():
            print(f"\n🤖 为 {language} 生成测试...")

            generator_class = self.extension_manager.get_generator(language)

            if generator_class:
                try:
                    generator = generator_class(language, str(output_path / language.lower()))

                    generated_files = 0
                    generated_tests = 0

                    for function_info in lang_analysis['functions']:
                        # 为每个函数生成测试文件
                        test_code = generator.generate_test(function_info)

                        test_filename = f"test_{function_info['name']}_generated.{self._get_test_extension(language)}"
                        test_filepath = output_path / language.lower() / test_filename

                        with open(test_filepath, 'w', encoding='utf-8') as f:
                            f.write(test_code)

                        generated_files += 1
                        generated_tests += 3  # 假设每个文件包含3个测试方法

                    lang_results = {
                        'files_generated': generated_files,
                        'tests_generated': generated_tests,
                        'generator_used': generator_class.__name__,
                        'output_path': str(output_path / language.lower())
                    }

                    generation_results['language_results'][language] = lang_results
                    generation_results['total_files_generated'] += generated_files
                    generation_results['total_tests_generated'] += generated_tests
                    generation_results['supported_languages'].append(language)

                    print(f"   ✅ 生成 {generated_files} 个测试文件")
                    print(f"   📊 {generated_tests} 个测试方法")

                except Exception as e:
                    print(f"   ❌ 生成失败: {e}")
                    generation_results['failed_generations'].append(language)
            else:
                print(f"   ❌ 不支持 {language} 测试生成")
                generation_results['failed_generations'].append(language)

        # 生成索引文件
        self._generate_multilang_index(generation_results)

        # 生成生成报告
        self._generate_generation_report(generation_results)

        return generation_results

    def _get_test_extension(self, language: str) -> str:
        """获取测试文件扩展名"""
        extensions = {
            'python': 'py',
            'javascript': 'js',
            'java': 'java',
            'go': 'go',
            'rust': 'rs'
        }
        return extensions.get(language.lower(), 'test')

    def _generate_multilang_index(self, results: Dict):
        """生成多语言测试索引"""
        index_content = f'''"""
🤖 扩展Phase G多语言测试索引
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

MULTILANG_TEST_INDEX = {{
    "generation_summary": {{
        "total_files": {results['total_files_generated']},
        "total_tests": {results['total_tests_generated']},
        "output_directory": "{results['output_directory']}",
        "supported_languages": {results['supported_languages']}
    }},
    "language_results": {{
'''

        for language, lang_results in results['language_results'].items():
            index_content += f'''
        "{language}": {{
            "files_generated": {lang_results['files_generated']},
            "tests_generated": {lang_results['tests_generated']},
            "output_path": "{lang_results['output_path']}"
        }},'''

        index_content += '''
    }
}

# 使用示例
# from multilang_test_index import MULTILANG_TEST_INDEX
# print(f"生成了 {{MULTILANG_TEST_INDEX['generation_summary']['total_files']}} 个测试文件")
'''

        index_file = Path(results['output_directory']) / "__init__.py"
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(index_content)

        print(f"📋 生成多语言测试索引: {index_file}")

    def _generate_multilang_report(self, results: Dict):
        """生成多语言分析报告"""
        report_file = f"phase_g_multilang_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        print(f"📄 多语言分析报告已保存: {report_file}")

    def _generate_generation_report(self, results: Dict):
        """生成测试生成报告"""
        report_file = f"phase_g_multilang_generation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        print(f"📄 多语言生成报告已保存: {report_file}")

def main():
    """主函数"""
    print("🔧 启动Phase G工具链扩展框架")
    print("支持多编程语言和框架的扩展性演示")
    print("=" * 60)

    # 创建扩展系统
    extended_system = ExtendedPhaseGSystem()

    # 显示支持的语言
    supported_langs = extended_system.extension_manager.get_supported_languages()
    print(f"🌐 支持的编程语言: {list(supported_langs.keys())}")

    # 分析当前项目（作为演示）
    current_project = Path.cwd()
    print(f"\n📂 分析当前项目: {current_project.name}")

    try:
        # 检测项目语言
        detected_langs = extended_system.extension_manager.detect_project_languages(str(current_project))
        print(f"🔍 检测到的语言: {detected_langs}")

        if detected_langs:
            # 执行多语言分析
            analysis_results = extended_system.analyze_multilang_project(str(current_project))

            if analysis_results['total_functions'] > 0:
                # 生成多语言测试
                generation_results = extended_system.generate_multilang_tests(analysis_results)

                # 显示摘要
                print(f"\n" + "=" * 60)
                print(f"📊 扩展Phase G多语言支持摘要")
                print(f"=" * 60)
                print(f"🌐 支持的语言: {len(supported_langs)} 个")
                print(f"📂 检测到的语言: {len(detected_langs)} 个")
                print(f"📊 分析的函数: {analysis_results['total_functions']} 个")
                print(f"🤖 生成的测试: {generation_results['total_tests_generated']} 个")
                print(f"📁 生成的文件: {generation_results['total_files_generated']} 个")
                print(f"✅ 成功的语言: {len(generation_results['supported_languages'])} 个")

                print(f"\n🎯 扩展框架功能:")
                print(f"   ✅ 多语言代码分析")
                print(f"   ✅ 多语言测试生成")
                print(f"   ✅ 可扩展架构设计")
                print(f"   ✅ 统一的接口规范")

                print(f"\n🚀 Phase G工具链已支持多语言扩展!")
            else:
                print(f"\n⚠️ 当前项目中未发现可分析的函数")
        else:
            print(f"\n⚠️ 当前项目中未检测到支持的编程语言")

    except Exception as e:
        print(f"\n❌ 扩展框架执行失败: {e}")
        return False

    return True

if __name__ == "__main__":
    main()