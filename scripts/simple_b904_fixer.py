#!/usr/bin/env python3
"""
简单B904修复工具 - 专注于新增API优化模块的B904错误
"""

import os
import re


def fix_b904_in_optimization_modules():
    """修复API优化模块中的B904错误"""

    # 重点处理的文件（新的API优化模块）
    target_files = [
        "src/api/optimization/cache_performance_api.py",
        "src/api/optimization/database_performance_api.py"
    ]

    total_fixed = 0

    for file_path in target_files:
        if not os.path.exists(file_path):
            continue


        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            # 备份原文件
            backup_path = file_path + '.b904_backup'
            with open(backup_path, 'w', encoding='utf-8') as backup:
                backup.write(content)

            original_content = content

            # 修复B904错误：找到except块中的raise HTTPException并添加异常链
            lines = content.split('\n')
            fixed_lines = []

            i = 0
            while i < len(lines):
                line = lines[i]

                # 检测except块
                if re.match(r'^(\s*)except Exception as (\w+):', line):
                    except_indent = len(line) - len(line.lstrip())
                    exception_var = re.search(r'except Exception as (\w+):', line).group(1)

                    # 添加except块开始
                    fixed_lines.append(line)
                    i += 1

                    # 处理except块内容
                    while i < len(lines):
                        current_line = lines[i]
                        current_indent = len(current_line) - len(current_line.lstrip())

                        # 如果遇到更小或相等的缩进，说明except块结束
                        if current_line.strip() and current_indent <= except_indent:
                            break

                        # 查找raise HTTPException
                        if re.search(r'raise HTTPException\(', current_line):
                            # 检查是否已经有异常链
                            if ' from ' not in current_line:
                                # 添加异常链
                                if current_line.rstrip().endswith(')'):
                                    # 单行raise语句
                                    fixed_line = current_line.rstrip() + f' from {exception_var}'
                                    fixed_lines.append(fixed_line)
                                    total_fixed += 1
                                else:
                                    # 多行raise语句，需要找到结束行
                                    fixed_lines.append(current_line)
                                    i += 1
                                    while i < len(lines):
                                        next_line = lines[i]
                                        fixed_lines.append(next_line)
                                        if next_line.rstrip().endswith(')'):
                                            # 在结束行添加异常链
                                            fixed_lines[-1] = next_line.rstrip() + f' from {exception_var}'
                                            total_fixed += 1
                                            break
                                        i += 1
                                    i -= 1  # 调整索引，因为外层循环会+1
                            else:
                                fixed_lines.append(current_line)
                        else:
                            fixed_lines.append(current_line)

                        i += 1
                    continue  # 跳过外层的i+=1
                else:
                    fixed_lines.append(line)

                i += 1

            # 写入修复后的内容
            if original_content != '\n'.join(fixed_lines):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(fixed_lines))
            else:
                os.remove(backup_path)  # 删除不需要的备份

        except Exception:
            pass

    return total_fixed

def main():

    fix_b904_in_optimization_modules()


    # 验证修复效果
    remaining_b904 = 0

    target_files = [
        "src/api/optimization/cache_performance_api.py",
        "src/api/optimization/database_performance_api.py"
    ]

    for file_path in target_files:
        if os.path.exists(file_path):
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            # 统计剩余的B904错误
            b904_count = len(re.findall(r'except\s+.*?\s+as\s+\w+.*?raise\s+HTTPException\(', content, re.DOTALL))
            remaining_b904 += b904_count

    if remaining_b904 == 0:
        pass
    else:
        pass

if __name__ == "__main__":
    main()
