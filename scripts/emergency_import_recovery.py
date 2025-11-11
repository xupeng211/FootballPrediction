#!/usr/bin/env python3
"""
紧急恢复脚本 - 修复被E402修复脚本破坏的导入结构
"""

import os
import re
from pathlib import Path

def recover_broken_files():
    """恢复被破坏的文件导入结构"""

    # 需要恢复的文件列表
    files_to_recover = [
        "tests/integration/conftest.py",
        "tests/integration/test_football_data_api.py",
        "tests/unit/api/test_auth_dependencies.py",
        "tests/integration/test_api_data_source_simple.py",
        "tests/unit/scripts/test_create_api_tests.py",
        "tests/unit/scripts/test_create_service_tests.py",
        "tests/unit/scripts/test_phase35_ai_coverage_master.py",
        "tests/unit/scripts/test_phase35_ai_coverage_master_extended.py"
    ]

    recovered_count = 0

    for file_path in files_to_recover:
        try:
            if not os.path.exists(file_path):
                print(f"⚠️ 文件不存在: {file_path}")
                continue

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 恢复常见的缺失导入
            common_imports = [
                "import os",
                "import sys",
                "import time",
                "import asyncio",
                "import json",
                "import tempfile",
                "from datetime import datetime, timedelta",
                "from pathlib import Path",
                "from unittest.mock import Mock, AsyncMock, patch",
                "import pytest",
                "from dotenv import load_dotenv",
                "from typing import AsyncGenerator",
                "from sqlalchemy.exc import IntegrityError, OperationalError"
            ]

            lines = content.split('\n')
            new_lines = []
            imports_added = set()

            for line in lines:
                new_lines.append(line)

                # 检查是否需要添加缺失的导入
                for imp in common_imports:
                    if imp in line:
                        imports_added.add(imp)

            # 检查并添加缺失的导入到文件开头
            final_lines = []
            import_section = []
            after_imports = False

            for line in lines:
                stripped = line.strip()

                # 如果还没有开始导入部分，先添加文档字符串
                if not after_imports and not stripped.startswith(('import', 'from', '#')):
                    if stripped and not stripped.startswith('"""') and not stripped.startswith("'''"):
                        # 这里应该插入导入
                        for imp in common_imports:
                            if imp not in imports_added:
                                # 检查文件内容中是否使用了这些模块
                                module_name = imp.split()[1] if imp.startswith('import') else imp.split()[1]
                                if module_name in content:
                                    import_section.append(imp)
                                    imports_added.add(imp)

                        if import_section:
                            final_lines.extend(import_section)
                            final_lines.append('')  # 空行

                        after_imports = True

                final_lines.append(line)

            recovered_content = '\n'.join(final_lines)

            if recovered_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(recovered_content)
                print(f"✅ 恢复了 {file_path}")
                recovered_count += 1
            else:
                print(f"⏭️ 跳过 {file_path} (无需恢复)")

        except Exception as e:
            print(f"❌ 恢复 {file_path} 时出错: {e}")

    return recovered_count

def specific_fixes():
    """针对特定文件的具体修复"""

    fixes_applied = 0

    # 修复 test_football_data_api.py
    try:
        file_path = "tests/integration/test_football_data_api.py"
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 确保有正确的导入顺序
            if "import os" not in content:
                content = content.replace(
                    "import asyncio\nimport os",
                    "import asyncio\nimport os"
                )

            if "import sys" not in content:
                content = content.replace(
                    "import asyncio\nimport os",
                    "import asyncio\nimport os\nimport sys"
                )

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"✅ 具体修复了 {file_path}")
            fixes_applied += 1

    except Exception as e:
        print(f"❌ 具体修复 {file_path} 时出错: {e}")

    return fixes_applied

if __name__ == "__main__":
    print("🚨 紧急恢复被破坏的导入结构...")

    recovered = recover_broken_files()
    specific_fixes_count = specific_fixes()

    total_fixed = recovered + specific_fixes_count
    print(f"📊 总共恢复了 {total_fixed} 个文件")

    if total_fixed > 0:
        print("🔄 请重新运行代码质量检查以验证恢复效果")
    else:
        print("ℹ️ 没有发现需要恢复的文件")