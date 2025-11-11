#!/usr/bin/env python3
"""
覆盖率分析工具 - 简化版本
"""

import subprocess
import sys
from pathlib import Path


def count_lines_of_code(file_path: str) -> int:
    """计算文件的有效代码行数"""
    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()

        code_lines = 0
        for line in lines:
            line = line.strip()
            # 排除空行和单行注释
            if line and not line.startswith("#"):
                code_lines += 1
        return code_lines
    except Exception:
        return 0

def get_coverage_data():
    """获取覆盖率数据"""
    try:
        # 运行pytest获取覆盖率
        result = subprocess.run([
            "python", "-m", "pytest", "tests/", "--cov=src",
            "--cov-report=term-missing", "--tb=no", "-q"
        ], capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            return {}
        else:
            return {}
    except Exception:
        return {}

def main():
    """主函数"""

    # 计算代码行数
    src_dir = Path("src")
    if src_dir.exists():
        py_files = list(src_dir.rglob("*.py"))
        sum(count_lines_of_code(str(f)) for f in py_files)

    # 获取覆盖率数据
    get_coverage_data()

    return 0

if __name__ == '__main__':
    sys.exit(main())
