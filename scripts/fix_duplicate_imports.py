#!/usr/bin/env python3
"""
修复重复的类型导入
"""

import re
from pathlib import Path


def fix_duplicate_imports(file_path: Path):
    """修复单个文件的重复导入"""
    content = file_path.read_text(encoding="utf-8")
    original = content

    # 修复重复的 Any 导入
    content = re.sub(
        r"from typing import Any,.*?, Any", "from typing import Any,", content
    )
    content = re.sub(r"from typing import Any, Any", "from typing import Any", content)

    # 修复重复的 Dict 导入
    content = re.sub(r"Dict\[str, Any\]\[str, Any\]", "Dict[str, Any]", content)
    content = re.sub(r"dict\[str, Any\]\[str, Any\]", "dict[str, Any]", content)

    # 修复重复的 List 导入
    content = re.sub(r"List\[Any\]\[str\]", "List[str]", content)
    content = re.sub(r"List\[Any\]\[Any\]", "List[Any]", content)
    content = re.sub(
        r"List\[Any\]\[Dict\[str, Any\]\]", "List[Dict[str, Any]]", content
    )

    # 修复其他类型
    content = re.sub(r"Optional\[.*?\] \| None", "Optional[{}]", content)

    if content != original:
        file_path.write_text(content, encoding="utf-8")
        print(f"✓ 修复 {file_path.relative_to(PROJECT_ROOT)}")


def main():
    print("🔧 修复重复的类型导入")
    print("=" * 50)

    # 需要修复的文件列表
    files_to_fix = [
        "src/data/quality/exception_handler.py",
        "src/data/quality/prometheus.py",
        "src/data/storage/lake.py",
        "src/services/audit_service_mod/models.py",
        "src/domain/models/team.py",
        "src/cache/redis/core/key_manager.py",
        "src/cqrs/dto.py",
        "src/cqrs/base.py",
        "src/utils/file_utils.py",
        "src/adapters/factory_simple.py",
        "src/adapters/registry_simple.py",
        "src/cache/ttl_cache_enhanced/cache_entry.py",
        "src/utils/dict_utils.py",
        "src/core/prediction/cache_manager.py",
    ]

    for file_path in files_to_fix:
        path = PROJECT_ROOT / file_path
        if path.exists():
            fix_duplicate_imports(path)

    print("\n✅ 修复完成！")


if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).parent.parent
    main()
