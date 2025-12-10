#!/usr/bin/env python3
"""
快速修复剩余语法错误
"""

import re

def fix_remaining_syntax_errors():
    """修复剩余的语法错误"""

    # 1. 修复 test_db_integration.py 第246行附近的问题
    try:
        with open('tests/integration/test_db_integration.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # 修复批量操作中的字典格式问题
        content = re.sub(
            r'(\w+_data)\s*{\s*(\w+):\s*(.+?)\s*}',
            r'\1,\n            {\n                "\2": \3\n            }',
            content,
            flags=re.DOTALL
        )

        with open('tests/integration/test_db_integration.py', 'w', encoding='utf-8') as f:
            f.write(content)

        print("✅ 修复 test_db_integration.py")
    except Exception as e:
        print(f"❌ 修复 test_db_integration.py 失败: {e}")

    # 2. 修复 test_football_data_cleaner.py 第138行附近的问题
    try:
        with open('tests/unit/data/processing/test_football_data_cleaner.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # 修复config字典中的逗号问题
        content = re.sub(
            r'"remove_duplicates": False\s*"',
            r'"remove_duplicates": False,\n            "',
            content
        )

        with open('tests/unit/data/processing/test_football_data_cleaner.py', 'w', encoding='utf-8') as f:
            f.write(content)

        print("✅ 修复 test_football_data_cleaner.py")
    except Exception as e:
        print(f"❌ 修复 test_football_data_cleaner.py 失败: {e}")

    # 3. 修复 test_enhanced_ev_calculator.py 第277行附近的问题
    try:
        with open('tests/unit/services/betting/test_enhanced_ev_calculator.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # 修复函数调用参数中的逗号问题
        content = re.sub(
            r'calculator\.backtest_strategy\(\s*strategy_name="balanced_enhanced"\s*historical_bets=historical_bets',
            r'calculator.backtest_strategy(\n                strategy_name="balanced_enhanced",\n                historical_bets=historical_bets',
            content
        )

        with open('tests/unit/services/betting/test_enhanced_ev_calculator.py', 'w', encoding='utf-8') as f:
            f.write(content)

        print("✅ 修复 test_enhanced_ev_calculator.py")
    except Exception as e:
        print(f"❌ 修复 test_enhanced_ev_calculator.py 失败: {e}")

if __name__ == "__main__":
    fix_remaining_syntax_errors()