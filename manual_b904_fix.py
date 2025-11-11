#!/usr/bin/env python3
"""
手动B904修复工具
逐个文件安全地修复B904错误
"""

import re


def fix_b904_in_file(file_path, line_numbers):
    """安全地修复指定文件中指定行的B904错误"""
    try:
        with open(file_path, encoding='utf-8') as f:
            lines = f.readlines()

        fix_count = 0
        modified = False

        for line_num in line_numbers:
            line_index = line_num - 1  # 转换为0-based索引

            if line_index < len(lines):
                line = lines[line_index]

                # 查找HTTPException的raise语句
                if 'raise HTTPException(' in line and 'from e' not in line:
                    # 在HTTPException后添加 from e
                    modified_line = re.sub(
                        r'(\)\s*#?.*)$',
                        r') from e  # \1',
                        line.strip()
                    )
                    lines[line_index] = modified_line + '\n'
                    modified = True
                    fix_count += 1

        # 写回文件
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return fix_count
        else:
            return 0

    except Exception:
        return 0

def main():
    """主函数"""

    # betting_api.py的B904错误行
    betting_api_errors = [238, 290, 338, 399, 439, 518]  # 180已修复

    # 修复betting_api.py
    fix_b904_in_file("src/api/betting_api.py", betting_api_errors)


    # 验证修复结果
    import subprocess
    result = subprocess.run(
        "ruff check src/api/betting_api.py --select=B904",
        shell=True,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        pass
    else:
        pass

if __name__ == "__main__":
    main()
