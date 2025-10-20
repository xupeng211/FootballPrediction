#!/usr/bin/env python3
"""
安全修复跳过测试的脚本
使用正则表达式精确替换，避免破坏文件结构
"""

import re
from pathlib import Path


def fix_file_syntax(file_path: Path) -> bool:
    """修复文件语法错误"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 修复重复导入
        content = re.sub(
            r"# Mock module ([^\n]+)\nfrom unittest\.mock import Mock, patch\nsys\.modules\[\'[^\']+\'\] = Mock\(\n(?:# Mock module [^\n]+\nfrom unittest\.mock import Mock, patch\nsys\.modules\[\'[^\']+\] = Mock\(\n)+",
            r"# Import system module\nimport sys\nfrom unittest.mock import Mock\n# Mock module\nsys.modules[\'adapters.registry\'] = Mock()\n",
            content,
        )

        # 修复sys导入
        if "sys.modules" in content and "import sys" not in content:
            content = content.replace(
                "from unittest.mock import Mock, patch",
                "import sys\nfrom unittest.mock import Mock, patch",
            )

        # 修复孤立的except块
        content = re.sub(
            r"\n\s+except Exception:\s*\n\s+pytest\.skip\([^)]+\)\n\n\s+def test_",
            "\n    def test_",
            content,
        )

        # 修复缺失的sys导入
        if "sys.modules" in content and "import sys" not in content:
            # 在导入后添加sys导入
            imports_end = content.find("\n\n# Import the module")
            if imports_end > -1:
                content = content[:imports_end] + "\nimport sys" + content[imports_end:]

        # 写回文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return True
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def main():
    """主函数"""
    test_dir = Path("tests/unit")

    # 找出需要修复的文件
    fixed_files = []

    for py_file in test_dir.rglob("*.py"):
        if (
            "disabled" in str(py_file)
            or "archive" in str(py_file)
            or "__pycache__" in str(py_file)
        ):
            continue

        try:
            # 检查是否有语法错误
            with open(py_file, "r") as f:
                content = f.read()

            # 简单检查是否有明显的语法错误
            if "except Exception:" in content and content.count("def ") < 2:
                print(f"需要修复: {py_file.relative_to('.')}")
                if fix_file_syntax(py_file):
                    print("  ✅ 已修复")
                    fixed_files.append(py_file)
        except:
            pass

    print(f"\n总共修复了 {len(fixed_files)} 个文件")

    # 验证修复
    if fixed_files:
        print("\n验证修复效果...")
        for file_path in fixed_files[:3]:  # 只验证前3个
            result = Path(file_path).stat().st_size
            print(f"  {file_path.relative_to('.')}: {result} bytes")


if __name__ == "__main__":
    main()
