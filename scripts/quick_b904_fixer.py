#!/usr/bin/env python3
"""
快速B904异常处理修复工具
Quick B904 Exception Handler Fixer

针对单个文件的快速B904错误修复工具.
"""

import subprocess
import sys
from pathlib import Path


def get_b904_lines(file_path):
    """获取文件中B904错误的具体行号"""
    try:
        result = subprocess.run(
            ["ruff", "check", "--select", "B904", file_path, "--output-format=concise"],
            capture_output=True,
            text=True,
            cwd="/home/user/projects/FootballPrediction"
        )

        lines = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                parts = line.split(':')
                if len(parts) >= 2:
                    line_num = int(parts[1])
                    lines.append(line_num)
        return lines
    except Exception:
        return []

def fix_b904_in_file(file_path):
    """修复单个文件中的B904错误"""

    # 获取B904错误行号
    b904_lines = get_b904_lines(file_path)
    if not b904_lines:
        return True


    try:
        with open(file_path, encoding='utf-8') as f:
            lines = f.readlines()

        fixed_count = 0
        for line_num in b904_lines:
            # 转换为0-based索引
            idx = line_num - 1
            if idx < len(lines):
                line = lines[idx]

                # 检查是否是raise语句且没有from子句
                if 'raise ' in line and ') from ' not in line and ')' in line:
                    # 在)后添加 from e
                    lines[idx] = line.rstrip() + ' from e\n'
                    fixed_count += 1

        if fixed_count > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
        else:
            return False

    except Exception:
        return False

def verify_fix(file_path):
    """验证修复效果"""
    result = subprocess.run(
        ["ruff", "check", "--select", "B904", file_path, "--output-format=concise"],
        capture_output=True,
        text=True,
        cwd="/home/user/projects/FootballPrediction"
    )

    return "All checks passed!" in result.stdout or "Found 0 errors" in result.stdout

def main():
    """主函数"""
    if len(sys.argv) != 2:
        sys.exit(1)

    file_path = sys.argv[1]

    if not Path(file_path).exists():
        sys.exit(1)


    # 修复文件
    if fix_b904_in_file(file_path):
        # 验证修复效果
        if verify_fix(file_path):
            pass
        else:
            pass
    else:
        pass

if __name__ == "__main__":
    main()
