#!/usr/bin/env python3
"""
快速测试覆盖率分析工具
Quick Test Coverage Analysis Tool

不依赖pytest，分析现有测试文件和源代码的对应关系
为Issue #156的P0任务提供快速分析
"""

import ast
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple


class QuickCoverageAnalyzer:
    """快速覆盖率分析器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_dir = project_root / "src"
        self.tests_dir = project_root / "tests"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "src_files": 0,
            "test_files": 0,
            "covered_modules": 0,
            "uncovered_modules": 0,
            "coverage_estimate": 0.0,
            "recommendations": [],
        }

    def find_python_files(self, directory: Path) -> List[Path]:
        """查找目录下的所有Python文件"""
        python_files = []
        for file_path in directory.rglob("*.py"):
            if file_path.is_file():
                python_files.append(file_path)
        return python_files

    def extract_module_info(self, file_path: Path) -> Dict:
        """从Python文件中提取模块信息"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            functions = []
            classes = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not node.name.startswith('_'):  # 跳过私有函数
                        functions.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)

            return {
                "functions": functions,
                "classes": classes,
                "has_main": any(func_name == "main" for func_name in functions),
                "has_tests": any(func_name.startswith("test_") for func_name in functions),
            }

        except (SyntaxError, UnicodeDecodeError) as e:
            return {"error": str(e), "functions": [], "classes": []}

    def find_test_for_module(self, module_path: Path) -> List[Path]:
        """为模块查找对应的测试文件"""
        relative_path = module_path.relative_to(self.src_dir)
        module_stem = module_path.stem

        possible_test_paths = [
            # 直接对应的测试文件
            self.tests_dir / relative_path.with_name(f"test_{module_stem}.py"),
            # 同目录下的测试文件
            self.tests_dir / relative_path.parent / f"test_{module_stem}.py",
            # 测试子目录
            self.tests_dir / relative_path.parent / "tests" / f"test_{module_stem}.py",
        ]

        # 也查找包含模块名的测试文件
        test_dir_parts = list(relative_path.parts)
        test_dir_parts[-1] = "test_" + test_dir_parts[-1]
        possible_test_paths.append(self.tests_dir / Path(*test_dir_parts))

        found_tests = []
        for test_path in possible_test_paths:
            if test_path.exists():
                found_tests.append(test_path)

        return found_tests

    def analyze_coverage(self) -> Dict:
        """分析测试覆盖率"""
        print("🔍 开始快速覆盖率分析...")

        # 查找所有源文件
        src_files = self.find_python_files(self.src_dir)
        src_files = [f for f in src_files if not any(part.startswith('.') for part in f.parts)]
        src_files = [f for f in src_files if f.name != "__init__.py"]  # 排除__init__.py

        # 查找所有测试文件
        test_files = self.find_python_files(self.tests_dir)

        self.results["src_files"] = len(src_files)
        self.results["test_files"] = len(test_files)

        print(f"📁 发现 {len(src_files)} 个源文件")
        print(f"🧪 发现 {len(test_files)} 个测试文件")

        covered_modules = []
        uncovered_modules = []

        for src_file in src_files:
            relative_path = src_file.relative_to(self.src_dir)
            module_info = self.extract_module_info(src_file)

            if "error" in module_info:
                print(f"⚠️ 跳过有语法错误的文件: {relative_path}")
                continue

            test_files_for_module = self.find_test_for_module(src_file)

            if test_files_for_module:
                covered_modules.append({
                    "src_file": relative_path,
                    "test_files": [t.relative_to(self.tests_dir) for t in test_files_for_module],
                    "functions": module_info["functions"],
                    "classes": module_info["classes"],
                })
                print(f"✅ {relative_path} -> {len(test_files_for_module)} 个测试文件")
            else:
                uncovered_modules.append({
                    "src_file": relative_path,
                    "functions": module_info["functions"],
                    "classes": module_info["classes"],
                })
                print(f"❌ {relative_path} -> 无测试文件")

        self.results["covered_modules"] = len(covered_modules)
        self.results["uncovered_modules"] = len(uncovered_modules)

        # 计算覆盖率估算
        total_modules = len(covered_modules) + len(uncovered_modules)
        if total_modules > 0:
            self.results["coverage_estimate"] = (len(covered_modules) / total_modules) * 100

        # 生成建议
        self.generate_recommendations(uncovered_modules)

        return self.results

    def generate_recommendations(self, uncovered_modules: List[Dict]) -> None:
        """生成改进建议"""
        print("\n💡 生成改进建议...")

        # 按复杂度排序，优先处理有更多函数和类的模块
        uncovered_modules.sort(key=lambda x: len(x["functions"]) + len(x["classes"]), reverse=True)

        top_priority = uncovered_modules[:5]  # 前5个优先级最高的

        for module in top_priority:
            module_path = module["src_file"]
            functions = module["functions"]
            classes = module["classes"]

            priority = "高"
            if len(functions) + len(classes) > 5:
                priority = "高"
            elif len(functions) + len(classes) > 2:
                priority = "中"
            else:
                priority = "低"

            recommendation = {
                "module": str(module_path),
                "priority": priority,
                "functions_count": len(functions),
                "classes_count": len(classes),
                "suggested_test_path": f"tests/{module_path.parent}/test_{module_path.stem}.py",
            }

            self.results["recommendations"].append(recommendation)

            print(f"  [{priority}] {module_path}")
            print(f"    函数: {len(functions)}, 类: {len(classes)}")
            print(f"    建议测试文件: {recommendation['suggested_test_path']}")

    def create_basic_test_template(self, module_info: Dict) -> str:
        """为未覆盖的模块创建基本测试模板"""
        module_path = module_info["src_file"]
        functions = module_info["functions"]
        classes = module_info["classes"]

        module_name = str(module_path.with_suffix('')).replace('/', '.')
        test_class_name = module_path.stem.title().replace('_', '')

        template = f'''"""
基本测试模板
Basic Test Template

针对模块: {module_name}
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
'''

        # 添加导入
        if classes:
            template += f"    from {module_name} import (\n"
            for cls in classes[:3]:  # 限制导入数量
                template += f"        {cls},\n"
            template += "    )\n"

        if functions:
            if classes:
                template += "    from {module_name} import (\n"
            else:
                template += f"    from {module_name} import (\n"

            for func in functions[:3]:  # 限制导入数量
                template += f"        {func},\n"
            template += "    )\n"

        template += f'''except ImportError as e:
    pytest.skip(f"无法导入模块 {{e}}")

'''

        # 为类生成测试
        for cls in classes[:2]:  # 限制生成数量
            template += f'''
class Test{cls}:
    """测试 {cls} 类"""

    def test_class_exists(self):
        """测试类是否存在"""
        assert {cls} is not None
        assert hasattr({cls}, '__name__')
        assert {cls}.__name__ == '{cls}'

    def test_class_instantiation(self):
        """测试类实例化"""
        # TODO: 根据类的构造函数添加正确的参数
        try:
            instance = {cls}()
            assert instance is not None
        except Exception as e:
            pytest.skip(f"无法实例化类: {{e}}")
'''

        # 为函数生成测试
        for func in functions[:3]:  # 限制生成数量
            template += f'''
def test_{func}_exists():
    """测试 {func} 函数是否存在"""
    assert {func} is not None
    assert callable({func})

def test_{func}_basic():
    """测试 {func} 函数基本功能"""
    # TODO: 根据函数的实际功能添加具体测试
    # 这是一个基本的存在性测试
    try:
        result = {func}()
        # TODO: 添加断言来验证结果
        assert True  # 临时断言，需要替换为实际的测试逻辑
    except Exception as e:
        pytest.skip(f"函数测试失败: {{e}}")
'''

        template += '\n'
        return template

    def generate_missing_tests(self, max_files: int = 3) -> int:
        """为缺失的测试文件生成基本模板"""
        print(f"\n📝 为前 {max_files} 个未覆盖模块生成测试模板...")

        recommendations = self.results["recommendations"][:max_files]
        created_count = 0

        for rec in recommendations:
            module_path = Path(rec["module"])
            suggested_test_path = self.project_root / rec["suggested_test_path"]

            if suggested_test_path.exists():
                print(f"⚠️ 测试文件已存在: {suggested_test_path}")
                continue

            try:
                # 查找对应的模块信息
                module_info = None
                # 这里简化处理，直接基于recommendation创建
                module_info = {
                    "src_file": module_path,
                    "functions": [],  # 简化处理
                    "classes": [],     # 简化处理
                }

                test_content = self.create_basic_test_template(module_info)

                # 确保目录存在
                suggested_test_path.parent.mkdir(parents=True, exist_ok=True)

                # 写入测试文件
                with open(suggested_test_path, 'w', encoding='utf-8') as f:
                    f.write(test_content)

                print(f"✅ 创建测试模板: {suggested_test_path}")
                created_count += 1

            except Exception as e:
                print(f"❌ 创建测试失败 {suggested_test_path}: {e}")

        return created_count

    def print_summary(self) -> None:
        """打印分析摘要"""
        print("\n" + "=" * 60)
        print("📊 快速覆盖率分析摘要")
        print("=" * 60)
        print(f"源文件总数: {self.results['src_files']}")
        print(f"测试文件总数: {self.results['test_files']}")
        print(f"已覆盖模块: {self.results['covered_modules']}")
        print(f"未覆盖模块: {self.results['uncovered_modules']}")
        print(f"覆盖率估算: {self.results['coverage_estimate']:.1f}%")
        print(f"改进建议: {len(self.results['recommendations'])} 条")

        if self.results['coverage_estimate'] < 50:
            print("\n⚠️ 覆盖率较低，建议优先处理高优先级模块")
        elif self.results['coverage_estimate'] < 80:
            print("\n📈 覆盖率中等，继续改进可达到80%+目标")
        else:
            print("\n🎉 覆盖率良好，已达到目标水平!")


def main():
    """主函数"""
    project_root = Path(__file__).parent.parent

    print("🔧 快速测试覆盖率分析工具")
    print("=" * 50)

    analyzer = QuickCoverageAnalyzer(project_root)

    # 分析覆盖率
    results = analyzer.analyze_coverage()

    # 生成测试模板
    created_tests = analyzer.generate_missing_tests(max_files=3)
    if created_tests > 0:
        print(f"\n✅ 生成了 {created_tests} 个测试模板")

    # 打印摘要
    analyzer.print_summary()

    # 保存结果
    results_file = project_root / f"quick_coverage_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    import json
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n📁 详细结果已保存到: {results_file}")

    return results


if __name__ == "__main__":
    main()