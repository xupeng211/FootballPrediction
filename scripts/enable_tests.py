#!/usr/bin/env python3
"""
重新启用之前被禁用的测试
"""

import re
from pathlib import Path

def enable_tests():
    """重新启用测试"""
    test_file = Path("tests/unit/api/test_data_comprehensive.py")

    if not test_file.exists():
        print("❌ 测试文件不存在")
        return False

    content = test_file.read_text(encoding='utf-8')

    # 移除 @pytest.mark.skip 装饰器
    pattern = r'(\s+)@pytest\.mark\.skip\(reason="Function not implemented in src\.api\.data"\)\s*\n(\s+@pytest\.mark\.asyncio)'
    replacement = r'\2'
    content = re.sub(pattern, replacement, content)

    # 保存文件
    test_file.write_text(content, encoding='utf-8')
    print("✅ 已重新启用测试")
    return True

if __name__ == "__main__":
    enable_tests()