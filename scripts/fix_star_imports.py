#!/usr/bin/env python3
"""
批量修复star imports问题
将 from module import * 替换为明确的导入
"""

import os
from pathlib import Path
import re

def fix_star_imports_in_file(file_path):
    """修复单个文件中的star imports"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 常见的star imports模式
        patterns = [
            # core.exceptions
            {
                'pattern': r'from core\.exceptions import \*',
                'replacement': '''from src.core.exceptions import (
        FootballPredictionError,
        ConfigError,
        DataError,
        ValidationError,
        DatabaseError,
        AuthenticationError,
        AuthorizationError,
        NetworkError,
        APIServiceError,
        CacheError,
        TaskExecutionError,
        TaskTimeoutError,
        TaskRetryError,
        TrackingError,
        ModelLoadError,
        PredictionError,
        DataValidationError,
        ModelValidationError,
        ProcessingError,
        ExternalAPIError,
        InternalError,
    )'''
            },
            # core.di
            {
                'pattern': r'from core\.di import \*',
                'replacement': '''from src.core.di import (
    ServiceLifetime,
    ServiceDescriptor,
    DIContainer,
    ServiceCollection,
    get_service,
    resolve_service,
    inject,
)'''
            },
            # core.config_di
            {
                'pattern': r'from core\.config_di import \*',
                'replacement': '''from src.core.config_di import (
    ConfigurationBinder,
    get_binder,
    ConfigurationProfile,
    load_profile,
)'''
            },
        ]

        # 应用替换模式
        for pattern_info in patterns:
            content = re.sub(
                pattern_info['pattern'],
                pattern_info['replacement'],
                content
            )

        # 如果内容发生了变化，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✅ 修复: {file_path}")
            return True
        else:
            return False

    except Exception as e:
        print(f"  ❌ 错误: {file_path} - {e}")
        return False

def main():
    """主函数"""
    print("🔧 批量修复star imports问题...")

    # 查找所有Python测试文件
    test_files = []
    for pattern in [
        "tests/unit/test_core_*.py",
        "tests/integration/test_*.py"
    ]:
        test_files.extend(Path().glob(pattern))

    fixed_count = 0
    for file_path in test_files:
        if fix_star_imports_in_file(file_path):
            fixed_count += 1

    print(f"✅ 修复完成: {fixed_count} 个文件")

if __name__ == "__main__":
    main()