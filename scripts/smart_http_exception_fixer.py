#!/usr/bin/env python3
"""
智能HTTPException修复器
Smart HTTPException Fixer

智能识别和修复HTTPException语法错误。
"""

import os
import re


def fix_http_exception_in_file(file_path):
    """智能修复文件中的HTTPException语法错误"""

    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        original_content = content
        changes_made = False

        # 模式1: 修复分离的HTTPException
        # 查找: raise HTTPException(\n)\n    status_code=...
        # 替换为: raise HTTPException(\n    status_code=...
        pattern1 = r'(raise HTTPException\(\s*\n)\s*\)\s*\n(\s+status_code=.*?)(\s*\))'
        replacement1 = r'\1\2\3'

        new_content = re.sub(pattern1, replacement1, content, flags=re.MULTILINE | re.DOTALL)
        if new_content != content:
            content = new_content
            changes_made = True

        # 模式2: 修复带异常链的HTTPException
        # 查找: raise HTTPException(\n    ... from e\n)\n    status_code=...
        pattern2 = r'(raise HTTPException\(\s*\n)\s*\.\.\.\s+from\s+e\s*\n\s*\)\s*\n(\s+status_code=.*?)(\s*\))'
        replacement2 = r'\1\2\3'

        new_content = re.sub(pattern2, replacement2, content, flags=re.MULTILINE | re.DOTALL)
        if new_content != content:
            content = new_content
            changes_made = True

        # 模式3: 删除文件末尾的异常链片段
        pattern3 = r'\n\s*\)\s+from\s+e\s*#\s*TODO:\s*B904\s+exception\s+chaining\s*$'
        new_content = re.sub(pattern3, '', content)
        if new_content != content:
            content = new_content
            changes_made = True

        # 模式4: 修复更复杂的分离情况
        pattern4 = r'raise HTTPException\(\s*\n\s*\)\s*\n((?:\s+.*?\n)*?\s*\))'
        def fix_complex_match(match):
            inner_content = match.group(1)
            # 清理多余的前缀空格和括号
            lines = inner_content.split('\n')
            fixed_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith(')'):
                    fixed_lines.append(line)
            return 'raise HTTPException(\n' + '\n'.join(fixed_lines)

        new_content = re.sub(pattern4, fix_complex_match, content, flags=re.MULTILINE | re.DOTALL)
        if new_content != content:
            content = new_content
            changes_made = True

        # 模式5: 清理多余的空行和格式
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # 减少连续空行
        content = re.sub(r'\n\s*$', '\n', content)  # 确保末尾只有一个换行符

        # 写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return changes_made
        else:
            return False

    except Exception:
        return False

def main():
    """主函数"""

    api_files = [
        "src/api/betting_api.py",
        "src/api/features.py",
        "src/api/features_simple.py",
        "src/api/middleware.py",
        "src/api/performance_management.py",
        "src/api/predictions_enhanced.py",
        "src/api/predictions_srs_simple.py",
        "src/api/realtime_streaming.py",
        "src/api/tenant_management.py",
        "src/api/routes/user_management.py"
    ]


    fixed_count = 0

    for file_path in api_files:
        if os.path.exists(file_path):
            if fix_http_exception_in_file(file_path):
                fixed_count += 1
        else:
            pass


    if fixed_count > 0:
        pass


if __name__ == "__main__":
    main()
