#!/usr/bin/env python3
"""
修复缩进和语法错误
专门处理 Python 函数定义、类定义和代码块的缩进问题
"""

import re
from pathlib import Path


def fix_function_indentation(file_path: Path) -> bool:
    """修复函数和类的缩进问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content
        lines = content.split('\n')
        fixed_lines = []
        current_indent = 0
        expected_indent = 0
        in_function = False
        in_class = False
        indent_stack = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 跳过空行和注释
            if not stripped or stripped.startswith('#'):
                fixed_lines.append(line)
                continue

            # 检查函数定义
            if re.match(r'^\s*(async\s+)?def\s+\w+', line):
                # 计算函数定义的缩进
                current_indent = len(line) - len(line.lstrip())
                expected_indent = current_indent
                fixed_lines.append(line)
                in_function = True
                continue

            # 检查类定义
            if re.match(r'^\s*class\s+\w+', line):
                current_indent = len(line) - len(line.lstrip())
                expected_indent = current_indent
                fixed_lines.append(line)
                in_class = True
                continue

            # 检查装饰器
            if stripped.startswith('@'):
                # 装饰器应该与后面的函数或类有相同的缩进
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if re.match(r'^\s*(async\s+)?def\s+\w+|^class\s+\w+', next_line):
                        next_indent = len(next_line) - len(next_line.lstrip())
                        fixed_lines.append(' ' * next_indent + stripped)
                    else:
                        fixed_lines.append(line)
                else:
                    fixed_lines.append(line)
                continue

            # 修复函数/类内部的缩进
            if in_function or in_class:
                # 计算当前行的缩进
                line_indent = len(line) - len(line.lstrip())

                # 如果是控制结构（if, for, while, try, with等），保持当前缩进
                if re.match(r'^(if|elif|else|for|while|try|except|finally|with)\b', stripped):
                    if stripped.startswith(('elif', 'else', 'except', 'finally')):
                        # elif/else/except/finally 应该与对应的 if/try 保持相同缩进
                        fixed_lines.append(' ' * expected_indent + stripped)
                    else:
                        # if/for/while/try/with 保持当前缩进
                        fixed_lines.append(' ' * expected_indent + stripped)
                        # 下一行需要增加缩进
                        indent_stack.append(expected_indent)
                        expected_indent += 4
                elif stripped == ':':
                    # 单独的冒号，通常在函数定义后
                    fixed_lines.append(line)
                    expected_indent += 4
                elif line_indent < expected_indent and stripped:
                    # 缩进不足，修复它
                    fixed_lines.append(' ' * expected_indent + stripped)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        content = '\n'.join(fixed_lines)

        # 修复常见的语法错误
        # 1. 修复函数定义中的冒号
        content = re.sub(r'(async\s+)?def\s+(\w+)\s*\([^)]*\)\s*([^{:]*)\s*$',
                        r'\1def \2(\3):', content, flags=re.MULTILINE)

        # 2. 修复类定义中的冒号
        content = re.sub(r'class\s+(\w+)\s*(\([^)]*\))?\s*([^{:]*)\s*$',
                        r'class \1\2\3:', content, flags=re.MULTILINE)

        # 3. 修复缺失的冒号（在控制结构后）
        for keyword in ['if', 'elif', 'else', 'for', 'while', 'try', 'except', 'finally', 'with']:
            pattern = rf'^(\s*){keyword}\s+.*(?<!:)$'
            content = re.sub(pattern, r'\1' + keyword + r' \2:', content, flags=re.MULTILINE)

        # 4. 修复 return 语句后的括号
        content = re.sub(r'return\s*\(\s*\)', 'return None', content)

        # 5. 修复空的元组
        content = re.sub(r'\(\s*\)', 'None', content)

        # 写回文件
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"    错误: {file_path} - {e}")
        return False


def fix_specific_test_files():
    """修复特定的测试文件"""
    target_files = [
        'tests/unit/services/test_prediction_logic.py',
        'tests/unit/domain/strategies/test_base_strategy.py'
    ]

    print("🔧 修复特定测试文件的缩进和语法...")
    print("=" * 60)

    for file_path in target_files:
        path = Path(file_path)
        if path.exists():
            print(f"\n处理: {file_path}")

            # 读取并修复文件
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            original = content

            # 修复 test_prediction_logic.py 的特定问题
            if 'test_prediction_logic.py' in file_path:
                # 修复函数定义
                content = re.sub(r'def calculate_confidence\(\s*\n\s*historical_accuracy: float,',
                               'def calculate_confidence(\n            historical_accuracy: float,', content)
                content = re.sub(r'def calculate_score_probability\(\s*\n\t*home_attack: float,',
                               'def calculate_score_probability(\n            home_attack: float,', content)
                content = re.sub(r'def validate_match_time\(\s*\n\t*match_time: datetime,',
                               'def validate_match_time(\n            match_time: datetime,', content)
                content = re.sub(r'def check_eligibility\(\s*\n\t*is_active: bool,',
                               'def check_eligibility(\n            is_active: bool,', content)
                content = re.sub(r'def calculate_score\(\s*\n\tpredicted_home: int,',
                               'def calculate_score(\n            predicted_home: int,', content)

                # 修复缺失的冒号
                content = re.sub(r'def calculate_confidence\([^)]*\)(?<!:)$',
                               'def calculate_confidence(historical_accuracy: float, team_form_diff: float, home_advantage: float = 0.1):', content)
                content = re.sub(r'def calculate_score_probability\([^)]*\)(?<!:)$',
                               'def calculate_score_probability(home_attack: float, home_defense: float, away_attack: float, away_defense: float):', content)
                content = re.sub(r'def validate_match_time\([^)]*\)(?<!:)$',
                               'def validate_match_time(match_time: datetime, prediction_time: datetime):', content)
                content = re.sub(r'def check_eligibility\([^)]*\)(?<!:)$',
                               'def check_eligibility(is_active: bool, has_suspended: bool, min_predictions: int = 0):', content)
                content = re.sub(r'def calculate_score\([^)]*\)(?<!:)$',
                               'def calculate_score(predicted_home: int, predicted_away: int, actual_home: int, actual_away: int):', content)

                # 修复缩进
                lines = content.split('\n')
                fixed_lines = []
                in_function = False
                func_indent = 0

                for line in lines:
                    stripped = line.strip()

                    # 函数定义
                    if re.match(r'^\s*def\s+', line):
                        in_function = True
                        func_indent = len(line) - len(line.lstrip())
                        fixed_lines.append(line)
                    elif in_function and stripped and not line.startswith(' ' * (func_indent + 4)):
                        # 函数体内容，确保正确的缩进
                        if not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
                            fixed_lines.append(' ' * (func_indent + 4) + stripped)
                        else:
                            fixed_lines.append(line)
                    else:
                        fixed_lines.append(line)

                content = '\n'.join(fixed_lines)

            # 修复 test_base_strategy.py 的特定问题
            elif 'test_base_strategy.py' in file_path:
                # 修复 return 语句
                content = re.sub(r'return \(\s*\n\s*input_data\.match_id is not None',
                               'return (\n            input_data.match_id is not None', content)

                # 修复函数定义参数
                content = re.sub(r'async def _predict_internal\(\s*\n\s*self, processed_input',
                               'async def _predict_internal(\n        self, processed_input', content)

                # 修复 PredictionOutput 初始化
                content = re.sub(r'return PredictionOutput\(\s*\n_prediction',
                               'return PredictionOutput(\n            _prediction', content)

                # 修复 fixture 函数
                content = re.sub(r'return PredictionInput\(\s*\n\s*match_id=123,',
                               'return PredictionInput(\n        match_id=123,', content)

                # 修复测试方法的参数列表
                content = re.sub(r'async def test_successful_prediction_flow\(\s*\n\s*self, mock_strategy',
                               'async def test_successful_prediction_flow(\n        self, mock_strategy', content)

                # 修复字典初始化
                content = re.sub(r'strategy_data = \{\s*\n"name": "deserialized_strategy"',
                               'strategy_data = {\n            "name": "deserialized_strategy"', content)

                # 修复 async def 调用
                content = re.sub(r'await mock_strategy\.initialize\(config\)\s*\n\s*assert',
                               'await mock_strategy.initialize(config)\n\n        assert', content)

            # 写回文件
            if content != original:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  ✅ 修复成功")
            else:
                print(f"  ⚪ 无需修复")
        else:
            print(f"  ❌ 文件不存在: {file_path}")


def main():
    """主函数"""
    print("🔧 修复缩进和语法错误...")
    print("=" * 60)

    # 先修复特定的测试文件
    fix_specific_test_files()

    print("\n" + "=" * 60)
    print("✨ 修复完成！")

    # 验证修复结果
    print("\n🧪 验证修复结果...")

    import subprocess
    import sys

    # 检查语法
    test_files = [
        'tests/unit/services/test_prediction_logic.py',
        'tests/unit/domain/strategies/test_base_strategy.py'
    ]

    for test_file in test_files:
        path = Path(test_file)
        if path.exists():
            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'py_compile', str(path)],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print(f"  ✅ {test_file} - 语法正确")
                else:
                    print(f"  ❌ {test_file} - 仍有语法错误")
                    if result.stderr:
                        print(f"      错误: {result.stderr[:200]}")
            except Exception as e:
                print(f"  ⚠️  无法检查 {test_file}: {e}")


if __name__ == '__main__':
    main()