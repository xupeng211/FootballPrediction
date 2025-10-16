#!/usr/bin/env python3
"""
修复domain模块剩余的语法错误
"""

import re
import os

def fix_domain_syntax_errors():
    """修复domain模块的语法错误"""

    fixes = {
        'src/domain/models/prediction.py': [
            (r'(\w+: Optional\[.*?)\] = None', r'\1] = None'),
        ],
        'src/domain/models/team.py': [
            (r'f"([^"]*?)"([^"]*?)"', r'f"\1\2"'),
        ],
        'src/domain/models/match.py': [
            (r'(\w+: Optional\[.*?)\] = None', r'\1] = None'),
        ],
        'src/domain/strategies/config.py': [
            (r'(\w+: Optional\[.*?)\] = None', r'\1] = None'),
        ],
        'src/domain/strategies/base.py': [
            (r'(\w+: Optional\[.*?)\] = None', r'\1] = None'),
        ],
        'src/domain/strategies/historical.py': [
            (r'(\w+: Dict\[.*?)\]', r'\1]'),
        ],
        'src/domain/strategies/ensemble.py': [
            (r'\}', ']'),
        ],
        'src/domain/strategies/statistical.py': [
            (r'(\w+: Dict\[.*?)\]', r'\1]'),
        ],
        'src/domain/strategies/factory.py': [
            (r'\}', ']'),
        ],
        'src/domain/services/scoring_service.py': [
            (r'(\w+: Optional\[.*?)\] = None', r'\1] = None'),
        ],
        'src/domain/services/team_service.py': [
            (r'(\w+: Optional\[.*?)\] = None', r'\1] = None'),
        ],
        'src/domain/events/base.py': [
            (r'"([^"]*?)(\\n)?$', r'"\1"'),
        ],
        'src/domain/events/prediction_events.py': [
            (r'(\w+: Optional\[.*?)\] = None', r'\1] = None'),
        ],
    }

    fixed_files = []

    for filepath, patterns in fixes.items():
        if not os.path.exists(filepath):
            print(f"文件不存在: {filepath}")
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            fixed_files.append(filepath)
            print(f"✓ 修复了 {filepath}")

    return fixed_files

if __name__ == "__main__":
    print("开始修复domain模块剩余语法错误...")
    fixed = fix_domain_syntax_errors()
    print(f"\n修复了 {len(fixed)} 个文件")
    for f in fixed:
        print(f"  - {f}")
