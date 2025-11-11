#!/usr/bin/env python3
"""
B904最终修复工具
批量修复异常处理中的raise语句，添加from e链
"""

import re
from pathlib import Path


def fix_b904_in_file(file_path: Path) -> tuple[int, bool]:
    """修复单个文件中的B904错误"""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        original_content = content
        fix_count = 0

        # 匹配except块中的raise HTTPException
        pattern1 = r'(\s+)(except Exception as e:.*?\n)(.*?)raise HTTPException\((.*?)\)\n'

        def replacement1(match):
            nonlocal fix_count
            indent = match.group(1)
            except_block = match.group(2)
            before_raise = match.group(3)
            httpexception_content = match.group(4)

            fix_count += 1
            return f"{indent}{except_block}{before_raise}raise HTTPException({httpexception_content}) from e\n"

        content = re.sub(pattern1, replacement1, content, flags=re.DOTALL)

        # 匹配其他raise语句
        pattern2 = r'(\s+)(except Exception as e:.*?\n)(.*?)raise (\w+Exception?)\((.*?)\)\n'

        def replacement2(match):
            nonlocal fix_count
            indent = match.group(1)
            except_block = match.group(2)
            before_raise = match.group(3)
            exception_class = match.group(4)
            exception_args = match.group(5)

            # 避免重复修复HTTPException
            if 'HTTPException' in exception_class:
                return match.group(0)

            fix_count += 1
            return f"{indent}{except_block}{before_raise}raise {exception_class}({exception_args}) from e\n"

        content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)

        # 写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return fix_count, True
        else:
            return 0, False

    except Exception:
        return 0, False

def find_b904_files() -> list[Path]:
    """查找包含B904错误的Python文件"""
    import subprocess
    try:
        result = subprocess.run(
            ['ruff', 'check', '--select=B904', '--output-format=text'],
            capture_output=True,
            text=True,
            cwd='.'
        )

        files = set()
        if result.stdout:
            for line in result.stdout.split('\n'):
                if line.strip() and 'B904' in line:
                    file_path = line.split(':')[0]
                    if file_path and file_path.endswith('.py'):
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
    success_count = 0

    for file_path in files_to_fix:
        fixes, success = fix_b904_in_file(file_path)
        total_fixes += fixes
        if success:
            success_count += 1
            if fixes > 0:
                pass
            else:
                pass
        else:
            pass


    # 验证修复效果
    try:
        import subprocess
        result = subprocess.run(
            ['ruff', 'check', '--select=B904', '--output-format=concise'],
            capture_output=True,
            text=True
        )
        remaining = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0

        if remaining == 0:
            pass
        else:
            pass

    except Exception:
        pass

if __name__ == "__main__":
    main()
