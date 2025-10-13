#!/usr/bin/env python3
"""
修复 try 块中的未使用导入
"""

import re
from pathlib import Path


def fix_unused_imports_in_try_blocks():
    """修复 try 块中条件使用的导入"""

    # 需要修复的文件列表
    files_to_fix = [
        "tests/unit/api/test_api_comprehensive.py",
        "tests/unit/api/test_models_functional.py",
        "tests/unit/core/test_core_comprehensive.py",
        "tests/unit/coverage_boost/test_class_methods.py",
        "tests/unit/coverage_boost/test_config_functionality.py",
        "tests/unit/coverage_boost/test_import_coverage.py",
        "tests/unit/coverage_boost/test_massive_import.py",
        "tests/unit/coverage_boost/test_models_instantiation.py",
        "tests/unit/coverage_boost/test_simple_class_instantiation.py",
        "tests/unit/coverage_boost/test_utils_functionality.py",
        "tests/unit/extra/extra_coverage_boost.py",
        "tests/unit/test_coverage_boost.py",
        "tests/unit/test_main_extended.py",
        "tests/unit/quick_coverage/test_simple_modules.py",
        "tests/unit/services/test_services_enhanced.py",
        "tests/unit/services/test_services_fixed.py",
        "tests/unit/utils/test_time_utils_functional.py",
        "tests/unit/utils/test_utils_functional.py",
    ]

    fixed_count = 0

    for file_path_str in files_to_fix:
        file_path = Path(file_path_str)

        if not file_path.exists():
            continue

        content = file_path.read_text(encoding="utf-8")
        original_content = content

        # 修复特定的未使用导入
        fixes = [
            # 移除单独的未使用导入
            (r"from pydantic import BaseModel\s*\n", "", "pydantic.BaseModel"),
            (
                r"from src\.api\.config import APIConfig\s*\n",
                "",
                "src.api.config.APIConfig",
            ),
            (r"import asyncio\s*\n", "", "asyncio"),
            (
                r"from fastapi import BackgroundTasks\s*\n",
                "",
                "fastapi.BackgroundTasks",
            ),
            (
                r"from src\.api\.models import TeamInfo\s*\n",
                "",
                "src.api.models.TeamInfo",
            ),
            (
                r"from src\.api\.models import MatchStatus\s*\n",
                "",
                "src.api.models.MatchStatus",
            ),
            (r"import logging\s*\n", "", "logging"),
            (
                r"from src\.utils\.time_utils import parse_datetime\s*\n",
                "",
                "src.utils.time_utils.parse_datetime",
            ),
            (
                r"from src\.utils\.dict_utils import unflatten_dict\s*\n",
                "",
                "src.utils.dict_utils.unflatten_dict",
            ),
            (
                r"from src\.utils\.retry import retry_with_backoff\s*\n",
                "",
                "src.utils.retry.retry_with_backoff",
            ),
            (
                r"from src\.utils\.string_utils import camel_case_to_snake_case, snake_case_to_camel_case\s*\n",
                "",
                "src.utils.string_utils case conversion functions",
            ),
            (
                r"from src\.utils\.file_utils import safe_filename, generate_temp_filename\s*\n",
                "",
                "src.utils.file_utils filename functions",
            ),
            (
                r"from src\.utils\.file_utils import read_file_chunked\s*\n",
                "",
                "src.utils.file_utils.read_file_chunked",
            ),
            (
                r"from src\.utils\.file_utils import get_file_size, get_file_hash\s*\n",
                "",
                "src.utils.file_utils size/hash functions",
            ),
            (
                r"from src\.utils\.dict_utils import filter_dict\s*\n",
                "",
                "src.utils.dict_utils.filter_dict",
            ),
            (
                r"from src\.utils\.dict_utils import rename_keys\s*\n",
                "",
                "src.utils.dict_utils.rename_keys",
            ),
            (
                r"from src\.utils\.dict_utils import sort_dict_by_values\s*\n",
                "",
                "src.utils.dict_utils.sort_dict_by_values",
            ),
            (
                r"from src\.utils\.dict_utils import invert_dict\s*\n",
                "",
                "src.utils.dict_utils.invert_dict",
            ),
            (
                r"from src\.utils\.time_utils import parse_datetime_string\s*\n",
                "",
                "src.utils.time_utils.parse_datetime_string",
            ),
            (
                r"from src\.utils\.time_utils import get_timestamp_ms\s*\n",
                "",
                "src.utils.time_utils.get_timestamp_ms",
            ),
            (
                r"from src\.utils\.time_utils import get_timezone_offset\s*\n",
                "",
                "src.utils.time_utils.get_timezone_offset",
            ),
            (
                r"from src\.utils\.time_utils import convert_timezone\s*\n",
                "",
                "src.utils.time_utils.convert_timezone",
            ),
            (
                r"from src\.utils\.time_utils import is_weekend, is_holiday\s*\n",
                "",
                "src.utils.time_utils date functions",
            ),
            (
                r"from src\.utils\.time_utils import add_time_units, subtract_time_units\s*\n",
                "",
                "src.utils.time_utils time arithmetic",
            ),
            (
                r"from src\.utils\.time_utils import get_time_range, get_date_range\s*\n",
                "",
                "src.utils.time_utils range functions",
            ),
            (
                r"from src\.utils\.time_utils import format_duration, calculate_age\s*\n",
                "",
                "src.utils.time_utils formatting",
            ),
            (
                r"from src\.utils\.crypto_utils import encrypt_data, decrypt_data\s*\n",
                "",
                "src.utils.crypto_utils encryption",
            ),
            (
                r"from src\.utils\.crypto_utils import generate_secure_token\s*\n",
                "",
                "src.utils.crypto_utils token generation",
            ),
            (
                r"from src\.utils\.crypto_utils import hash_password, verify_password\s*\n",
                "",
                "src.utils.crypto_utils password",
            ),
            (
                r"from src\.utils\.crypto_utils import generate_uuid, generate_short_uuid\s*\n",
                "",
                "src.utils.crypto_utils uuid",
            ),
            (
                r"from src\.utils\.retry import RetryConfig, RetryError\s*\n",
                "",
                "src.utils.retry classes",
            ),
            (
                r"from src\.utils\.response import create_success_response, create_error_response\s*\n",
                "",
                "src.utils.response creators",
            ),
            (
                r"from src\.utils\.response import StandardResponse, ResponseStatus\s*\n",
                "",
                "src.utils.response types",
            ),
            (
                r"from database\.models\.league import League\s*\n",
                "",
                "database.models.league.League",
            ),
            (
                r"from database\.models\.team import Team\s*\n",
                "",
                "database.models.team.Team",
            ),
            (
                r"from database\.models\.match import Match\s*\n",
                "",
                "database.models.match.Match",
            ),
            (
                r"from database\.models\.odds import Odds\s*\n",
                "",
                "database.models.odds.Odds",
            ),
            (
                r"from database\.models\.predictions import Prediction\s*\n",
                "",
                "database.models.predictions.Prediction",
            ),
        ]

        # 在 try 块内应用修复
        for pattern, replacement, desc in fixes:
            # 只在 try 块内替换
            # 查找 try 块的范围
            try_block_pattern = r"try:\s*\n((?:\s{4,}.*\n)*?)\s{0,3}except"

            def replace_in_try_block(match):
                try_content = match.group(1)
                # 应用替换
                try_content = re.sub(pattern, replacement, try_content)
                return f"try:\n{try_content}    except"

            content = re.sub(
                try_block_pattern, replace_in_try_block, content, flags=re.MULTILINE
            )

        # 特殊处理：修复多行导入中的部分导入
        # 例如：from src.api.models import MatchResponse, TeamInfo, MatchStatus
        # 只移除 TeamInfo 和 MatchStatus
        content = re.sub(
            r"from src\.api\.models import MatchResponse, TeamInfo, MatchStatus",
            "from src.api.models import MatchResponse",
            content,
        )

        content = re.sub(
            r"from src\.utils\.time_utils import \(\s*get_current_time,\s*format_datetime,\s*parse_datetime,",
            "from src.utils.time_utils import (\n        get_current_time,\n        format_datetime,",
            content,
        )

        content = re.sub(
            r"from src\.utils\.dict_utils import \(\s*deep_merge,\s*flatten_dict,\s*unflatten_dict,",
            "from src.utils.dict_utils import (\n        deep_merge,\n        flatten_dict,",
            content,
        )

        content = re.sub(
            r"from src\.utils\.retry import retry, retry_with_backoff, exponential_backoff",
            "from src.utils.retry import retry, exponential_backoff",
            content,
        )

        # 只保留实际使用的导入
        content = re.sub(
            r"from src\.utils\.string_utils import \(\s*normalize_string,\s*slugify,\s*camel_case_to_snake_case,\s*snake_case_to_camel_case,\s*\)",
            "from src.utils.string_utils import (\n        normalize_string,\n        slugify,\n    )",
            content,
        )

        content = re.sub(
            r"from src\.utils\.file_utils import \(\s*safe_filename,\s*generate_temp_filename,",
            "from src.utils.file_utils import (",
            content,
        )

        content = re.sub(
            r"from src\.utils\.dict_utils import \(\s*merge_dicts,\s*deep_merge,\s*flatten_dict,",
            "from src.utils.dict_utils import (\n        merge_dicts,\n        deep_merge,\n        flatten_dict,",
            content,
        )

        content = re.sub(
            r"from src\.utils\.time_utils import \(\s*get_current_timestamp,\s*get_current_time,\s*format_datetime,",
            "from src.utils.time_utils import (\n        get_current_timestamp,\n        get_current_time,\n        format_datetime,",
            content,
        )

        content = re.sub(
            r"from src\.utils\.crypto_utils import \(\s*generate_uuid,\s*hash_string,",
            "from src.utils.crypto_utils import (\n        generate_uuid,\n        hash_string,",
            content,
        )

        content = re.sub(
            r"from src\.utils\.retry import \(\s*retry,\s*RetryConfig,",
            "from src.utils.retry import (\n        retry,\n        RetryConfig,",
            content,
        )

        # 如果有修改，写入文件
        if content != original_content:
            file_path.write_text(content, encoding="utf-8")
            fixed_count += 1
            print(f"  ✓ 修复了 {file_path}")

    return fixed_count


def main():
    """主函数"""
    print("修复 try 块中的未使用导入...")

    fixed_count = fix_unused_imports_in_try_blocks()

    print(f"\n✅ 修复了 {fixed_count} 个文件！")


if __name__ == "__main__":
    main()
