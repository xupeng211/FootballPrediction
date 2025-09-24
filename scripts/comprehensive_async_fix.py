#!/usr/bin/env python3
"""
Comprehensive fix for all AsyncMock patterns in test_features_phase3.py
"""

import re
from pathlib import Path

def fix_all_async_tests():
    """Fix all AsyncMock patterns in the test file"""

    test_file = Path("tests/unit/api/test_features_phase3.py")

    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern 1: Simple scalar_one_or_none pattern
    pattern1 = r'(\s+)mock_result = AsyncMock\(\)\s+mock_result\.scalar_one_or_none\.return_value = ([^\s]+)\s+mock_session\.execute\.return_value = mock_result'

    def replacement1(match):
        indent = match.group(1)
        mock_value = match.group(2)
        return f'{indent}mock_session.execute.return_value = MockAsyncResult(scalar_one_or_none_result={mock_value})'

    content = re.sub(pattern1, replacement1, content, flags=re.MULTILINE)

    # Write back
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print("Fixed all AsyncMock patterns")

if __name__ == "__main__":
    fix_all_async_tests()