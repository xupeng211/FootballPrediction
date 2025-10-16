#!/usr/bin/env python3
"""
终极修复所有模块的语法错误
"""

import ast
import os
import re

def find_and_fix_all_errors():
    """查找并修复所有语法错误"""

    # 获取所有需要检查的文件
    all_files = []
    for module in ['src/domain', 'src/services', 'src/database']:
        if os.path.exists(module):
            for root, dirs, files in os.walk(module):
                for file in files:
                    if file.endswith('.py'):
                        all_files.append(os.path.join(root, file))

    # 批量修复规则
    fix_rules = [
        # 修复类型注解中的括号
        (r'(\w+: Optional\[.*?\])\] = None', r'\1 = None'),
        (r'(\w+: Optional\[.*?\])\] = None,', r'\1 = None,'),
        (r'(\w+: Dict\[.*?\])\] = None', r'\1 = None'),
        (r'(\w+: Dict\[.*?\])\] = {}', r'\1 = {}'),
        (r'(\w+: List\[.*?\])\] = None', r'\1 = None'),
        (r'(\w+: List\[.*?\])\] = \{\}', r'\1 = []'),
        (r'(\w+: Union\[.*?\])\] = None', r'\1 = None'),

        # 修复字典初始化
        (r' = \{\]\]', r' = {}'),
        (r' = \}\]', r' = {}'),
        (r' = \[\}', r' = []'),

        # 修复函数参数
        (r'\)\s*\)\s*:', r')):'),
        (r'\]\s*\]\s*=', r']] ='),
        (r'\]\s*\]\s*\)', r']])'),

        # 修复类型注解的返回类型
        (r'-> Optional\[Dict\[str, Any\]:', r'-> Optional[Dict[str, Any]]:'),
        (r'-> Dict\[str, Dict\[str, Any\]:', r'-> Dict[str, Dict[str, Any]]:'),

        # 修复未闭合的字符串
        (r'return f"([^"]*?)(?<!")$', r'return f"\1"'),
        (r'print\(f"([^"]*?)(?<!")$', r'print(f"\1")'),

        # 修复三引号文档字符串
        (r'"""$', r'"""'),

        # 修复Type注解
        (r'Dict\[str, Type\[Any, PredictionStrategy\]\]', r'Dict[str, Type[PredictionStrategy]]'),
        (r'Dict\[str, Type\[Any, .*\]\]', r'Dict[str, Type[\1]]'),

        # 修复except子句
        (r'except\s*\(\s*([^)]*?)\s*\)\s*as\s*:', r'except (\1) as:'),

        # 修复其他常见错误
        (r',\s*\)\s*\.', r').'),
        (r'\]\s*\.\s*\w+', r'].\1'),
    ]

    fixed_files = []
    error_files = []

    for filepath in all_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 应用所有修复规则
            for pattern, replacement in fix_rules:
                new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                if new_content != content:
                    content = new_content

            # 特殊修复某些文件
            if 'events/base.py' in filepath:
                content = fix_events_base(content)
            elif 'team.py' in filepath and 'models' in filepath:
                content = fix_team_model(content)

            # 如果内容有变化，写回文件
            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_files.append(filepath)

            # 验证修复
            try:
                ast.parse(content)
            except SyntaxError as e:
                error_files.append((filepath, f"Line {e.lineno}: {e.msg}"))

        except Exception as e:
            error_files.append((filepath, f"Error reading/writing: {e}"))

    return fixed_files, error_files

def fix_events_base(content):
    """修复events/base.py的特殊问题"""
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # 修复字典项缺少逗号
        if '"event_id": self.event_id,' in line and not line.strip().endswith(','):
            lines[i] = line.rstrip() + ','
        if '"event_type": self.__class__.__name__,' in line and not line.strip().endswith(','):
            lines[i] = line.rstrip() + ','
        if '"aggregate_id": self.aggregate_id,' in line and not line.strip().endswith(','):
            lines[i] = line.rstrip() + ','
        if '"occurred_at": self.occurred_at.isoformat(),' in line and not line.strip().endswith(','):
            lines[i] = line.rstrip() + ','
        if '"version": self.version,' in line and not line.strip().endswith(','):
            lines[i] = line.rstrip() + ','
        if '"data": self._get_event_data(),' in line and not line.strip().endswith(','):
            lines[i] = line.rstrip() + ','
    return '\n'.join(lines)

def fix_team_model(content):
    """修复team模型的未闭合字符串"""
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # 查找未闭合的f-string
        if 'return f"' in line or 'print(f"' in line:
            if not line.strip().endswith('"') and '"' in line:
                # 计算引号数量
                quote_count = line.count('"')
                if quote_count % 2 == 1:  # 奇数个引号，说明未闭合
                    lines[i] = line.rstrip() + '"'
    return '\n'.join(lines)

def verify_all_modules():
    """验证所有模块"""
    modules = {
        'domain': 'src/domain',
        'services': 'src/services',
        'database': 'src/database',
        'api': 'src/api',
        'core': 'src/core',
        'utils': 'src/utils',
        'cache': 'src/cache',
        'collectors': 'src/collectors',
        'adapters': 'src/adapters',
    }

    total_files = 0
    total_success = 0
    module_results = {}

    for module_name, module_path in modules.items():
        if os.path.exists(module_path):
            success = 0
            total = 0
            for root, dirs, files in os.walk(module_path):
                for file in files:
                    if file.endswith('.py'):
                        filepath = os.path.join(root, file)
                        total += 1
                        total_files += 1
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                content = f.read()
                            ast.parse(content)
                            success += 1
                            total_success += 1
                        except:
                            pass
            module_results[module_name] = (success, total)

    return total_files, total_success, module_results

if __name__ == "__main__":
    print("=" * 60)
    print("开始终极修复所有语法错误")
    print("=" * 60)

    fixed, errors = find_and_fix_all_errors()

    print(f"\n修复了 {len(fixed)} 个文件")
    if errors:
        print(f"\n仍有 {len(errors)} 个文件存在错误:")
        for filepath, error in errors[:10]:
            print(f"  - {filepath}: {error}")
        if len(errors) > 10:
            print(f"  ... 还有 {len(errors)-10} 个错误")

    print("\n" + "=" * 60)
    print("验证修复结果")
    print("=" * 60)

    total_files, total_success, results = verify_all_modules()

    print(f"\n总体结果:")
    print(f"  总计: {total_success}/{total_files} 文件语法正确")
    print(f"  成功率: {total_success/total_files*100:.1f}%")

    print("\n各模块详情:")
    for module, (success, total) in results.items():
        if total > 0:
            rate = success/total*100
            status = "✓" if success == total else "✗"
            print(f"  {status} {module}: {success}/{total} ({rate:.1f}%)")

    if total_success == total_files:
        print("\n🎉 所有文件语法检查通过！")
    else:
        print(f"\n⚠ 还有 {total_files - total_success} 个文件存在语法错误")
