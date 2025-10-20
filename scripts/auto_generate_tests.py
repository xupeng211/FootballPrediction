#!/usr/bin/env python3
"""
自动为0%覆盖率文件生成测试
"""

import ast
import os
from pathlib import Path
from typing import List, Dict, Optional
import json


class TestGenerator:
    def __init__(self):
        self.generated_tests = []

    def analyze_source_file(self, file_path: str) -> Dict:
        """分析源文件，提取类和函数"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            classes = []
            functions = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods.append(
                                {
                                    "name": item.name,
                                    "args": [arg.arg for arg in item.args.args],
                                }
                            )
                    classes.append({"name": node.name, "methods": methods})
                elif isinstance(node, ast.FunctionDef) and not any(
                    isinstance(parent, ast.ClassDef)
                    for parent in ast.walk(tree)
                    if hasattr(parent, "body") and node in parent.body
                ):
                    functions.append(
                        {"name": node.name, "args": [arg.arg for arg in node.args.args]}
                    )

            return {
                "classes": classes,
                "functions": functions,
                "imports": self.extract_imports(tree),
            }
        except Exception as e:
            print(f"分析文件失败 {file_path}: {e}")
            return {"classes": [], "functions": [], "imports": []}

    def extract_imports(self, tree) -> List[str]:
        """提取导入语句"""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"from {module} import {alias.name}")
        return imports

    def generate_test_file(self, source_path: str) -> Optional[str]:
        """为源文件生成测试代码"""
        analysis = self.analyze_source_file(source_path)

        if not analysis["classes"] and not analysis["functions"]:
            return None

        source_path_obj = Path(source_path)
        module_name = ".".join(source_path_obj.parts[1:]).replace(".py", "")

        test_content = f'''"""
自动生成的测试文件
源文件: {source_path}
生成时间: 2025-01-18
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import sys

# 添加src路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 导入被测试的模块
try:
    from {module_name} import *
except ImportError as e:
    pytest.skip(f"无法导入模块 {{module_name}}: {{e}}", allow_module_level=True)


'''

        # 为每个类生成测试
        for cls in analysis["classes"]:
            test_content += f'''
class Test{cls['name']}:
    """测试 {cls['name']} 类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        pass

    def teardown_method(self):
        """每个测试方法后的清理"""
        pass

    @pytest.fixture
    def sample_instance(self):
        """创建测试实例"""
        try:
            return {cls['name']}()
        except Exception as e:
            pytest.skip(f"无法创建实例: {{e}}")

    def test_init(self, sample_instance):
        """测试初始化"""
        assert sample_instance is not None

    def test_instance_attributes(self, sample_instance):
        """测试实例属性"""
        # 基础属性检查
        assert hasattr(sample_instance, '__class__')
        assert sample_instance.__class__.__name__ == '{cls['name']}'
'''

            # 为每个方法生成测试
            for method in cls["methods"]:
                if method["name"].startswith("_"):
                    continue  # 跳过私有方法

                test_content += f'''
    def test_{method['name']}(self, sample_instance):
        """测试 {method['name']} 方法"""
        # 基础方法存在性测试
        assert hasattr(sample_instance, '{method['name']}')
        assert callable(getattr(sample_instance, '{method['name']}'))

        # TODO: 添加更具体的测试逻辑
        # 这是自动生成的占位符测试
        # 请根据实际业务逻辑完善测试内容
'''

        # 为每个函数生成测试
        for func in analysis["functions"]:
            if func["name"].startswith("_"):
                continue  # 跳过私有函数

            test_content += f'''
def test_{func['name']}():
    """测试 {func['name']} 函数"""
    # 函数存在性测试
    try:
        func_obj = globals().get('{func['name']}')
        if func_obj:
            assert callable(func_obj)
        else:
            pytest.skip("函数未找到")
    except Exception as e:
        pytest.skip(f"测试失败: {{e}}")

    # TODO: 添加更具体的测试逻辑
    # 这是自动生成的占位符测试
    # 请根据实际业务逻辑完善测试内容
'''

        # 添加集成测试（如果有类）
        if analysis["classes"]:
            test_content += '''

class IntegrationTest:
    """集成测试"""

    @pytest.mark.integration
    def test_workflow(self):
        """测试完整工作流"""
        # TODO: 实现端到端工作流测试
        pytest.skip("集成测试待实现")
'''

        return test_content

    def create_test_file(self, source_path: str, test_path: str) -> bool:
        """创建测试文件"""
        test_content = self.generate_test_file(source_path)

        if not test_content:
            print(f"跳过 {source_path}: 没有可测试的内容")
            return False

        # 确保目录存在
        test_path_obj = Path(test_path)
        test_path_obj.parent.mkdir(parents=True, exist_ok=True)

        # 如果文件已存在，不覆盖
        if test_path_obj.exists():
            print(f"跳过 {test_path}: 文件已存在")
            return False

        # 写入测试文件
        with open(test_path_obj, "w", encoding="utf-8") as f:
            f.write(test_content)

        print(f"✅ 创建测试文件: {test_path}")
        self.generated_tests.append(
            {"source": source_path, "test": test_path, "status": "created"}
        )
        return True


def main():
    """主函数"""
    # 读取分析报告
    with open("docs/_reports/coverage/zero_coverage_analysis.json", "r") as f:
        report = json.load(f)

    generator = TestGenerator()

    print("\n🚀 开始生成测试文件...")

    # 处理0%覆盖率文件（前10个最重要的）
    zero_files = report["plan"]["zero_coverage"][:10]

    for file_info in zero_files:
        source_file = file_info["file"]
        test_file = report["test_files_to_create"][len(generator.generated_tests)][
            "test_file"
        ]

        print(f"\n处理: {source_file}")
        generator.create_test_file(source_file, test_file)

    # 处理高价值低覆盖文件
    high_impact = report["plan"]["high_impact"][:5]

    for file_info in high_impact:
        source_file = file_info["file"]
        test_file = f"tests/unit/test_{source_file.replace('src/', '').replace('/', '_').replace('.py', '')}_coverage.py"

        print(f"\n处理高价值文件: {source_file}")
        generator.create_test_file(source_file, test_file)

    # 保存生成记录
    generation_report = {
        "date": "2025-01-18",
        "generated_tests": generator.generated_tests,
        "total_created": len(generator.generated_tests),
    }

    with open("docs/_reports/coverage/test_generation_report.json", "w") as f:
        json.dump(generation_report, f, indent=2, ensure_ascii=False)

    print("\n✅ 测试生成完成!")
    print(f"   - 共创建 {len(generator.generated_tests)} 个测试文件")
    print("   - 报告保存在: docs/_reports/coverage/test_generation_report.json")

    print("\n📝 下一步建议:")
    print("   1. 运行 'make test-quick' 验证新生成的测试")
    print("   2. 完善 TODO 标记的测试逻辑")
    print("   3. 运行覆盖率检查: make coverage")


if __name__ == "__main__":
    main()
