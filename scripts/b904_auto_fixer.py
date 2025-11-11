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

    except Exception:
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

        return sorted(files)

    except Exception:
        return []


def main():
    """主函数"""

    # 查找需要修复的文件
    files_to_fix = find_b904_files()

    if not files_to_fix:
        return

    for file_path in files_to_fix:
        pass

    total_fixes = 0

    for file_path in files_to_fix:
        fixes = fix_b904_in_file(file_path)
        total_fixes += fixes
        if fixes > 0:
            pass
        else:
            pass


    # 验证修复效果
    try:
        import subprocess
        result = subprocess.run(
            ['ruff', 'check', '--select=B904', 'src/', '--output-format=concise'],
            capture_output=True,
            text=True
        )
        remaining = result.stdout.count('\n') if result.stdout else 0

        if remaining == 0:
            pass
        else:
            pass

    except Exception:
        pass


if __name__ == "__main__":
    main()
