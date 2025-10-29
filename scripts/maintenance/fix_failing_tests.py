#!/usr/bin/env python3
"""
修复失败测试的系统化脚本
系统性地识别和修复常见的测试问题
"""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Dict


class TestFixer:
    """测试修复器"""

    def __init__(self):
        self.root = Path(__file__).parent.parent
        self.fixes_applied = 0

    def get_failing_tests(self) -> List[Tuple[str, str]]:
        """获取失败的测试列表"""
        print("🔍 检测失败的测试...")

        # 运行pytest并收集失败信息
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/",
            "--tb=no",
            "-q",
            "--maxfail=100",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.root)

        failing_tests = []
        for line in result.stdout.split("\n"):
            if "FAILED" in line:
                # 提取测试文件和名称
                match = re.search(r"(tests/.*?\.py::.*?)\s+FAILED", line)
                if match:
                    test_path = match.group(1)
                    failing_tests.append((test_path, line))

        print(f"✅ 发现 {len(failing_tests)} 个失败的测试")
        return failing_tests

    def fix_common_issues(self, file_path: Path) -> int:
        """修复文件中的常见问题"""
        fixes = 0

        if not file_path.exists():
            return fixes

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            original_content = content

            # 1. 修复变量名问题 (data -> _data)
            patterns = [
                # assert data[ -> assert _data[
                (r"assert data\[", "assert _data["),
                # for data in -> for _data in
                (r"\bfor data in\b", "for _data in"),
                # data = response.json() -> _data = response.json()
                (r"\bdata = response\.json\(\)", "_data = response.json()"),
            ]

            for pattern, replacement in patterns:
                if re.search(pattern, content):
                    content = re.sub(pattern, replacement, content)
                    fixes += 1

            # 2. 修复未定义的config变量
            config_patterns = [
                (r"\bconfig\.", "_config."),
                (r"\bconfig\[", "_config["),
                (
                    r"factory\._configs\[.*?\]\s*=\s*config",
                    r"factory._configs[\1] = _config",
                ),
            ]

            for pattern, replacement in config_patterns:
                if re.search(pattern, content):
                    content = re.sub(pattern, replacement, content)
                    fixes += 1

            # 3. 修复未定义的result变量
            result_patterns = [
                (r"\bresult\b", "_result"),
            ]

            # 只在测试文件中应用result修复
            if "test_" in file_path.name:
                for pattern, replacement in result_patterns:
                    # 避免替换类名或方法名
                    content = re.sub(rf"\b{pattern[1:]}\b(?!\s*\()", replacement, content)

            # 4. 修复常见的导入问题
            if "NameError" in str(
                subprocess.run(
                    [sys.executable, "-m", "pytest", str(file_path), "--collect-only"],
                    capture_output=True,
                    text=True,
                )
            ):
                # 检查缺失的导入
                missing_imports = self.find_missing_imports(content)
                for imp in missing_imports:
                    if imp not in content:
                        # 在适当位置添加导入
                        content = self.add_import(content, imp)
                        fixes += 1

            # 5. 修复async/await问题
            if "async def test_" in content:
                # 确保使用了pytest.mark.asyncio
                if "@pytest.mark.asyncio" not in content:
                    content = content.replace(
                        "import pytest",
                        "import pytest\nimport pytest_asyncio\n\n@pytest.mark.asyncio",
                    )
                    fixes += 1

            # 保存修复后的文件
            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  ✅ 修复了 {fixes} 个问题在 {file_path}")

        except Exception as e:
            print(f"  ❌ 修复 {file_path} 时出错: {e}")

        return fixes

    def find_missing_imports(self, content: str) -> List[str]:
        """查找缺失的导入"""
        imports = []

        # 常见的缺失导入
        common_imports = {
            "AdapterConfig": "from src.adapters.factory import AdapterConfig",
            "Adapter": "from src.adapters.base import Adapter",
            "datetime": "from datetime import datetime",
            "date": "from datetime import date",
            "Dict": "from typing import Dict",
            "Any": "from typing import Any",
            "Optional": "from typing import Optional",
            "List": "from typing import List",
            "AsyncMock": "from unittest.mock import AsyncMock",
            "Mock": "from unittest.mock import Mock",
            "patch": "from unittest.mock import patch",
        }

        for name, import_stmt in common_imports.items():
            if name in content and import_stmt not in content:
                imports.append(import_stmt)

        return imports

    def add_import(self, content: str, import_stmt: str) -> str:
        """添加导入语句"""
        lines = content.split("\n")

        # 找到合适的插入位置（在其他导入之后）
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                insert_idx = i + 1

        lines.insert(insert_idx, import_stmt)
        return "\n".join(lines)

    def fix_test_files(self, test_dir: Path = None) -> Dict[str, int]:
        """批量修复测试文件"""
        if test_dir is None:
            test_dir = self.root / "tests" / "unit"

        print(f"\n🔧 开始修复测试文件在: {test_dir}")

        fix_stats = {"files_processed": 0, "fixes_applied": 0, "errors": 0}

        for py_file in test_dir.rglob("*.py"):
            if py_file.name.startswith("test_"):
                fixes = self.fix_common_issues(py_file)
                if fixes > 0:
                    fix_stats["files_processed"] += 1
                    fix_stats["fixes_applied"] += fixes

        return fix_stats

    def run_specific_test(self, test_path: str) -> bool:
        """运行特定测试查看是否通过"""
        cmd = [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0

    def generate_fix_report(self, stats: Dict[str, int]):
        """生成修复报告"""
        print("\n" + "=" * 60)
        print("📊 测试修复报告")
        print("=" * 60)
        print(f"📁 处理的文件数: {stats['files_processed']}")
        print(f"🔧 应用的修复数: {stats['fixes_applied']}")
        print(f"❌ 错误数: {stats['errors']}")

        if stats["fixes_applied"] > 0:
            print("\n✅ 修复完成！建议重新运行测试验证效果。")
            print("\n推荐的验证命令:")
            print("  python -m pytest tests/unit/ -x --tb=short -q")
        else:
            print("\nℹ️  没有发现可自动修复的问题。")


def main():
    """主函数"""
    print("🚀 测试修复工具启动")
    print("=" * 60)

    fixer = TestFixer()

    # 获取用户选择
    print("\n请选择修复模式:")
    print("1. 修复所有测试文件")
    print("2. 只修复失败的测试文件")
    print("3. 修复指定目录")

    choice = input("\n请输入选择 (1-3): ").strip()

    if choice == "1":
        # 修复所有测试文件
        stats = fixer.fix_test_files()

    elif choice == "2":
        # 先获取失败的测试
        failing_tests = fixer.get_failing_tests()

        # 收集失败的文件路径
        failed_files = set()
        for test_path, _ in failing_tests:
            file_path = Path(test_path.split("::")[0])
            failed_files.add(file_path)

        # 修复失败的文件
        stats = {"files_processed": 0, "fixes_applied": 0, "errors": 0}
        for file_path in failed_files:
            fixes = fixer.fix_common_issues(file_path)
            if fixes > 0:
                stats["files_processed"] += 1
                stats["fixes_applied"] += fixes

    elif choice == "3":
        # 修复指定目录
        dir_path = input("请输入目录路径 (相对或绝对): ").strip()
        test_dir = Path(dir_path)
        if not test_dir.is_absolute():
            test_dir = Path.cwd() / test_dir

        stats = fixer.fix_test_files(test_dir)

    else:
        print("❌ 无效的选择")
        return

    # 生成报告
    fixer.generate_fix_report(stats)


if __name__ == "__main__":
    main()
