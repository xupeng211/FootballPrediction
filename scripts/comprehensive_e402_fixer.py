#!/usr/bin/env python3
"""
全面的E402模块导入位置修复工具
处理剩余的58个E402错误
"""

import subprocess
from pathlib import Path


def find_e402_files() -> list[dict]:
    """查找所有E402错误"""
    try:
        result = subprocess.run(
            ['ruff', 'check', '--select=E402', '--output-format=json'],
            capture_output=True,
            text=True,
            cwd='src'
        )

        files = set()
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip() and 'E402' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        files.add(parts[0])
        return sorted(files)
    except Exception:
        return []

def fix_e402_in_file(file_path: Path) -> int:
    """修复单个文件中的E402错误"""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        original_content = content
        lines = content.split('\n')
        if not lines:
            return 0

        # 查找文档字符串结束位置
        docstring_end = 0
        in_docstring = False
        docstring_delimiter = None

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 检查文档字符串开始
            if not in_docstring and ('"""' in stripped or "'''" in stripped):
                in_docstring = True
                if stripped.count('"""') == 2 or stripped.count("''") == 2:
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

            # 检查第一个导入
            if not in_docstring and stripped.startswith(('import ', 'from ')):
                if docstring_end == 0:
                    docstring_end = i
                break

        # 提取所有导入
        imports = []
        other_lines = []

        # 第二次遍历，分离导入和其他内容
        for i, line in enumerate(lines):
            stripped = line.strip()

            if stripped.startswith(('import ', 'from ')):
                imports.append(line.rstrip())
            else:
                other_lines.append(line)

        # 重新组织文件
        if imports:
            new_content = []

            # 文档字符串部分
            new_content.extend(lines[:docstring_end])
            new_content.append('')  # 空行分隔

            # 导入部分
            new_content.extend(imports)
            new_content.append('')  # 空行分隔

            # 其他内容
            new_content.extend(other_lines[docstring_end:])

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

    # 查找E402文件
    files_to_fix = find_e402_files()

    if not files_to_fix:
        return

    for file_path in files_to_fix:
        pass

    total_fixes = 0

    # 修复每个文件
    for file_path_str in files_to_fix:
        file_path = Path(file_path_str)
        fixes = fix_e402_in_file(file_path)
        total_fixes += fixes
        if fixes > 0:
            pass
        else:
            pass


    # 验证修复效果
    try:
        result = subprocess.run(
            ['ruff', 'check', '--select=E402', 'src/', '--output-format=concise'],
            capture_output=True,
            text=True
        )
        remaining = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0

        if remaining == 0:
            pass
        else:
            pass

    except Exception:
        pass

if __name__ == "__main__":
    main()
