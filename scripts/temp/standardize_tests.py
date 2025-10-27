#!/usr/bin/env python3
"""
测试文件标准化脚本
自动为测试文件添加pytest标记和重命名文件
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Dict, Set

class TestStandardizer:
    def __init__(self, tests_dir: str = "tests"):
        self.tests_dir = Path(tests_dir)
        self.standardized_count = 0
        self.renamed_count = 0
        self.errors = []

    def identify_test_type(self, file_path: Path) -> List[str]:
        """根据文件路径和内容识别测试类型"""
        markers = []

        # 基于路径推断标记
        path_str = str(file_path)

        if "unit" in path_str:
            markers.append("unit")
        elif "integration" in path_str:
            markers.append("integration")
        elif "e2e" in path_str:
            markers.append("e2e")
        elif "performance" in path_str:
            markers.append("performance")

        if "api" in path_str:
            markers.append("api")
        if "database" in path_str:
            markers.append("database")
        if "cache" in path_str:
            markers.append("cache")
        if "auth" in path_str:
            markers.append("auth")
        if "monitoring" in path_str:
            markers.append("monitoring")
        if "streaming" in path_str:
            markers.append("streaming")

        # 读取文件内容推断额外标记
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if "external_api" in content or "http" in content.lower():
                markers.append("external_api")
            if "docker" in content.lower():
                markers.append("docker")
            if "slow" in content.lower() or "sleep(" in content:
                markers.append("slow")
            if "critical" in content.lower():
                markers.append("critical")

        except Exception as e:
            self.errors.append(f"Error reading {file_path}: {e}")

        return markers

    def generate_standard_name(self, file_path: Path) -> str:
        """生成标准化的测试文件名"""
        if file_path.name.startswith("test_"):
            return file_path.name  # 已经符合规范

        # 获取模块信息
        base_name = file_path.stem

        # 如果已经是标准格式但缺少test_前缀
        if base_name.endswith("_test"):
            base_name = f"test_{base_name[:-5]}"
        else:
            base_name = f"test_{base_name}"

        return f"{base_name}.py"

    def add_pytest_markers(self, file_path: Path, markers: List[str]) -> bool:
        """为测试文件添加pytest标记"""
        if not markers:
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查是否已经有标记
            if "@pytest.mark" in content:
                return False  # 已有标记，跳过

            # 找到第一个测试类或函数
            lines = content.split('\n')
            insert_index = -1

            for i, line in enumerate(lines):
                if line.strip().startswith('class Test') or line.strip().startswith('def test_'):
                    insert_index = i
                    break

            if insert_index == -1:
                return False  # 没有找到测试函数或类

            # 插入标记
            marker_lines = []
            for marker in markers:
                marker_lines.append(f"@pytest.mark.{marker}")

            # 在标记后添加空行
            marker_lines.append("")

            # 重新组合内容
            lines[insert_index:insert_index] = marker_lines
            new_content = '\n'.join(lines)

            # 确保有pytest导入
            if "import pytest" not in new_content:
                # 在第一个import后添加pytest导入
                import_index = -1
                for i, line in enumerate(lines):
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
                        import_index = i + 1
                        break

                if import_index > -1:
                    lines = new_content.split('\n')
                    lines.insert(import_index, "import pytest")
                    new_content = '\n'.join(lines)

            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return True

        except Exception as e:
            self.errors.append(f"Error adding markers to {file_path}: {e}")
            return False

    def rename_file(self, file_path: Path, new_name: str) -> bool:
        """重命名测试文件"""
        try:
            new_path = file_path.parent / new_name
            if new_path.exists():
                return False  # 目标文件已存在

            file_path.rename(new_path)
            return True

        except Exception as e:
            self.errors.append(f"Error renaming {file_path} to {new_name}: {e}")
            return False

    def process_directory(self, directory: Path) -> Dict[str, int]:
        """处理目录中的所有测试文件"""
        stats = {
            'total_files': 0,
            'renamed_files': 0,
            'marked_files': 0,
            'errors': 0
        }

        # 递归查找所有Python文件
        for file_path in directory.rglob("*.py"):
            if file_path.name in ["__init__.py", "conftest.py"]:
                continue  # 跳过配置文件

            stats['total_files'] += 1

            # 1. 识别测试类型
            markers = self.identify_test_type(file_path)

            # 2. 添加pytest标记
            if self.add_pytest_markers(file_path, markers):
                stats['marked_files'] += 1
                self.standardized_count += 1

            # 3. 重命名文件（如果需要）
            if not file_path.name.startswith("test_"):
                new_name = self.generate_standard_name(file_path)
                if self.rename_file(file_path, new_name):
                    stats['renamed_files'] += 1
                    self.renamed_count += 1

        return stats

    def run(self) -> Dict[str, any]:
        """执行标准化流程"""
        print("🧪 开始测试文件标准化...")

        if not self.tests_dir.exists():
            raise FileNotFoundError(f"Tests directory {self.tests_dir} not found")

        # 处理所有文件
        stats = self.process_directory(self.tests_dir)

        result = {
            'stats': stats,
            'standardized_count': self.standardized_count,
            'renamed_count': self.renamed_count,
            'errors': self.errors
        }

        return result

def main():
    """主函数"""
    standardizer = TestStandardizer()

    try:
        result = standardizer.run()

        print("\n✅ 标准化完成!")
        print(f"📊 处理文件总数: {result['stats']['total_files']}")
        print(f"🏷️  添加标记文件: {result['stats']['marked_files']}")
        print(f"📝 重命名文件: {result['stats']['renamed_files']}")
        print(f"❌ 错误数量: {len(result['errors'])}")

        if result['errors']:
            print("\n⚠️ 错误详情:")
            for error in result['errors'][:10]:  # 只显示前10个错误
                print(f"  - {error}")

        return result

    except Exception as e:
        print(f"❌ 标准化失败: {e}")
        return None

if __name__ == "__main__":
    main()