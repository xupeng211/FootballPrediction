#!/usr/bin/env python3
"""
全面的E402模块导入位置修复工具
处理剩余的58个E402错误
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import subprocess

def find_e402_files() -> List[Dict]:
    """查找所有E402错误"""
    try:
        result = subprocess.run(
            ['ruff', 'check', '--select=E402', '--output-format=json'],
            capture_output=True,
            text=True,
            cwd='src'
        )

        files = set()
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip() and 'E402' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        files.add(parts[0])
        return sorted(list(files))
    except Exception as e:
        print(f"❌ 查找E402文件失败: {e}")
        return []

def fix_e402_in_file(file_path: Path) -> int:
    """修复单个文件中的E402错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        lines = content.split('\n')
        if not lines:
            return 0

        # 查找文档字符串结束位置
        docstring_end = 0
        in_docstring = False
        docstring_delimiter = None

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 检查文档字符串开始
            if not in_docstring and ('"""' in stripped or "'''" in stripped):
                in_docstring = True
                if stripped.count('"""') == 2 or stripped.count("''") == 2:
                    # 单行文档字符串
                    docstring_end = i + 1
                    in_docstring = False
                else:
                    # 多行文档字符串开始
                    docstring_delimiter = '"""' if '"""' in stripped else "'''"
                continue

            # 检查文档字符串结束
            if in_docstring and docstring_delimiter in stripped:
                docstring_end = i + 1
                in_docstring = False
                docstring_delimiter = None
                continue

            # 检查第一个导入
            if not in_docstring and stripped.startswith(('import ', 'from ')):
                if docstring_end == 0:
                    docstring_end = i
                break

        # 提取所有导入
        imports = []
        other_lines = []

        # 第二次遍历，分离导入和其他内容
        for i, line in enumerate(lines):
            stripped = line.strip()

            if stripped.startswith(('import ', 'from ')):
                imports.append(line.rstrip())
            else:
                other_lines.append(line)

        # 重新组织文件
        if imports:
            new_content = []

            # 文档字符串部分
            new_content.extend(lines[:docstring_end])
            new_content.append('')  # 空行分隔

            # 导入部分
            new_content.extend(imports)
            new_content.append('')  # 空行分隔

            # 其他内容
            new_content.extend(other_lines[docstring_end:])

            new_content = '\n'.join(new_content)
        else:
            new_content = content

        # 写回文件
        if new_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return len(imports)
        else:
            return 0

    except Exception as e:
        print(f"❌ 修复文件失败 {file_path}: {e}")
        return 0

def main():
    """主函数"""
    print("🚀 全面的E402模块导入位置修复工具")
    print("=" * 60)

    # 查找E402文件
    files_to_fix = find_e402_files()

    if not files_to_fix:
        print("✅ 没有发现E402问题")
        return

    print(f"📁 发现 {len(files_to_fix)} 个文件需要修复:")
    for file_path in files_to_fix:
        print(f"   - {file_path}")

    print()
    total_fixes = 0

    # 修复每个文件
    for file_path_str in files_to_fix:
        file_path = Path(file_path_str)
        print(f"🔧 修复文件: {file_path}")
        fixes = fix_e402_in_file(file_path)
        total_fixes += fixes
        if fixes > 0:
            print(f"   ✅ 修复了 {fixes} 个导入位置问题")
        else:
            print(f"   ℹ️  没有发现可修复的问题")
        print()

    print("=" * 60)
    print(f"📊 修复总结:")
    print(f"   处理文件: {len(files_to_fix)} 个")
    print(f"   修复错误: {total_fixes} 个")

    # 验证修复效果
    print()
    print("🔍 验证修复效果...")
    try:
        result = subprocess.run(
            ['ruff', 'check', '--select=E402', 'src/', '--output-format=concise'],
            capture_output=True,
            text=True
        )
        remaining = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
        print(f"   剩余E402错误: {remaining}个")

        if remaining == 0:
            print("🎉 所有E402错误已修复完成！")
        else:
            print(f"⚠️  还有 {remaining} 个E402错误需要进一步处理")

    except Exception as e:
        print(f"❌ 验证失败: {e}")

if __name__ == "__main__":
    main()