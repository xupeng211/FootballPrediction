#!/usr/bin/env python3
"""
验证 Phase 3 - Mock 外部依赖的效果
"""

import subprocess
import re
import time


def main():
    print("Phase 3 验证：Mock 外部依赖")
    print("=" * 60)
    print("目标：所有测试能执行且无连接超时")
    print("-" * 60)

    # 测试之前使用外部依赖的模块
    test_files = [
        ("数据库测试", "tests/unit/database/test_database_basic.py"),
        ("Kafka 测试", "tests/unit/streaming/test_kafka_consumer.py"),
        ("集成测试", "tests/integration/test_database_integration.py"),
        ("API 测试", "tests/unit/api/test_api_endpoints.py"),
        ("缓存测试", "tests/unit/cache/test_mock_redis.py"),
    ]

    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_errors = 0
    total_skipped = 0
    timeout_count = 0

    for name, test_file in test_files:
        print(f"\n测试 {name} ({test_file})...")

        cmd = [
            "pytest",
            test_file,
            "-v",
            "--disable-warnings",
            "--tb=short",
            "--timeout=30",
            "-x",  # 第一个失败就停止
        ]

        try:
            # 设置超时
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,  # 60秒超时
            )

            output = result.stdout + result.stderr

            # 统计结果
            passed = len(re.findall(r"PASSED", output))
            failed = len(re.findall(r"FAILED", output))
            errors = len(re.findall(r"ERROR", output))
            skipped = len(re.findall(r"SKIPPED", output))

            # 检查是否有超时
            if "timeout" in output.lower() or "TIMEOUT" in output:
                timeout_count += 1
                print("  ⚠️  超时")
            else:
                print(f"  通过: {passed}, 失败: {failed}, 错误: {errors}, 跳过: {skipped}")

            total_tests += passed + failed + errors + skipped
            total_passed += passed
            total_failed += failed
            total_errors += errors
            total_skipped += skipped

        except subprocess.TimeoutExpired:
            print("  ⚠️  测试超时")
            timeout_count += 1
        except Exception as e:
            print(f"  ✗️  执行错误: {e}")

    # 运行一个更大的测试集
    print("\n" + "-" * 60)
    print("运行更大的测试集...")

    cmd = [
        "pytest",
        "tests/unit/",
        "-v",
        "--disable-warnings",
        "--tb=no",
        "--maxfail=20",
        "--timeout=30",
    ]

    try:
        print("执行: pytest tests/unit/ (30秒超时)...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # 2分钟超时
        )

        output = result.stdout + result.stderr

        # 解析结果
        passed = len(re.findall(r"PASSED", output))
        failed = len(re.findall(r"FAILED", output))
        errors = len(re.findall(r"ERROR", output))
        skipped = len(re.findall(r"SKIPPED", output))

        print("\n批量测试结果:")
        print(f"  通过: {passed}")
        print(f"  失败: {failed}")
        print(f"  错误: {errors}")
        print(f"  跳过: {skipped}")
        print(f"  总计: {passed + failed + errors + skipped}")

    except subprocess.TimeoutExpired:
        print("\n批量测试超时")

    print("\n" + "=" * 60)
    print("Phase 3 验证结果:")
    print(f"  超时测试数: {timeout_count}")
    print(
        f"  样本测试: 总计={total_tests}, 通过={total_passed}, 失败={total_failed}, 错误={total_errors}, 跳过={total_skipped}"
    )

    # 评估结果
    if timeout_count == 0:
        print("\n✅ Phase 3 目标基本达成：没有测试超时")
        print("\n建议：")
        print("  - 检查失败的测试并修复")
        print("  - 检查错误的测试并修复")
        print("  - 大部分测试现在能够快速运行")
        return True
    else:
        print(f"\n⚠️  Phase 3 需要继续优化：{timeout_count} 个测试超时")
        print("\n建议：")
        print("  - 进一步 Mock 外部依赖")
        print("  - 优化测试性能")
        print("  - 跳过慢速测试或并行执行")
        return False


if __name__ == "__main__":
    success = main()
    print("\n" + "=" * 60)
    if success:
        print("Phase 3 已基本完成！")
    else:
        print("Phase 3 需要继续优化。")
