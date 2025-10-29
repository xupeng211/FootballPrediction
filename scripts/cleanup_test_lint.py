#!/usr/bin/env python3
"""
清理测试文件中的 lint 错误
"""

import re
from pathlib import Path


def fix_unused_imports(file_path):
    """修复未使用的导入"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # 移除未使用的导入（简单模式）
    # F401 错误 - 移除单行的未使用导入
    lines = content.split("\n")
    new_lines = []

    for i, line in enumerate(lines):
        line_stripped = line.strip()

        # 跳过文档字符串
        if line_stripped.startswith('"""') or line_stripped.startswith("'''"):
            new_lines.append(line)
            if line_stripped.count('"""') == 1 or line_stripped.count("'''") == 1:
                # 跨行文档字符串
                if line_stripped.count('"""') == 1:
                    end_marker = '"""'
                else:
                    end_marker = "'''"
                # 找到结束
                j = i + 1
                while j < len(lines) and end_marker not in lines[j]:
                    new_lines.append(lines[j])
                    j += 1
                if j < len(lines):
                    new_lines.append(lines[j])
            continue

        # 保留非导入行
        if not line_stripped.startswith("import ") and not line_stripped.startswith("from "):
            new_lines.append(line)
            continue

        # 检查是否在注释中
        if line_stripped.startswith("#"):
            new_lines.append(line)
            continue

        # 对于导入行，暂时保留（需要更复杂的分析）
        new_lines.append(line)

    content = "\n".join(new_lines)

    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"修复了未使用的导入: {file_path}")
        return True

    return False


def fix_bare_except(file_path):
    """修复裸露的 except"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # 替换 bare except
    content = re.sub(r"except Exception:\s*$", "except Exception:", content)
    content = re.sub(r"except Exception:\s*#", "except Exception:  #", content)

    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"修复了裸露的 except Exception: {file_path}")
        return True

    return False


def fix_module_level_imports(file_path):
    """修复模块级导入位置"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")

    # 找到所有导入行
    import_lines = []
    other_lines = []
    in_docstring = False

    for line in lines:
        stripped = line.strip()

        # 处理文档字符串
        if stripped.startswith('"""') or stripped.startswith("'''"):
            in_docstring = not in_docstring
            other_lines.append(line)
            continue

        if in_docstring:
            other_lines.append(line)
            continue

        # 收集导入行
        if stripped.startswith("import ") or stripped.startswith("from "):
            import_lines.append(line)
        else:
            other_lines.append(line)

    # 重新组织文件
    new_content = "\n".join(import_lines + [""] + other_lines)

    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"修复了模块级导入位置: {file_path}")
        return True

    return False


def main():
    """主函数"""
    print("开始清理测试文件中的 lint 错误...\n")

    test_dir = Path("tests")
    fixed_count = 0

    # 遍历所有 Python 测试文件
    for py_file in test_dir.rglob("*.py"):
        if py_file.name.startswith("."):
            continue

        file_path = str(py_file)
        fixed = False

        # 修复各种问题
        if fix_bare_except(file_path):
            fixed = True

        if fix_module_level_imports(file_path):
            fixed = True

        # 暂时不自动修复未使用的导入（需要更复杂的分析）
        # if fix_unused_imports(file_path):
        #     fixed = True

        if fixed:
            fixed_count += 1

    print(f"\n清理完成！共修复了 {fixed_count} 个文件。")

    if fixed_count > 0:
        print("\n建议运行以下命令检查修复结果：")
        print("make lint")
        print("make test-quick")


if __name__ == "__main__":
    main()
