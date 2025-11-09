#!/usr/bin/env python3
"""
修复剩余的B904错误
"""

import re

def fix_b904_in_file(file_path: str):
    """修复单个文件中的B904错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 备份原文件
        backup_path = file_path + '.b904_backup'
        with open(backup_path, 'w', encoding='utf-8') as backup:
            backup.write(content)

        # 简单的正则表达式修复
        # 查找并修复except块中的raise HTTPException
        pattern = r'(\s+)(.*?)(except\s+\S+\s+as\s+(\w+):.*?raise\s+HTTPException\([^)]+\))'

        def replacement(match):
            indent = match.group(1)
            prefix = match.group(2)
            exception_var = match.group(4)
            raise_statement = match.group(3)

            # 如果已经有异常链，不修改
            if ' from ' in raise_statement:
                return match.group(0)

            # 添加异常链
            return f"{indent}{prefix}{raise_statement} from {exception_var}"

        # 使用更简单的逐行替换方法
        lines = content.split('\n')
        fixed_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # 查找except行
            except_match = re.match(r'^(\s*)except\s+\S+\s+as\s+(\w+):', line)
            if except_match:
                except_indent = except_match.group(1)
                exception_var = except_match.group(2)

                # 添加except行
                fixed_lines.append(line)
                i += 1

                # 处理except块的内容
                while i < len(lines):
                    current_line = lines[i]
                    current_indent = len(current_line) - len(current_line.lstrip())

                    # 如果遇到更小或相等的缩进，说明except块结束
                    if current_line.strip() and current_indent <= len(except_indent):
                        break

                    # 查找raise HTTPException
                    if 'raise HTTPException(' in current_line and ' from ' not in current_line:
                        # 处理多行raise语句
                        fixed_lines.append(current_line)
                        i += 1

                        # 继续查找raise语句的结束
                        while i < len(lines):
                            next_line = lines[i]
                            fixed_lines.append(next_line)

                            if ')' in next_line:
                                # 在结束行添加异常链
                                fixed_lines[-1] = next_line.rstrip() + f' from {exception_var}'
                                print(f"✅ 修复 {file_path} 行 {i+1}")
                                break
                            i += 1
                    else:
                        fixed_lines.append(current_line)
                        i += 1

                continue  # 跳过外层的i+=1
            else:
                fixed_lines.append(line)

            i += 1

        # 写入修复后的内容
        fixed_content = '\n'.join(fixed_lines)
        if fixed_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"💾 已修复 {file_path}")
            return True
        else:
            print(f"ℹ️ {file_path} 无需修改")
            os.remove(backup_path)
            return False

    except Exception as e:
        print(f"❌ 修复 {file_path} 时出错: {e}")
        return False

import os

def main():
    print("🔧 修复剩余B904错误")
    print("=" * 30)

    # 需要修复的文件
    files_to_fix = [
        "src/performance/api.py",
        "src/realtime/match_api.py"
    ]

    total_fixed = 0

    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_b904_in_file(file_path):
                total_fixed += 1
        else:
            print(f"⚠️ 文件不存在: {file_path}")

    print(f"\n🎉 修复完成! 修复了 {total_fixed} 个文件")

if __name__ == "__main__":
    main()