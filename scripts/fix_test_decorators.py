import os
#!/usr/bin/env python3
"""
修复测试文件中的装饰器问题
"""

import re
from pathlib import Path

def fix_test_decorators():
    """修复装饰器问题"""
    test_file = Path("tests/unit/api/test_data_comprehensive.py")

    if not test_file.exists():
        print("❌ 测试文件不存在")
        return False

    content = test_file.read_text(encoding='utf-8')

    # 修复连续的装饰器问题
    pattern = r'(\s+)@pytest\.mark\.skip\(reason = os.getenv("FIX_TEST_DECORATORS_REASON_20")\)\s*@pytest\.mark\.asyncio'
    replacement = r'\1@pytest.mark.asyncio'
    content = re.sub(pattern, replacement, content)

    # 保存文件
    test_file.write_text(content, encoding='utf-8')
    print("✅ 已修复装饰器问题")
    return True

if __name__ == "__main__":
    fix_test_decorators()