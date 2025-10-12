#!/usr/bin/env python3
"""
验证 Phase 3 v2 - Mock 外部依赖的效果
"""

import subprocess
import re
import time
import sys


def run_test_with_mock(test_file, description):
    """运行单个测试并返回结果"""
    print(f"\n测试 {description} ({test_file})...")

    # 使用预加载Mock
    cmd = [
        "python", "-c",
        f"""
import sys
sys.path.insert(0, 'tests')
from conftest_preload import pytest_configure
import pytest.config

# 现在运行pytest
sys.exit(subprocess.run([
    'pytest',
    '{test_file}',
    '-v',
    '--disable-warnings',
    '--tb=short',
    '--timeout=10',
    '-x'
]).returncode)
"""
    ]

    # 更简单的方法：使用环境变量预加载
    env = os.environ.copy()
    env['PYTHONPATH'] = 'tests:src'
    env['TESTING'] = 'true'

    cmd = [
        "pytest",
        test_file,
        "-v",
        "--disable-warnings",
        "--tb=short",
        "--timeout=10",
        "-x"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )

        output = result.stdout + result.stderr

        # 统计结果
        passed = len(re.findall(r"PASSED", output))
        failed = len(re.findall(r"FAILED", output))
        errors = len(re.findall(r"ERROR", output))
        skipped = len(re.findall(r"SKIPPED", output))

        # 检查是否有超时或连接错误
        has_timeout = "timeout" in output.lower() or "TIMEOUT" in output
        has_connection_error = any(err in output for err in [
            "ConnectionError", "OperationalError", "TimeoutError",
            "连接", "超时", "connection", "timeout"
        ])

        if has_timeout or has_connection_error:
            print(f"  ⚠️  连接超时或错误")
            return False, output
        else:
            print(f"  ✓ 通过: {passed}, 失败: {failed}, 错误: {errors}, 跳过: {skipped}")
            return True, output

    except subprocess.TimeoutExpired:
        print(f"  ⚠️  测试超时")
        return False, "Timeout"
    except Exception as e:
        print(f"  ✗️  执行错误: {e}")
        return False, str(e)


def main():
    print("Phase 3 v2 验证：Mock 外部依赖")
    print("=" * 60)
    print("目标：所有测试能执行且无连接超时")
    print("-" * 60)

    # 测试之前使用外部依赖的模块
    test_files = [
        ("数据库基础测试", "tests/unit/database/test_database_basic.py"),
        ("数据库兼容性测试", "tests/unit/database/test_compatibility.py"),
        ("Kafka 测试", "tests/unit/streaming/test_kafka_consumer.py"),
        ("API 测试", "tests/unit/api/test_api_endpoints.py"),
        ("缓存测试", "tests/unit/cache/test_mock_redis.py"),
    ]

    success_count = 0
    total_count = len(test_files)

    for name, test_file in test_files:
        success, output = run_test_with_mock(test_file, name)
        if success:
            success_count += 1

        # 如果有错误，显示详细信息
        if not success and output != "Timeout":
            # 显示前几行错误信息
            lines = output.split('\n')[:20]
            for line in lines:
                if line.strip():
                    print(f"    {line}")

    print("\n" + "=" * 60)
    print(f"Phase 3 v2 验证结果:")
    print(f"  成功: {success_count}/{total_count}")

    if success_count == total_count:
        print("\n✅ Phase 3 v2 目标达成：所有测试都能运行且无超时")
        print("\n建议：")
        print("  - Mock 配置正确")
        print("  - 可以进入 Phase 4：校准覆盖率配置")
        return True
    else:
        print(f"\n⚠️  Phase 3 v2 需要继续优化：{total_count - success_count} 个测试仍有问题")
        print("\n建议：")
        print("  - 检查失败的测试并修复Mock")
        print("  - 确保Mock在导入阶段就生效")
        return False


if __name__ == "__main__":
    import os
    success = main()
    print("\n" + "=" * 60)
    if success:
        print("Phase 3 v2 已完成！")
    else:
        print("Phase 3 v2 需要继续优化。")
    sys.exit(0 if success else 1)