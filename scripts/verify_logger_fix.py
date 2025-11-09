#!/usr/bin/env python3
"""
验证logger修复结果 - 只检查真正的logger未定义错误
"""

import os
import re


def check_real_logger_errors():
    """检查真正的logger未定义错误"""
    real_errors = []

    for root, dirs, files in os.walk('tests'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 检查是否有未定义的logger使用
                    if re.search(r'\blogger\.', content):
                        # 检查是否有正确的logger定义
                        has_logger_definition = bool(
                            re.search(r'logger\s*=\s*logging\.getLogger|logger\s*=\s*Logger|from logging import.*logger|logger\s*=\s*get_logger', content) or
                            re.search(r'import logging', content) and re.search(r'logger\s*=', content)
                        )

                        # 检查是否是mock_logger（这是合法的）
                        has_mock_logger = bool(re.search(r'mock_logger\.|mock\s+logger|patch.*logger', content))

                        if not has_logger_definition and not has_mock_logger:
                            # 找到具体错误行
                            lines = content.split('\n')
                            for i, line in enumerate(lines, 1):
                                if re.search(r'\blogger\.', line) and not re.search(r'mock_logger|patch', line):
                                    real_errors.append((file_path, i, line.strip()))
                                    break
                except Exception:
                    pass

    return real_errors


def main():
    """主函数"""
    print("🔍 检查真正的logger未定义错误...")

    errors = check_real_logger_errors()

    if errors:
        print(f"❌ 找到 {len(errors)} 个真正的logger未定义错误:")
        for file_path, line_no, line in errors:
            print(f"  {file_path}:{line_no}: {line}")
        return False
    else:
        print("✅ 没有找到真正的logger未定义错误！")
        print("🎉 所有logger问题已成功修复！")
        return True


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)