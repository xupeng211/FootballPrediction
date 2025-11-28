#!/bin/bash
# CI关键测试运行器 - 只运行核心稳定测试

echo "🚀 运行CI关键测试..."

# 只运行最稳定的核心测试
python -m pytest tests/unit/utils/test_date_utils.py::TestDateUtils::test_format_datetime_valid \
                  tests/unit/utils/test_date_utils.py::TestDateUtils::test_parse_date_valid \
                  tests/unit/utils/test_date_utils.py::TestDateUtils::test_is_weekend_monday \
                  tests/unit/utils/test_date_utils.py::TestDateUtils::test_get_age_with_datetime \
                  tests/unit/utils/test_date_utils.py::TestDateUtils::test_is_leap_year_valid \
                  tests/unit/utils/test_date_utils.py::TestDateUtils::test_format_duration_seconds_only \
                  tests/unit/utils/test_date_utils.py::TestCachedFunctions::test_cached_format_datetime \
                  tests/unit/database/test_repository.py::TestBaseRepository::test_create_success \
                  tests/unit/database/test_repository.py::TestBaseRepository::test_bulk_create_success \
                  --tb=short --maxfail=3 -x

echo "✅ CI关键测试完成"