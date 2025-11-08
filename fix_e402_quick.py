#!/usr/bin/env python3
"""
快速修复E402导入顺序错误的脚本
"""

import re
from pathlib import Path

def fix_e402_in_file(file_path: Path) -> bool:
    """修复单个文件的E402错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        if len(lines) < 5:
            return False

        # 查找文档字符串模式
        docstring_pattern = r'^"""[\s\S]*?"""'

        # 分离导入、文档字符串和代码
        imports_before_docstring = []
        docstring_lines = []
        imports_after_docstring = []
        other_lines = []

        i = 0
        # 收集文档字符串前的导入
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith(('import ', 'from ')):
                imports_before_docstring.append(lines[i])
                i += 1
            elif line.startswith('"""') and not docstring_lines:
                # 找到文档字符串开始
                docstring_start = i
                if '"""' in lines[i][3:]:
                    # 单行文档字符串
                    docstring_lines.append(lines[i])
                    i += 1
                else:
                    # 多行文档字符串
                    docstring_lines.append(lines[i])
                    i += 1
                    while i < len(lines) and '"""' not in lines[i]:
                        docstring_lines.append(lines[i])
                        i += 1
                    if i < len(lines):
                        docstring_lines.append(lines[i])
                        i += 1
                break
            else:
                break

        # 收集文档字符串后的导入和代码
        in_docstring = bool(docstring_lines)
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith(('import ', 'from ')) and not in_docstring:
                imports_after_docstring.append(lines[i])
                i += 1
            else:
                if line.startswith('"""'):
                    in_docstring = not in_docstring
                other_lines.append(lines[i])
                i += 1

        # 如果没有找到需要修复的模式，返回False
        if not imports_before_docstring and not imports_after_docstring:
            return False

        # 重新组织内容
        new_lines = []

        # 添加所有导入
        all_imports = imports_before_docstring + imports_after_docstring
        if all_imports:
            new_lines.extend(all_imports)
            new_lines.append('')

        # 添加文档字符串
        if docstring_lines:
            new_lines.extend(docstring_lines)
            new_lines.append('')

        # 添加其他代码
        new_lines.extend(other_lines)

        # 写回文件
        new_content = '\n'.join(new_lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True

    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {e}")
        return False

def main():
    """主函数"""
    # 手动指定需要修复的文件列表
    files_to_fix = [
        "src/facades/subsystems/database.py",
        "src/quality_gates/gate_system.py",
        "src/realtime/match_api.py",
        "src/scheduler/celery_config.py"
    ]

    fixed_count = 0
    for file_str in files_to_fix:
        file_path = Path(file_str)
        if file_path.exists():
            if fix_e402_in_file(file_path):
                print(f"修复了文件: {file_path}")
                fixed_count += 1
        else:
            print(f"文件不存在: {file_path}")

    print(f"总共修复了 {fixed_count} 个文件")

if __name__ == "__main__":
    main()