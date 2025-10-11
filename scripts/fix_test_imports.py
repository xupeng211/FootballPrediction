#!/usr/bin/env python3
"""
修复测试导入错误脚本
批量修复测试文件中的导入问题
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Dict
import subprocess


def get_common_import_fixes() -> Dict[str, str]:
    """返回常见的导入修复映射"""
    return {
        # Logger 相关
        "from src.core.logging import": "from src.core.logger import",
        "from src.core.logging_system import": "from src.core.logger import",
        "from .logging import LoggerManager": "from .logger import Logger",
        # Base Service 相关
        "from src.services.base import": "from src.services.base_unified import",
        "from src.services.base_service import": "from src.services.base_unified import",
        # API 相关
        "from src.api.predictions.models import": "from src.api.schemas import",
        "from src.api.predictions.service import": "from src.services.prediction_service import",
        # Database 相关
        "from src.database.base import": "from src.database.connection_mod import",
        "from src.database.models.base import": "from src.database.models import",
        # Utils 相关
        "from src.utils.time_util import": "from src.utils.time_utils import",
        "from src.utils.cache_util import": "from src.utils.cache_utils import",
        # Core 相关
        "from src.core.config import": "from src.core.configuration import",
        "from src.core.exceptions import": "from src.core.exception import",
        # 其他常见修复
        "LoggerManager": "Logger",
        "get_logger": "get_logger",
        "get_async_session": "get_db_session",
    }


def fix_file_imports(file_path: Path) -> int:
    """修复单个文件的导入错误"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        fixes = get_common_import_fixes()

        # 应用修复
        for old, new in fixes.items():
            content = content.replace(old, new)

        # 特殊模式修复
        # 1. 修复相对导入
        content = re.sub(r"from \.\.(\w+)", r"from src.\1", content)

        # 2. 修复缺失的模型导入
        if "from sqlalchemy import" in content and "Base" not in content:
            if "from sqlalchemy.orm import" in content:
                content = re.sub(
                    r"from sqlalchemy\.orm import (.*)",
                    r"from sqlalchemy.orm import \1\nfrom sqlalchemy.ext.declarative import declarative_base\n\nBase = declarative_base()",
                    content,
                )

        # 3. 修复 Optional 导入
        if "Optional[" in content and "from typing import Optional" not in content:
            if "from typing import" in content:
                content = re.sub(
                    r"from typing import (.*)",
                    r"from typing import \1, Optional",
                    content,
                )
            else:
                content = "from typing import Optional\n" + content

        # 4. 修复 Dict/Any 导入
        if "Dict[" in content and "from typing import Dict" not in content:
            if "from typing import" in content:
                content = re.sub(
                    r"from typing import (.*)", r"from typing import \1, Dict", content
                )
            else:
                content = "from typing import Dict\n" + content

        if "Any" in content and "from typing import Any" not in content:
            if "from typing import" in content:
                content = re.sub(
                    r"from typing import (.*)", r"from typing import \1, Any", content
                )
            else:
                content = "from typing import Any\n" + content

        # 5. 修复 AsyncMock 导入
        if (
            "AsyncMock" in content
            and "from unittest.mock import" in content
            and "AsyncMock" not in content
        ):
            content = content.replace(
                "from unittest.mock import", "from unittest.mock import AsyncMock, "
            )

        # 6. 修复 pytest fixtures
        content = re.sub(
            r'@pytest\.fixture\("session"\)',
            '@pytest.fixture(scope="session")',
            content,
        )

        # 保存修复后的文件
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return 1

        return 0

    except Exception as e:
        print(f"   ❌ 修复 {file_path} 时出错: {str(e)}")
        return 0


def find_broken_import_files() -> List[Path]:
    """查找有导入错误的测试文件"""
    broken_files = []

    # 运行 pytest --collect-only 来收集错误
    result = subprocess.run(
        ["python", "-m", "pytest", "--collect-only", "-q", "tests/"],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )

    # 解析错误输出
    for line in result.stderr.split("\n"):
        if "ERROR collecting" in line:
            # 提取文件路径
            match = re.search(r"ERROR collecting ([^\s]+)", line)
            if match:
                file_path = Path(match.group(1))
                if file_path.exists() and file_path.suffix == ".py":
                    broken_files.append(file_path)

    return broken_files


def main():
    """主函数"""
    print("🔧 修复测试导入错误...\n")

    # 1. 查找有错误的文件
    print("1. 查找有导入错误的文件...")
    broken_files = find_broken_import_files()

    if not broken_files:
        print("   ✅ 没有发现导入错误！")
        return

    print(f"   发现 {len(broken_files)} 个文件需要修复")

    # 2. 修复文件
    print("\n2. 修复导入错误...")
    fixed_count = 0

    for file_path in broken_files:
        print(f"   修复 {file_path.relative_to(Path.cwd())}...", end=" ")
        if fix_file_imports(file_path):
            print("✅")
            fixed_count += 1
        else:
            print("⚠️ 无需修复")

    print(f"\n✅ 修复完成！共修复 {fixed_count} 个文件")

    # 3. 验证修复
    print("\n3. 验证修复结果...")
    result = subprocess.run(
        ["python", "-m", "pytest", "--collect-only", "-q", "tests/"],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )

    error_count = result.stderr.count("ERROR collecting")
    if error_count == 0:
        print("   ✅ 所有导入错误已修复！")
    else:
        print(f"   ⚠️ 还有 {error_count} 个错误需要手动修复")

    # 4. 运行部分测试验证
    print("\n4. 运行部分测试验证...")
    test_files = [
        f
        for f in broken_files
        if "test_api_simple.py" in str(f) or "test_placeholder.py" in str(f)
    ]

    if test_files:
        for test_file in test_files[:3]:  # 只测试前3个
            print(f"   测试 {test_file.name}...", end=" ")
            result = subprocess.run(
                ["python", "-m", "pytest", str(test_file), "-q"],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print("✅ 通过")
            else:
                print("❌ 失败")

    print("\n📌 建议：")
    print("1. 运行 `pytest tests/unit/api/test_api_simple.py -v` 验证核心功能")
    print("2. 运行 `make coverage-local` 检查整体覆盖率")
    print("3. 手动修复剩余的特殊错误")


if __name__ == "__main__":
    main()
