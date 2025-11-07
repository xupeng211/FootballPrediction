#!/usr/bin/env python3
"""
B904异常处理自动修复工具
快速修复raise语句缺少异常链的问题
"""

import re
from pathlib import Path


def fix_b904_in_file(file_path: Path) -> int:
    """修复单个文件中的B904错误"""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        original_content = content
        fix_count = 0

        # 匹配各种raise异常的模式
        patterns = [
            # 基本模式: except Exception as e: ... raise HTTPException(...)
            (r'(\s+)(except\s+\w+\s+as\s+\w+:.*?\n)(\s+)(raise\s+\w+Exception\([^)]+\))\n',
             r'\1\2\3\4 from e\n'),

            # 换行模式: except Exception as e:\n... raise (\n ...)
            (r'(\s+)(except\s+\w+\s+as\s+\w+:.*?\n)(\s+)(raise\s+\w+Exception\(\n.*?\))\n',
             r'\1\2\3\4 from e\n'),
        ]

        for pattern, replacement in patterns:
            new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)
            content = new_content
            fix_count += count

        # 特殊处理：确保raise语句在except块中
        # 查找所有except块并确保其中的raise语句都有from e
        except_blocks = re.findall(r'except\s+\w+\s+as\s+(\w+):(.*?)(?=\n\s*(except|def|class|if|for|while|try|#|\Z|\n\s*\n))',
                                content, re.DOTALL)

        for except_var, block_content in except_blocks:
            # 在块中查找raise语句
            raise_pattern = r'(\s+)(raise\s+\w+Exception\([^)]*\))\n'
            raise_matches = re.findall(raise_pattern, block_content)

            for indent, raise_stmt in raise_matches:
                # 检查是否已经有from e
                if 'from' not in raise_stmt:
                    old_pattern = rf'{indent}{raise_stmt}\n'
                    new_pattern = f'{indent}{raise_stmt} from {except_var}\n'
                    content = content.replace(old_pattern, new_pattern)
                    fix_count += 1

        # 如果有修改，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return fix_count
        else:
            return 0

    except Exception as e:
        print(f"❌ 处理文件失败 {file_path}: {e}")
        return 0


def find_b904_files() -> list[Path]:
    """查找包含B904错误的Python文件"""
    import subprocess
    try:
        result = subprocess.run(
            ['ruff', 'check', '--select=B904', '--output-format=json'],
            capture_output=True,
            text=True,
            cwd='src'
        )

        files = set()
        if result.stdout:
            # 简单解析ruff输出
            for line in result.stdout.split('\n'):
                if line.strip() and 'B904' in line:
                    file_path = line.split(':')[0]
                    if file_path:
                        files.add(Path(file_path))

        return sorted(list(files))

    except Exception as e:
        print(f"❌ 查找B904文件失败: {e}")
        return []


def main():
    """主函数"""
    print("🔧 B904异常处理自动修复工具")
    print("=" * 50)

    # 查找需要修复的文件
    files_to_fix = find_b904_files()

    if not files_to_fix:
        print("✅ 没有发现B904错误")
        return

    print(f"📁 发现 {len(files_to_fix)} 个文件需要修复:")
    for file_path in files_to_fix:
        print(f"   - {file_path}")

    print()
    total_fixes = 0

    for file_path in files_to_fix:
        print(f"🔧 修复文件: {file_path}")
        fixes = fix_b904_in_file(file_path)
        total_fixes += fixes
        if fixes > 0:
            print(f"   ✅ 修复了 {fixes} 个B904错误")
        else:
            print("   ℹ️  没有发现可自动修复的错误")
        print()

    print("=" * 50)
    print("📊 修复总结:")
    print(f"   处理文件: {len(files_to_fix)} 个")
    print(f"   修复错误: {total_fixes} 个")

    # 验证修复效果
    print()
    print("🔍 验证修复效果...")
    try:
        import subprocess
        result = subprocess.run(
            ['ruff', 'check', '--select=B904', 'src/', '--output-format=concise'],
            capture_output=True,
            text=True
        )
        remaining = result.stdout.count('\n') if result.stdout else 0
        print(f"   剩余B904错误: {remaining}个")

        if remaining == 0:
            print("🎉 所有B904错误已修复完成！")
        else:
            print(f"⚠️  还有 {remaining} 个B904错误需要手动处理")

    except Exception as e:
        print(f"❌ 验证失败: {e}")


if __name__ == "__main__":
    main()
