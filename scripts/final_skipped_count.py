#!/usr/bin/env python3
"""
最终的 skipped 测试统计
"""

import subprocess
import os


def main():
    """统计 skipped 测试"""
    print("=" * 80)
    print("📊 Phase 6.2 最终统计")
    print("=" * 80)

    env = os.environ.copy()
    env["PYTHONPATH"] = "tests:src"
    env["TESTING"] = "true"

    # 运行测试
    cmd = [
        "pytest",
        "tests/unit/api/test_health.py",
        "tests/unit/services/test_audit_service.py",
        "tests/unit/core/test_di.py",
        "-v",
        "--disable-warnings",
        "--tb=no",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
    output = result.stdout + result.stderr

    # 统计
    passed = output.count("PASSED")
    failed = output.count("FAILED")
    errors = output.count("ERROR")
    skipped = output.count("SKIPPED")

    print("\n📈 测试结果统计:")
    print(f"  ✓ 通过: {passed}")
    print(f"  ❌ 失败: {failed}")
    print(f"  💥 错误: {errors}")
    print(f"  ⏭️  跳过: {skipped}")

    print("\n📋 Phase 6.2 总结:")
    print("  初始 skipped 测试: 18 个")
    print(f"  最终 skipped 测试: {skipped} 个")
    print(f"  减少数量: {18 - skipped} 个")

    if skipped <= 10:
        print("\n✅ 成功达成目标！")
        print(f"   skipped 测试已减少到 {skipped} 个（目标 < 10）")
    else:
        print("\n⚠️  接近目标，但还需要继续努力")
        print(f"   还需要减少 {skipped - 10} 个测试")

    print("\n🎯 剩余 skipped 测试分布:")
    if "SKIPPED" in output:
        for line in output.split("\n"):
            if "SKIPPED" in line and "::" in line:
                print(f"  - {line.strip()}")

    print("\n📄 建议:")
    print("  1. 为需要外部依赖的测试添加 mock fixtures")
    print("  2. 修复 DI 循环依赖测试")
    print("  3. 继续优化不必要的 skipif 条件")


if __name__ == "__main__":
    main()
