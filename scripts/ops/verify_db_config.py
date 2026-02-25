#!/usr/bin/env python3
"""
V172 数据库配置统一验证脚本

检查所有文件是否使用统一的数据库配置，检测违规的硬编码密码。

使用方法：
    python scripts/ops/verify_db_config.py
    python scripts/ops/verify_db_config.py --fix  # 显示修复建议
"""

import argparse
import re
from pathlib import Path
from typing import NamedTuple


class Violation(NamedTuple):
    """违规项"""
    file: str
    line: int
    content: str
    pattern: str


# 禁止出现的硬编码密码模式
FORBIDDEN_PATTERNS = [
    (r"password\s*[=:]\s*['\"]football_pass['\"]", "硬编码 football_pass 密码"),
    (r"password\s*[=:]\s*['\"]postgres['\"]", "硬编码 postgres 密码"),
    (r"DB_PASSWORD\s*\|\|\s*['\"]football_pass['\"]", "football_pass 默认值"),
    (r"DB_PASSWORD\s*\|\|\s*['\"]postgres['\"]", "postgres 默认值"),
    (r"PGPASSWORD['\"]?\s*[=:]\s*['\"]football_pass['\"]", "PGPASSWORD 硬编码"),
]

# 排除的目录
EXCLUDE_DIRS = {
    'node_modules',
    '_deprecated',
    '.git',
    '__pycache__',
    '.pytest_cache',
    '.ruff_cache',
    'venv',
    '.venv',
}


def scan_file(filepath: Path) -> list[Violation]:
    """扫描单个文件中的违规配置"""
    violations = []

    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')

        for line_num, line in enumerate(lines, start=1):
            for pattern, desc in FORBIDDEN_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append(Violation(
                        file=str(filepath),
                        line=line_num,
                        content=line.strip(),
                        pattern=desc
                    ))
    except Exception as e:
        print(f"⚠️ 无法读取文件 {filepath}: {e}")

    return violations


def scan_directory(root: Path) -> dict[str, list[Violation]]:
    """扫描目录下所有文件"""
    results = {}

    for ext in ['*.js', '*.py', '*.ts']:
        for filepath in root.rglob(ext):
            # 排除特定目录
            if any(excluded in str(filepath) for excluded in EXCLUDE_DIRS):
                continue

            violations = scan_file(filepath)
            if violations:
                results[str(filepath.relative_to(root))] = violations

    return results


def print_report(results: dict[str, list[Violation]], show_fix: bool = False) -> int:
    """打印扫描报告"""
    total_violations = sum(len(v) for v in results.values())

    if not results:
        print("✅ 所有文件数据库配置符合规范")
        return 0

    print(f"❌ 发现 {total_violations} 个违规配置，涉及 {len(results)} 个文件：\n")

    for filepath, violations in sorted(results.items()):
        print(f"📄 {filepath}")
        for v in violations:
            print(f"   Line {v.line}: [{v.pattern}]")
            print(f"   {v.content}")
            if show_fix:
                print(f"   💡 修复建议: 使用 config/database.js (JS) 或 src/database/db_pool.py (Python)")
        print()

    return 1


def main():
    parser = argparse.ArgumentParser(description='数据库配置验证脚本')
    parser.add_argument('--fix', action='store_true', help='显示修复建议')
    args = parser.parse_args()

    root = Path(__file__).parent.parent.parent
    print(f"🔍 扫描目录: {root}\n")

    results = scan_directory(root)
    exit_code = print_report(results, show_fix=args.fix)

    if results:
        print(f"\n📊 统计:")
        print(f"   违规文件数: {len(results)}")
        print(f"   违规项总数: {sum(len(v) for v in results.values())}")
        print(f"\n💡 提示: 运行 'python scripts/ops/verify_db_config.py --fix' 查看修复建议")

    return exit_code


if __name__ == "__main__":
    exit(main())
