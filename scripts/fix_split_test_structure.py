#!/usr/bin/env python3
"""
修复拆分测试文件的类结构
"""

import os
import re


def fix_test_file_structure(filepath):
    """修复测试文件的类结构"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")
        fixed_lines = []

        # 添加文件头
        fixed_lines.append(lines[0])  # 保留第一行的docstring开始

        # 找到docstring结束位置
        docstring_end = 1
        for i in range(1, len(lines)):
            if '"""' in lines[i]:
                docstring_end = i + 1
                break

        # 保留docstring内容
        for i in range(1, docstring_end):
            fixed_lines.append(lines[i])

        # 添加导入
        fixed_lines.append("\n")
        fixed_lines.append("import pytest\n")
        fixed_lines.append("from unittest.mock import Mock, patch\n")
        fixed_lines.append("import sys\n")
        fixed_lines.append("import os\n")

        # 添加测试类
        class_name = (
            os.path.basename(filepath)
            .replace(".py", "")
            .replace("test_", "")
            .title()
            .replace("_", "")
        )
        class_name = re.sub(r"[^a-zA-Z0-9]", "", class_name)
        fixed_lines.append(f"\n\nclass Test{class_name}:\n")
        fixed_lines.append('    """测试类"""\n\n')

        # 处理测试函数
        in_class = False
        for i in range(docstring_end, len(lines)):
            line = lines[i]

            # 跳过原有的导入语句
            if line.strip().startswith("import ") or line.strip().startswith("from "):
                continue

            # 识别测试函数
            if re.match(r"^def\s+test_\w+", line):
                # 添加到类中，增加缩进
                fixed_lines.append("    " + line)
                in_class = True
            elif (
                in_class
                and line.strip()
                and not line.startswith("    ")
                and not line.strip().startswith("#")
            ):
                # 遇到下一个函数或类定义，说明当前函数结束
                if re.match(r"def\s+test_\w+", line):
                    fixed_lines.append("    " + line)
                else:
                    # 非测试函数，跳过
                    continue
            elif in_class:
                # 在类内的代码，保持缩进或增加缩进
                if line.strip() == "":
                    fixed_lines.append(line)
                elif line.startswith("    "):
                    fixed_lines.append(line)
                else:
                    fixed_lines.append("    " + line)

        # 写回文件
        fixed_content = "\n".join(fixed_lines)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(fixed_content)

        return True
    except Exception as e:
        print(f"修复文件 {filepath} 时出错: {e}")
        return False


def main():
    """主函数"""
    # 查找所有拆分的文件
    import glob

    pattern = "tests/unit/utils/test_date_time_utils_part_*.py"
    split_files = glob.glob(pattern)

    print("🔧 修复拆分测试文件结构...")
    print(f"找到 {len(split_files)} 个拆分文件")

    fixed_count = 0
    for filepath in split_files:
        filename = os.path.basename(filepath)
        print(f"  修复: {filename}")

        if fix_test_file_structure(filepath):
            print("  ✅ 修复成功")
            fixed_count += 1
        else:
            print("  ❌ 修复失败")

    print(f"\n📊 修复总结: {fixed_count}/{len(split_files)} 个文件已修复")

    # 验证一个文件
    if split_files:
        test_file = split_files[0]
        print(f"\n🔍 验证修复效果: {os.path.basename(test_file)}")
        try:
            import subprocess

            result = subprocess.run(
                ["python3", "-m", "pytest", test_file, "--collect-only", "-q"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                print("  ✅ 测试文件结构正确")
            else:
                print(f"  ❌ 仍有问题: {result.stderr}")
        except Exception as e:
            print(f"  ⚠️ 验证失败: {e}")


if __name__ == "__main__":
    main()
