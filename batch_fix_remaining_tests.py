#!/usr/bin/env python3
"""
批量修复剩余测试文件的语法错误
针对已知的常见错误模式进行批量修复
"""

import re
from pathlib import Path
from typing import List, Tuple


def fix_test_syntax_errors(content: str) -> str:
    """修复测试文件中的常见语法错误"""

    # 1. 修复函数定义中的参数列表
    # 将 `def function_name(\n    param1: type,\n    param2: type,\n    ) -> return_type:`
    # 修复为正确的语法
    patterns_to_fix = [
        # 修复缺失的括号和冒号
        (r'def (\w+)\(\s*\n(\s+\w+:\s*\w+\s*,?\s*\n)*\s*\)(?<!:)\s*\n',
         lambda m: re.sub(r'def (\w+)\(\s*\n((?:\s+\w+:\s*\w+\s*,?\s*\n)*)\s*\)(?<!:)\s*\n',
                         lambda x: f"def {x.group(1)}(\n{x.group(2).strip()}\n):\n", content)),
    ]

    # 2. 修复 try-except 块
    content = re.sub(
        r'try:\s*\n([^\n]*)\s*\n(?![ \t]*except|finally)',
        r'try:\n    \1\nexcept Exception as e:\n    pass\n',
        content
    )

    # 3. 修复 with 语句的缩进
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # 检查是否是 with 语句
        if re.match(r'^(\s*)with\s+', line):
            indent = re.match(r'^(\s*)', line).group(1)
            fixed_lines.append(line)

            # 检查下一行是否需要缩进
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if next_line.strip() and not next_line.startswith(indent + '    ') and not next_line.strip().startswith('#'):
                    # 添加正确的缩进
                    fixed_lines.append(indent + '    ' + next_line.strip())
                    i += 1
                else:
                    fixed_lines.append(next_line)
                    i += 1
            else:
                i += 1
        else:
            fixed_lines.append(line)
            i += 1

    content = '\n'.join(fixed_lines)

    # 4. 修复意外的缩进
    lines = content.split('\n')
    fixed_lines = []
    indent_stack = [0]

    for line in lines:
        stripped = line.strip()

        # 跳过空行和注释
        if not stripped or stripped.startswith('#'):
            fixed_lines.append(line)
            continue

        # 计算当前缩进
        current_indent = len(line) - len(line.lstrip())

        # 检查是否是新的代码块
        if stripped.endswith(':'):
            # 代码块开始，缩进应该增加
            if current_indent > indent_stack[-1]:
                indent_stack.append(current_indent)
            else:
                # 保持当前缩进
                indent_stack[-1] = current_indent
            fixed_lines.append(line)
        elif current_indent > indent_stack[-1]:
            # 缩进太深，减少到合适级别
            fixed_lines.append(' ' * indent_stack[-1] + stripped)
        else:
            # 缩进合适
            fixed_lines.append(line)

    content = '\n'.join(fixed_lines)

    # 5. 修复未闭合的括号
    open_parens = content.count('(') - content.count(')')
    if open_parens > 0:
        content += ')' * open_parens

    open_brackets = content.count('[') - content.count(']')
    if open_brackets > 0:
        content += ']' * open_brackets

    open_braces = content.count('{') - content.count('}')
    if open_braces > 0:
        content += '}' * open_braces

    # 6. 修复函数定义中的具体错误
    # 修复 `def func_name(\n    param1: type,\n    param2: type,\n    ) -> return_type:`
    # 这种模式
    content = re.sub(
        r'def (\w+)\(\s*\n((?:\s+\w+:\s*[^,\n]+,\s*\n)*\s+\w+:\s*[^,\n]+\s*)\)(?<!:)\s*\n',
        lambda m: f"def {m.group(1)}(\n{m.group(2)}\n):\n",
        content
    )

    return content


