#!/usr/bin/env python3
"""
批量修复异步测试中的MockAsyncResult问题
"""

import re
from pathlib import Path


def fix_test_file(file_path):
    """修复测试文件中的AsyncMock问题"""

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 修复模式1：简单的scalar_one_or_none情况
    pattern1 = r"""mock_result = AsyncMock\(\)
        mock_result\.scalar_one_or_none\.return_value = ([^)]
+)
        mock_session\.execute\.return_value = mock_result"""

    replacement1 = r"""mock_session.execute.return_value = MockAsyncResult(scalars_result=[], scalar_one_or_none_result=\1)"""

    content = re.sub(pattern1, replacement1, content, flags=re.MULTILINE)

    # 修复模式2：有all()调用的情况
    pattern2 = r"""mock_result = AsyncMock\(\)
        mock_result\.scalars\(\)\.all\(\)\.return_value = ([^)]
+)
        mock_session\.execute\.return_value = mock_result"""

    replacement2 = (
        r"""mock_session.execute.return_value = MockAsyncResult(scalars_result=\1)"""
    )

    content = re.sub(pattern2, replacement2, content, flags=re.MULTILINE)

    # 修复模式3：既有scalars又有scalar_one_or_none
    pattern3 = r"""mock_result = AsyncMock\(\)
        mock_result\.scalar_one_or_none\.return_value = ([^)}
+])
        mock_result\.scalars\(\)\.all\(\)\.return_value = ([^)}
+])
        mock_session\.execute\.return_value = mock_result"""

    replacement3 = r"""mock_session.execute.return_value = MockAsyncResult(scalars_result=\2, scalar_one_or_none_result=\1)"""

    content = re.sub(pattern3, replacement3, content, flags=re.MULTILINE | re.DOTALL)

    # 写回文件
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Fixed {file_path}")


if __name__ == "__main__":
    # 修复test_features_phase3.py
    fix_test_file("tests/unit/api/test_features_phase3.py")
    print("Async test fixes completed!")
