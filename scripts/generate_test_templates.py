#!/usr/bin/env python3
"""
自动生成测试模板脚本
根据源代码结构生成测试文件模板
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple


class TestTemplateGenerator:
    """测试模板生成器"""

    def __init__(self, src_dir: str = "src", test_dir: str = "tests/unit"):
        self.src_dir = Path(src_dir)
        self.test_dir = Path(test_dir)
        self.visited_files: Set[Path] = set()

    def analyze_source_file(self, file_path: Path) -> Dict:
        """分析源代码文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                tree = ast.parse(f.read())
            except SyntaxError as e:
                print(f"⚠️  无法解析 {file_path}: {e}")
                return {}

        analysis = {"classes": [], "functions": [], "imports": []}

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods.append(item.name)
                analysis["classes"].append({"name": node.name, "methods": methods})
            elif isinstance(node, ast.FunctionDef):
                # 检查是否是模块级函数（不在类内）
                for parent in ast.walk(tree):
                    if isinstance(parent, ast.ClassDef):
                        break
                else:
                    analysis["functions"].append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    analysis["imports"].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    analysis["imports"].append(
                        f"{module}.{alias.name}" if module else alias.name
                    )

        return analysis

    def generate_class_test_template(self, class_info: Dict, module_name: str) -> str:
        """生成类测试模板"""
        class_name = class_info["name"]
        methods = class_info["methods"]

        template = f"""
class Test{class_name}:
    \"\"\"测试{class_name}类\"\"\"

    @pytest.fixture
    def sample_{class_name.lower()}(self):
        \"\"\"创建{class_name}实例\"\"\"
        # TODO: 根据实际需要调整初始化参数
        pass

    def test_{class_name.lower()}_creation(self, sample_{class_name.lower()}):
        \"\"\"测试{class_name}创建\"\"\"
        # TODO: 实现测试逻辑
        assert sample_{class_name.lower()} is not None

"""

        # 为每个方法生成测试模板
        for method_name in methods:
            if not method_name.startswith("_"):  # 跳过私有方法
                template += f"""    def test_{method_name}(self, sample_{class_name.lower()}):
        \"\"\"测试{method_name}方法\"\"\"
        # Given - 准备测试数据
        # TODO: 准备测试数据

        # When - 执行操作
        # TODO: 调用方法
        # result = sample_{class_name.lower()}.{method_name}(...)

        # Then - 验证结果
        # TODO: 验证结果
        # assert result is not None

"""

        return template

    def generate_function_test_template(self, function_name: str) -> str:
        """生成函数测试模板"""
        template = f"""
def test_{function_name}():
    \"\"\"测试{function_name}函数\"\"\"
    # Given - 准备测试数据
    # TODO: 准备测试数据

    # When - 执行操作
    # TODO: 调用函数
    # from {self.get_module_path()} import {function_name}
    # result = {function_name}(...)

    # Then - 验证结果
    # TODO: 验证结果
    # assert result is not None

"""
        return template

    def get_module_path(self, file_path: Path) -> str:
        """获取模块导入路径"""
        relative_path = file_path.relative_to(self.src_dir)
        module_path = str(relative_path.with_suffix("")).replace(os.sep, ".")
        return module_path

    def generate_test_file(self, src_file: Path) -> Tuple[str, Path]:
        """为源代码文件生成测试文件"""
        # 分析源代码
        analysis = self.analyze_source_file(src_file)
        if not analysis:
            return "", None

        # 计算测试文件路径
        relative_path = src_file.relative_to(self.src_dir)
        test_file_path = self.test_dir / relative_path.with_name(
            f"test_{relative_path.name}"
        )

        # 生成测试文件内容
        module_name = self.get_module_path(src_file)

        content = f'''"""
{module_name} 模块测试

自动生成的测试模板，请根据需要完善测试用例
"""

import pytest
'''

        # 添加导入
        if analysis["imports"]:
            content += "\n# 导入被测试的模块\n"
            content += f"from {module_name} import (\n"

            # 添加类导入
            for class_info in analysis["classes"]:
                content += f"    {class_info['name']},\n"

            # 添加函数导入
            if analysis["functions"]:
                content += "\n    # 函数\n"
                for func_name in analysis["functions"]:
                    content += f"    {func_name},\n"

            content += ")\n\n"

        # 生成类测试
        for class_info in analysis["classes"]:
            content += self.generate_class_test_template(class_info, module_name)

        # 生成函数测试
        for func_name in analysis["functions"]:
            content += self.generate_function_test_template(func_name)

        return content, test_file_path

    def discover_source_files(self) -> List[Path]:
        """发现所有Python源代码文件"""
        python_files = []
        for root, dirs, files in os.walk(self.src_dir):
            # 跳过__pycache__目录
            dirs[:] = [d for d in dirs if d != "__pycache__"]

            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    python_files.append(Path(root) / file)

        return sorted(python_files)

    def discover_missing_tests(self) -> List[Path]:
        """发现缺少测试的源代码文件"""
        missing_tests = []
        source_files = self.discover_source_files()

        for src_file in source_files:
            # 计算对应的测试文件路径
            relative_path = src_file.relative_to(self.src_dir)
            test_file = self.test_dir / relative_path.with_name(
                f"test_{relative_path.name}"
            )

            if not test_file.exists():
                missing_tests.append(src_file)

        return missing_tests

    def generate_missing_tests(self, overwrite: bool = False) -> int:
        """生成缺失的测试文件"""
        missing_tests = self.discover_missing_tests()

        if not missing_tests:
            print("✅ 所有源代码文件都有对应的测试文件")
            return 0

        print(f"📝 发现 {len(missing_tests)} 个缺少测试的源代码文件")
        generated_count = 0

        for src_file in missing_tests:
            content, test_file_path = self.generate_test_file(src_file)

            if content:
                # 创建目录
                test_file_path.parent.mkdir(parents=True, exist_ok=True)

                # 检查文件是否已存在
                if test_file_path.exists() and not overwrite:
                    print(f"⚠️  跳过已存在的文件: {test_file_path}")
                    continue

                # 写入测试文件
                with open(test_file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                print(f"✅ 生成测试文件: {test_file_path}")
                generated_count += 1

        return generated_count

    def report_coverage_status(self):
        """报告测试覆盖状态"""
        source_files = self.discover_source_files()
        missing_tests = self.discover_missing_tests()

        total_files = len(source_files)
        tested_files = total_files - len(missing_tests)
        coverage_percent = (tested_files / total_files * 100) if total_files > 0 else 0

        print("\n" + "=" * 60)
        print("📊 测试文件覆盖报告")
        print("=" * 60)
        print(f"📁 源代码文件总数: {total_files}")
        print(f"✅ 已测试文件数: {tested_files}")
        print(f"❌ 未测试文件数: {len(missing_tests)}")
        print(f"📈 文件覆盖率: {coverage_percent:.1f}%")

        if missing_tests:
            print("\n❌ 缺少测试的文件:")
            for src_file in missing_tests[:10]:  # 只显示前10个
                relative_path = src_file.relative_to(self.src_dir)
                print(f"  - {relative_path}")

            if len(missing_tests) > 10:
                print(f"  ... 还有 {len(missing_tests) - 10} 个文件")

        print("\n" + "=" * 60)

        return {
            "total_files": total_files,
            "tested_files": tested_files,
            "missing_tests": len(missing_tests),
            "coverage_percent": coverage_percent,
        }


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="生成测试模板工具")
    parser.add_argument("--src-dir", default="src", help="源代码目录")
    parser.add_argument("--test-dir", default="tests/unit", help="测试目录")
    parser.add_argument("--report-only", action="store_true", help="仅生成报告")
    parser.add_argument("--overwrite", action="store_true", help="覆盖已存在的测试文件")

    args = parser.parse_args()

    generator = TestTemplateGenerator(args.src_dir, args.test_dir)

    # 生成报告
    generator.report_coverage_status()

    if not args.report_only:
        print("\n🚀 开始生成测试模板...")
        generated = generator.generate_missing_tests(overwrite=args.overwrite)

        if generated > 0:
            print(f"\n✅ 成功生成 {generated} 个测试文件")
            print("\n📝 提示:")
            print("1. 请打开生成的测试文件")
            print("2. 完善 TODO 部分的测试逻辑")
            print("3. 运行 pytest 验证测试")
        else:
            print("\n✨ 所有文件都已存在测试文件")


if __name__ == "__main__":
    main()
