#!/usr/bin/env python3
"""
批量修复E402模块导入位置错误的工具
"""

from pathlib import Path


def fix_e402_in_file(file_path):
    """修复单个文件中的E402错误"""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        original_content = content
        lines = content.split('\n')

        # 提取所有模块级导入
        imports = []
        non_import_lines = []
        in_import_section = True

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 检查是否是导入行
            if stripped.startswith(('import ', 'from ')):
                if in_import_section:
                    imports.append(line)
                else:
                    # 这是一个需要移动的导入
                    non_import_lines.append(('import', i, line))
            elif stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
                if in_import_section:
                    in_import_section = False
                    non_import_lines.append(('code', i, line))
                else:
                    non_import_lines.append(('code', i, line))
            elif stripped.startswith('#') or not stripped:
                non_import_lines.append(('other', i, line))

        # 如果没有需要移动的导入，跳过
        moved_imports = [item for item in non_import_lines if item[0] == 'import']
        if not moved_imports:
            return 0

        # 重新组织文件内容
        new_imports = imports + [item[2] for item in moved_imports]
        other_lines = [item[2] for item in non_import_lines if item[0] != 'import']

        # 查找文档字符串的结束位置
        docstring_end = 0
        in_docstring = False
        for i, line in enumerate(lines):
            if '"""' in line:
                if not in_docstring:
                    in_docstring = True
                    if line.count('"""') == 2:
                        # 单行文档字符串
                        in_docstring = False
                        docstring_end = i + 1
                else:
                    in_docstring = False
                    docstring_end = i + 1
                    break

        # 构建新内容
        if docstring_end > 0:
            # 保留文档字符串前的内容
            before_docstring = lines[:docstring_end]
            # 添加导入
            # 移除文档字符串中已有的重复导入
            new_content_lines = before_docstring + [''] + new_imports + [''] + lines[docstring_end:]
        else:
            new_content_lines = new_imports + [''] + other_lines

        new_content = '\n'.join(new_content_lines)

        # 写回文件
        if new_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return len(moved_imports)
        else:
            return 0

    except Exception:
        return 0

def main():
    """主函数"""
    src_dir = Path("src")
    total_fixes = 0


    # 优先处理API文件
    api_files = list(src_dir.glob("api/**/*.py"))
    for file_path in api_files:
        if file_path.is_file():
            fixes = fix_e402_in_file(file_path)
            total_fixes += fixes

    # 处理其他重要文件
    important_files = [
        src_dir / "main.py",
        src_dir / "collectors/oddsportal_integration.py",
        src_dir / "services/betting/ev_calculator.py",
        src_dir / "tasks/maintenance_tasks.py"
    ]

    for file_path in important_files:
        if file_path.is_file():
            fixes = fix_e402_in_file(file_path)
            total_fixes += fixes


if __name__ == "__main__":
    main()
