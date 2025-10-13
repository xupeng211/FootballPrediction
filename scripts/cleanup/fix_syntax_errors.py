#!/usr/bin/env python3
"""
修复语法错误的脚本
"""

import re
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent


def fix_syntax_errors():
    """修复所有语法错误"""

    # 需要修复的文件列表
    files_to_fix = [
        "src/repositories/match.py",
        "src/repositories/prediction.py",
        "src/repositories/user.py",
    ]

    total_fixes = 0

    for file_path in files_to_fix:
        full_path = PROJECT_ROOT / file_path
        if not full_path.exists():
            continue

        content = full_path.read_text(encoding="utf-8")
        original_content = content

        # 修复 self.session.add 错误
        content = re.sub(
            r"self\.session\.add\(  # type: ignore(\w+)\)",
            r"self.session.add(\1)  # type: ignore",
            content,
        )

        # 修复 self.session.refresh 错误
        content = re.sub(
            r"await self\.session\.refresh\(  # type: ignore(\w+)\)",
            r"await self.session.refresh(\1)  # type: ignore",
            content,
        )

        # 修复其他的类似错误
        content = re.sub(
            r"self\.session\.add\(  # type: ignoreentity\)  # type: ignore",
            r"self.session.add(entity)  # type: ignore",
            content,
        )

        content = re.sub(
            r"await self\.session\.refresh\(  # type: ignoreentity\)",
            r"await self.session.refresh(entity)  # type: ignore",
            content,
        )

        if content != original_content:
            full_path.write_text(content, encoding="utf-8")
            print(f"✓ 修复语法错误: {file_path}")
            total_fixes += 1

    return total_fixes


def main():
    print("🔧 修复语法错误脚本")
    print("=" * 50)

    fixes = fix_syntax_errors()

    print(f"\n总计修复了 {fixes} 个文件")

    # 运行 MyPy 检查
    import subprocess

    print("\n运行 MyPy 检查...")
    result = subprocess.run(
        ["mypy", "src", "--no-error-summary"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("✅ MyPy 检查通过！没有错误")
    else:
        print(f"❌ 还有 {result.stdout.count('error:')} 个错误")
        print(result.stdout)


if __name__ == "__main__":
    main()