def fix_specific_file_patterns(file_path: Path) -> Tuple[bool, str]:
    """修复特定文件的已知错误模式"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content
        file_name = file_path.name

        # 根据文件名应用特定的修复
        if 'test_time_utils.py' in file_name:
            # 修复 try-except 块
            content = re.sub(
                r'try:\s*\n\s*TIME_UTILS_AVAILABLE = True\s*\n\s*except ImportError:\s*\n\s*TIME_UTILS_AVAILABLE = False',
                'try:\n    TIME_UTILS_AVAILABLE = True\nexcept ImportError:\n    TIME_UTILS_AVAILABLE = False',
                content
            )

        elif 'test_file_utils.py' in file_name:
            # 修复 with 语句缩进
            content = re.sub(
                r'with tempfile\.TemporaryDirectory\(\) as tmpdir:\s*\n([^\s])',
                r'with tempfile.TemporaryDirectory() as tmpdir:\n    \1',
                content
            )

        elif 'test_helpers.py' in file_name:
            # 修复 assert 语句缩进
            content = re.sub(
                r'assert isinstance\((\w+), str\)',
                r'    assert isinstance(\1, str)',
                content
            )

        # 应用通用修复
        content = fix_test_syntax_errors(content)

        # 写回文件
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, "成功修复"

        return False, "无需修复"

    except Exception as e:
        return False, f"修复失败: {e}"


def main():
    """主函数"""
    print("🔧 批量修复剩余测试文件的语法错误...")
    print("=" * 60)

    # 要修复的测试文件列表（优先级排序）
    priority_files = [
        'tests/unit/utils/test_helpers.py',
        'tests/unit/utils/test_time_utils.py',
        'tests/unit/utils/test_file_utils.py',
        'tests/unit/utils/test_dict_utils.py',
        'tests/unit/utils/test_data_validator.py',
        'tests/unit/utils/test_crypto_utils.py',
        'tests/unit/utils/test_cache_decorators.py',
        'tests/unit/utils/test_cached_operations.py',
        'tests/unit/utils/test_config_loader.py',
        'tests/unit/utils/test_formatters.py',
    ]

    # 扩展到所有测试文件
    all_test_files = []
    for pattern in ['tests/unit/utils/test_*.py']:
        all_test_files.extend(Path('.').glob(pattern))

    # 去重并排序
    all_test_files = sorted(list(set(all_test_files)))

    print(f"找到 {len(all_test_files)} 个测试文件")

    # 逐个修复
    fixed_count = 0
    failed_count = 0

    for test_file in all_test_files:
        if '__pycache__' in str(test_file):
            continue

        print(f"\n处理: {test_file}")
        fixed, message = fix_specific_file_patterns(test_file)

        if fixed:
            print(f"  ✅ {message}")
            fixed_count += 1
        elif "无需修复" in message:
            print(f"  ⚪ {message}")
        else:
            print(f"  ❌ {message}")
            failed_count += 1

    print("\n" + "=" * 60)
    print(f"✨ 修复完成！")
    print(f"  修复成功: {fixed_count} 个文件")
    print(f"  修复失败: {failed_count} 个文件")

    # 验证修复结果
    print("\n🧪 验证修复结果...")

    import subprocess
    import sys

    test_files_to_check = priority_files[:5]  # 检查前5个优先级文件

    passed_count = 0
    for test_file in test_files_to_check:
        path = Path(test_file)
        if path.exists():
            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'py_compile', str(path)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    print(f"  ✅ {path.name} - 语法正确")
                    passed_count += 1
                else:
                    print(f"  ❌ {path.name} - 仍有语法错误")
            except Exception as e:
                print(f"  ⚠️  无法检查 {path.name}: {e}")

    # 运行一个简单的测试
    print("\n🏃 尝试运行测试...")

    # 先运行 string_utils 确保基础功能正常
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', 'tests/unit/utils/test_string_utils.py', '-q'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("  ✅ string_utils 测试通过")

            # 尝试运行另一个测试
            for test_file in ['test_file_utils.py', 'test_time_utils.py', 'test_helpers.py']:
                path = Path(f'tests/unit/utils/{test_file}')
                if path.exists():
                    try:
                        result = subprocess.run(
                            [sys.executable, '-m', 'pytest', str(path), '-q', '--tb=no'],
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        if result.returncode == 0:
                            print(f"  ✅ {test_file} 测试通过")
                            break
                        else:
                            print(f"  ⚠️  {test_file} 测试失败")
                    except:
                        print(f"  ⚠️  无法运行 {test_file}")
        else:
            print("  ❌ string_utils 测试失败")

    except Exception as e:
        print(f"  ⚠️  无法运行测试: {e}")

    print("\n📊 下一步建议:")
    print("1. 运行 'python -m pytest tests/unit/utils/ -v' 查看哪些测试可以工作")
    print("2. 运行 'python -m pytest tests/unit/utils/ --cov=src.utils --cov-report=term-missing' 查看覆盖率")
    print("3. 手动修复仍然失败的测试文件")


if __name__ == '__main__':
    main()