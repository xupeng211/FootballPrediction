#!/usr/bin/env python3
"""
清理并重新修复logger导入问题
"""

import re
from pathlib import Path


def clean_and_fix_logger(file_path):
    """清理并重新修复单个文件中的logger问题"""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 步骤1：移除所有错误的logger定义（在import之前的）
        lines = content.split('\n')
        new_lines = []
        skip_logger_line = False

        for i, line in enumerate(lines):
            # 检查是否是错误的logger定义
            if re.match(r'^\s*logger\s*=\s*logging\.getLogger', line.strip()):
                # 检查前面是否有import logging
                has_import = False
                for j in range(max(0, i-20), i):  # 检查前面20行
                    if re.match(r'^\s*import\s+logging', lines[j].strip()):
                        has_import = True
                        break
                if has_import:
                    new_lines.append(line)  # 保留正确的logger定义
                else:
                    skip_logger_line = True  # 跳过错误的logger定义
            else:
                if not (skip_logger_line and line.strip() == ''):
                    new_lines.append(line)
                skip_logger_line = False

        content = '\n'.join(new_lines)

        # 步骤2：检查是否需要添加logger
        if 'logger.' in content and 'logger = logging.getLogger(__name__)' not in content:
            # 找到最后一个import的位置
            lines = content.split('\n')
            last_import_pos = -1

            for i, line in enumerate(lines):
                if re.match(r'^\s*(import|from)\s+', line.strip()):
                    last_import_pos = i

            if last_import_pos >= 0:
                # 确保有logging导入
                has_logging_import = any('import logging' in line for line in lines[:last_import_pos+1])

                if not has_logging_import:
                    # 添加logging导入
                    insert_pos = last_import_pos + 1
                    while insert_pos < len(lines) and (lines[insert_pos].strip() == '' or lines[insert_pos].strip().startswith('#')):
                        insert_pos += 1
                    lines.insert(insert_pos, 'import logging')
                    lines.insert(insert_pos + 1, '')
                    last_import_pos += 2

                # 在最后一个import后添加logger定义
                insert_pos = last_import_pos + 1
                while insert_pos < len(lines) and (lines[insert_pos].strip() == '' or lines[insert_pos].strip().startswith('#')):
                    insert_pos += 1

                lines.insert(insert_pos, 'logger = logging.getLogger(__name__)')
                lines.insert(insert_pos + 1, '')
            else:
                # 如果没有找到import，在文档字符串后添加
                docstring_end = -1
                in_docstring = False

                for i, line in enumerate(lines):
                    if '"""' in line:
                        if not in_docstring:
                            in_docstring = True
                        else:
                            docstring_end = i
                            break

                if docstring_end >= 0:
                    insert_pos = docstring_end + 1
                    lines.insert(insert_pos, '')
                    lines.insert(insert_pos + 1, 'import logging')
                    lines.insert(insert_pos + 2, 'logger = logging.getLogger(__name__)')
                    lines.insert(insert_pos + 3, '')
                else:
                    # 在文件开头添加
                    lines.insert(0, 'import logging')
                    lines.insert(1, '')
                    lines.insert(2, 'logger = logging.getLogger(__name__)')
                    lines.insert(3, '')

            content = '\n'.join(lines)

        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False

    except Exception:
        return False

def main():
    """主函数"""
    # 找到所有有logger问题的文件
    problem_files = []
    tests_dir = Path('tests/unit')

    for py_file in tests_dir.rglob('*.py'):
        try:
            with open(py_file, encoding='utf-8') as f:
                content = f.read()

            # 检查是否有logger问题
            if ('logger.' in content and
                'import logging' not in content) or \
               ('logger.' in content and
                'logger = logging.getLogger(__name__)' not in content):
                problem_files.append(str(py_file))
        except:
            continue


    fixed_count = 0

    for file_path in problem_files:
        if clean_and_fix_logger(Path(file_path)):
            fixed_count += 1
        else:
            pass


if __name__ == "__main__":
    main()
