#!/usr/bin/env python3
"""
全面修复所有模块的语法错误
"""

import ast
import os
import re

def check_syntax(filepath):
    """检查文件语法"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

def fix_all_syntax_errors():
    """修复所有语法错误"""

    # 需要修复的文件列表
    error_files = [
        'src/domain/models/league.py',
        'src/domain/models/prediction.py',
        'src/domain/models/team.py',
        'src/domain/models/match.py',
        'src/domain/strategies/config.py',
        'src/domain/strategies/base.py',
        'src/domain/strategies/historical.py',
        'src/domain/strategies/ensemble.py',
        'src/domain/strategies/statistical.py',
        'src/domain/strategies/ml_model.py',
        'src/domain/strategies/factory.py',
        'src/domain/services/scoring_service.py',
        'src/domain/services/team_service.py',
        'src/domain/events/base.py',
        'src/domain/events/prediction_events.py',
    ]

    # 通用修复模式
    common_fixes = [
        # 修复类型注解中的括号不匹配
        (r'(\w+: Optional\[.*?)\] = None,', r'\1] = None,'),
        (r'(\w+: Optional\[.*?)\] = None\)', r'\1] = None)'),
        (r'(\w+: Optional\[.*?)\] = None$', r'\1] = None'),
        (r'(\w+: Dict\[.*?)\] = None', r'\1] = None'),
        (r'(\w+: Dict\[.*?)\] = \{\}', r'\1] = {}'),
        (r'(\w+: List\[.*?)\] = None', r'\1] = None'),
        (r'(\w+: List\[.*?)\] = \{\}', r'\1] = {}'),
        (r'(\w+: Union\[.*?)\] = None', r'\1] = None'),

        # 修复字典初始化
        (r' = \]\]', r' = {}'),
        (r' = \{\]', r' = {}'),
        (r' = \[\}', r' = []'),

        # 修复f-string
        (r'f"([^"]*?)""([^"]*?)"', r'f"\1\2"'),
        (r'f"([^}]*?)$([^}]*)"', r'f"\1\2"'),

        # 修复三引号字符串
        (r'""""', r'"""'),
        (r"''''", r"'''"),

        # 修复except子句
        (r'except \(([^)]*)\) as e:', r'except (\1) as e:'),
    ]

    fixed_files = []

    for filepath in error_files:
        if not os.path.exists(filepath):
            print(f"⚠ 文件不存在: {filepath}")
            continue

        # 读取文件
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 应用通用修复
        for pattern, replacement in common_fixes:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        # 特定文件的修复
        if 'team.py' in filepath:
            content = re.sub(r'return f"\{self\.name\} \(\{self\.code or self\.short_name\}\) - \{self\.rank\}"',
                           r'return f"{self.name} ({self.code or self.short_name}) - {self.rank}"', content)

        if 'events/base.py' in filepath:
            # 修复三引号文档字符串
            content = re.sub(r'^"""$', '"""', content, flags=re.MULTILINE)
            content = re.sub(r'f"\{self\.__class__\.__name__\}\(\{self\.event_id\}\)"""',
                           r'return f"{self.__class__.__name__}({self.event_id})"', content)
            if 'return f"' in content and '"""' not in content.split('return f"')[1].split('\n')[0]:
                content = re.sub(r'return f"([^"]*)"', r'return f"\1"', content)

        # 写回文件
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            fixed_files.append(filepath)
            print(f"✓ 修复了 {filepath}")

        # 验证修复
        is_valid, error = check_syntax(filepath)
        if not is_valid:
            print(f"✗ {filepath} 仍有错误: {error}")

    return fixed_files

def verify_all_modules():
    """验证所有模块的语法正确性"""

    modules = {
        'domain': 'src/domain',
        'services': 'src/services',
        'database': 'src/database',
    }

    total_files = 0
    total_success = 0

    for module_name, module_path in modules.items():
        print(f"\n验证 {module_name} 模块:")
        success_count = 0
        file_count = 0

        if os.path.exists(module_path):
            for root, dirs, files in os.walk(module_path):
                for file in files:
                    if file.endswith('.py'):
                        filepath = os.path.join(root, file)
                        file_count += 1
                        total_files += 1

                        is_valid, error = check_syntax(filepath)
                        if is_valid:
                            success_count += 1
                            total_success += 1
                        else:
                            print(f"  ✗ {filepath}: {error}")

        print(f"  成功: {success_count}/{file_count} 文件语法正确")

    print(f"\n总体结果:")
    print(f"  总计: {total_success}/{total_files} 文件语法正确")
    print(f"  成功率: {total_success/total_files*100:.1f}%")

    return total_success == total_files

if __name__ == "__main__":
    print("=" * 50)
    print("开始全面修复语法错误")
    print("=" * 50)

    fixed = fix_all_syntax_errors()
    print(f"\n修复了 {len(fixed)} 个文件")

    print("\n" + "=" * 50)
    print("验证修复结果")
    print("=" * 50)

    all_good = verify_all_modules()

    if all_good:
        print("\n🎉 所有模块语法检查通过！")
    else:
        print("\n⚠ 仍有文件存在语法错误")
