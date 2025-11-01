#!/usr/bin/env python3
"""
覆盖率差异分析工具
对比原版系统和v2.0系统的模块识别差异
"""

import ast
from pathlib import Path
from typing import Set

class CoverageComparisonAnalyzer:
    """覆盖率差异分析器"""

    def __init__(self):
        self.test_root = Path(__file__).parent
        self.src_root = self.test_root.parent / "src"

    def extract_imports_from_file(self, file_path: Path) -> Set[str]:
        """从文件中提取导入"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content)

            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
            return imports
        except (SyntaxError, ValueError):
            return set()

    def filter_imports_v1(self, imports: Set[str]) -> Set[str]:
        """原版系统过滤策略 (7个前缀)"""
        internal_prefixes = ['core.', 'database.', 'services.', 'api.', 'domain.', 'config.', 'adapters.']

        internal_imports = {
            imp for imp in imports
            if any(imp.startswith(prefix) for prefix in internal_prefixes)
        }
        return internal_imports

    def filter_imports_v2(self, imports: Set[str]) -> Set[str]:
        """v2.0系统过滤策略 (19个前缀)"""
        internal_prefixes = [
            'core.', 'database.', 'services.', 'api.',
            'domain.', 'config.', 'adapters.', 'cache.',
            'monitoring.', 'middleware.', 'decorators.',
            'performance.', 'security.', 'utils.',
            'cqrs.', 'realtime.', 'timeseries.',
            'ml.', 'data.', 'tasks.', 'patterns.'
        ]

        internal_imports = {
            imp for imp in imports
            if any(imp.startswith(prefix) for prefix in internal_prefixes)
        }
        return internal_imports

    def discover_project_modules(self) -> Set[str]:
        """发现项目所有模块"""
        modules = set()

        if not self.src_root.exists():
            return modules

        for py_file in self.src_root.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            try:
                relative_path = py_file.relative_to(self.src_root)
                module_path = str(relative_path.with_suffix('')).replace("/", ".")
                modules.add(module_path)
            except ValueError:
                continue

        return modules

    def analyze_coverage_difference(self):
        """分析覆盖率差异"""
        print("🔍 开始分析覆盖率差异原因...")
        print("=" * 60)

        # 1. 发现所有测试文件
        test_files = list(self.test_root.glob("test_*.py"))
        test_files = [f for f in test_files if f.is_file() and f.name != "__init__.py"]

        print(f"📁 发现测试文件: {len(test_files)}个")

        # 2. 收集所有导入
        all_imports = set()
        v1_covered = set()
        v2_covered = set()

        for test_file in test_files:
            imports = self.extract_imports_from_file(test_file)
            all_imports.update(imports)

            v1_covered.update(self.filter_imports_v1(imports))
            v2_covered.update(self.filter_imports_v2(imports))

        # 3. 发现项目模块
        project_modules = self.discover_project_modules()

        print("\n📊 导入统计分析:")
        print(f"  🔍 总导入数: {len(all_imports)}")
        print(f"  📦 项目模块总数: {len(project_modules)}")
        print(f"  ✅ v1系统覆盖: {len(v1_covered)}个")
        print(f"  ✅ v2系统覆盖: {len(v2_covered)}个")

        # 4. 计算覆盖率
        v1_coverage = (len(v1_covered) / len(project_modules) * 100) if project_modules else 0
        v2_coverage = (len(v2_covered) / len(project_modules) * 100) if project_modules else 0

        print("\n📈 覆盖率计算:")
        print(f"  🎯 v1系统覆盖率: {v1_coverage:.1f}%")
        print(f"  🚀 v2系统覆盖率: {v2_coverage:.1f}%")
        print(f"  📊 差异: +{v2_coverage - v1_coverage:.1f}个百分点")

        # 5. 分析差异来源
        v2_only = v2_covered - v1_covered

        print(f"\n🔍 v2系统额外覆盖的模块 ({len(v2_only)}个):")

        # 按前缀分组
        prefix_groups = {}
        for module in sorted(v2_only):
            for prefix in ['cache.', 'monitoring.', 'middleware.', 'decorators.',
                          'performance.', 'security.', 'utils.', 'cqrs.',
                          'realtime.', 'timeseries.', 'ml.', 'data.', 'tasks.', 'patterns.']:
                if module.startswith(prefix):
                    if prefix not in prefix_groups:
                        prefix_groups[prefix] = []
                    prefix_groups[prefix].append(module)
                    break

        for prefix, modules in prefix_groups.items():
            print(f"\n  📂 {prefix} ({len(modules)}个):")
            for module in modules[:10]:  # 显示前10个
                print(f"    ✅ {module}")
            if len(modules) > 10:
                print(f"    ... 还有 {len(modules) - 10} 个")

        # 6. 核心发现总结
        print("\n🎯 核心发现总结:")
        print(f"  📈 覆盖率提升: {v2_coverage - v1_coverage:.1f}个百分点")
        print("  🔧 提升原因: v2.0系统扩展了模块识别范围")
        print("  📊 前缀扩展: 从7个增加到19个 (+171%)")
        print("  ✨ 技术本质: 更全面的模块覆盖率统计")

        print("\n💡 结论:")
        print("  v2.0系统的'惊人突破'主要是由于:")
        print("  1. 扩展了内部模块的识别范围")
        print("  2. 包含了更多项目模块类别")
        print("  3. 更准确地反映了项目的真实模块覆盖情况")
        print("  4. 不是性能突破，而是统计准确性的提升")

def main():
    """主函数"""
    analyzer = CoverageComparisonAnalyzer()
    analyzer.analyze_coverage_difference()

if __name__ == "__main__":
    main()