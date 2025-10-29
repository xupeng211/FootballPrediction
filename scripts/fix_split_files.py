#!/usr/bin/env python3
"""
修复拆分文件的缩进问题
"""

import os
import re


def fix_split_file_indentation(filepath):
    """修复拆分文件的缩进问题"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")
        fixed_lines = []

        for i, line in enumerate(lines):
            if i < 9:  # 前9行保持不变（文件头）
                fixed_lines.append(line)
            else:
                # 从第10行开始，修复缩进
                if line.strip():
                    # 检查是否是函数定义
                    if re.match(r"^\s+def\s+\w+", line):
                        # 修复函数定义的缩进
                        fixed_lines.append(line.lstrip())
                    elif re.match(r"^\s+class\s+\w+", line):
                        # 修复类定义的缩进
                        fixed_lines.append(line.lstrip())
                    elif re.match(r"^\s+@(?:pytest\.mark\.)?\w+", line):
                        # 修复装饰器的缩进
                        fixed_lines.append(line.lstrip())
                    else:
                        # 其他行，如果缩进过深，减少一层
                        if line.startswith("            "):  # 12个空格
                            # 检查是否应该保持深层缩进
                            if line.strip().startswith(
                                (
                                    "if ",
                                    "for ",
                                    "while ",
                                    "try:",
                                    "except",
                                    "with ",
                                    "elif",
                                    "else:",
                                )
                            ):
                                fixed_lines.append("        " + line.lstrip())  # 8个空格
                            else:
                                fixed_lines.append("    " + line.lstrip())  # 4个空格
                        elif line.startswith("        "):  # 8个空格
                            fixed_lines.append(line)
                        elif line.startswith("    "):  # 4个空格
                            fixed_lines.append(line)
                        else:
                            # 没有缩进的行，可能是空行或注释
                            fixed_lines.append(line)
                else:
                    fixed_lines.append(line)

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
    # 需要修复的拆分文件
    split_files = [
        "tests/unit/domain/test_prediction_algorithms_part_2.py",
        "tests/unit/domain/test_prediction_algorithms_part_3.py",
        "tests/unit/domain/test_prediction_algorithms_part_4.py",
        "tests/unit/domain/test_prediction_algorithms_part_5.py",
    ]

    print("🔧 修复拆分文件的缩进问题...")

    fixed_count = 0
    for filepath in split_files:
        if os.path.exists(filepath):
            print(f"  修复: {os.path.basename(filepath)}")
            if fix_split_file_indentation(filepath):
                print(f"  ✅ 修复成功: {os.path.basename(filepath)}")
                fixed_count += 1
            else:
                print(f"  ❌ 修复失败: {os.path.basename(filepath)}")
        else:
            print(f"  ⚠️ 文件不存在: {filepath}")

    print(f"\n📊 修复总结: {fixed_count}/{len(split_files)} 个文件已修复")


if __name__ == "__main__":
    main()
