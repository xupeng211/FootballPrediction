#!/usr/bin/env python3
"""
手动B904修复工具
逐个文件安全地修复B904错误
"""

import re
from pathlib import Path

def fix_b904_in_file(file_path, line_numbers):
    """安全地修复指定文件中指定行的B904错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
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
                    print(f"✅ 修复了第{line_num}行")

        # 写回文件
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            print(f"📁 文件 {file_path} 修复完成: {fix_count}个错误")
            return fix_count
        else:
            print(f"ℹ️  文件 {file_path} 没有需要修复的B904错误")
            return 0

    except Exception as e:
        print(f"❌ 修复文件失败 {file_path}: {e}")
        return 0

def main():
    """主函数"""
    print("🚀 开始手动修复B904错误...")

    # betting_api.py的B904错误行
    betting_api_errors = [238, 290, 338, 399, 439, 518]  # 180已修复

    # 修复betting_api.py
    print("\n📝 修复 src/api/betting_api.py...")
    fixes = fix_b904_in_file("src/api/betting_api.py", betting_api_errors)

    print(f"\n📊 总计修复: {fixes}个B904错误")

    # 验证修复结果
    print("\n🔍 验证修复结果...")
    import subprocess
    result = subprocess.run(
        "ruff check src/api/betting_api.py --select=B904",
        shell=True,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("✅ betting_api.py的所有B904错误已修复")
    else:
        print(f"⚠️  betting_api.py仍有B904错误需要处理")
        print(result.stdout)

if __name__ == "__main__":
    main()