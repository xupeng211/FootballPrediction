#!/usr/bin/env python3
"""
E402批量修复工具
专门处理模块导入位置问题
"""

import re
from pathlib import Path
from typing import List, Tuple

def fix_e402_in_file(file_path: Path) -> Tuple[int, bool]:
    """修复单个文件中的E402错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        lines = content.split('\n')
        if not lines:
            return 0, True

        # 查找文档字符串结束位置
        docstring_end = 0
        in_docstring = False
        docstring_delimiter = None
        shebang_found = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 处理shebang
            if stripped.startswith('#!') and not shebang_found:
                shebang_found = True
                continue

            # 检查文档字符串开始
            if not in_docstring and ('"""' in stripped or "'''" in stripped):
                in_docstring = True
                if stripped.count('"""') == 2 or stripped.count("'''") == 2:
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

            # 检查第一个导入或代码
            if not in_docstring and (stripped.startswith(('import ', 'from ')) or
                                   (stripped and not stripped.startswith('#') and
                                    not stripped.startswith('"""') and not stripped.startswith("'''"))):
                if docstring_end == 0:
                    docstring_end = i
                break

        # 分离导入和其他内容
        imports = []
        other_lines = []
        current_imports = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            if stripped.startswith(('import ', 'from ')):
                current_imports.append(line)
            elif current_imports:
                # 导入块结束
                imports.extend(current_imports)
                current_imports = []
                other_lines.append(line)
            else:
                other_lines.append(line)

        # 添加最后的导入块
        if current_imports:
            imports.extend(current_imports)

        # 重新组织文件
        if imports:
            new_lines = []

            # 保留shebang和文档字符串
            for i, line in enumerate(lines):
                if i < docstring_end:
                    new_lines.append(line)
                else:
                    break

            # 添加空行
            if new_lines and not new_lines[-1].strip() == '':
                new_lines.append('')

            # 添加所有导入
            new_lines.extend(imports)

            # 添加空行
            if new_lines and not new_lines[-1].strip() == '':
                new_lines.append('')

            # 添加其他内容（跳过原来的导入）
            skip_mode = True
            for i, line in enumerate(lines[docstring_end:], docstring_end):
                stripped = line.strip()
                if stripped.startswith(('import ', 'from ')):
                    continue  # 跳过导入语句
                else:
                    skip_mode = False

                if not skip_mode:
                    new_lines.append(line)

            new_content = '\n'.join(new_lines)
        else:
            new_content = content

        # 写回文件
        if new_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return len(imports), True
        else:
            return 0, False

    except Exception as e:
        print(f"❌ 修复文件失败 {file_path}: {e}")
        return 0, False

def find_e402_files() -> List[Path]:
    """查找包含E402错误的Python文件"""
    import subprocess

    try:
        result = subprocess.run(
            ['ruff', 'check', '--select=E402', '--output-format=text'],
            capture_output=True,
            text=True,
            cwd='.'
        )

        files = set()
        if result.stdout:
            for line in result.stdout.split('\n'):
                if line.strip() and 'E402' in line:
                    file_path = line.split(':')[0]
                    if file_path and file_path.endswith('.py'):
                        files.add(Path(file_path))

        return sorted(list(files))

    except Exception as e:
        print(f"❌ 查找E402文件失败: {e}")
        return []

def main():
    """主函数"""
    print("🔧 E402批量修复工具")
    print("=" * 50)

    # 查找需要修复的文件
    files_to_fix = find_e402_files()

    if not files_to_fix:
        print("✅ 没有发现E402错误")
        return

    print(f"📁 发现 {len(files_to_fix)} 个文件需要修复:")
    for file_path in files_to_fix:
        print(f"   - {file_path}")

    print()
    total_fixes = 0
    success_count = 0

    for file_path in files_to_fix:
        print(f"🔧 修复文件: {file_path}")
        fixes, success = fix_e402_in_file(file_path)
        total_fixes += fixes
        if success:
            success_count += 1
            if fixes > 0:
                print(f"   ✅ 修复了 {fixes} 个导入位置问题")
            else:
                print(f"   ℹ️  没有发现可修复的问题")
        else:
            print(f"   ❌ 修复失败")
        print()

    print("=" * 50)
    print(f"📊 修复总结:")
    print(f"   处理文件: {len(files_to_fix)} 个")
    print(f"   成功修复: {success_count} 个")
    print(f"   修复错误: {total_fixes} 个")

if __name__ == "__main__":
    main()