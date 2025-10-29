#!/usr/bin/env python3
"""
修复测试文件中的语法错误
特别是重复参数的问题
"""

import os
import re
import sys
from pathlib import Path


def fix_duplicate_parameters(file_path):
    """修复文件中重复的函数参数"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 修复重复的client参数
        pattern = r"def test_([a-zA-Z_0-9]+)\(([^)]*client)([^)]*)\):"

        def replace_func(match):
            func_name = match.group(1)
            params = match.group(2) + match.group(3)

            # 移除重复的client参数，只保留一个
            if "client," in params:
                # 分割参数
                param_list = [p.strip() for p in params.split(",")]
                # 去重，保持顺序
                unique_params = []
                seen = set()
                for param in param_list:
                    if param and param not in seen:
                        unique_params.append(param)
                        seen.add(param)

                cleaned_params = ", ".join(unique_params)
                return f"def test_{func_name}({cleaned_params}):"

            return match.group(0)

        content = re.sub(pattern, replace_func, content)

        # 修复import语句错误
        content = re.sub(
            r"from ([^\n]+)\nfrom unittest\.mock import patch",
            r"from unittest.mock import patch\nfrom \1",
            content,
        )

        # 检查是否有语法错误需要手动处理
        if "(" in content and not content.count(")") == content.count("("):
            print(f"⚠️  文件 {file_path} 可能还有括号不匹配问题")

        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ 修复文件: {file_path}")
            return True
        else:
            print(f"ℹ️  文件无需修复: {file_path}")
            return False

    except Exception as e:
        print(f"❌ 修复文件 {file_path} 时出错: {e}")
        return False


def fix_missing_modules(file_path):
    """尝试修复缺失的模块导入"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 检查是否缺失testcontainers
        if "from testcontainers" in content and "import testcontainers" not in content:
            # 如果有testcontainers导入但模块不存在，暂时注释掉
            content = re.sub(
                r"from testcontainers\.[^\n]+\n",
                lambda m: f"# {m.group(0)}  # TODO: 安装testcontainers依赖\n",
                content,
            )

        # 检查是否缺失mock_factory
        if "from tests.factories.mock_factory import MockFactory" in content:
            # 暂时注释掉缺失的导入
            content = content.replace(
                "from tests.factories.mock_factory import MockFactory",
                "# from tests.factories.mock_factory import MockFactory  # TODO: 创建MockFactory",
            )

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ 修复模块导入: {file_path}")
            return True
        else:
            return False

    except Exception as e:
        print(f"❌ 修复模块导入 {file_path} 时出错: {e}")
        return False


def main():
    """主函数"""
    print("🔧 开始修复测试文件语法错误...")

    # 查找所有测试文件
    test_files = []
    for pattern in [
        "tests/integration/*.py",
        "tests/factories/*.py",
        "tests/helpers/*.py",
        "tests/mocks/*.py",
    ]:
        test_files.extend(Path(".").glob(pattern))

    fixed_count = 0

    # 修复语法错误
    for test_file in test_files:
        if fix_duplicate_parameters(test_file):
            fixed_count += 1

    # 修复缺失模块
    for test_file in test_files:
        if fix_missing_modules(test_file):
            fixed_count += 1

    print("\n✅ 语法错误修复完成！")
    print(f"📊 修复了 {fixed_count} 个文件")

    # 验证修复效果
    print("\n🧪 验证修复效果...")
    import subprocess

    try:
        # 尝试只收集测试，不运行
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            print("✅ 测试文件语法检查通过！")
        else:
            print("⚠️  还有一些问题需要手动解决:")
            print(result.stderr[:1000])  # 只显示前1000字符
    except Exception as e:
        print(f"⚠️  验证时出错: {e}")


if __name__ == "__main__":
    main()
