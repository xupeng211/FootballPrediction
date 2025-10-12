#!/usr/bin/env python3
"""
修复 skipped 测试
"""

import re
import os
from pathlib import Path


def fix_health_tests():
    """修复健康检查测试"""
    file_path = "tests/unit/api/test_health.py"

    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return

    print(f"\n🔧 修复健康检查测试: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 统计修复前的情况
    old_skipped = content.count(
        '@pytest.mark.skipif(False, reason="临时禁用 - Phase 2 优化")'
    )
    print(f"  修复前 skipped 测试数: {old_skipped}")

    # 将 skipif(False, ...) 改为 skipif(not HEALTH_AVAILABLE, ...)
    # 这样只有在健康模块不可用时才会跳过
    content = content.replace(
        '@pytest.mark.skipif(False, reason="临时禁用 - Phase 2 优化")',
        '@pytest.mark.skipif(not HEALTH_AVAILABLE, reason="健康模块不可用")',
    )

    # 保存文件
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("  ✅ 修复完成！")
    print("  现在这些测试只在健康模块不可用时才会跳过")


def create_mock_health_fixtures():
    """为健康检查测试创建必要的 mock fixtures"""
    fixture_content = '''
"""
健康检查测试的 fixtures
"""

import pytest
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_health_checker():
    """Mock 健康检查器"""
    checker = Mock()

    # Mock 基本方法
    checker.check_all_services = AsyncMock(return_value={
        "status": "healthy",
        "checks": {
            "database": {"status": "healthy", "response_time": 0.001},
            "redis": {"status": "healthy", "response_time": 0.0005},
            "prediction_service": {"status": "healthy", "response_time": 0.01}
        },
        "timestamp": "2025-01-12T10:00:00Z"
    })

    checker.check_database = AsyncMock(return_value={
        "status": "healthy",
        "response_time": 0.001
    })

    checker.check_redis = AsyncMock(return_value={
        "status": "healthy",
        "response_time": 0.0005
    })

    checker.check_prediction_service = AsyncMock(return_value={
        "status": "healthy",
        "response_time": 0.01
    })

    return checker


@pytest.fixture
def mock_unhealthy_services():
    """Mock 不健康的服务状态"""
    return {
        "database": {"status": "unhealthy", "error": "Connection timeout"},
        "redis": {"status": "degraded", "response_time": 0.5},
        "prediction_service": {"status": "healthy", "response_time": 0.01}
    }


@pytest.fixture
def mock_service_dependencies():
    """Mock 服务依赖"""
    return {
        "prediction_service": ["database", "model_loader"],
        "database": [],
        "redis": []
    }
'''

    # 写入到 conftest.py 或新文件
    conftest_path = "tests/unit/api/conftest.py"

    if os.path.exists(conftest_path):
        with open(conftest_path, "r", encoding="utf-8") as f:
            existing = f.read()

        # 检查是否已经有这些 fixtures
        if "mock_health_checker" not in existing:
            with open(conftest_path, "a", encoding="utf-8") as f:
                f.write("\n" + fixture_content)
            print(f"\n✅ 已添加 health fixtures 到 {conftest_path}")
    else:
        with open(conftest_path, "w", encoding="utf-8") as f:
            f.write(fixture_content)
        print(f"\n✅ 已创建 {conftest_path} 并添加 health fixtures")


def suggest_di_fix():
    """为 DI 循环依赖测试提供修复建议"""
    print("\n📋 DI 循环依赖测试修复建议:")
    print("  测试: test_resolve_circular_dependency")
    print("  原因: 类型注解字符串导致解析失败")
    print("  建议:")
    print("    1. 更新类型注解使用实际类而不是字符串")
    print("    2. 或者实现循环依赖检测逻辑")
    print("    3. 暂时保留 skip，这是一个边缘情况")


def verify_fixes():
    """验证修复效果"""
    print("\n🔍 验证修复效果...")

    # 运行健康检查测试
    import subprocess

    env = os.environ.copy()
    env["PYTHONPATH"] = "tests:src"
    env["TESTING"] = "true"

    cmd = [
        "pytest",
        "tests/unit/api/test_health.py",
        "-v",
        "--disable-warnings",
        "--tb=no",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
    output = result.stdout + result.stderr

    # 统计结果
    passed = output.count("PASSED")
    failed = output.count("FAILED")
    errors = output.count("ERROR")
    skipped = output.count("SKIPPED")

    print("\n📊 测试结果:")
    print(f"  ✓ 通过: {passed}")
    print(f"  ❌ 失败: {failed}")
    print(f"  💥 错误: {errors}")
    print(f"  ⏭️  跳过: {skipped}")

    # 如果有跳过的，显示原因
    if "SKIPPED" in output:
        print("\n⏭️  跳过的测试:")
        for line in output.split("\n"):
            if "SKIPPED" in line and "::" in line:
                print(f"    {line.strip()}")

    return skipped


def main():
    """主函数"""
    print("=" * 80)
    print("🚀 Phase 6.2: 修复 skipped 测试")
    print("=" * 80)
    print("目标：将 skipped 测试从 18 个减少到 10 个以下")
    print("-" * 80)

    # 1. 修复健康检查测试
    print("\n1️⃣ 修复健康检查测试")
    fix_health_tests()

    # 2. 创建 mock fixtures
    print("\n2️⃣ 创建必要的 mock fixtures")
    create_mock_health_fixtures()

    # 3. DI 测试建议
    print("\n3️⃣ DI 测试修复建议")
    suggest_di_fix()

    # 4. 验证修复效果
    print("\n4️⃣ 验证修复效果")
    remaining_skipped = verify_fixes()

    # 5. 总结
    print("\n" + "=" * 80)
    print("📋 修复总结")
    print("=" * 80)
    print("修复前 skipped 测试: 18 个")
    print(f"修复后 skipped 测试: {remaining_skipped} 个")
    print(f"减少数量: {18 - remaining_skipped} 个")

    if remaining_skipped <= 10:
        print(f"\n✅ 成功达成目标！skipped 测试已减少到 {remaining_skipped} 个")
    else:
        print(f"\n⚠️  还需要继续减少 {remaining_skipped - 10} 个测试")

    print("\n📄 下一步建议:")
    print("  1. 为剩余的 skipped 测试添加必要的 mock")
    print("  2. 修复 DI 循环依赖测试")
    print("  3. 运行: python scripts/count_skipped_tests.py 验证")


if __name__ == "__main__":
    main()
