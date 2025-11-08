#!/usr/bin/env python3
"""
API模块B904异常处理批量修复工具
Batch B904 Exception Fixer for API Modules

针对API模块的快速B904错误修复工具.
"""

import re
import subprocess


def fix_b904_in_file(file_path):
    """修复单个文件中的B904错误"""

    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        # 修复模式: 在HTTPException后添加 from e
        # 匹配多行raise HTTPException语句
        pattern = r'raise HTTPException\(\s*[^)]*\)\s*$'

        # 使用正则表达式找到所有raise HTTPException语句
        matches = list(re.finditer(pattern, content, re.MULTILINE))

        if not matches:
            return 0

        fixed_count = 0
        # 从后往前处理，避免位置偏移
        for match in reversed(matches):
            start, end = match.span()
            original = match.group()

            # 检查是否已经有from子句
            if ' from ' not in original:
                # 在括号后添加 from e
                modified = original.rstrip() + ' from e'
                content = content[:start] + modified + content[end:]
                fixed_count += 1

        if fixed_count > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return fixed_count
        else:
            return 0

    except Exception:
        return 0

def get_b904_files(directory):
    """获取目录中有B904错误的文件列表"""
    try:
        result = subprocess.run(
            ["ruff", "check", "--select", "B904", directory, "--output-format=concise"],
            capture_output=True,
            text=True,
            cwd="/home/user/projects/FootballPrediction"
        )

        files = set()
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                parts = line.split(':')
                if len(parts) >= 2:
                    file_path = parts[0]
                    if file_path.startswith(directory + '/'):
                        files.add(file_path)

        return sorted(files)
    except Exception:
        return []

def main():
    """主函数"""

    api_directory = "src/api"

    # 获取需要修复的API文件
    files = get_b904_files(api_directory)

    if not files:
        return


    # 统计初始错误数量
    try:
        result = subprocess.run(
            ["ruff", "check", "--select", "B904", api_directory, "--output-format=concise"],
            capture_output=True,
            text=True,
            cwd="/home/user/projects/FootballPrediction"
        )
        initial_count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
    except:
        initial_count = 0

    # 批量修复
    total_fixed = 0
    for _i, file_path in enumerate(files, 1):
        fixed = fix_b904_in_file(file_path)
        total_fixed += fixed

    # 统计最终结果
    try:
        result = subprocess.run(
            ["ruff", "check", "--select", "B904", api_directory, "--output-format=concise"],
            capture_output=True,
            text=True,
            cwd="/home/user/projects/FootballPrediction"
        )
        final_count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
    except:
        final_count = 0


    if initial_count > 0:
        ((initial_count - final_count) / initial_count) * 100

    if final_count > 0:
        pass
    else:
        pass

if __name__ == "__main__":
    main()
