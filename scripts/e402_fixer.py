#!/usr/bin/env python3
"""
E402模块导入位置规范化工具
解决模块导入位置问题
"""

from pathlib import Path


def fix_e402_in_file(file_path):
    """修复单个文件中的E402错误"""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        original_content = content
        lines = content.split('\n')
        if not lines:
            return 0

        # 找到文档字符串的结束位置
        docstring_end = 0
        in_docstring = False
        docstring_delimiter = None

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 检查文档字符串开始
            if not in_docstring and ('"""' in stripped or "'''" in stripped):
                in_docstring = True
                if stripped.count('"""') == 2 or stripped.count("'''") == 2:
                    # 单行文档字符串
                    docstring_end = i + 1
                    in_docstring = False
                else:
                    # 多行文档字符串开始
                    docstring_delimiter = '"""' if '"""' in stripped else "'''"
                continue

            # 检查文档字符串结束
            if in_docstring and docstring_delimiter in stripped:
                docstring_end = i + 1
                in_docstring = False
                docstring_delimiter = None
                continue

            # 在文档字符串结束后开始检查导入
            if not in_docstring and stripped.startswith(('import ', 'from ')):
                # 这是第一个导入，文档字符串应该在这之前结束
                if docstring_end == 0:
                    docstring_end = i
                break

        # 提取所有模块级导入
        imports = []
        other_lines = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 检查是否是导入行
            if stripped.startswith(('import ', 'from ')):
                # 这是需要移动的导入
                imports.append(line.rstrip())
            else:
                # 这是其他内容
                other_lines.append(line)

        # 重新组织文件
        if imports:
            # 在文档字符串后添加导入
            if docstring_end == 0:
                # 如果没有找到文档字符串结束，将导入添加到文件开头
                new_content = '\n'.join(imports) + '\n' + '\n'.join(lines)
            else:
                # 在文档字符串后插入导入
                before_docstring = lines[:docstring_end]
                after_docstring = lines[docstring_end:]

                new_content = []
                new_content.extend(before_docstring)
                new_content.append('')  # 空行
                new_content.extend(imports)
                new_content.append('')  # 空行
                new_content.extend(after_docstring)

                new_content = '\n'.join(new_content)
        else:
            new_content = content

        # 写回文件
        if new_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return len(imports)
        else:
            return 0

    except Exception:
        return 0

def main():
    """主函数"""
    # 优先处理主要文件
    target_files = [
        "src/main.py",
        "src/collectors/oddsportal_integration.py",
        "src/services/betting/ev_calculator.py",
        "src/tasks/maintenance_tasks.py"
    ]

    total_fixes = 0

    for file_path in target_files:
        path = Path(file_path)
        if path.exists():
            fixes = fix_e402_in_file(path)
            total_fixes += fixes
        else:
            pass


    # 验证修复效果
    import subprocess

    try:
        result = subprocess.run(
            'ruff check src/main.py --select=E402 --output-format=concise | wc -l',
            shell=True,
            capture_output=True,
            text=True
        )

        remaining = int(result.stdout.strip()) if result.stdout.strip() else 0

        if remaining == 0:
            pass
        else:
            pass

    except Exception:
        pass

if __name__ == "__main__":
    main()
