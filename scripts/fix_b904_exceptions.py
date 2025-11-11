#!/usr/bin/env python3
"""
B904异常处理问题批量修复工具
Batch Fix Tool for B904 Exception Handling Issues

自动修复所有B904异常处理问题，提高代码质量和错误处理能力.
"""

import re
import subprocess


def run_command(cmd, description=""):
    """运行命令并处理结果"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd="/home/user/projects/FootballPrediction"
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return None
    except Exception:
        return None

def get_b904_files():
    """获取所有有B904错误的文件列表"""

    cmd = "ruff check --select B904 src/ --output-format=json"
    output = run_command(cmd, "获取B904错误列表")

    if not output:
        return []

    files = set()
    for line in output.split('\n'):
        if line.strip() and line.startswith('{'):
            # 简单解析，提取文件名
            if '"file":"' in line:
                file_match = re.search(r'"file":"([^"]+)"', line)
                if file_match:
                    files.add(file_match.group(1))

    return sorted(files)

def fix_b904_in_file(file_path):
    """修复单个文件中的B904错误"""

    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        # 修复模式1: raise Exception(... )  →  raise Exception(... ) from e

        # 修复模式2: 处理多行raise语句

        # 应用修复
        new_content = content

        # 简单的启发式方法：查找 except Exception as e: 块中的 raise 语句
        lines = new_content.split('\n')
        result_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # 检查是否在except块中
            if re.match(r'\s*except\s+\S+\s+as\s+\w+:', line):
                result_lines.append(line)
                i += 1

                # 处理except块内容
                while i < len(lines):
                    current_line = lines[i]
                    result_lines.append(current_line)

                    # 检查是否有raise语句需要修复
                    if re.search(r'\s*raise\s+\w+\(', current_line) and 'from e' not in current_line:
                        # 查找raise语句的结束
                        if ')' in current_line and not current_line.strip().endswith('('):
                            # 单行raise语句
                            result_lines[-1] = current_line.rstrip() + ' from e'
                        else:
                            # 多行raise语句，需要找到结束行
                            j = i + 1
                            paren_count = current_line.count('(') - current_line.count(')')
                            while j < len(lines) and paren_count > 0:
                                result_lines.append(lines[j])
                                paren_count += lines[j].count('(') - lines[j].count(')')
                                j += 1

                            # 在最后一行添加 from e
                            if result_lines and ')' in result_lines[-1]:
                                result_lines[-1] = result_lines[-1].rstrip() + ' from e'
                            i = j - 1

                    i += 1

                    # 检查是否遇到下一个except或函数结束
                    if i < len(lines) and (lines[i].strip() == '' or
                                         lines[i].strip().startswith(('except', 'def', 'class', '@', '#'))):
                        break
            else:
                result_lines.append(line)
                i += 1

        new_content = '\n'.join(result_lines)

        # 如果内容有变化，写回文件
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
        else:
            return False

    except Exception:
        return False

def verify_fix(file_path):
    """验证文件修复效果"""
    cmd = f"ruff check --select B904 {file_path} --output-format=concise"
    output = run_command(cmd, f"验证 {file_path}")

    if output == "All checks passed!":
        return True
    else:
        return False

def main():
    """主函数"""

    # 获取所有需要修复的文件
    files = get_b904_files()

    if not files:
        return


    # 统计初始错误数量
    initial_cmd = "ruff check --select B904 src/ --output-format=concise | wc -l"
    run_command(initial_cmd, "统计初始错误数量")

    # 批量修复
    fixed_count = 0
    for _i, file_path in enumerate(files, 1):

        if fix_b904_in_file(file_path):
            # 验证修复效果
            if verify_fix(file_path):
                fixed_count += 1
            else:
                pass

    # 统计最终结果
    final_cmd = "ruff check --select B904 src/ --output-format=concise | wc -l"
    final_count = run_command(final_cmd, "统计最终错误数量")


    if int(final_count) > 0:
        pass
    else:
        pass

if __name__ == "__main__":
    main()
