#!/usr/bin/env python3
"""
独立的测试运行脚本，避免复杂的依赖问题
"""

import sys
from pathlib import Path

# 添加src目录到sys.path
sys.path.insert(0, str(Path(__file__).parent / "src"))


# 直接导入模块进行测试
def test_time_utils():
    """测试TimeUtils模块"""
    print("🧪 测试TimeUtils模块...")

    from utils.time_utils import TimeUtils
    from datetime import datetime, timezone

    tests_passed = 0
    tests_total = 0

    # 测试now_utc
    tests_total += 1
    try:
        now = TimeUtils.now_utc()
        assert isinstance(now, datetime)
        assert now.tzinfo == timezone.utc
        print("  ✅ test_now_utc passed")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ test_now_utc failed: {e}")

    # 测试timestamp_to_datetime
    tests_total += 1
    try:
        timestamp = 1609459200.0  # 2021-01-01 00:00:00 UTC
        dt = TimeUtils.timestamp_to_datetime(timestamp)
        assert isinstance(dt, datetime)
        assert dt.tzinfo == timezone.utc
        assert dt.year == 2021
        print("  ✅ test_timestamp_to_datetime passed")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ test_timestamp_to_datetime failed: {e}")

    # 测试datetime_to_timestamp
    tests_total += 1
    try:
        dt = datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        timestamp = TimeUtils.datetime_to_timestamp(dt)
        assert isinstance(timestamp, float)
        assert timestamp == 1609459200.0
        print("  ✅ test_datetime_to_timestamp passed")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ test_datetime_to_timestamp failed: {e}")

    # 测试format_datetime
    tests_total += 1
    try:
        dt = datetime(2021, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        formatted = TimeUtils.format_datetime(dt)
        assert formatted == "2021-01-01 12:30:45"
        print("  ✅ test_format_datetime passed")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ test_format_datetime failed: {e}")

    # 测试parse_datetime
    tests_total += 1
    try:
        date_str = "2021-01-01 12:30:45"
        dt = TimeUtils.parse_datetime(date_str)
        assert dt.year == 2021
        assert dt.month == 1
        assert dt.day == 1
        print("  ✅ test_parse_datetime passed")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ test_parse_datetime failed: {e}")

    print(f"\nTimeUtils测试结果: {tests_passed}/{tests_total} 通过")
    return tests_passed, tests_total


def test_dict_utils():
    """测试DictUtils模块"""
    print("\n🧪 测试DictUtils模块...")

    from utils.dict_utils import DictUtils

    tests_passed = 0
    tests_total = 0

    # 测试deep_merge
    tests_total += 1
    try:
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {"a": 1, "b": 3, "c": 4}
        print("  ✅ test_deep_merge passed")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ test_deep_merge failed: {e}")

    # 测试flatten_dict
    tests_total += 1
    try:
        nested = {"a": {"b": {"c": 1}}, "d": 2}
        result = DictUtils.flatten_dict(nested)
        assert result == {"a.b.c": 1, "d": 2}
        print("  ✅ test_flatten_dict passed")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ test_flatten_dict failed: {e}")

    # 测试filter_none_values
    tests_total += 1
    try:
        data = {"a": 1, "b": None, "c": 3, "d": None}
        result = DictUtils.filter_none_values(data)
        assert result == {"a": 1, "c": 3}
        print("  ✅ test_filter_none_values passed")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ test_filter_none_values failed: {e}")

    print(f"\nDictUtils测试结果: {tests_passed}/{tests_total} 通过")
    return tests_passed, tests_total


def test_string_utils():
    """测试StringUtils模块"""
    print("\n🧪 测试StringUtils模块...")

    from utils.string_utils import StringUtils

    tests_passed = 0
    tests_total = 0

    # 测试truncate
    tests_total += 1
    try:
        text = "Hello, World!"
        result = StringUtils.truncate(text, 5)
        assert result == "He..."  # 5 - len("...") = 2 characters
        print("  ✅ test_truncate passed")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ test_truncate failed: {e}")

    # 测试slugify
    tests_total += 1
    try:
        result = StringUtils.slugify("Hello World!")
        assert result == "hello-world"
        print("  ✅ test_slugify passed")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ test_slugify failed: {e}")

    # 测试camel_to_snake
    tests_total += 1
    try:
        result = StringUtils.camel_to_snake("HelloWorld")
        assert result == "hello_world"
        print("  ✅ test_camel_to_snake passed")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ test_camel_to_snake failed: {e}")

    # 测试snake_to_camel
    tests_total += 1
    try:
        result = StringUtils.snake_to_camel("hello_world")
        assert result == "helloWorld"
        print("  ✅ test_snake_to_camel passed")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ test_snake_to_camel failed: {e}")

    # 测试clean_text
    tests_total += 1
    try:
        result = StringUtils.clean_text("  Hello   World  ")
        assert result == "Hello World"
        print("  ✅ test_clean_text passed")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ test_clean_text failed: {e}")

    # 测试extract_numbers
    tests_total += 1
    try:
        result = StringUtils.extract_numbers("The price is $12.34 and 56 items")
        assert result == [12.34, 56.0]
        print("  ✅ test_extract_numbers passed")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ test_extract_numbers failed: {e}")

    print(f"\nStringUtils测试结果: {tests_passed}/{tests_total} 通过")
    return tests_passed, tests_total


def main():
    """运行所有测试"""
    print("=" * 60)
    print("🚀 独立测试运行器")
    print("=" * 60)

    total_passed = 0
    total_tests = 0

    # 运行各模块测试
    passed, tests = test_time_utils()
    total_passed += passed
    total_tests += tests

    passed, tests = test_dict_utils()
    total_passed += passed
    total_tests += tests

    passed, tests = test_string_utils()
    total_passed += passed
    total_tests += tests

    # 打印总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print(f"✅ 总测试通过数: {total_passed}")
    print(f"📝 总测试数: {total_tests}")
    print(f"📈 通过率: {total_passed/total_tests*100:.1f}%")

    if total_passed == total_tests:
        print("\n✨ 所有测试通过！")
        return 0
    else:
        print(f"\n❌ {total_tests - total_passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
