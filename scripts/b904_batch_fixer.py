#!/usr/bin/env python3
"""
B904异常处理批量修复工具
专门用于修复raise HTTPException缺少from e的问题
"""

import re
import subprocess


def find_b904_errors() -> list[dict]:
    """查找所有B904错误"""
    try:
        result = subprocess.run(
            ['ruff', 'check', '--select=B904', '--output-format=json'],
            capture_output=True,
            text=True,
            cwd='src'
        )

        errors = []
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip():
                    parts = line.split(':')
                    if len(parts) >= 4:
                        errors.append({
                            'file': parts[0],
                            'line': int(parts[1]),
                            'col': int(parts[2]),
                            'rule': parts[3],
                            'message': ':'.join(parts[4:]) if len(parts) > 4 else ''
                        })
        return errors
    except Exception as e:
        print(f"❌ 查找B904错误失败: {e}")
        return []

def fix_http_exception_in_file(file_path: str) -> int:
    """修复单个文件中的HTTPException B904错误"""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        original_content = content
        fix_count = 0

        # 匹配常见的HTTPException模式
        patterns = [
            # 基本模式: except Exception as e: ... raise HTTPException(...)
            (r'(\s+)(except\s+\w+\s+as\s+\w+.*?\n)(\s+)(raise\s+HTTPException\([^)]+\))\n',
             r'\1\2\3\4 from e\n'),

            # 特殊情况: raise HTTPException(status_code=..., detail=str(e))
            (r'raise\s+HTTPException\(status_code=\d+,\s+detail=str\([^)]+\))\n',
             r'raise HTTPException(status_code=\d+, detail=str(\1)) from e\n'),

            # 带f-string的情况: raise HTTPException(status_code=..., detail=f"...{e}")
            (r'raise\s+HTTPException\(status_code=\d+,\s+detail=f"[^"]*\{[^}]*\}[^"]*"\))\n',
             r'raise HTTPException(status_code=\d+, detail=f"\1{e}\2") from e\n'),
        ]

        for pattern, replacement in patterns:
            new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
            content = new_content
            fix_count += count

        # 如果有修改，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return fix_count
        else:
            return 0

    except Exception as e:
        print(f"❌ 修复文件失败 {file_path}: {e}")
        return 0

def main():
    """主函数"""
    print("🔧 B904异常处理批量修复工具")
    print("=" * 50)

    # 查找B904错误
    errors = find_b904_errors()

    if not errors:
        print("✅ 没有发现B904错误")
        return

    # 按文件分组
    files_to_fix = {}
    for error in errors:
        file_path = error['file']
        if file_path not in files_to_fix:
            files_to_fix[file_path] = []
        files_to_fix[file_path].append(error)

    print(f"📁 发现 {len(files_to_fix)} 个文件需要修复:")
    for file_path, file_errors in files_to_fix.items():
        print(f"   - {file_path}: {len(file_errors)} 个错误")

    print()
    total_fixes = 0

    # 修复每个文件
    for file_path in files_to_fix.keys():
        print(f"🔧 修复文件: {file_path}")
        fixes = fix_http_exception_in_file(file_path)
        total_fixes += fixes
        if fixes > 0:
            print(f"   ✅ 修复了 {fixes} 个B904错误")
        else:
            print("   ℹ️  需要手动处理")
        print()

    print("=" * 50)
    print("📊 修复总结:")
    print(f"   处理文件: {len(files_to_fix)} 个")
    print(f"   修复错误: {total_fixes} 个")

    # 验证修复效果
    print()
    print("🔍 验证修复效果...")
    try:
        result = subprocess.run(
            ['ruff', 'check', '--select=B904', 'src/', '--output-format=concise'],
            capture_output=True,
            text=True
        )
        remaining = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
        print(f"   剩余B904错误: {remaining}个")

        if remaining == 0:
            print("🎉 所有B904错误已修复完成！")
        else:
            print(f"⚠️  还有 {remaining} 个B904错误需要手动处理")

    except Exception as e:
        print(f"❌ 验证失败: {e}")

if __name__ == "__main__":
    main()
