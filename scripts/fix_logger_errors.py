#!/usr/bin/env python3
"""
修复测试文件中的logger未定义错误
Fix logger undefined errors in test files

将所有测试文件中的logger调用替换为print语句
"""

import os
import re
import sys


def fix_logger_in_file(file_path):
    """修复单个文件中的logger问题"""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 替换logger调用为print语句
        # logger.debug("message") -> print("message")
        # logger.info("message") -> print("message")
        # logger.warning("message") -> print("message")
        # logger.error("message") -> print("message")

        # 匹配各种logger级别 - 改进的多行匹配
        patterns = [
            (r'logger\.debug\((.*?)\)', r'print(\1)'),
            (r'logger\.info\((.*?)\)', r'print(\1)'),
            (r'logger\.warning\((.*?)\)', r'print(\1)'),
            (r'logger\.error\((.*?)\)', r'print(\1)'),
            (r'logger\.critical\((.*?)\)', r'print(\1)'),
        ]

        # 使用更强大的正则表达式，包括多行匹配
        multiline_patterns = [
            # 匹配 logger.debug( ... ) 的多行形式
            (r'logger\.debug\(([^)]*(?:\([^)]*\)[^)]*)*)\)', r'print(\1)'),
            (r'logger\.info\(([^)]*(?:\([^)]*\)[^)]*)*)\)', r'print(\1)'),
            (r'logger\.warning\(([^)]*(?:\([^)]*\)[^)]*)*)\)', r'print(\1)'),
            (r'logger\.error\(([^)]*(?:\([^)]*\)[^)]*)*)\)', r'print(\1)'),
            (r'logger\.critical\(([^)]*(?:\([^)]*\)[^)]*)*)\)', r'print(\1)'),
        ]

        changes_made = 0
        all_patterns = patterns + multiline_patterns

        for pattern, replacement in all_patterns:
            # 使用re.DOTALL标志让.匹配换行符，支持多行匹配
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                content = re.sub(pattern, replacement, content, flags=re.DOTALL)
                changes_made += len(matches)

        # 如果有修改，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return changes_made

        return 0

    except Exception:
        return -1


def main():
    """主函数"""

    # 找到所有有logger问题的文件
    problem_files = []
    for root, _dirs, files in os.walk('tests'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, encoding='utf-8') as f:
                        content = f.read()
                    # 检查是否有logger使用但没有导入
                    if re.search(r'logger\.', content):
                        has_import = bool(re.search(r'import logging|from logging import|logger\s*=', content))
                        if not has_import:
                            problem_files.append(file_path)
                except Exception:
                    pass


    total_fixes = 0
    successful_files = 0

    for file_path in problem_files:
        fixes = fix_logger_in_file(file_path)
        if fixes > 0:
            total_fixes += fixes
            successful_files += 1
        elif fixes == 0:
            pass
        else:
            pass


    return successful_files > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
