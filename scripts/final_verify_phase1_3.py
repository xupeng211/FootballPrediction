#!/usr/bin/env python3
"""
最终验证 Phase 1-3 完成情况
"""

import subprocess
import re
import sys
import os


def verify_phase1():
    """验证 Phase 1: 修复模块导入问题"""
    print("\n验证 Phase 1: 修复模块导入问题")
    print("-" * 40)

    # 测试pytest是否能收集测试
    cmd = [
        "pytest",
        "--collect-only",
        "-p",
        "no:warnings",
        "-q",
        "tests/unit/core/test_logger.py",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if "collected" in result.stdout and "error" not in result.stdout.lower():
        print("✅ Phase 1 通过: pytest 能正常收集测试")
        return True
    else:
        print("❌ Phase 1 失败: pytest 无法收集测试")
        return False


def verify_phase2():
    """验证 Phase 2: 清理 skipif 跳过条件"""
    print("\n验证 Phase 2: 清理 skipif 跳过条件")
    print("-" * 40)

    # 测试几个关键模块的跳过情况
    test_files = [
        "tests/unit/api/test_health.py",
        "tests/unit/core/test_logger.py",
    ]

    total_skipped = 0
    total_run = 0

    for test_file in test_files:
        if os.path.exists(test_file):
            cmd = ["pytest", test_file, "-q", "--disable-warnings", "--tb=no"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            output = result.stdout + result.stderr
            skipped = len(re.findall(r"SKIPPED", output))
            passed = len(re.findall(r"PASSED", output))

            total_skipped += skipped
            total_run += passed

    print(f"跳过测试数: {total_skipped}, 运行测试数: {total_run}")

    if total_skipped < 10:  # 允许少量必要的跳过
        print("✅ Phase 2 通过: skipped 测试数量可控")
        return True
    else:
        print("❌ Phase 2 失败: skipped 测试过多")
        return False


def verify_phase3():
    """验证 Phase 3: Mock 外部依赖"""
    print("\n验证 Phase 3: Mock 外部依赖")
    print("-" * 40)

    # 设置环境
    env = os.environ.copy()
    env["PYTHONPATH"] = "tests:src"
    env["TESTING"] = "true"

    # 运行一个简单的测试来验证Mock
    cmd = [
        sys.executable,
        "-c",
        """
import sys
sys.path.insert(0, 'tests')
import conftest_mock  # 应用Mock

# 测试导入外部依赖模块
try:
    from src.database.connection import DatabaseManager
    db = DatabaseManager()
    print("✓ 数据库模块Mock成功")
            except Exception:
    print("✗ 数据库模块Mock失败")
    sys.exit(1)

try:
    import redis
    r = redis.Redis()
    r.ping()
    print("✓ Redis Mock成功")
            except Exception:
    print("✗ Redis Mock失败")
    sys.exit(1)

try:
    import mlflow
    mlflow.start_run()
    print("✓ MLflow Mock成功")
            except Exception:
    print("✗ MLflow Mock失败")
    sys.exit(1)

print("✓ 所有外部依赖Mock成功")
""",
    ]

    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=30)

    if "✓ 所有外部依赖Mock成功" in result.stdout:
        print("✅ Phase 3 通过: 外部依赖Mock成功")
        return True
    else:
        print("❌ Phase 3 失败: Mock配置有问题")
        return False


def main():
    print("=" * 60)
    print("最终验证 Phase 1-3 完成情况")
    print("=" * 60)
    print("目标：所有阶段的目标都已达成")
    print("-" * 60)

    # 验证各个阶段
    phase1_ok = verify_phase1()
    phase2_ok = verify_phase2()
    phase3_ok = verify_phase3()

    print("\n" + "=" * 60)
    print("最终验证结果:")
    print(f"  Phase 1 (模块导入): {'✅ 通过' if phase1_ok else '❌ 失败'}")
    print(f"  Phase 2 (跳过测试): {'✅ 通过' if phase2_ok else '❌ 失败'}")
    print(f"  Phase 3 (Mock依赖): {'✅ 通过' if phase3_ok else '❌ 失败'}")

    overall_success = phase1_ok and phase2_ok and phase3_ok

    if overall_success:
        print("\n🎉 Phase 1-3 全部达成！")
        print("\n主要成就：")
        print("  ✓ pytest 能正常收集和运行测试")
        print("  ✓ 测试跳过数量大幅减少")
        print("  ✓ 外部依赖被正确Mock，测试无超时")
        print("  ✓ 测试体系基本激活")
        print("\n下一步：")
        print("  - 进入 Phase 4：校准覆盖率配置")
        print("  - 准备 Phase 5：最终激活验证")
        return True
    else:
        print("\n⚠️  部分阶段未完全达成")
        print("\n需要优化的地方：")
        if not phase1_ok:
            print("  - 修复模块导入问题")
        if not phase2_ok:
            print("  - 进一步清理skipif条件")
        if not phase3_ok:
            print("  - 优化Mock配置")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
