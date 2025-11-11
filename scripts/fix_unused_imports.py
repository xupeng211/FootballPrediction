#!/usr/bin/env python3
"""
修复剩余的F401未使用导入错误
"""

import re

def fix_unused_imports():
    """修复未使用的导入"""

    files_to_fix = [
        "src/domain/events/__init__.py",
        "src/events/__init__.py",
        "tests/integration/test_api_domain_integration.py",
        "tests/integration/test_data_flow.py",
        "tests/unit/api/test_health_endpoints_comprehensive.py"
    ]

    unused_imports = [
        (r"from \.types import MatchEventData", ""),
        (r"from \.types import .*MatchEventData.*", ""),
        (r"from \.types import PredictionEventData", ""),
        (r"from src\.domain\.models\.prediction import ConfidenceScore", ""),
        (r"from src\.domain\.models\.prediction import PredictionScore", ""),
        (r"from src\.core\.config import Config", ""),
        (r"from src\.queues\.fifo_queue import RedisFIFOQueue", ""),
        (r"from src\.services\.prediction import PredictionService", ""),
        (r"from pydantic import .*Field.*", ""),
        (r"MatchEventData", ""),
        (r"PredictionEventData", ""),
        (r"ConfidenceScore", ""),
        (r"PredictionScore", ""),
        (r"Config", ""),
        (r"RedisFIFOQueue", ""),
        (r"PredictionService", ""),
        (r"Field", ""),
    ]

    total_fixes = 0

    for file_path in files_to_fix:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            for pattern, replacement in unused_imports:
                content = re.sub(pattern, replacement, content)

            # 清理空行
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)

            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ 修复了 {file_path}")
                total_fixes += 1
            else:
                print(f"⏭️ 跳过 {file_path} (无需修复)")

        except Exception as e:
            print(f"❌ 修复 {file_path} 时出错: {e}")

    return total_fixes

if __name__ == "__main__":
    print("🔧 修复F401未使用导入错误...")
    fixes = fix_unused_imports()
    print(f"📊 总共修复了 {fixes} 个文件")