#!/usr/bin/env python3
"""
快速HTTPException语法修复
"""

import re
from pathlib import Path


def fix_http_exception_errors(content):
    """修复HTTPException语法错误"""
    # 修复分离的HTTPException参数
    pattern1 = r'raise HTTPException\(\s*\)\s+status_code=([^,]+),\s+detail=([^)]+)\s*\)'
    content = re.sub(pattern1, r'raise HTTPException(\n    status_code=\1,\n    detail=\2\n)', content)

    # 删除多余的异常链片段
    content = re.sub(r'\s+\) from e\s*# TODO: B904 exception chaining', '', content)

    # 修复不完整的HTTPException
    content = re.sub(r'raise HTTPException\(\s*\)\s+status_code=([^,]+),\s+detail=([^)]+)\)',
                    r'raise HTTPException(\n    status_code=\1,\n    detail=\2\n)', content)

    return content

def main():
    """主函数"""
    api_files = [
        "src/api/betting_api.py",
        "src/api/features.py",
        "src/api/middleware.py",
        "src/api/auth/router.py",
        "src/api/auth_dependencies.py"
    ]

    for file_path in api_files:
        path = Path(file_path)
        if path.exists():

            with open(path, encoding='utf-8') as f:
                content = f.read()

            fixed_content = fix_http_exception_errors(content)

            if fixed_content != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
            else:
                pass

if __name__ == "__main__":
    main()
