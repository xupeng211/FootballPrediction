#!/usr/bin/env python3
"""
AI 自动测试生成器 - 分析代码并生成 pytest 单元测试
"""

import ast
import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import re

logger = logging.getLogger(__name__)

@dataclass
class TestGenerationConfig:
    """测试生成配置"""
    # 输出控制
    output_dir: str = "tests/auto_generated"
    max_tests_per_function: int = 5
    timeout_per_generation: int = 60  # 秒

    # 测试类型
    generate_normal: bool = True
    generate_boundary: bool = True
    generate_exception: bool = True
    generate_parameterized: bool = True

    # 质量控制
    require_assertions: bool = True
    min_assertions_per_test: int = 1
    max_test_length: int = 50  # 行数

    # 项目特定配置
    use_project_fixtures: bool = True
    follow_project_patterns: bool = True

class AITestGenerator:
    """AI 测试生成器"""

    def __init__(self, config: Optional[TestGenerationConfig] = None):
        self.config = config or TestGenerationConfig()
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 项目模式分析
        self.project_patterns = self._analyze_project_patterns()
        self.available_fixtures = self._discover_fixtures()

    def _analyze_project_patterns(self) -> Dict[str, Any]:
        """分析项目测试模式"""
        patterns = {
            "imports": set(),
            "assertion_patterns": [],
            "fixture_usage": [],
            "mock_patterns": []
        }

        try:
            # 分析现有测试文件
            test_files = list(Path("tests").glob("**/test_*.py"))
            for test_file in test_files[:10]:  # 只分析前10个文件
                try:
                    with open(test_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                        # 提取导入模式
                        import_matches = re.findall(r'^(from\s+\S+\s+)?import\s+\S+', content, re.MULTILINE)
                        patterns["imports"].update(import_matches)

                        # 提取断言模式
                        assert_matches = re.findall(r'assert\s+.+', content)
                        patterns["assertion_patterns"].extend(assert_matches[:5])

                        # 提取fixture使用
                        fixture_matches = re.findall(r'def\s+(test_\w+)\([^)]*fixture[^)]*\)', content)
                        patterns["fixture_usage"].extend(fixture_matches)

                except Exception as e:
                    logger.warning(f"Failed to analyze {test_file}: {e}")

        except Exception as e:
            logger.error(f"Failed to analyze project patterns: {e}")

        return patterns

    def _discover_fixtures(self) -> List[str]:
        """发现项目中可用的fixtures"""
        fixtures = []

        try:
            # 运行pytest --fixtures
            result = subprocess.run(
                ["python", "-m", "pytest", "--fixtures"],
                capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                # 解析fixture输出
                fixture_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\n'
                fixtures = re.findall(fixture_pattern, result.stdout)

        except Exception as e:
            logger.warning(f"Failed to discover fixtures: {e}")

        return fixtures

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """分析指定文件的函数和类"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            analysis = {
                "file_path": file_path,
                "classes": [],
                "functions": [],
                "imports": [],
                "dependencies": []
            }

            # 分析导入
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        analysis["imports"].append(node.module)

            # 分析类和函数
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    class_info = self._analyze_class(node)
                    analysis["classes"].append(class_info)
                elif isinstance(node, ast.FunctionDef):
                    func_info = self._analyze_function(node)
                    analysis["functions"].append(func_info)

            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze {file_path}: {e}")
            return {"file_path": file_path, "error": str(e)}

    def _analyze_class(self, node: ast.ClassDef) -> Dict[str, Any]:
        """分析类定义"""
        class_info = {
            "name": node.name,
            "methods": [],
            "docstring": ast.get_docstring(node),
            "line_number": node.lineno
        }

        for method in node.body:
            if isinstance(method, ast.FunctionDef):
                method_info = self._analyze_function(method)
                class_info["methods"].append(method_info)

        return class_info

    def _analyze_function(self, node: ast.FunctionDef) -> Dict[str, Any]:
        """分析函数定义"""
        args_info = []
        for arg in node.args.args:
            args_info.append({
                "name": arg.arg,
                "annotation": ast.unparse(arg.annotation) if arg.annotation else None
            })

        defaults = []
        for default in node.args.defaults:
            try:
                defaults.append(ast.unparse(default))
            except:
                defaults.append("Unknown")

        return {
            "name": node.name,
            "args": args_info,
            "defaults": defaults,
            "returns": ast.unparse(node.returns) if node.returns else None,
            "docstring": ast.get_docstring(node),
            "line_number": node.lineno,
            "is_async": isinstance(node, ast.AsyncFunctionDef)
        }

    def generate_tests_for_file(self, file_path: str) -> Dict[str, Any]:
        """为指定文件生成测试"""
        start_time = time.time()

        try:
            # 分析文件
            analysis = self.analyze_file(file_path)
            if "error" in analysis:
                return {"error": analysis["error"]}

            # 生成测试内容
            test_content = self._generate_test_file_content(analysis)

            # 保存测试文件
            test_file_path = self._get_test_file_path(file_path)
            with open(test_file_path, 'w', encoding='utf-8') as f:
                f.write(test_content)

            # 验证生成的测试
            validation_result = self._validate_generated_test(test_file_path)

            execution_time = time.time() - start_time

            return {
                "original_file": file_path,
                "test_file": str(test_file_path),
                "analysis": analysis,
                "validation": validation_result,
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to generate tests for {file_path}: {e}")
            return {"error": str(e)}

    def _generate_test_file_content(self, analysis: Dict[str, Any]) -> str:
        """生成测试文件内容"""
        lines = [
            '"""',
            f'Auto-generated tests for {analysis["file_path"]}',
            f'Generated at: {datetime.now().isoformat()}',
            '"""',
            '',
            'import pytest',
            'from unittest.mock import Mock, patch',
            'import sys',
            'from pathlib import Path',
            '',
            '# Add project root to path',
            'sys.path.insert(0, str(Path(__file__).parent.parent.parent))',
            ''
        ]

        # 添加项目特定的导入
        module_path = self._get_module_import(analysis["file_path"])
        if module_path:
            lines.append(f'import {module_path}')
            lines.append('')

        # 添加fixtures
        if self.config.use_project_fixtures and self.available_fixtures:
            lines.extend([
                '# Project fixtures',
                'from tests.conftest import *',
                ''
            ])

        # 为每个类生成测试
        for class_info in analysis["classes"]:
            class_tests = self._generate_class_tests(class_info, analysis["imports"])
            lines.extend(class_tests)

        # 为每个函数生成测试
        for func_info in analysis["functions"]:
            func_tests = self._generate_function_tests(func_info, analysis["imports"])
            lines.extend(func_tests)

        return '\n'.join(lines)

    def _get_module_import(self, file_path: str) -> str:
        """获取模块导入路径"""
        if file_path.startswith("src/"):
            # 转换文件路径到模块路径
            module_path = file_path[4:].replace("/", ".")[:-3]  # 移除src/和.py
            return module_path
        return ""

    def _get_test_file_path(self, original_file: str) -> Path:
        """获取测试文件路径"""
        if original_file.startswith("src/"):
            # src/module/file.py -> tests/auto_generated/test_module_file.py
            relative_path = original_file[4:]  # 移除src/
            test_name = f"test_{relative_path.replace('/', '_')[:-3]}"  # 移除.py
            return self.output_dir / test_name
        else:
            test_name = f"test_{Path(original_file).stem}"
            return self.output_dir / test_name

    def _generate_class_tests(self, class_info: Dict[str, Any], imports: List[str]) -> List[str]:
        """为类生成测试"""
        tests = []

        # 类测试类
        test_class_name = f"Test{class_info['name']}"
        tests.extend([
            f'class {test_class_name}:',
            '    """',
            f'    Auto-generated tests for {class_info["name"]}',
            '    """',
            ''
        ])

        # 初始化测试
        tests.extend([
            '    def test_class_initialization(self):',
            '        """Test class can be initialized"""',
            f'        # TODO: Implement initialization test for {class_info["name"]}',
            '        pass',
            ''
        ])

        # 为每个方法生成测试
        for method in class_info["methods"]:
            method_tests = self._generate_function_tests(method, imports, indent=4)
            tests.extend(method_tests)

        return tests

    def _generate_function_tests(self, func_info: Dict[str, Any], imports: List[str], indent: int = 0) -> List[str]:
        """为函数生成测试"""
        tests = []
        prefix = ' ' * indent

        # 跳过私有方法和特殊方法
        if func_info["name"].startswith('_') and not func_info["name"].startswith('__'):
            return tests

        test_func_name = f"test_{func_info['name']}"

        # 正常情况测试
        if self.config.generate_normal:
            tests.extend([
                f'{prefix}def {test_func_name}_normal(self):',
                f'{prefix}    """Test {func_info["name"]} with normal input"""',
                f'{prefix}    # TODO: Generate normal test case for {func_info["name"]}'
            ])

            # 添加基本的参数占位符
            if func_info["args"]:
                args_str = ", ".join([f"arg_{arg['name']}={{TODO}}" for arg in func_info["args"]])
                tests.append(f'{prefix}    result = target_function({args_str})')
            else:
                tests.append(f'{prefix}    result = target_function()')

            tests.extend([
                f'{prefix}    assert result is not None, "Function should return result"',
                f'{prefix}    # Add more specific assertions based on expected behavior',
                ''
            ])

        # 边界条件测试
        if self.config.generate_boundary and func_info["args"]:
            tests.extend([
                f'{prefix}def {test_func_name}_boundary(self):',
                f'{prefix}    """Test {func_info["name"]} with boundary conditions"""',
                f'{prefix}    # TODO: Generate boundary test cases for {func_info["name"]}',
                f'{prefix}    pass',
                ''
            ])

        # 异常情况测试
        if self.config.generate_exception:
            tests.extend([
                f'{prefix}def {test_func_name}_exception(self):',
                f'{prefix}    """Test {func_info["name"]} with invalid input"""',
                f'{prefix}    # TODO: Generate exception test cases for {func_info["name"]}',
                f'{prefix}    pass',
                ''
            ])

        # 参数化测试
        if self.config.generate_parameterized and len(func_info["args"]) > 1:
            tests.extend([
                f'{prefix}@pytest.mark.parametrize("input_data,expected", [',
                f'{prefix}    # TODO: Add test cases for {func_info["name"]}',
                f'{prefix}    ({{}}, {{}}),  # Normal case',
                f'{prefix}    ({{}}, {{}}),  # Edge case',
                f'{prefix}])',
                f'{prefix}def {test_func_name}_parameterized(self, input_data, expected):',
                f'{prefix}    """Test {func_info["name"]} with parameterized input"""',
                f'{prefix}    result = target_function(**input_data)',
                f'{prefix}    assert result == expected',
                ''
            ])

        return tests

    def _validate_generated_test(self, test_file_path: Path) -> Dict[str, Any]:
        """验证生成的测试文件"""
        validation = {
            "file_exists": True,
            "syntax_valid": False,
            "has_assertions": False,
            "has_todo": False,
            "test_count": 0,
            "assertion_count": 0,
            "todo_count": 0,
            "line_count": 0,
            "passes_pytest": False
        }

        try:
            # 检查语法
            with open(test_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            try:
                ast.parse(content)
                validation["syntax_valid"] = True
            except SyntaxError as e:
                validation["syntax_error"] = str(e)

            # 分析内容
            lines = content.split('\n')
            validation["line_count"] = len(lines)

            for line in lines:
                line = line.strip()
                if line.startswith('def test_'):
                    validation["test_count"] += 1
                if line.startswith('assert '):
                    validation["assertion_count"] += 1
                if 'TODO' in line.upper():
                    validation["todo_count"] += 1

            validation["has_assertions"] = validation["assertion_count"] > 0
            validation["has_todo"] = validation["todo_count"] > 0

            # 尝试运行pytest检查
            try:
                result = subprocess.run(
                    ["python", "-m", "pytest", str(test_file_path), "--collect-only"],
                    capture_output=True, text=True, timeout=30
                )
                validation["passes_pytest"] = result.returncode == 0
                if result.returncode != 0:
                    validation["pytest_error"] = result.stderr

            except subprocess.TimeoutExpired:
                validation["pytest_timeout"] = True
            except Exception as e:
                validation["pytest_error"] = str(e)

        except Exception as e:
            validation["validation_error"] = str(e)

        return validation

    def generate_tests_for_directory(self, directory: str, pattern: str = "*.py") -> Dict[str, Any]:
        """为目录下的所有文件生成测试"""
        start_time = time.time()
        results = []

        try:
            dir_path = Path(directory)
            python_files = list(dir_path.glob(pattern))

            for file_path in python_files:
                if file_path.name.startswith("test_"):
                    continue  # 跳过测试文件

                logger.info(f"Generating tests for {file_path}")
                result = self.generate_tests_for_file(str(file_path))
                results.append(result)

            execution_time = time.time() - start_time

            return {
                "directory": directory,
                "pattern": pattern,
                "files_processed": len(results),
                "results": results,
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to generate tests for directory {directory}: {e}")
            return {"error": str(e)}

    def get_generation_statistics(self) -> Dict[str, Any]:
        """获取测试生成统计信息"""
        stats = {
            "total_files": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "total_tests": 0,
            "total_assertions": 0,
            "average_tests_per_file": 0,
            "quality_score": 0
        }

        try:
            # 分析生成的测试文件
            test_files = list(self.output_dir.glob("test_*.py"))
            stats["total_files"] = len(test_files)

            for test_file in test_files:
                try:
                    validation = self._validate_generated_test(test_file)
                    if validation.get("syntax_valid", False):
                        stats["successful_generations"] += 1
                        stats["total_tests"] += validation.get("test_count", 0)
                        stats["total_assertions"] += validation.get("assertion_count", 0)
                    else:
                        stats["failed_generations"] += 1
                except Exception as e:
                    logger.warning(f"Failed to validate {test_file}: {e}")
                    stats["failed_generations"] += 1

            if stats["total_files"] > 0:
                stats["average_tests_per_file"] = stats["total_tests"] / stats["total_files"]
                success_rate = stats["successful_generations"] / stats["total_files"]
                stats["quality_score"] = success_rate * 100

        except Exception as e:
            logger.error(f"Failed to get generation statistics: {e}")

        return stats

    def cleanup_generated_tests(self):
        """清理生成的测试文件"""
        try:
            for test_file in self.output_dir.glob("test_*.py"):
                test_file.unlink()
            logger.info(f"Cleaned up generated tests in {self.output_dir}")
        except Exception as e:
            logger.error(f"Failed to cleanup generated tests: {e}")


def main():
    """主函数 - 用于测试"""
    import argparse

    parser = argparse.ArgumentParser(description="AI Test Generator")
    parser.add_argument("target", help="Target file or directory")
    parser.add_argument("--stats", action="store_true", help="Show generation statistics")
    parser.add_argument("--cleanup", action="store_true", help="Clean up generated tests")
    parser.add_argument("--validate", type=str, help="Validate generated test file")

    args = parser.parse_args()

    generator = AITestGenerator()

    if args.cleanup:
        generator.cleanup_generated_tests()
        return

    if args.stats:
        stats = generator.get_generation_statistics()
        print(json.dumps(stats, indent=2))
        return

    if args.validate:
        validation = generator._validate_generated_test(Path(args.validate))
        print(json.dumps(validation, indent=2))
        return

    target_path = Path(args.target)
    if target_path.is_file():
        result = generator.generate_tests_for_file(str(target_path))
        print(json.dumps(result, indent=2))
    elif target_path.is_dir():
        result = generator.generate_tests_for_directory(str(target_path))
        print(json.dumps(result, indent=2))
    else:
        print(f"Target not found: {args.target}")


if __name__ == "__main__":
    main()